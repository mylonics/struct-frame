#!/usr/bin/env python3
"""
Tests for ``struct-frame diff``: the wire-compatibility check between two
schema revisions.

The command is run as a subprocess (``main.py diff OLD NEW --format json``)
and the reported change kinds/categories are asserted, so every wire-relevant
difference (message IDs, magic bytes, field types/numbers, enum values,
extensions, order-sensitive oneof variants) is pinned down, while harmless
differences (comments, declaration order, file moves) and source-only renames
are verified to be reported separately.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from test_utils import SRC_DIR, _check

BASE = """\
// Header comment
package demo;
option pkgid = 7;

enum Mode {
  IDLE = 0;
  RUN = 1;
}

message Small {
  uint8 v = 1;
}

message Big {
  uint32 v = 1;
}

message Inner {
  option msgid = 1;
  uint8 a = 1;
  uint16 b = 2;
}

message Telemetry {
  option msgid = 2;
  uint32 time = 1;
  Inner inner = 2;
  Mode mode = 3;
  string name = 4 [max_size = 16];
}

message Choice {
  option msgid = 3;
  oneof data {
    option discriminator = "field_order";
    Small small = 1;
    Big big = 2;
  }
}

message Evolving {
  option msgid = 4;
  uint8 a = 1;
}
"""


def _edit(text: str, old: str, new: str) -> str:
    _check(old in text, f"test bug: {old!r} not found in schema")
    return text.replace(old, new, 1)


def _run_diff(old_text: str, new_text: str, *flags: str, files=None):
    """Write both schemas to a temp dir and run ``main.py diff``."""
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        (tmp / "old.sf").write_text(old_text)
        (tmp / "new.sf").write_text(new_text)
        for name, text in (files or {}).items():
            (tmp / name).write_text(text)
        env = dict(os.environ, PYTHONPATH=str(SRC_DIR))
        return subprocess.run(
            [sys.executable, str(SRC_DIR / "main.py"), "diff", str(tmp / "old.sf"), str(tmp / "new.sf"),
             "--format", "json", *flags],
            capture_output=True, text=True, env=env)


def _report(old_text: str, new_text: str, *flags: str, files=None):
    result = _run_diff(old_text, new_text, *flags, files=files)
    _check(result.returncode in (0, 1), f"diff failed unexpectedly ({result.returncode}):\n{result.stdout}{result.stderr}")
    return result.returncode, json.loads(result.stdout)


def _kinds(report, category):
    return sorted(c["kind"] for c in report["changes"] if c["category"] == category)


def _find(report, kind, path=None):
    matches = [c for c in report["changes"] if c["kind"] == kind and (path is None or c["path"] == path)]
    _check(matches, f"expected a {kind!r} change at {path!r}, got:\n{json.dumps(report['changes'], indent=2)}")
    return matches[0]


# ---------------------------------------------------------------------------
# Harmless differences
# ---------------------------------------------------------------------------

def test_identical_schemas_have_no_differences():
    code, report = _report(BASE, BASE)
    _check(code == 0 and report["changes"] == [], f"expected no differences: {report}")
    _check(report["wire_compatible"] is True, "identical schemas must be wire compatible")


def test_comments_and_declaration_order_are_ignored():
    reordered = BASE.replace("// Header comment", "// A different header\n// with more lines")
    reordered = _edit(reordered, "message Small {\n  uint8 v = 1;\n}\n\n", "")
    reordered = reordered + "\n// moved to the end\nmessage Small {\n  // doc\n  uint8 v = 1;\n}\n"
    reordered = _edit(reordered, "  IDLE = 0;\n  RUN = 1;\n", "  // run first\n  RUN = 1;\n  IDLE = 0;\n")
    code, report = _report(BASE, reordered)
    _check(code == 0 and report["changes"] == [], f"docs/order must not be reported: {report['changes']}")


def test_file_moves_are_reported_separately_and_never_fail():
    inner = "package demo;\noption pkgid = 7;\n\nmessage Inner {\n  option msgid = 1;\n  uint8 a = 1;\n  uint16 b = 2;\n}\n"
    moved = _edit(BASE, "message Inner {\n  option msgid = 1;\n  uint8 a = 1;\n  uint16 b = 2;\n}\n\n", "")
    moved = _edit(moved, "option pkgid = 7;\n", 'option pkgid = 7;\nimport "inner.sf";\n')
    code, report = _report(BASE, moved, "--fail-on", "any", files={"inner.sf": inner})
    _check(code == 0, f"file moves must never fail, got {code}: {report}")
    _check(_kinds(report, "move") == ["file_moved"], f"unexpected moves: {report['changes']}")
    _check(len(report["changes"]) == 1, f"a pure file move must be the only difference: {report['changes']}")
    _check(_find(report, "file_moved", "demo.Inner")["new"] == "inner.sf", "moved-to file not reported")
    _check(report["summary"]["move"] == 1 and report["summary"]["breaking"] == 0, "summary mismatch")


# ---------------------------------------------------------------------------
# Wire-breaking differences
# ---------------------------------------------------------------------------

def test_message_id_change_is_breaking():
    code, report = _report(BASE, _edit(BASE, "msgid = 2;", "msgid = 20;"))
    _check(code == 1, "msgid change must fail")
    _find(report, "msgid_changed", "demo.Telemetry")
    _check(report["wire_compatible"] is False, "msgid change is not wire compatible")


def test_package_id_change_is_breaking():
    code, report = _report(BASE, _edit(BASE, "pkgid = 7", "pkgid = 8"))
    _check(code == 1, "package id change must fail")
    _find(report, "package_id_changed", "demo")


def test_field_type_change_is_breaking():
    code, report = _report(BASE, _edit(BASE, "uint32 time = 1;", "uint64 time = 1;"))
    _check(code == 1, "field type change must fail")
    change = _find(report, "field_type_changed", "demo.Telemetry.time")
    _check(change["old"] == "uint32" and change["new"] == "uint64", f"types not reported: {change}")
    magic = _find(report, "magic_bytes_changed", "demo.Telemetry")
    _check(magic["old"] != magic["new"], "magic bytes must differ when a field type changes")


def test_field_size_option_change_is_breaking():
    code, report = _report(BASE, _edit(BASE, "max_size = 16", "max_size = 32"))
    _check(code == 1, "string size change must fail")
    _find(report, "field_type_changed", "demo.Telemetry.name")


def test_removed_and_base_added_fields_are_breaking():
    removed = _edit(BASE, "  string name = 4 [max_size = 16];\n", "")
    code, report = _report(BASE, removed)
    _check(code == 1, "removing a field must fail")
    _find(report, "field_removed", "demo.Telemetry.name")

    added = _edit(BASE, "  string name = 4 [max_size = 16];\n", "  string name = 4 [max_size = 16];\n  uint8 extra = 5;\n")
    code, report = _report(BASE, added)
    _check(code == 1, "adding a field to the base layout must fail")
    _find(report, "field_added_to_base", "demo.Telemetry.extra")


def test_field_reorder_is_one_breaking_finding():
    swapped = _edit(BASE, "  uint8 a = 1;\n  uint16 b = 2;\n", "  uint16 b = 1;\n  uint8 a = 2;\n")
    code, report = _report(BASE, swapped)
    _check(code == 1, "reordering fields must fail")
    change = _find(report, "fields_reordered", "demo.Inner")
    _check(change["old"] == ["a", "b"] and change["new"] == ["b", "a"], f"order not reported: {change}")
    _check("field_type_changed" not in _kinds(report, "breaking"), "reorder must not be reported as N type changes")


def test_reorder_with_extension_addition_is_still_breaking():
    old = """\
package demo;
message Evolving {
  option msgid = 4;
  uint8 a = 1;
  uint8 b = 2;
}
"""
    new = """\
package demo;
message Evolving {
  option msgid = 4;
  uint8 b = 1;
  uint8 a = 2;
  option extensions_start = 3;
  uint8 c = 3;
}
"""
    code, report = _report(old, new)
    _check(code == 1, f"reordering common fields must fail despite an extension addition: {report}")
    reorder = _find(report, "fields_reordered", "demo.Evolving")
    _check(reorder["old"] == ["a", "b"] and reorder["new"] == ["b", "a"],
           f"common field order not reported: {reorder}")
    _find(report, "field_extension_added", "demo.Evolving.c")


def test_message_removed_and_added():
    removed = _edit(BASE, "message Evolving {\n  option msgid = 4;\n  uint8 a = 1;\n}\n", "")
    code, report = _report(BASE, removed)
    _check(code == 1, "removed message must fail")
    _find(report, "message_removed", "demo.Evolving")

    added = BASE + "\nmessage Extra {\n  option msgid = 9;\n  uint8 a = 1;\n}\n"
    code, report = _report(BASE, added)
    _check(code == 0, "adding a message is wire compatible")
    _find(report, "message_added", "demo.Extra")
    _check(report["wire_compatible"] is True, "added message is wire compatible")


# ---------------------------------------------------------------------------
# Order-sensitive oneof variants
# ---------------------------------------------------------------------------

def test_oneof_variant_reorder_is_breaking_with_discriminator_values():
    swapped = _edit(BASE, "    Small small = 1;\n    Big big = 2;\n", "    Big big = 1;\n    Small small = 2;\n")
    code, report = _report(BASE, swapped)
    _check(code == 1, "variant reordering must fail")
    change = _find(report, "variants_reordered", "demo.Choice.data")
    _check(change["old"] == ["small", "big"] and change["new"] == ["big", "small"], f"order not reported: {change}")
    _check("small 1 -> 2" in change["message"] and "big 2 -> 1" in change["message"],
           f"discriminator values missing: {change['message']}")


def test_oneof_variant_type_change_and_removal_are_breaking():
    retyped = _edit(BASE, "    Big big = 2;\n", "    Small big = 2;\n")
    code, report = _report(BASE, retyped)
    _check(code == 1, "variant type change must fail")
    _find(report, "variant_type_changed", "demo.Choice.data.big")

    removed = _edit(BASE, "    Big big = 2;\n", "")
    code, report = _report(BASE, removed)
    _check(code == 1, "variant removal must fail")
    _find(report, "variant_removed", "demo.Choice.data.big")


def test_oneof_variant_rename_is_source_only():
    renamed = _edit(BASE, "    Big big = 2;\n", "    Big large = 2;\n")
    code, report = _report(BASE, renamed)
    _check(code == 0, "a variant rename keeps the wire format")
    _check(_kinds(report, "rename") == ["variant_renamed"], f"unexpected: {report['changes']}")
    _check(_kinds(report, "breaking") == [], "variant rename must not be breaking")


# ---------------------------------------------------------------------------
# Extensions
# ---------------------------------------------------------------------------

def test_appended_extension_field_and_variant_are_compatible():
    extended = _edit(BASE, "message Evolving {\n  option msgid = 4;\n  uint8 a = 1;\n}",
                     "message Evolving {\n  option msgid = 4;\n  uint8 a = 1;\n\n  option extensions_start = 2;\n  uint32 b = 2;\n}")
    code, report = _report(BASE, extended)
    _check(code == 0, f"appending an extension must be compatible: {report['changes']}")
    _check(_kinds(report, "breaking") == [], f"unexpected breaking: {report['changes']}")
    _find(report, "field_extension_added", "demo.Evolving.b")
    _find(report, "extensions_start_changed", "demo.Evolving")

    with_variant = _edit(BASE, "    Big big = 2;\n",
                         "    Big big = 2;\n\n    option extensions_start = 3;\n    Mid mid = 3;\n")
    with_variant = _edit(with_variant, "message Inner {", "message Mid {\n  uint16 v = 1;\n}\n\nmessage Inner {")
    base_with_mid = _edit(BASE, "message Inner {", "message Mid {\n  uint16 v = 1;\n}\n\nmessage Inner {")
    code, report = _report(base_with_mid, with_variant)
    _check(code == 0, f"appending an extension variant must be compatible: {report['changes']}")
    _find(report, "variant_extension_added", "demo.Choice.data.mid")


def test_growing_oneof_union_that_shifts_later_oneof_is_breaking():
    old = """\
package demo;
message TwoChoices {
  option msgid = 8;
  oneof first {
    option discriminator = "field_order";
    option extensions_start = 2;
    uint8 small = 1;
    uint8 extra = 2;
  }
  oneof second {
    option discriminator = "field_order";
    uint8 other = 1;
  }
}
"""
    new = old.replace(
        "    uint8 extra = 2;\n",
        "    uint8 extra = 2;\n    uint64 large = 3;\n")
    code, report = _report(old, new)
    _check(code == 1, f"union growth must not shift the later discriminator compatibly: {report}")
    _find(report, "variant_extension_added", "demo.TwoChoices.first.large")
    shifted = _find(report, "oneof_offset_changed", "demo.TwoChoices.second")
    _check(shifted["old"] == 2 and shifted["new"] == 9, f"unexpected discriminator offsets: {shifted}")
    _check(_kinds(report, "breaking") == ["oneof_offset_changed"],
           f"only the shifted later oneof should be breaking: {report['changes']}")


def test_moving_a_field_into_the_extension_block_is_breaking():
    base = _edit(BASE, "message Evolving {\n  option msgid = 4;\n  uint8 a = 1;\n}",
                 "message Evolving {\n  option msgid = 4;\n  uint8 a = 1;\n  uint32 b = 2;\n}")
    ext = _edit(base, "uint8 a = 1;\n  uint32 b = 2;\n}", "uint8 a = 1;\n  option extensions_start = 2;\n  uint32 b = 2;\n}")
    code, report = _report(base, ext)
    _check(code == 1, f"turning a base field into an extension changes the base layout: {report['changes']}")
    _find(report, "field_extension_changed", "demo.Evolving.b")
    _find(report, "magic_bytes_changed", "demo.Evolving")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

def test_enum_changes():
    value_changed = _edit(BASE, "RUN = 1;", "RUN = 2;")
    code, report = _report(BASE, value_changed)
    _check(code == 1, "enum value change must fail")
    _find(report, "enum_entry_value_changed", "demo.Mode.RUN")

    removed = _edit(BASE, "  RUN = 1;\n", "")
    code, report = _report(BASE, removed)
    _check(code == 1, "enum entry removal must fail")
    _find(report, "enum_entry_removed", "demo.Mode.RUN")

    added = _edit(BASE, "  RUN = 1;\n", "  RUN = 1;\n  STOP = 2;\n")
    code, report = _report(BASE, added)
    _check(code == 0, "enum entry addition is wire compatible")
    _find(report, "enum_entry_added", "demo.Mode.STOP")

    renamed = _edit(BASE, "RUN = 1;", "RUNNING = 1;")
    code, report = _report(BASE, renamed)
    _check(code == 0, "enum entry rename is source-only")
    _check(_kinds(report, "rename") == ["enum_entry_renamed"], f"unexpected: {report['changes']}")


def test_enum_rename_is_source_only_and_not_a_field_type_change():
    renamed = _edit(BASE, "enum Mode {", "enum Operation {")
    renamed = _edit(renamed, "Mode mode = 3;", "Operation mode = 3;")
    code, report = _report(BASE, renamed)
    _check(code == 0, f"enum rename must be wire compatible: {report['changes']}")
    _check(_kinds(report, "rename") == ["enum_renamed"], f"unexpected: {report['changes']}")
    _check(_kinds(report, "breaking") == [], "enum rename must not be breaking")


def test_message_scoped_enums_follow_their_message():
    base = _edit(BASE, "message Evolving {\n  option msgid = 4;\n  uint8 a = 1;\n}",
                 "message Evolving {\n  option msgid = 4;\n  enum Kind {\n    A = 0;\n    B = 1;\n  }\n  Kind kind = 1;\n}")
    code, report = _report(base, _edit(base, "B = 1;", "B = 3;"))
    _check(code == 1, "nested enum value change must fail")
    _find(report, "enum_entry_value_changed", "demo.Evolving.Kind.B")

    # Renaming the message must not report its nested enum as renamed/removed.
    code, report = _report(base, _edit(base, "message Evolving", "message Developing"))
    _check(code == 0, f"renaming a message with a nested enum is source-only: {report['changes']}")
    _check(_kinds(report, "rename") == ["message_renamed"], f"unexpected: {report['changes']}")

    code, report = _report(base, _edit(base, "enum Kind", "enum Type").replace("Kind kind", "Type kind"))
    _check(code == 0 and _kinds(report, "rename") == ["enum_renamed"], f"nested enum rename: {report['changes']}")

    flattened = _edit(base, "  enum Kind {\n    A = 0;\n    B = 1;\n  }\n  Kind kind = 1;", "  uint8 kind = 1;")
    code, report = _report(base, flattened)
    _check(code == 1, "removing a nested enum must fail")
    _find(report, "enum_removed", "demo.Evolving.Kind")


def test_multi_package_schemas():
    other = "package other;\noption pkgid = 8;\n\nmessage Ping {\n  option msgid = 1;\n  uint8 seq = 1;\n}\n"
    main = 'package demo;\noption pkgid = 7;\nimport "other.sf";\n\nmessage Wrap {\n  option msgid = 1;\n  other.Ping ping = 1;\n}\n'
    code, report = _report(main, main, files={"other.sf": other})
    _check(code == 0 and report["changes"] == [], f"identical multi-package schemas: {report['changes']}")

    # Same schema text in both runs; compare against a changed imported package
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        (tmp / "old").mkdir()
        (tmp / "new").mkdir()
        (tmp / "old" / "other.sf").write_text(other)
        (tmp / "old" / "main.sf").write_text(main)
        (tmp / "new" / "other.sf").write_text(other.replace("uint8 seq", "uint16 seq"))
        (tmp / "new" / "main.sf").write_text(main)
        env = dict(os.environ, PYTHONPATH=str(SRC_DIR))
        result = subprocess.run([sys.executable, str(SRC_DIR / "main.py"), "diff", str(tmp / "old" / "main.sf"),
                                 str(tmp / "new" / "main.sf"), "--format", "json"],
                                capture_output=True, text=True, env=env)
    _check(result.returncode == 1, f"imported package change must fail: {result.stdout}{result.stderr}")
    report = json.loads(result.stdout)
    _find(report, "field_type_changed", "other.Ping.seq")
    # The embedding message keeps its layout in the base portion but grows by a byte.
    _find(report, "size_changed", "demo.Wrap")


# ---------------------------------------------------------------------------
# Source-only renames
# ---------------------------------------------------------------------------

def test_field_and_message_renames_are_reported_separately():
    renamed = _edit(BASE, "uint32 time = 1;", "uint32 timestamp = 1;")
    code, report = _report(BASE, renamed)
    _check(code == 0, "a field rename keeps the wire format")
    _check(_kinds(report, "rename") == ["field_renamed"], f"unexpected: {report['changes']}")
    _check(_find(report, "field_renamed")["new"] == "timestamp", "new field name not reported")

    code, report = _report(BASE, renamed, "--fail-on", "rename")
    _check(code == 1, "--fail-on rename must fail on a rename")
    code, report = _report(BASE, renamed, "--fail-on", "any")
    _check(code == 1, "--fail-on any must fail on a rename")


def test_message_rename_changes_magic_bytes_of_embedding_messages():
    """Magic bytes hash the *name* of embedded message types, so renaming a
    message that others embed is not wire-neutral, even though the message ID is
    unchanged.  The rename and the magic-byte change are reported separately."""
    renamed = BASE.replace("message Inner", "message Core").replace("Inner inner = 2;", "Core inner = 2;")
    code, report = _report(BASE, renamed)
    _check(code == 1, "renaming an embedded message changes the embedding message's magic bytes")
    _find(report, "message_renamed", "demo.Inner")
    magic = _find(report, "magic_bytes_changed", "demo.Telemetry")
    _check("demo.Inner" in magic["message"], f"cause not reported: {magic['message']}")
    _check(_kinds(report, "breaking") == ["magic_bytes_changed"],
           f"only the magic bytes should be breaking: {report['changes']}")


def test_rename_of_unembedded_message_is_source_only():
    renamed = _edit(BASE, "message Evolving", "message Developing")
    code, report = _report(BASE, renamed)
    _check(code == 0, f"renaming an unembedded message keeps the wire format: {report['changes']}")
    _check(_kinds(report, "rename") == ["message_renamed"], f"unexpected: {report['changes']}")
    _check(report["wire_compatible"] is True, "must be wire compatible")


# ---------------------------------------------------------------------------
# Defaults and size options
# ---------------------------------------------------------------------------

def test_default_change_is_compatible():
    base = _edit(BASE, "message Evolving {\n  option msgid = 4;\n  uint8 a = 1;\n}",
                 "message Evolving {\n  option msgid = 4;\n  uint8 a = 1 [default = 1];\n}")
    new = _edit(base, "[default = 1]", "[default = 2]")
    code, report = _report(base, new)
    _check(code == 0, "a default change does not alter the wire format")
    _find(report, "field_default_changed", "demo.Evolving.a")


# ---------------------------------------------------------------------------
# CLI behaviour
# ---------------------------------------------------------------------------

def test_text_report_groups_categories():
    renamed = _edit(BASE, "uint32 time = 1;", "uint32 timestamp = 1;")
    changed = _edit(renamed, "msgid = 2;", "msgid = 20;")
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        (tmp / "old.sf").write_text(BASE)
        (tmp / "new.sf").write_text(changed)
        env = dict(os.environ, PYTHONPATH=str(SRC_DIR))
        result = subprocess.run([sys.executable, str(SRC_DIR / "main.py"), "diff", str(tmp / "old.sf"),
                                 str(tmp / "new.sf")], capture_output=True, text=True, env=env)
    _check(result.returncode == 1, f"expected exit 1, got {result.returncode}")
    out = result.stdout
    _check("Wire-breaking changes (1):" in out, f"missing breaking section:\n{out}")
    _check("Source-only renames (review separately) (1):" in out, f"missing rename section:\n{out}")
    _check(out.index("Wire-breaking") < out.index("Source-only renames"), "breaking changes must be listed first")
    _check("Result: WIRE-BREAKING" in out, f"missing result line:\n{out}")


def test_invalid_input_exits_with_error_status():
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        (tmp / "good.sf").write_text(BASE)
        (tmp / "bad.sf").write_text("package demo;\nmessage Broken {\n  Missing x = 1;\n}\n")
        env = dict(os.environ, PYTHONPATH=str(SRC_DIR))

        def run(*paths):
            return subprocess.run([sys.executable, str(SRC_DIR / "main.py"), "diff", *map(str, paths)],
                                  capture_output=True, text=True, env=env)

        result = run(tmp / "good.sf", tmp / "missing.sf")
        _check(result.returncode == 2 and "file not found" in result.stderr, f"missing file: {result.returncode} {result.stderr}")
        result = run(tmp / "good.sf", tmp / "bad.sf")
        _check(result.returncode == 2 and "schema is not valid" in result.stderr,
               f"invalid schema: {result.returncode} {result.stderr}")


def test_malformed_nested_snapshot_exits_with_load_error():
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        (tmp / "baseline.json").write_text(
            json.dumps({"version": 1, "packages": {"demo": {}}}), encoding="utf-8")
        (tmp / "current.sf").write_text(BASE, encoding="utf-8")
        env = dict(os.environ, PYTHONPATH=str(SRC_DIR))
        result = subprocess.run(
            [sys.executable, str(SRC_DIR / "main.py"), "diff", str(tmp / "baseline.json"),
             str(tmp / "current.sf"), "--format", "json"],
            capture_output=True, text=True, env=env)
    _check(result.returncode == 2, f"malformed snapshot should exit with load-error status 2: {result}")
    _check("invalid schema snapshot" in result.stderr and "Traceback" not in result.stderr,
           f"malformed snapshot must be reported without traceback: {result.stderr}")


def test_snapshot_round_trip_matches_schema_diff():
    changed = _edit(BASE, "uint32 time = 1;", "uint64 time = 1;")
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        (tmp / "old.sf").write_text(BASE)
        (tmp / "new.sf").write_text(changed)
        env = dict(os.environ, PYTHONPATH=str(SRC_DIR))
        main = str(SRC_DIR / "main.py")
        written = subprocess.run([sys.executable, main, "diff", str(tmp / "old.sf"), str(tmp / "old.sf"),
                                  "--write-snapshot", str(tmp / "baseline.json")],
                                 capture_output=True, text=True, env=env)
        _check(written.returncode == 0, f"snapshot write failed: {written.stderr}")
        direct = subprocess.run([sys.executable, main, "diff", str(tmp / "old.sf"), str(tmp / "new.sf"),
                                 "--format", "json"], capture_output=True, text=True, env=env)
        via_snapshot = subprocess.run([sys.executable, main, "diff", str(tmp / "baseline.json"), str(tmp / "new.sf"),
                                       "--format", "json"], capture_output=True, text=True, env=env)
    _check(direct.returncode == via_snapshot.returncode == 1, "both comparisons must fail")
    direct_changes = [(c["kind"], c["path"]) for c in json.loads(direct.stdout)["changes"]]
    snapshot_changes = [(c["kind"], c["path"]) for c in json.loads(via_snapshot.stdout)["changes"]]
    _check(direct_changes == snapshot_changes, f"snapshot baseline differs: {direct_changes} vs {snapshot_changes}")


def test_schema_file_named_diff_still_generates():
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        (tmp / "diff").write_text(BASE)
        env = dict(os.environ, PYTHONPATH=str(SRC_DIR))
        result = subprocess.run([sys.executable, str(SRC_DIR / "main.py"), "diff", "--validate"],
                                capture_output=True, text=True, env=env, cwd=tmp)
    _check(result.returncode == 0 and "Validation successful" in result.stdout,
           f"a schema file named 'diff' must still be a schema: {result.stdout}{result.stderr}")
