#!/usr/bin/env python3
"""Regression tests for generator front-end bugs found in the Oct 2026 review.

Every test here asserts the *correct* behaviour. Tests covering bugs that are
still open are expected to FAIL until the bug is fixed; a failure is the
signal that the bug is still present. Where several fixes are acceptable
(e.g. "reject at generate time" vs "reject at write time") the test accepts
any of them. Each docstring names the review item it pins down (see
``memory/project-full-review-oct2026.md`` / the review plan, section numbers
B*, G*, R*, T*).

Run with ``pytest tests/test_generator_regressions.py``.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from test_utils import REPO_ROOT, SRC_DIR, load_generated_module, run_generator


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def write(tmp: Path, name: str, text: str) -> Path:
    path = tmp / name
    path.write_text(text, encoding="utf-8")
    return path


def gen(tmp: Path, main: Path, *flags: str) -> subprocess.CompletedProcess:
    return run_generator(main, *flags)


def validate(main: Path, *flags: str) -> subprocess.CompletedProcess:
    return run_generator(main, "--validate", *flags)


def out(r: subprocess.CompletedProcess) -> str:
    return (r.stdout or "") + "\n" + (r.stderr or "")


def no_traceback(r: subprocess.CompletedProcess) -> bool:
    return "Traceback" not in out(r)


def read_all(directory: Path, pattern: str) -> str:
    return "\n".join(p.read_text(encoding="utf-8", errors="replace")
                     for p in sorted(directory.rglob(pattern)))


# ---------------------------------------------------------------------------
# #2  parse failures must not exit 0
# ---------------------------------------------------------------------------

def test_missing_schema_file_fails(tmp_path):
    r = gen(tmp_path, tmp_path / "does_not_exist.sf",
            "--build_py", "--py_path", str(tmp_path / "o"))
    assert r.returncode != 0, out(r)
    assert "successfully completed" not in out(r).lower()
    assert not (tmp_path / "o").exists(), "boilerplate written despite failure"


def test_syntax_error_fails(tmp_path):
    sf = write(tmp_path, "bad.sf",
               "package bad;\nmessage A {\n  option msgid = 1;\n  uint8 x = 1\n}\n")
    r = gen(tmp_path, sf, "--build_py", "--py_path", str(tmp_path / "o"))
    assert r.returncode != 0, out(r)
    assert "successfully completed" not in out(r).lower()


@pytest.mark.parametrize("body,label", [
    ("message A { option msgid = 1; uint8 x = 1; }\n"
     "message A { option msgid = 2; uint8 y = 1; }\n", "duplicate message"),
    ("message A { option msgid = 1; uint8 x = 1; uint16 x = 2; }\n",
     "duplicate field"),
    ("enum E { A = 0; }\nenum E { B = 0; }\n"
     "message M { option msgid = 1; uint8 x = 1; }\n", "duplicate enum"),
    ("message M { option msgid = 1; uint8 x = 1; oneof o { uint8 a = 1; }"
     " oneof o { uint8 b = 1; } }\n", "duplicate oneof"),
])
def test_redeclarations_are_validation_errors(tmp_path, body, label):
    sf = write(tmp_path, "dup.sf", "package dup;\n" + body)
    r = validate(sf)
    assert r.returncode != 0, f"{label}: {out(r)}"
    assert "validation successful" not in out(r).lower()


# ---------------------------------------------------------------------------
# #3  message ids that do not fit the wire id byte
# ---------------------------------------------------------------------------

def test_msgid_above_255_never_silently_truncated(tmp_path):
    """Accept either: rejected at generate time, or rejected when encoding with
    a profile that only has a 1-byte message id."""
    sf = write(tmp_path, "big.sf",
               "package big;\nmessage M { option msgid = 300; uint8 x = 1; }\n")
    o = tmp_path / "py"
    r = gen(tmp_path, sf, "--build_py", "--py_path", str(o))
    if r.returncode != 0:
        return  # rejected at generate time: fine
    mod = load_generated_module(o / "struct_frame" / "generated" / "big.py", "big_msgid")
    frames = load_generated_module(o / "frame_profiles.py", "big_frame_profiles")
    msg = mod.M()
    try:
        frame = frames.encode_message(frames.PROFILE_STANDARD_CONFIG, msg)
    except (ValueError, OverflowError):
        return  # rejected at write time: fine
    # Standard frame: [0x90][0x71][LEN][MSG_ID][payload][CRC1][CRC2]
    assert frame[3] != 300 & 0xFF, "msgid 300 was silently truncated to 44 on the wire"


# ---------------------------------------------------------------------------
# #4  reserved words
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("word", ["class", "self", "fn", "delete", "def", "None"])
def test_reserved_word_field_is_rejected_or_escaped_in_python(tmp_path, word):
    sf = write(tmp_path, "kw.sf",
               f"package kw;\nmessage M {{ option msgid = 1; uint8 {word} = 1; }}\n")
    o = tmp_path / "py"
    r = gen(tmp_path, sf, "--build_py", "--py_path", str(o))
    if r.returncode != 0:
        assert no_traceback(r)
        return
    src = (o / "struct_frame" / "generated" / "kw.py").read_text(encoding="utf-8")
    compile(src, "kw.py", "exec")  # must at least be valid Python


def test_reserved_word_rejected_for_c_family(tmp_path):
    """A C header with a member called ``class`` cannot be included from C++."""
    sf = write(tmp_path, "kw.sf",
               "package kw;\nmessage M { option msgid = 1; uint8 class = 1; }\n")
    r = gen(tmp_path, sf, "--build_c", "--c_path", str(tmp_path / "c"))
    if r.returncode != 0:
        return
    hdr = read_all(tmp_path / "c", "kw.structframe.h")
    assert not re.search(r"\buint8_t\s+class\s*;", hdr), \
        "C header declares a member named 'class' (breaks C++ includers)"


def test_validate_runs_name_validation_without_build_flags(tmp_path):
    """--validate must report the same name collisions generation would."""
    sf = write(tmp_path, "col.sf",
               "package col;\nmessage M { option msgid = 1; uint8 fooBar = 1; uint8 foo_bar = 2; }\n")
    gen_r = gen(tmp_path, sf, "--build_csharp", "--csharp_path", str(tmp_path / "cs"), "--force")
    assert gen_r.returncode != 0, "premise: C# generation rejects this schema"
    assert validate(sf).returncode != 0, \
        "--validate without --build_* accepted a schema that generation rejects"


# ---------------------------------------------------------------------------
# #5  enums
# ---------------------------------------------------------------------------

def test_enum_value_out_of_storage_range_rejected(tmp_path):
    sf = write(tmp_path, "en.sf",
               "package en;\nenum E { A = 0; C = 300; }\n"
               "message M { option msgid = 1; E e = 1; }\n")
    assert validate(sf).returncode != 0


def test_negative_enum_value_rejected(tmp_path):
    sf = write(tmp_path, "en.sf",
               "package en;\nenum E { A = 0; D = -5; }\n"
               "message M { option msgid = 1; E e = 1; }\n")
    assert validate(sf).returncode != 0


def test_duplicate_enum_values_rejected(tmp_path):
    sf = write(tmp_path, "en.sf",
               "package en;\nenum E { A = 0; B = 0; }\n"
               "message M { option msgid = 1; E e = 1; }\n")
    assert validate(sf).returncode != 0


# ---------------------------------------------------------------------------
# crashes -> clean errors
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("decl,label", [
    ("float f = 1 [default = 1e40];", "float32 overflow default"),
    ("E e = 1 [default = Big];", "enum default outside 0..255"),
])
def test_bad_defaults_give_clean_error_not_traceback(tmp_path, decl, label):
    sf = write(tmp_path, "d.sf",
               "package d;\nenum E { Zero = 0; Big = 300; }\n"
               f"message M {{ option msgid = 1; {decl} }}\n")
    r = validate(sf)
    assert no_traceback(r), f"{label}: {out(r)}"
    assert r.returncode != 0, label


@pytest.mark.parametrize("opt", ['msgid = "5"', "msgid = 1.5"])
def test_non_integer_msgid_is_clean_error(tmp_path, opt):
    sf = write(tmp_path, "d.sf", f"package d;\nmessage M {{ option {opt}; uint8 x = 1; }}\n")
    r = validate(sf)
    assert no_traceback(r), out(r)
    assert r.returncode != 0, out(r)


def test_non_integer_pkgid_is_clean_error(tmp_path):
    sf = write(tmp_path, "d.sf",
               'package d;\noption pkgid = "5";\nmessage M { option msgid = 1; uint8 x = 1; }\n')
    r = validate(sf)
    assert no_traceback(r), out(r)
    assert r.returncode != 0


def test_msgid_redefinition_rejected(tmp_path):
    sf = write(tmp_path, "d.sf",
               "package d;\nmessage M { option msgid = 0; option msgid = 7; uint8 x = 1; }\n")
    assert validate(sf).returncode != 0


# ---------------------------------------------------------------------------
# B7  unknown options
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("decl", [
    "uint8 x = 1 [defualt = 5];",
    "repeated uint8 x = 1 [size = 4, max_sise = 4];",
])
def test_unknown_field_option_rejected(tmp_path, decl):
    sf = write(tmp_path, "o.sf", f"package o;\nmessage M {{ option msgid = 1; {decl} }}\n")
    assert validate(sf).returncode != 0


def test_unknown_message_option_rejected(tmp_path):
    sf = write(tmp_path, "o.sf", "package o;\nmessage M { option msg_id = 1; uint8 x = 1; }\n")
    assert validate(sf).returncode != 0


# ---------------------------------------------------------------------------
# #1 / #6  cross-package type resolution
# ---------------------------------------------------------------------------

def _two_pkg_with_clashing_inner(tmp: Path) -> Path:
    write(tmp, "b3.sf",
          "package pb;\noption pkgid = 2;\n"
          "message Inner { uint64 a = 1; uint64 b = 2; }\n"
          "message Outer { option msgid = 1; Inner x = 1; }\n")
    return write(tmp, "a3.sf",
                 "package pa;\noption pkgid = 1;\nimport \"b3.sf\";\n"
                 "message Inner { uint8 z = 1; }\n"
                 "message Use { option msgid = 1; pb.Outer o = 1; }\n")


def test_imported_type_resolves_in_owning_package(tmp_path):
    a = _two_pkg_with_clashing_inner(tmp_path)
    o = tmp_path / "c"
    r = gen(tmp_path, a, "--build_c", "--c_path", str(o))
    assert r.returncode == 0, out(r)
    pb = (o / "pb.structframe.h").read_text(encoding="utf-8")
    m = re.search(r"#define\s+PB_OUTER_MAX_SIZE\s+(\d+)", pb)
    assert m, "PB_OUTER_MAX_SIZE missing"
    assert m.group(1) == "16", f"pb.Outer sized {m.group(1)}: Inner resolved in the wrong package"
    assert "PaInner x" not in pb


def test_ambiguous_unqualified_type_is_rejected(tmp_path):
    write(tmp_path, "pa.sf", "package pa;\noption pkgid = 1;\nmessage Pos { uint8 x = 1; }\n")
    write(tmp_path, "pb.sf",
          "package pb;\noption pkgid = 2;\nmessage Pos { uint32 x = 1; uint32 y = 2; }\n")
    main = write(tmp_path, "main.sf",
                 'package main;\noption pkgid = 3;\nimport "pa.sf";\nimport "pb.sf";\n'
                 "message M { option msgid = 1; Pos p = 1; }\n")
    assert validate(main).returncode != 0, "ambiguous 'Pos' silently resolved"


def test_type_from_non_imported_package_is_rejected(tmp_path):
    write(tmp_path, "pb.sf", "package pb;\noption pkgid = 2;\nmessage B { uint8 x = 1; }\n")
    write(tmp_path, "pc.sf", "package pc;\noption pkgid = 4;\nmessage C { uint8 y = 1; }\n")
    main = write(tmp_path, "top.sf",
                 'package top;\noption pkgid = 5;\nimport "pb.sf";\n'
                 "message T { option msgid = 1; C c = 1; }\n")
    # pc.sf is only loaded if something imports it
    write(tmp_path, "pb.sf",
          'package pb;\noption pkgid = 2;\nimport "pc.sf";\nmessage B { option msgid = 1; uint8 x = 1; }\n')
    assert validate(main).returncode != 0, "'C' resolved through a transitive, un-imported package"


# ---------------------------------------------------------------------------
# #8  discriminators and cross-package id collisions (the repo TODO item)
# ---------------------------------------------------------------------------

def test_cross_package_effective_id_collision_rejected(tmp_path):
    write(tmp_path, "pb.sf", "package pb;\nmessage Y { option msgid = 5; uint8 y = 1; }\n")
    main = write(tmp_path, "pa.sf",
                 'package pa;\noption pkgid = 1;\nimport "pb.sf";\n'
                 "message X { option msgid = 5; uint8 x = 1; }\n")
    r = validate(main)
    assert r.returncode != 0, "pa.X and (inherited-pkgid) pb.Y both have id 0x0105"


def test_duplicate_msgid_discriminator_values_rejected(tmp_path):
    sf = write(tmp_path, "d.sf",
               "package d;\nmessage Foo { option msgid = 3; uint8 v = 1; }\n"
               "message Holder { option msgid = 4; oneof body { Foo x = 1; Foo y = 2; } }\n")
    assert validate(sf).returncode != 0, "two variants share discriminator value 3"


# ---------------------------------------------------------------------------
# #7  msgid = 0 must be a real id
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("flag,ext,declaration", [
    ("--build_ts", "ts", r"_msgid: number = 0;"),
    ("--build_js", "js", r"_msgid = 0;"),
    ("--build_csharp", "cs", r"const ushort MsgId = 0;"),
])
def test_msgid_zero_is_not_treated_as_missing(tmp_path, flag, ext, declaration):
    """``option msgid = 0`` is a real id; every language must declare it."""
    sf = write(tmp_path, "z.sf",
               "package z;\nmessage Zero { option msgid = 0; uint8 x = 1; }\n"
               "message One { option msgid = 1; uint8 y = 1; }\n")
    o = tmp_path / "o"
    path_flag = "--csharp_path" if ext == "cs" else f"--{ext}_path"
    r = gen(tmp_path, sf, flag, path_flag, str(o))
    assert r.returncode == 0, out(r)
    text = read_all(o, f"*.{ext}")
    assert re.search(declaration, text), f"no id declaration matching {declaration!r} for msgid=0"
    # and it must be registered for dispatch like any other message
    registry = "Zero" if ext != "cs" else "Zero.MsgId"
    assert registry in text


# ---------------------------------------------------------------------------
# misc validation gaps
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("body,label", [
    ("oneof v { }", "empty oneof"),
    ("repeated uint8 a = 1 [size = 4, max_size = 8];", "size and max_size together"),
    ("repeated uint8 a = 1 [max_size = 4, element_size = 2];", "element_size on non-string array"),
    ("oneof v { option max_size = 4; option min_size = 16; uint8 a = 1; uint16 b = 2; }",
     "oneof min_size > max_size"),
])
def test_contradictory_options_rejected(tmp_path, body, label):
    sf = write(tmp_path, "c.sf", f"package c;\nmessage M {{ option msgid = 1; {body} }}\n")
    assert validate(sf).returncode != 0, label


def test_extension_marker_in_trailing_comment_does_not_change_layout(tmp_path):
    """Prose mentioning ``Extension::`` must not move ``extensions_start``.
    The magic bytes are derived from the base layout, so they must be identical
    with and without the comment."""
    def magic(comment: str) -> list[str]:
        sub = tmp_path / ("with" if comment else "without")
        sub.mkdir()
        lines = ["package ext;", "message M {", "  option msgid = 1;",
                 f"  uint8 a = 1;{comment}", "  uint8 b = 2;", "  uint8 c = 3;", "}"]
        sf = write(sub, "ext.sf", "\n".join(lines) + "\n")
        o = sub / "c"
        r = gen(sub, sf, "--build_c", "--c_path", str(o))
        assert r.returncode == 0, out(r)
        hdr = (o / "ext.structframe.h").read_text(encoding="utf-8")
        found = re.findall(r"#define\s+EXT_M_MAGIC\w*\s+(\S+)", hdr)
        assert found, "no magic defines found in generated header"
        return found

    assert magic("") == magic(" // see Extension:: docs"), \
        "'Extension::' in a trailing comment changed the wire layout"


# ---------------------------------------------------------------------------
# B10  UTF-8 schemas on any platform
# ---------------------------------------------------------------------------

def test_utf8_comments_survive_generation(tmp_path):
    sf = tmp_path / "u.sf"
    sf.write_bytes("package u;\n// Temperature in °C — range ≤ 100\n"
                   "message M { option msgid = 1; uint8 t = 1; }\n".encode("utf-8"))
    o = tmp_path / "c"
    r = gen(tmp_path, sf, "--build_c", "--c_path", str(o))
    assert r.returncode == 0, out(r)
    hdr = (o / "u.structframe.h").read_text(encoding="utf-8")
    assert "°C — range ≤ 100" in hdr, "UTF-8 comment mangled (schema read with locale encoding)"


# ---------------------------------------------------------------------------
# generation cache
# ---------------------------------------------------------------------------

def test_cache_key_includes_import_graph(tmp_path):
    write(tmp_path, "pc.sf", "package pc;\noption pkgid = 3;\nmessage C { option msgid = 1; uint8 c = 1; }\n")
    a = write(tmp_path, "pa.sf",
              'package pa;\noption pkgid = 1;\nimport "pc.sf";\n'
              "message A { option msgid = 1; uint8 x = 1; }\n")
    o = tmp_path / "py"
    flags = ("--build_py", "--py_path", str(o))
    assert gen(tmp_path, a, *flags).returncode == 0
    write(tmp_path, "pa.sf",
          "package pa;\noption pkgid = 1;\nmessage A { option msgid = 1; uint8 x = 1; }\n")
    assert gen(tmp_path, a, *flags).returncode == 0
    src = (o / "struct_frame" / "generated" / "pa.py").read_text(encoding="utf-8")
    assert "pc" not in src, "stale output: removed import still present (cache key ignores import graph)"


def test_cache_hit_regenerates_missing_outputs(tmp_path):
    sf = write(tmp_path, "c.sf", "package c;\nmessage M { option msgid = 1; uint8 x = 1; }\n")
    c_out, py_out = tmp_path / "c", tmp_path / "py"
    flags = ("--build_c", "--c_path", str(c_out), "--build_py", "--py_path", str(py_out))
    assert gen(tmp_path, sf, *flags).returncode == 0
    import shutil
    shutil.rmtree(py_out)
    assert gen(tmp_path, sf, *flags).returncode == 0
    assert (py_out / "struct_frame" / "generated" / "c.py").exists(), \
        "generation skipped on hash match although the Python output was deleted"


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------

def _diff(old: Path, new: Path):
    return run_generator_diff(old, new)


def run_generator_diff(old: Path, new: Path):
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, str(SRC_DIR / "main.py"), "diff",
                           str(old), str(new), "--format", "json"],
                          capture_output=True, text=True, env=env)


def test_diff_syntax_error_is_a_parse_error_not_a_diff(tmp_path):
    good = write(tmp_path, "v1.sf", "package d;\nmessage M { option msgid = 1; uint8 a = 1; }\n")
    bad = write(tmp_path, "v2.sf", "package d;\nmessage M { option msgid = 1; uint8 a = 1 }\n")
    r = _diff(good, bad)
    assert r.returncode == 2, f"expected parse-error exit 2, got {r.returncode}:\n{out(r)}"


TRIMMED = """package d;
message Small {{ uint8 a = 1; }}
message Big {{ uint8 a = 1; uint64 b = 2; }}
message M {{
  option msgid = 1;
  option variable = true;
  uint8 tag = 1;
  oneof v {{
    {opts}
    Small s = 1;
    Big b = 2;
  }}
}}
"""


def test_diff_raising_trimmed_oneof_min_size_is_breaking(tmp_path):
    old = write(tmp_path, "v1.sf", TRIMMED.format(opts=""))
    new = write(tmp_path, "v2.sf", TRIMMED.format(opts="option min_size = 16;"))
    r = _diff(old, new)
    if r.returncode == 2:
        pytest.skip("premise broken: schema does not parse")
    assert r.returncode == 1, \
        "min_size raised on a trimmed oneof: receivers now reject short payloads, but diff says compatible"


def test_diff_enum_moved_between_scopes_is_not_breaking(tmp_path):
    old = write(tmp_path, "v1.sf",
                "package d;\nmessage M { option msgid = 1; enum K { A = 0; B = 1; } K k = 1; }\n")
    new = write(tmp_path, "v2.sf",
                "package d;\nenum K { A = 0; B = 1; }\nmessage M { option msgid = 1; K k = 1; }\n")
    r = _diff(old, new)
    assert r.returncode == 0, f"wire-identical scope move reported breaking:\n{out(r)}"


# ---------------------------------------------------------------------------
# GraphQL (no graphql-core dependency: structural reference check)
# ---------------------------------------------------------------------------

GQL_SCALARS = {"Int", "Float", "String", "Boolean", "ID"}


def _gql_defined_and_used(text: str):
    text = re.sub(r'""".*?"""', "", text, flags=re.S)
    text = re.sub(r'"[^"\n]*"', "", text)
    text = re.sub(r"#[^\n]*", "", text)
    defined = set(re.findall(r"^\s*(?:type|enum|input|scalar|union|interface)\s+(\w+)", text, re.M))
    used = set()
    for body in re.findall(r"^\s*type\s+\w+[^{]*\{(.*?)^\}", text, re.M | re.S):
        used |= set(re.findall(r":\s*\[?\s*(\w+)", body))
    return defined, used


GQL_SCHEMA_A = ('package ga;\noption pkgid = 1;\nenum Mode { Idle = 0; Run = 1; }\n'
                "message Stamp { uint32 secs = 1; int64 ns = 2; }\n")
GQL_SCHEMA_B = ('package gb;\noption pkgid = 2;\nimport "ga.sf";\n'
                "message Event {\n  option msgid = 1;\n  enum Kind { K0 = 0; K1 = 1; }\n"
                "  Stamp when = 1;\n  Mode mode = 2;\n  Kind kind = 3;\n  uint64 id = 4;\n}\n")


def _gql(tmp: Path) -> Path:
    write(tmp, "ga.sf", GQL_SCHEMA_A)
    b = write(tmp, "gb.sf", GQL_SCHEMA_B)
    o = tmp / "gql"
    r = gen(tmp, b, "--build_gql", "--gql_path", str(o))
    assert r.returncode == 0, out(r)
    return o


def test_graphql_per_package_references_resolve_across_files(tmp_path):
    o = _gql(tmp_path)
    defined, used = set(), set()
    for f in o.glob("*.graphql"):
        if f.name == "schema.graphql":
            continue
        d, u = _gql_defined_and_used(f.read_text(encoding="utf-8"))
        defined |= d
        used |= u
    missing = used - defined - GQL_SCALARS
    assert not missing, f"undefined GraphQL types referenced: {sorted(missing)}"


def test_graphql_stitched_schema_is_self_contained(tmp_path):
    o = _gql(tmp_path)
    defined, used = _gql_defined_and_used((o / "schema.graphql").read_text(encoding="utf-8"))
    missing = used - defined - GQL_SCALARS
    assert not missing, f"stitched schema references undefined types: {sorted(missing)}"


def test_graphql_query_fields_unique(tmp_path):
    write(tmp_path, "ga.sf", "package ga;\noption pkgid = 1;\nmessage Ping { option msgid = 1; uint8 x = 1; }\n")
    b = write(tmp_path, "gb.sf",
              'package gb;\noption pkgid = 2;\nimport "ga.sf";\nmessage Ping { option msgid = 1; uint8 y = 1; }\n')
    o = tmp_path / "gql"
    assert gen(tmp_path, b, "--build_gql", "--gql_path", str(o)).returncode == 0
    text = (o / "schema.graphql").read_text(encoding="utf-8")
    q = re.search(r"type Query \{(.*?)\}", text, re.S).group(1)
    names = [l.split(":")[0].strip() for l in q.strip().splitlines() if l.strip()]
    assert len(names) == len(set(names)), f"duplicate Query fields: {names}"


def test_graphql_wide_integers_do_not_use_32bit_int(tmp_path):
    """GraphQL Int is signed 32-bit; uint32/int64/uint64 values overflow it."""
    o = _gql(tmp_path)
    text = (o / "ga.graphql").read_text(encoding="utf-8")
    for fld in ("secs", "ns"):
        m = re.search(rf"^\s*{fld}:\s*(\w+)", text, re.M)
        assert m and m.group(1) != "Int", f"field {fld} maps to 32-bit Int"


# ---------------------------------------------------------------------------
# examples must stay valid
# ---------------------------------------------------------------------------

EXAMPLE_SFS = sorted((REPO_ROOT / "examples").rglob("*.sf"))


@pytest.mark.parametrize("sf", EXAMPLE_SFS, ids=lambda p: p.relative_to(REPO_ROOT / "examples").as_posix())
def test_example_schemas_validate(sf):
    r = validate(sf)
    assert r.returncode == 0, out(r)


# ---------------------------------------------------------------------------
# runtime / tooling drift
# ---------------------------------------------------------------------------

def test_js_sdk_twin_has_everything_ts_sdk_has():
    base = SRC_DIR / "struct_frame" / "boilerplate"
    ts = (base / "ts" / "struct-frame-sdk" / "struct-frame-sdk.ts").read_text(encoding="utf-8")
    js = (base / "js" / "struct-frame-sdk" / "struct-frame-sdk.js").read_text(encoding="utf-8")
    members = set(re.findall(r"^\s{2}(?:public\s+|async\s+)?([a-zA-Z_]\w*)\s*\(", ts, re.M))
    members -= {"constructor", "if", "for", "while", "switch", "catch", "function"}
    missing = sorted(m for m in members if not re.search(rf"\b{m}\b", js))
    assert not missing, f"compiled JS SDK lacks members present in the TS SDK: {missing}"
    assert js.count("onError") >= ts.count("onError") // 2, "JS SDK is missing onError support"


def test_cpp_sdk_asio_is_not_a_git_symlink():
    """A git symlink becomes a 27-byte text file on Windows checkouts."""
    rel = "src/struct_frame/boilerplate/cpp/struct_frame_sdk/asio"
    try:
        r = subprocess.run(["git", "ls-files", "-s", rel], cwd=REPO_ROOT,
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("git not available")
    if r.returncode != 0:
        pytest.skip("not a git checkout")
    # An empty listing means the path is not tracked at all, which is fine: the
    # generator copies the headers from asio-repo/asio/include/asio instead.
    assert not r.stdout.startswith("120000"), f"{rel} is a symlink in git"


def test_wireshark_dissector_seeds_checksum_with_magic_bytes():
    """Every runtime appends MAGIC1/MAGIC2 to the Fletcher sum; the dissector
    must too, or real frames always show an invalid CRC."""
    lua = (REPO_ROOT / "wireshark" / "struct_frame.lua").read_text(encoding="utf-8")
    assert re.search(r"magic", lua, re.I), "dissector never references the message magic bytes"


# ---------------------------------------------------------------------------
# repo / CI hygiene (the tests that police the tests)
# ---------------------------------------------------------------------------

def _tracked():
    try:
        r = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True,
                           text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("git not available")
    if r.returncode != 0:
        pytest.skip("not a git checkout")
    return r.stdout.splitlines()


def test_no_binaries_or_logs_tracked():
    bad = [f for f in _tracked()
           if re.search(r"(\.exe|\.log|\.obj|\.pdb)$|(^|/)\.coverage$|_codeql_detected", f)
           and not f.startswith(("node_modules/",))]
    assert not bad, f"stray artifacts tracked by git: {bad}"


def test_workflows_do_not_run_main_less_test_files_as_scripts():
    """Running a pytest-style file as ``python file.py`` executes nothing when it
    has no ``__main__`` block (this silently disabled two coverage steps)."""
    wf_dir = REPO_ROOT / ".github" / "workflows"
    offenders = []
    for wf in wf_dir.glob("*.yml"):
        for line in wf.read_text(encoding="utf-8").splitlines():
            m = re.search(r"(tests/test_\w+\.py)", line)
            if not m or "pytest" in line:
                continue
            # find the logical command (line may continue from previous with '\')
            text = wf.read_text(encoding="utf-8")
            idx = text.find(line)
            window = text[max(0, idx - 200): idx + len(line)]
            if "pytest" in window.split("coverage run")[-1]:
                continue
            f = REPO_ROOT / m.group(1)
            if f.exists() and "__main__" not in f.read_text(encoding="utf-8"):
                offenders.append(f"{wf.name}: {m.group(1)}")
    assert not offenders, offenders


def test_validate_tests_that_check_for_no_output_pass_build_flags():
    """A 'no files written' assertion is vacuous unless a --build_* flag is given."""
    src = (REPO_ROOT / "tests" / "test_validate_flag.py").read_text(encoding="utf-8")
    block = src.split("def test_validate_no_output_files", 1)[1].split("\ndef ", 1)[0]
    assert "--build_" in block


# ---------------------------------------------------------------------------
# docs vs CLI drift
# ---------------------------------------------------------------------------

def _argparse_flags() -> set[str]:
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([sys.executable, str(SRC_DIR / "main.py"), "--help"],
                       capture_output=True, text=True, env=env)
    return set(re.findall(r"(--[a-z][a-z0-9_]*)", r.stdout)) - {"--help"}


def test_cli_reference_documents_only_real_flags():
    doc = (REPO_ROOT / "docs" / "src" / "content" / "docs" / "reference" / "cli-reference.md"
           ).read_text(encoding="utf-8")
    documented = set(re.findall(r"`(--[a-z][a-z0-9_-]*)", doc))
    # flags owned by `diff` are documented in the same page
    documented -= {"--format", "--fail-on", "--write-snapshot"}
    unknown = sorted(documented - _argparse_flags())
    assert not unknown, f"cli-reference.md documents flags that do not exist: {unknown}"


def test_every_cli_flag_is_documented():
    doc = (REPO_ROOT / "docs" / "src" / "content" / "docs" / "reference" / "cli-reference.md"
           ).read_text(encoding="utf-8")
    missing = sorted(f for f in _argparse_flags() if f not in doc)
    assert not missing, f"undocumented CLI flags: {missing}"


def test_name_overrides_flag_is_listed_in_help():
    assert "--name_overrides" in _argparse_flags()


def test_cpp_sdk_docs_do_not_claim_websocket_without_a_transport():
    """Every mention of WebSocket on the C++ SDK page must say it is NOT available,
    for as long as the C++ SDK has no such transport."""
    docs = (REPO_ROOT / "docs" / "src" / "content" / "docs" / "extended-features" / "cpp-sdk.md"
            ).read_text(encoding="utf-8")
    sdk = SRC_DIR / "struct_frame" / "boilerplate" / "cpp" / "struct_frame_sdk"
    has_ws = any("websocket" in p.read_text(encoding="utf-8", errors="ignore").lower()
                 for p in sdk.glob("*.hpp"))
    if has_ws:
        return
    claims = [line for line in docs.splitlines()
              if "websocket" in line.lower() and "no websocket" not in line.lower()]
    assert not claims, f"cpp-sdk.md claims WebSocket support the SDK lacks: {claims}"


def test_docs_do_not_reference_removed_cpp_namespace():
    docs_dir = REPO_ROOT / "docs" / "src" / "content" / "docs"
    hits = [str(p.relative_to(REPO_ROOT)) for p in docs_dir.rglob("*.md*")
            if "FrameParsers::" in p.read_text(encoding="utf-8")]
    assert not hits, f"docs use the removed FrameParsers:: namespace: {hits}"


def test_changelog_documents_unreleased_or_current_changes():
    """The released-version entry (or an Unreleased section) must list real changes
    under a ### heading, not just the compare link the release tool emits."""
    version = re.search(r'^version\s*=\s*"([^"]+)"',
                        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.M).group(1)
    log = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    sections = re.split(r"(?m)^## ", log)
    wanted = [sec for sec in sections
              if sec.startswith("Unreleased") or sec.startswith(f"[{version}]") or sec.startswith(f"[v{version}]")]
    assert wanted, f"no Unreleased or {version} section in CHANGELOG.md"
    assert any(re.search(r"(?m)^### \w+", sec) and re.search(r"(?m)^- \S", sec) for sec in wanted),         f"CHANGELOG sections for {version}/Unreleased list no changes"


def test_console_script_entry_point_declared():
    py = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[project.scripts]" in py, "no console script: `struct-frame` command does not exist"


# ---------------------------------------------------------------------------
# flatten collisions
# ---------------------------------------------------------------------------

def test_flatten_collision_with_imported_type_is_rejected(tmp_path):
    write(tmp_path, "inner.sf",
          "package inner;\noption pkgid = 2;\nmessage Pos { uint8 x = 1; uint8 mac_id = 2; }\n")
    main = write(tmp_path, "outer.sf",
                 'package outer;\noption pkgid = 1;\nimport "inner.sf";\n'
                 "message M { option msgid = 1; uint32 mac_id = 1; inner.Pos p = 2 [flatten = true]; }\n")
    r = validate(main)
    assert r.returncode != 0, "flattened child 'mac_id' collides with the parent field but was accepted"


def test_two_flattened_fields_of_the_same_type_collide(tmp_path):
    sf = write(tmp_path, "f.sf",
               "package f;\nmessage Pos { uint8 x = 1; }\n"
               "message M { option msgid = 1; Pos a = 1 [flatten = true]; Pos b = 2 [flatten = true]; }\n")
    assert validate(sf).returncode != 0, "both flattened fields expose a child named 'x'"
