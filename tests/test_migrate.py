"""``struct-frame migrate`` (old proto-style syntax -> struct-frame language) and ``fmt``.

``tests/schema_corpus/legacy/`` holds the repository's schemas as they were written in
the old syntax. Migrating each one must reproduce the checked-in new-syntax file exactly;
the IR goldens (tests/test_ir_golden.py) separately prove that the checked-in files build
the same model and generated code the old front end built from the originals.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

psp = pytest.importorskip("proto_schema_parser", reason="migrate needs proto-schema-parser")

from struct_frame.schema import legacy_proto  # noqa: E402
from struct_frame.schema.parser import parse_text  # noqa: E402
from struct_frame.schema.printer import print_file  # noqa: E402

LEGACY = ROOT / "tests" / "schema_corpus" / "legacy"
CASES = sorted(LEGACY.glob("*.sf"))


def _repo_file(legacy: Path) -> Path:
    return ROOT / legacy.name.replace("__", "/")


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _cli(*args, cwd=None, stdin=None):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    return subprocess.run([sys.executable, "-m", "struct_frame", *args], capture_output=True,
                          text=True, env=env, cwd=cwd, input=stdin)


def test_corpus_covers_the_repository_schemas():
    assert len(CASES) >= 25
    for case in CASES:
        assert _repo_file(case).is_file(), case.name


@pytest.mark.parametrize("legacy", CASES, ids=lambda p: p.name)
def test_migrating_the_legacy_schema_gives_the_checked_in_file(legacy):
    new_text, _warnings = legacy_proto.migrate_text(_text(legacy), str(legacy))
    assert new_text == _text(_repo_file(legacy))


@pytest.mark.parametrize("legacy", CASES, ids=lambda p: p.name)
def test_checked_in_schemas_are_formatted(legacy):
    text = _text(_repo_file(legacy))
    tree, sink = parse_text(text, str(legacy))
    assert not sink.errors, [d.render() for d in sink.errors]
    assert print_file(tree) == text


LEGACY_SNIPPET = """\
// Copyright header
package demo;
option pkgid = 3;

// Modes
enum Mode {
  IDLE = 0;   // idle
  RUN = 1;
}

// Status docs
message Status {
  option msgid = 7;  // the status message
  // A comment before an option documents nothing.
  option variable = true;
  option magic_bytes = "0xA3, 0x7F";
  uint32 uptime = 1 [default = 1000];
  string name = 2 [size = 8, default = "dev"];
  repeated uint8 data = 3 [max_size = 16];
  repeated string tags = 4 [size = 2, element_size = 6];
  Mode mode = 5 [default = RUN];
  option extensions_start = 6;
  float temp = 6;
}

message Wrapper {
  option msgid = 8;
  oneof body {
    option discriminator = field_order;
    Status status = 1;
    // Extension::
    Mode mode = 2;
  }
}
"""

MIGRATED_SNIPPET = """\
/// Copyright header

package demo @3;

/// Modes
enum Mode {
  IDLE = 0;  /// idle
  RUN = 1;
}

/// Status docs
message Status @7 [variable, magic = [0xA3, 0x7F]] {  /// the status message
  // A comment before an option documents nothing.
  uint32 uptime = 1000;
  fixed_string<8> name = "dev";
  vector<uint8, 16> data;
  array<fixed_string<6>, 2> tags;
  Mode mode = RUN;

  extensions {
    float temp;
  }
}

message Wrapper @8 {
  oneof body [discriminator = field_order] {
    Status status;
    extensions {
      /// Extension::
      Mode mode;
    }
  }
}
"""


def test_migration_of_every_construct():
    text, warnings = legacy_proto.migrate_text(LEGACY_SNIPPET, "demo.sf")
    assert text == MIGRATED_SNIPPET
    assert warnings == []


def test_migration_reports_dropped_constructs():
    text, warnings = legacy_proto.migrate_text(
        'syntax = "proto3";\npackage p;\nmessage M {\n  option msgid = 1;\n  option msg_id = 2;\n'
        '  uint8 a = 1 [defualt = 3];\n  reserved 5;\n  map<string, uint8> m = 2;\n}\n', "p.sf")
    joined = "\n".join(warnings)
    for words in ("syntax", "msg_id", "defualt", "Reserved", "MapField"):
        assert words in joined, (words, warnings)
    assert "// migrate: dropped" in text
    _tree, sink = parse_text(text, "p.sf")
    assert not sink.errors


def test_escaped_string_defaults_keep_their_text():
    # The old front end kept backslashes literally; the migrated literal must say the same.
    text, _ = legacy_proto.migrate_text(
        'package p;\nmessage M {\n  option msgid = 1;\n  string s = 1 [size = 8, default = "a\\nb"];\n}\n', "p.sf")
    assert 'fixed_string<8> s = "a\\\\nb";' in text


def test_cli_migrate_modes(tmp_path):
    legacy = tmp_path / "old.sf"
    legacy.write_text(LEGACY_SNIPPET, encoding="utf-8")
    r = _cli("migrate", str(legacy), "--check")
    assert r.returncode == 1 and "uses the old syntax" in r.stdout
    r = _cli("migrate", str(legacy))
    assert r.returncode == 0 and r.stdout == MIGRATED_SNIPPET
    r = _cli("migrate", str(legacy), "--in-place", "-q")
    assert r.returncode == 0, r.stderr
    assert _text(legacy) == MIGRATED_SNIPPET
    r = _cli("migrate", str(legacy), "--check")
    assert r.returncode == 0
    r = _cli("migrate", "-", stdin=LEGACY_SNIPPET)
    assert r.returncode == 0 and r.stdout == MIGRATED_SNIPPET


def test_cli_migrate_recursive_follows_imports(tmp_path):
    (tmp_path / "common.sf").write_text("package common;\noption pkgid = 1;\nmessage Pos { double lat = 1; }\n",
                                        encoding="utf-8")
    (tmp_path / "main.sf").write_text(
        'package main;\noption pkgid = 2;\nimport "common.sf";\nmessage M {\n  option msgid = 1;\n  common.Pos p = 1;\n}\n',
        encoding="utf-8")
    r = _cli("migrate", str(tmp_path / "main.sf"), "-i", "-r", "-q")
    assert r.returncode == 0, r.stderr
    assert "struct Pos {" in _text(tmp_path / "common.sf")
    r = _cli(str(tmp_path / "main.sf"), "--validate")
    assert r.returncode == 0, r.stdout + r.stderr


def test_compiling_a_legacy_schema_points_to_migrate(tmp_path):
    legacy = tmp_path / "old.sf"
    legacy.write_text(LEGACY_SNIPPET, encoding="utf-8")
    r = _cli(str(legacy), "--validate")
    assert r.returncode == 1
    assert "struct-frame migrate" in r.stderr


def test_cli_fmt(tmp_path):
    messy = tmp_path / "m.sf"
    messy.write_text("package p;\nstruct S {u8 a;   u16 b;}\nenum E { A = 0; };\n", encoding="utf-8")
    r = _cli("fmt", str(messy), "--check")
    assert r.returncode == 1
    r = _cli("fmt", str(messy), "-i")
    assert r.returncode == 0
    assert _text(messy) == "package p;\n\nstruct S {\n  u8 a;\n  u16 b;\n}\n\nenum E {\n  A = 0;\n}\n"
    r = _cli("fmt", str(messy), "--check")
    assert r.returncode == 0
    r = _cli("fmt", str(messy), "--types", "long")
    assert "uint8 a;" in r.stdout and "uint16 b;" in r.stdout
    bad = tmp_path / "bad.sf"
    bad.write_text("package p;\nstruct S { u8 a }\n", encoding="utf-8")
    r = _cli("fmt", str(bad))
    assert r.returncode == 2 and "SF0202" in r.stderr


@pytest.mark.parametrize("name", ["tests__proto__test_messages.sf", "tests__proto__wire_evolution_v2.sf",
                                  "tests__proto__envelope_messages.sf"])
def test_diff_reads_the_old_syntax(tmp_path, name):
    """A schema revision from before the syntax change compares equal to its conversion."""
    old = tmp_path / name.split("__")[-1]
    old.write_text(_text(LEGACY / name), encoding="utf-8")
    r = _cli("diff", str(old), str(_repo_file(LEGACY / name)))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "no differences" in r.stdout.lower(), r.stdout
