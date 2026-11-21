#!/usr/bin/env python3
"""The per-package ``WIRE_HASH`` constant: a fingerprint of the base wire contract.

Heartbeats carry it so a node can tell that a peer was built from another schema. It must
stay the same for every change that keeps two builds interoperable (renames, comments,
extension fields) and change for every change that breaks the wire.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from test_utils import SRC_DIR

BASE = """\
package fleet @3;

message Status @1 {
  uint32 uptime;
  float temperature;
}

message Command @2 [variable] {
  uint8 code;
  string<16> note;
}

struct Point {
  int16 x;
  int16 y;
}
"""


def _parse(text: str, tmp_path: Path):
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
    from struct_frame import generate as gen
    schema = tmp_path / f"s{abs(hash(text))}.sf"
    schema.write_text(text, encoding="utf-8")
    gen.reset_parse_state()
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            ok = gen.parseFile(str(schema)) and gen.validate_packages()
        return gen, (dict(gen.packages) if ok else None), out.getvalue()
    finally:
        gen.reset_parse_state()


def _hash(text: str, tmp_path: Path) -> int:
    gen, packages, log = _parse(text, tmp_path)
    assert packages is not None, log
    (pkg,) = packages.values()
    return gen.compute_wire_hash(pkg)


def _spec_hash(pkg_id: int, messages) -> int:
    """FNV-1a-32 over the package id and, per message in effective-id order, the
    effective id (u16), magic1, magic2, base size (u32), minimum size (u32) and the
    variable flag (u8), all little-endian (conformance section 9.4)."""
    data = bytes([pkg_id])
    for eff_id, m1, m2, base, min_size, variable in sorted(messages):
        data += struct.pack("<HBBIIB", eff_id, m1, m2, base, min_size, variable)
    h = 0x811C9DC5
    for b in data:
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def test_hash_follows_the_specified_algorithm(tmp_path):
    gen, packages, log = _parse(BASE, tmp_path)
    assert packages is not None, log
    pkg = packages["fleet"]
    rows = []
    for msg in pkg.messages.values():
        if msg.id is None:
            continue
        min_size = msg.min_size if msg.variable else msg.base_size
        rows.append(((3 << 8) | msg.id, msg.magic_bytes[0], msg.magic_bytes[1], msg.base_size, min_size,
                     int(msg.variable)))
    assert len(rows) == 2   # the struct has no id and is not part of the contract
    assert gen.compute_wire_hash(pkg) == _spec_hash(3, rows)


@pytest.mark.parametrize("label, edit", [
    ("rename a field", lambda s: s.replace("uint32 uptime;", "uint32 uptime_ms;")),
    ("rename a message", lambda s: s.replace("message Status @1", "message Health @1")),
    ("add a doc comment", lambda s: s.replace("message Status @1", "/// Health.\nmessage Status @1")),
    ("add an extension field", lambda s: s.replace("  float temperature;\n}",
                                                    "  float temperature;\n  extensions {\n    uint8 mode;\n  }\n}")),
    ("change an id-less struct", lambda s: s.replace("int16 y;", "int16 y;\n  int16 z;")),
    ("add a constant", lambda s: s.replace("package fleet @3;", "package fleet @3;\nconst uint8 N = 4;")),
])
def test_compatible_changes_keep_the_hash(tmp_path, label, edit):
    assert _hash(edit(BASE), tmp_path) == _hash(BASE, tmp_path), label


@pytest.mark.parametrize("label, edit", [
    ("change a field type", lambda s: s.replace("float temperature;", "double temperature;")),
    ("add a base field", lambda s: s.replace("float temperature;", "float temperature;\n  uint8 extra;")),
    ("reorder base fields", lambda s: s.replace("  uint32 uptime;\n  float temperature;",
                                                 "  float temperature;\n  uint32 uptime;")),
    ("change a message id", lambda s: s.replace("message Status @1", "message Status @5")),
    ("change the package id", lambda s: s.replace("package fleet @3;", "package fleet @4;")),
    ("drop the variable flag", lambda s: s.replace("message Command @2 [variable]", "message Command @2")),
    ("change a bound", lambda s: s.replace("string<16> note;", "string<32> note;")),
    ("add a message", lambda s: s + "\nmessage Extra @9 {\n  uint8 x;\n}\n"),
])
def test_breaking_changes_change_the_hash(tmp_path, label, edit):
    assert _hash(edit(BASE), tmp_path) != _hash(BASE, tmp_path), label


def test_builtin_schema_hash_is_pinned():
    """Changing the algorithm (or sf_system.sf's wire contract) must be deliberate: peers
    compare these values. Update together with conformance section 9.4."""
    py = (SRC_DIR / "struct_frame" / "boilerplate" / "py" / "sf_system.py").read_text(encoding="utf-8")
    assert re.search(r"^WIRE_HASH = (\d+)$", py, re.M).group(1) == "2865079104"


def test_every_language_emits_the_same_value(tmp_path):
    schema = tmp_path / "fleet.sf"
    schema.write_text(BASE, encoding="utf-8")
    out = tmp_path / "out"
    run = subprocess.run([sys.executable, "-m", "struct_frame", str(schema), "--lang", "all", "--out", str(out),
                          "--force"], capture_output=True, text=True,
                         env={**os.environ, "PYTHONPATH": str(SRC_DIR)})
    assert run.returncode == 0, run.stdout + run.stderr
    want = str(_hash(BASE, tmp_path))
    files = {
        "c": (out / "c" / "fleet.structframe.h", r"#define FLEET_WIRE_HASH \(\(uint32_t\)(\d+)u\)"),
        "cpp": (out / "cpp" / "fleet.structframe.hpp", r"constexpr uint32_t WIRE_HASH = (\d+)u;"),
        "py": (out / "py" / "structframe" / "fleet.py", r"^WIRE_HASH = (\d+)$"),
        "ts": (out / "ts" / "fleet.structframe.ts", r"export const WIRE_HASH: number = (\d+);"),
        "js": (out / "js" / "fleet.structframe.js", r"const WIRE_HASH = (\d+);"),
        "csharp": (out / "csharp" / "Fleet" / "Constants.cs", r"public const uint WIRE_HASH = (\d+)U;"),
        "rust": (out / "rust" / "fleet.structframe.rs", r"pub const WIRE_HASH: u32 = (\d+);"),
    }
    for lang, (path, pattern) in files.items():
        m = re.search(pattern, path.read_text(encoding="utf-8"), re.M)
        assert m and m.group(1) == want, f"{lang}: {path.name} lacks WIRE_HASH = {want}"


def test_wire_hash_is_a_reserved_constant_name(tmp_path):
    _gen, packages, log = _parse(BASE.replace("package fleet @3;", "package fleet @3;\nconst uint32 WIRE_HASH = 1;"),
                                 tmp_path)
    assert packages is None
    assert "WIRE_HASH" in log and "reserved" in log
