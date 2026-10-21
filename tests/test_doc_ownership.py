#!/usr/bin/env python3
"""
Tests for comment ownership in ``.sf`` files.

Rules (see "Comments and documentation" in the message-definition docs):

* File docs   -- own-line comments before the ``package`` statement document the
  *file*; they are emitted once in the generated file header and never attached
  to the first declaration.
* Leading     -- own-line comments directly above a declaration document that
  declaration (message, enum, enum entry, field, oneof, oneof variant).
* Trailing    -- a comment on the same line after a declaration documents *that*
  declaration, not the next one.
* Comments before ``option``/``import`` statements or dangling at the end of a
  scope document nothing.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from test_utils import _check, run_generator

SCHEMA = """\
// File header: describes this whole file
// and spans two lines

package docs_test;

// Priority levels
enum Level {
  // Lowest level
  LOW = 0;
  HIGH = 1; // Highest level
}

// Sensor reading
message Reading {
  // handled by the option
  option msgid = 1;

  uint32 first = 1; // Describes first
  // Leading docs for second
  uint32 second = 2;
  Level level = 3;
  oneof body {
    // Leading docs for variant
    uint8 small = 1; // Trailing docs for small
    uint16 large = 2;
  }
  // dangling at the end of the message
}
"""


def _generate(langs=("cpp", "csharp", "rust", "ts", "py", "gql")) -> dict[str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        proto = tmp_path / "docs.sf"
        proto.write_text(SCHEMA, encoding="utf-8")
        flags = ["--force"]
        for lang in langs:
            flags += [f"--build_{lang}", f"--{lang}_path", str(tmp_path / lang) + os.sep]
        result = run_generator(proto, *flags)
        _check(result.returncode == 0, f"Generation failed:\n{result.stdout}\n{result.stderr}")
        out = {}
        for lang in langs:
            for path in sorted((tmp_path / lang).rglob("*")):
                if path.is_file() and path.suffix in {".hpp", ".cs", ".rs", ".ts", ".py", ".graphql"}:
                    out[f"{lang}/{path.relative_to(tmp_path / lang).as_posix()}"] = path.read_text(encoding="utf-8")
        return out


def _find(output: dict[str, str], lang: str, suffix: str) -> str:
    for name, text in output.items():
        if name.startswith(lang + "/") and name.endswith(suffix):
            return text
    raise AssertionError(f"no {lang} file ending with {suffix}: {sorted(output)}")


def _lines_before(text: str, marker: str, count: int) -> list[str]:
    lines = text.splitlines()
    index = next(i for i, line in enumerate(lines) if marker in line)
    return [line.strip() for line in lines[max(0, index - count):index]]


def test_file_header_is_not_attached_to_first_declaration():
    out = _generate()
    cpp = _find(out, "cpp", "docs_test.structframe.hpp")
    _check(cpp.count("File header: describes this whole file") == 1,
           "File docs must be emitted exactly once")
    _check(cpp.index("File header") < cpp.index("#pragma once"),
           "File docs belong in the file header, before the code")
    _check("File header" not in "\n".join(_lines_before(cpp, "enum class Level", 4)),
           "File docs must not become the first enum's documentation")

    level_cs = _find(out, "csharp", "Enums/Level.cs")
    _check("File header" not in level_cs, "File docs must not document the first C# enum")
    _check("File header" in _find(out, "csharp", "MessageDefinitions.cs"),
           "C# carries file docs in MessageDefinitions.cs")

    rust = _find(out, "rust", "docs_test.structframe.rs")
    _check(rust.count("File header") == 1, "Rust file docs emitted once")
    _check("Priority levels" in rust and rust.count("Priority levels") == 1,
           "Rust must not repeat enum docs as 'package comments'")

    for lang, name in (("ts", "docs-test.structframe.ts"), ("py", "docs_test.py"), ("gql", "docs_test.graphql")):
        text = _find(out, lang, name)
        _check(text.count("File header: describes this whole file") == 1, f"{lang}: file docs once")
        _check("and spans two lines" in text, f"{lang}: full file docs emitted")


def test_leading_comments_document_next_declaration():
    out = _generate()
    cpp = _find(out, "cpp", "docs_test.structframe.hpp")
    _check(_lines_before(cpp, "enum class Level", 1) == ["// Priority levels"],
           "Leading comment should document the enum that follows")
    _check(_lines_before(cpp, "Low = 0", 1) == ["// Lowest level"],
           "Leading comment should document the enum entry that follows")
    _check(_lines_before(cpp, "uint32_t second;", 1) == ["// Leading docs for second"],
           "Leading comment should document the following field")
    _check("Sensor reading" in "\n".join(_lines_before(cpp, "struct Reading", 3)),
           "Leading comment should document the following message")
    _check("// Leading docs for variant" in cpp, "Oneof variant leading docs are emitted")


def test_trailing_comments_document_preceding_declaration():
    out = _generate()
    cpp = _find(out, "cpp", "docs_test.structframe.hpp")
    _check(_lines_before(cpp, "uint32_t first;", 1) == ["// Describes first"],
           "Trailing comment should document the field it follows")
    _check("Describes first" not in "\n".join(_lines_before(cpp, "uint32_t second;", 2)),
           "Trailing comment must not leak onto the next field")
    _check("Highest level" in cpp and "Highest level" not in "\n".join(_lines_before(cpp, "struct Reading", 6)),
           "Trailing comment on the last enum entry must not leak onto the next declaration")
    variant = "\n".join(_lines_before(cpp, "uint8_t small;", 2))
    _check(variant.index("Leading docs for variant") < variant.index("Trailing docs for small"),
           f"Leading docs precede trailing docs, got:\n{variant}")

    cs = _find(out, "csharp", "Messages/Reading.cs")
    first = cs.index("public uint First")
    _check("Describes first" in cs[:first] and "Describes first" not in cs[first:],
           "C#: trailing comment documents the field it follows")


def test_comments_before_options_and_at_scope_end_document_nothing():
    out = _generate()
    everything = "\n".join(out.values())
    _check("handled by the option" not in everything,
           "A comment above an option statement must not leak onto the next field")
    _check("dangling at the end" not in everything,
           "A dangling comment at the end of a scope documents nothing")
