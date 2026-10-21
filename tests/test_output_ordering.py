#!/usr/bin/env python3
"""
Tests that generated output order is stable and dependency-aware.

Parse/import order must not influence the generated code, otherwise reorganising
or splitting schema files churns every generated file.  The generator therefore
emits packages dependency-first, enums by name and messages dependencies-first
(then by name).  Order that is part of the schema itself -- message fields,
oneof variants (``field_order`` discriminators) and enum entries -- is left
untouched.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from test_utils import _check, run_generator

ALL_LANGS = ["c", "cpp", "ts", "js", "py", "gql", "csharp", "rust"]
IGNORED = {".structframe.hash", "sf_compile.json"}


def _generate_all(workdir: Path, main_file: str, files: dict[str, str]) -> dict[str, str]:
    """Write *files*, generate every language from *main_file*; return {relpath: text}."""
    src = workdir / "src"
    out = workdir / "out"
    src.mkdir()
    for name, text in files.items():
        (src / name).write_text(text, encoding="utf-8")
    flags = ["--force"]
    for lang in ALL_LANGS:
        flags += [f"--build_{lang}", f"--{lang}_path", str(out / lang) + os.sep]
    flags += ["--catalog_path", str(out / "catalog") + os.sep]
    result = run_generator(src / main_file, *flags)
    _check(result.returncode == 0, f"Generation failed:\n{result.stdout}\n{result.stderr}")
    generated = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name not in IGNORED:
            generated[path.relative_to(out).as_posix()] = path.read_text(encoding="utf-8", errors="replace")
    return generated


def _assert_same_output(a: dict[str, str], b: dict[str, str], what: str):
    _check(set(a) == set(b), f"{what}: generated file sets differ: {sorted(set(a) ^ set(b))}")
    for name in sorted(a):
        _check(a[name] == b[name], f"{what}: generated file {name} differs")


MESSAGES_A = """
// Counts apples
message Apple {
  option msgid = 1;
  uint8 count = 1;
}
"""
MESSAGES_B = """
message Banana {
  option msgid = 2;
  Apple apple = 1;
  uint16 ripeness = 2;
}
"""
MESSAGES_C = """
message Cherry {
  option msgid = 3;
  uint32 pits = 1;
  Banana banana = 2;
}
"""
ENUMS = """
enum Zone {
  ZETA = 0;
  ALPHA = 1;
}
enum Color {
  RED = 0;
  BLUE = 1;
}
"""


def _single(*blocks: str) -> str:
    return "package order_test;\n" + "".join(blocks)


def test_declaration_order_does_not_affect_output():
    """Declaring the same messages/enums in a different order yields identical output."""
    with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
        a = _generate_all(Path(t1), "schema.sf", {
            "schema.sf": _single(ENUMS, MESSAGES_A, MESSAGES_B, MESSAGES_C)})
        b = _generate_all(Path(t2), "schema.sf", {
            "schema.sf": _single(MESSAGES_C, MESSAGES_B, ENUMS, MESSAGES_A)})
    _assert_same_output(a, b, "reordered declarations")


def test_file_split_does_not_affect_output():
    """Splitting declarations over files / changing import order only changes
    the schema catalog's ``source_file`` fields, never the generated code."""
    with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2, \
            tempfile.TemporaryDirectory() as t3:
        single = _generate_all(Path(t1), "schema.sf", {
            "schema.sf": _single(ENUMS, MESSAGES_A, MESSAGES_B, MESSAGES_C)})
        split = _generate_all(Path(t2), "main.sf", {
            "base.sf": _single(MESSAGES_A, ENUMS),
            "mid.sf": 'import "base.sf";\n' + _single(MESSAGES_B),
            "main.sf": 'import "mid.sf";\n' + _single(MESSAGES_C),
        })
        split_swapped = _generate_all(Path(t3), "main.sf", {
            "base.sf": _single(ENUMS),
            "apple.sf": _single(MESSAGES_A),
            "mid.sf": 'import "base.sf";\nimport "apple.sf";\n' + _single(MESSAGES_B),
            "main.sf": 'import "mid.sf";\n' + _single(MESSAGES_C),
        })
    _assert_same_output(single, split, "split across files")
    _assert_same_output(split, split_swapped, "different file split")


def test_package_import_order_does_not_affect_output():
    """The order of ``import`` statements does not change per-package output."""
    common = "package common;\noption pkgid = 1;\nmessage Stamp {\n  option msgid = 1;\n  uint32 t = 1;\n}\n"
    sensors = "package sensors;\noption pkgid = 2;\nmessage Reading {\n  option msgid = 1;\n  uint32 v = 1;\n}\n"
    app_body = ("package app;\noption pkgid = 3;\nmessage Report {\n  option msgid = 1;\n"
                "  common.Stamp stamp = 1;\n  sensors.Reading reading = 2;\n}\n")
    files = {"common.sf": common, "sensors.sf": sensors}
    with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
        a = _generate_all(Path(t1), "app.sf", {
            **files, "app.sf": 'import "common.sf";\nimport "sensors.sf";\n' + app_body})
        b = _generate_all(Path(t2), "app.sf", {
            **files, "app.sf": 'import "sensors.sf";\nimport "common.sf";\n' + app_body})
    _assert_same_output(a, b, "swapped imports")


def _py_class_order(generated: dict[str, str]) -> list[str]:
    text = next(v for k, v in generated.items() if k.endswith("order_test.py"))
    return re.findall(r"^class (\w+)(?:\(Enum\))?:", text, re.MULTILINE)


def test_dependencies_precede_dependants_then_name_order():
    """A message that embeds another follows it; unrelated messages are sorted by name."""
    with tempfile.TemporaryDirectory() as tmp:
        generated = _generate_all(Path(tmp), "schema.sf", {
            "schema.sf": _single(MESSAGES_C, MESSAGES_B, MESSAGES_A,
                                 "message Aardvark {\n  option msgid = 9;\n  uint8 x = 1;\n}\n")})
    order = _py_class_order(generated)
    messages = [n for n in order if n in ("Apple", "Banana", "Cherry", "Aardvark")]
    _check(messages == ["Aardvark", "Apple", "Banana", "Cherry"],
           f"Messages should be dependency-ordered then alphabetical, got {messages}")
    _check(order.index("Apple") < order.index("Banana") < order.index("Cherry"),
           f"Dependencies must precede dependants, got {order}")


def test_enums_sorted_by_name_entries_keep_declaration_order():
    with tempfile.TemporaryDirectory() as tmp:
        generated = _generate_all(Path(tmp), "schema.sf", {"schema.sf": _single(ENUMS, MESSAGES_A)})
    text = next(v for k, v in generated.items() if k.endswith("order_test.py"))
    _check(text.index("class Color") < text.index("class Zone"), "Enums should be sorted by name")
    zone = text[text.index("class Zone"):]
    _check(zone.index("ZETA") < zone.index("ALPHA"),
           "Enum entries keep declaration order (not alphabetical)")


ONEOF_MESSAGE = """
message Holder {
  option msgid = 5;
  uint8 zeta = 1;
  uint8 alpha = 2;
  oneof payload {
    uint8 yankee = 1;
    uint16 alpha_v = 2;
    uint32 mike = 3;
  }
}
"""


def test_oneof_variant_and_field_order_preserved():
    """Normalising output order must never reorder oneof variants or fields."""
    with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
        a = _generate_all(Path(t1), "schema.sf", {"schema.sf": _single(ONEOF_MESSAGE, MESSAGES_A)})
        b = _generate_all(Path(t2), "schema.sf", {"schema.sf": _single(MESSAGES_A, ONEOF_MESSAGE)})
    _assert_same_output(a, b, "oneof message position")
    text = next(v for k, v in a.items() if k.endswith("order_test.py"))
    discriminator = text[text.index("class HolderPayloadField"):]
    discriminator = discriminator[:discriminator.index("\n\n")]
    values = re.findall(r"^\s+(\w+) = (\d+)", discriminator, re.MULTILINE)
    _check(values == [("NONE", "0"), ("YANKEE", "1"), ("ALPHA_V", "2"), ("MIKE", "3")],
           f"Oneof variants must keep declaration order, got {values}")
    holder = text[text.index("class Holder:"):]
    _check(holder.index("zeta") < holder.index("alpha"),
           "Message fields must keep declaration order")
