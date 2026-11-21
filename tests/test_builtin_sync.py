#!/usr/bin/env python3
"""The built-in ``sf_system`` schema and the code generated from it stay in step.

``src/struct_frame/builtin/sf_system.sf`` is generated into ``boilerplate/<lang>/`` and
committed, so the runtimes can use the system messages without generating anything.
Regenerate with ``python -m struct_frame.builtin --write`` (then recompile the JavaScript
runtime) after changing the schema or a generator.
"""
from __future__ import annotations

import contextlib
import io
import re
import subprocess
import sys
from pathlib import Path

import pytest

from test_utils import REPO_ROOT, SRC_DIR

BOILERPLATE = REPO_ROOT / "src" / "struct_frame" / "boilerplate"


def _builtin():
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
    from struct_frame import builtin
    return builtin


@pytest.fixture(scope="module")
def schema():
    """The parsed sf_system package (IR)."""
    from struct_frame import generate as gen
    gen.reset_parse_state()
    previous = gen.ALLOW_RESERVED_PACKAGES
    gen.ALLOW_RESERVED_PACKAGES = True
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            assert gen.parseFile(_builtin().SCHEMA) and gen.validate_packages()
        yield gen.packages["sf_system"]
    finally:
        gen.ALLOW_RESERVED_PACKAGES = previous
        gen.reset_parse_state()


def test_committed_builtin_code_is_current():
    stale = _builtin().stale()
    assert not stale, ("built-in schema code is stale; run `python -m struct_frame.builtin --write` "
                       f"and recompile the JavaScript runtime: {stale}")


def _camel(name):
    head, *rest = name.split("_")
    return head + "".join(part.capitalize() for part in rest)


def _pascal(name):
    return "".join(part.capitalize() for part in name.split("_"))


def test_generated_code_reflects_the_schema(schema):
    """Every field of every system message appears in each language's generated file. Guards
    against generating from (or being overwritten by) a previous generation."""
    files = {
        "c": (BOILERPLATE / "c" / "sf_system.structframe.h").read_text(encoding="utf-8"),
        "cpp": (BOILERPLATE / "cpp" / "sf_system.structframe.hpp").read_text(encoding="utf-8"),
        "py": (BOILERPLATE / "py" / "sf_system.py").read_text(encoding="utf-8"),
        "ts": (BOILERPLATE / "ts" / "sf-system.structframe.ts").read_text(encoding="utf-8"),
        "js": (BOILERPLATE / "js" / "sf-system.structframe.js").read_text(encoding="utf-8"),
        "rust": (BOILERPLATE / "rust" / "sf_system.rs").read_text(encoding="utf-8"),
    }
    cs_dir = BOILERPLATE / "csharp" / "Framework" / "SfSystem" / "Messages"
    for msg_name, msg in schema.messages.items():
        cs = (cs_dir / f"{msg_name}.cs").read_text(encoding="utf-8")
        for field in msg.fields:
            assert re.search(rf"\b{field}\b", files["c"]), f"C lacks {msg_name}.{field}"
            assert re.search(rf"\b{field}\b", files["cpp"]), f"C++ lacks {msg_name}.{field}"
            assert f"self.{field} =" in files["py"], f"Python lacks {msg_name}.{field}"
            assert f"get {_camel(field)}()" in files["ts"], f"TypeScript lacks {msg_name}.{field}"
            assert f"get {_camel(field)}()" in files["js"], f"JavaScript lacks {msg_name}.{field}"
            assert f"pub {field}:" in files["rust"], f"Rust lacks {msg_name}.{field}"
            assert f" {_pascal(field)} {{ get; set; }}" in cs, f"C# lacks {msg_name}.{field}"


def test_system_info_tables_match_the_schema(schema):
    builtin = _builtin()
    rows = builtin._system_table({"sf_system": schema})
    c = (BOILERPLATE / "c" / "sf_system_info.h").read_text(encoding="utf-8")
    cpp = (BOILERPLATE / "cpp" / "sf_system_info.hpp").read_text(encoding="utf-8")
    max_tail = int(schema.consts["MAX_TAIL"].value)
    for name, msg_id, size, m1, m2, tail in rows:
        extra = max_tail if tail else 0
        assert (f"case 0x{msg_id:02X}: fixed = {size}; tail = {extra}; magic1 = {m1}; magic2 = {m2}; "
                f"break; /* {name} */") in c
        assert f"case 0x{msg_id:02X}: return MessageInfo({size + extra}, {m1}, {m2}, {size + extra}, {size});" in cpp


def _names(pattern, text):
    return set(re.findall(pattern, text))


def test_every_runtime_lists_the_same_tail_messages():
    """The hand-written runtimes repeat builtin.TAIL_MESSAGES (C and C++ get generated tables)."""
    want = set(_builtin().TAIL_MESSAGES)
    py = (BOILERPLATE / "py" / "system_frames.py").read_text(encoding="utf-8")
    py_block = py.split("TAIL_MESSAGES = frozenset({", 1)[1].split("})", 1)[0]
    assert _names(r"sf_system\.(\w+)\.MSG_ID", py_block) == want

    ts = (BOILERPLATE / "ts" / "system-frames.ts").read_text(encoding="utf-8")
    ts_block = ts.split("export const TAIL_MESSAGES", 1)[1].split("]);", 1)[0]
    assert _names(r"sf\.(\w+)\._msgid", ts_block) == want

    cs = (BOILERPLATE / "csharp" / "Framework" / "Framing" / "SystemFrames.cs").read_text(encoding="utf-8")
    cs_block = cs.split("TailMessages = new HashSet<ushort>", 1)[1].split("};", 1)[0]
    assert _names(r"(\w+)\.MsgId", cs_block) == want

    rs = (BOILERPLATE / "rust" / "system_frames.rs").read_text(encoding="utf-8")
    rs_block = rs.split("pub const TAIL_MESSAGES", 1)[1].split("];", 1)[0]
    assert _names(r"sf_system::(\w+) as", rs_block) == want


def test_application_schemas_cannot_use_the_reserved_package(tmp_path):
    schema = tmp_path / "mine.sf"
    schema.write_text("package sf_system;\nmessage Mine @1 {\n  uint8 x;\n}\n", encoding="utf-8")
    run = subprocess.run([sys.executable, "-m", "struct_frame", str(schema), "--lang", "py",
                          "--out", str(tmp_path / "out")],
                         capture_output=True, text=True, cwd=tmp_path,
                         env={**__import__("os").environ, "PYTHONPATH": str(SRC_DIR)})
    assert run.returncode != 0
    assert "reserved" in (run.stdout + run.stderr)


def test_wireshark_dissector_knows_the_system_messages(schema):
    """wireshark/struct_frame.lua verifies system-frame checksums with its own copy of the
    system messages' ids and magic bytes."""
    lua = (REPO_ROOT / "wireshark" / "struct_frame.lua").read_text(encoding="utf-8")
    block = lua.split("local system_messages = {", 1)[1].split("\n}", 1)[0]
    listed = {int(i, 16): (name, int(m1), int(m2)) for i, name, m1, m2 in
              re.findall(r'\[0x([0-9A-Fa-f]+)\] = \{ "(\w+)", (\d+), (\d+) \}', block)}
    want = {msg.id: (name, msg.magic_bytes[0], msg.magic_bytes[1]) for name, msg in schema.messages.items()}
    assert listed == want
