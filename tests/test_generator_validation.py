#!/usr/bin/env python3
"""
Generator-validation tests: documents the intended error-detection behaviour
for semantically invalid .sf inputs.

Three negative-test scenarios are covered:
  1. Duplicate message IDs within a package (two messages share the same msgid).
  2. Duplicate package IDs across imported packages (two pkgs share pkgid).
  3. Circular imports (A imports B and B imports A).

Each test calls the generator with --validate and asserts that the exit code is
non-zero OR that the output contains an error indicator.  A test fails when the
generator silently accepts input that should be rejected.

NOTE: Tests 1-3 are currently EXPECTED TO FAIL because the generator does not
yet implement this validation.  They serve as documentation of desired behaviour
and will become green once the corresponding generator checks are added.

Usage:
    python tests/test_generator_validation.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
MAIN_PY = SRC_DIR / "main.py"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(sf_path: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, str(MAIN_PY), sf_path, "--validate"]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=cwd)


def _rejected(result: subprocess.CompletedProcess) -> bool:
    """Return True if the generator produced a visible rejection."""
    combined = (result.stdout + result.stderr).lower()
    return (result.returncode != 0
            or "error" in combined
            or "fail" in combined
            or "duplicate" in combined
            or "circular" in combined
            or "cycle" in combined)


PASS_MARKER = "PASS"
FAIL_MARKER = "FAIL"
TODO_MARKER = "TODO"   # test fails because generator does not yet catch this case


def _report(name: str, rejected: bool, expected_reject: bool) -> bool:
    """Print the result line and return overall test success."""
    if rejected == expected_reject:
        print(f"  {PASS_MARKER}: {name}")
        return True
    # The generator does not yet implement this check → mark as TODO
    marker = TODO_MARKER if expected_reject else FAIL_MARKER
    adjective = "reject" if expected_reject else "accept"
    print(f"  {marker}: {name} — generator should {adjective} this input")
    return False


# ---------------------------------------------------------------------------
# Test 1 – Duplicate message IDs within a package
# ---------------------------------------------------------------------------

def test_duplicate_msgid() -> bool:
    """Two messages in one package with identical msgid must be rejected."""
    proto = """\
package dup_id_test;

message Alpha {
  option msgid = 42;
  uint32 value = 1;
}

// Intentional duplicate — same msgid as Alpha
message Beta {
  option msgid = 42;
  uint32 value = 1;
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        sf = Path(tmp) / "dup_msgid.sf"
        sf.write_text(proto)
        result = _run(str(sf))
    return _report("duplicate_msgid", _rejected(result), expected_reject=True)


# ---------------------------------------------------------------------------
# Test 2 – Duplicate package IDs across imported packages
# ---------------------------------------------------------------------------

def test_duplicate_pkgid() -> bool:
    """Two imported packages sharing the same pkgid must be rejected."""
    proto_dep = """\
package pkg_dep;
option pkgid = 7;

message DepMsg {
  option msgid = 1;
  uint32 y = 1;
}
"""
    proto_main = """\
import "pkg_dep.sf";
package pkg_main;
option pkgid = 7;

message MainMsg {
  option msgid = 1;
  uint32 x = 1;
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "pkg_dep.sf").write_text(proto_dep)
        main_sf = Path(tmp) / "pkg_main.sf"
        main_sf.write_text(proto_main)
        result = _run(str(main_sf))
    return _report("duplicate_pkgid", _rejected(result), expected_reject=True)


# ---------------------------------------------------------------------------
# Test 3 – Circular imports
# ---------------------------------------------------------------------------

def test_circular_import() -> bool:
    """A → B → A circular import chain must be rejected."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "circ_a.sf").write_text("""\
import "circ_b.sf";
package circ_a;
option pkgid = 1;

message MsgA {
  option msgid = 1;
  uint32 a = 1;
}
""")
        (Path(tmp) / "circ_b.sf").write_text("""\
import "circ_a.sf";
package circ_b;
option pkgid = 2;

message MsgB {
  option msgid = 1;
  uint32 b = 1;
}
""")
        result = _run("circ_a.sf", cwd=tmp)
    return _report("circular_import", _rejected(result), expected_reject=True)


# ---------------------------------------------------------------------------
# Bonus: currently-working validation (generator already rejects these)
# ---------------------------------------------------------------------------

def test_multi_package_missing_pkgid() -> bool:
    """
    When two packages are compiled together and neither declares pkgid,
    the generator must reject the input.  This case IS currently handled.
    """
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "dep.sf").write_text("""\
package dep_pkg;

message DepMsg {
  option msgid = 1;
  uint32 y = 1;
}
""")
        main_sf = Path(tmp) / "main_pkg.sf"
        main_sf.write_text("""\
import "dep.sf";
package main_pkg;

message MainMsg {
  option msgid = 1;
  uint32 x = 1;
}
""")
        result = _run(str(main_sf))
    return _report("multi_package_missing_pkgid", _rejected(result), expected_reject=True)


# =============================================================================
# Tier B §3 additions — 10 untested generator-validation rules from
# docs/.../test-coverage.md §8.  Each test is currently EXPECTED TO FAIL
# (marked TODO) and serves as documentation for the generator change that
# must follow.  Drop the test into the suite, ship the generator rejection
# in a follow-up PR, and the TODO flips to PASS without further edits here.
# =============================================================================

def test_duplicate_field_numbers() -> bool:
    """Two fields in one message with the same field number must be rejected."""
    proto = """\
package dup_field_test;

message Foo {
  option msgid = 1;
  uint32 a = 1;
  uint32 b = 1;
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        sf = Path(tmp) / "dup_field.sf"
        sf.write_text(proto)
        result = _run(str(sf))
    return _report("duplicate_field_numbers", _rejected(result), expected_reject=True)


def test_array_missing_size() -> bool:
    """An array field with neither `size` nor `max_size` set must be rejected."""
    proto = """\
package missing_array_size_test;

message Foo {
  option msgid = 1;
  repeated uint32 xs = 1;
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        sf = Path(tmp) / "missing_array_size.sf"
        sf.write_text(proto)
        result = _run(str(sf))
    return _report("array_missing_size_or_max_size", _rejected(result), expected_reject=True)


def test_string_missing_size() -> bool:
    """A string field with neither `size` nor `max_size` set must be rejected."""
    proto = """\
package missing_string_size_test;

message Foo {
  option msgid = 1;
  string name = 1;
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        sf = Path(tmp) / "missing_string_size.sf"
        sf.write_text(proto)
        result = _run(str(sf))
    return _report("string_missing_size_or_max_size", _rejected(result), expected_reject=True)


def test_string_array_missing_element_size() -> bool:
    """A `repeated string` field without `element_size` must be rejected."""
    proto = """\
package missing_element_size_test;

message Foo {
  option msgid = 1;
  repeated string names = 1 [max_size = 4];
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        sf = Path(tmp) / "missing_element_size.sf"
        sf.write_text(proto)
        result = _run(str(sf))
    return _report("string_array_missing_element_size", _rejected(result), expected_reject=True)


def test_array_max_size_over_255_allowed() -> bool:
    """An array with `max_size > 255` must be accepted (two-byte count)."""
    proto = """\
package max_size_over_255_allowed_test;

message Foo {
  option msgid = 1;
  repeated uint32 xs = 1 [max_size = 300];
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        sf = Path(tmp) / "max_size_over_255_allowed.sf"
        sf.write_text(proto)
        result = _run(str(sf))
    return _report("array_max_size_greater_than_255_allowed", _rejected(result), expected_reject=False)


def test_string_max_size_over_255_allowed() -> bool:
    """A string with `max_size > 255` must be accepted (two-byte length)."""
    proto = """\
package string_max_size_over_255_allowed_test;

message Foo {
  option msgid = 1;
  string name = 1 [max_size = 300];
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        sf = Path(tmp) / "string_max_size_over_255_allowed.sf"
        sf.write_text(proto)
        result = _run(str(sf))
    return _report("string_max_size_greater_than_255_allowed", _rejected(result), expected_reject=False)


def test_envelope_zero_oneofs() -> bool:
    """An envelope message that declares no `oneof` block must be rejected."""
    proto = """\
package envelope_no_oneof_test;

message Empty {
  option msgid = 1;
  option envelope = true;
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        sf = Path(tmp) / "envelope_no_oneof.sf"
        sf.write_text(proto)
        result = _run(str(sf))
    return _report("envelope_with_zero_oneofs", _rejected(result), expected_reject=True)


def test_envelope_non_message_oneof_fields() -> bool:
    """An envelope `oneof` whose arms are scalars (not messages) must be rejected."""
    proto = """\
package envelope_scalar_oneof_test;

message Bad {
  option msgid = 1;
  option envelope = true;
  oneof payload {
    uint32 a = 1;
    uint32 b = 2;
  }
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        sf = Path(tmp) / "envelope_scalar_oneof.sf"
        sf.write_text(proto)
        result = _run(str(sf))
    return _report("envelope_non_message_oneof_field", _rejected(result), expected_reject=True)


def test_envelope_msgid_discriminator_without_msgid() -> bool:
    """An envelope using `discriminator = "msgid"` whose oneof arms
    reference messages that do not declare `option msgid` must be rejected."""
    proto = """\
package env_msgid_missing_test;

message Inner { uint32 v = 1; } // No msgid here on purpose.

message Outer {
  option msgid = 1;
  option envelope = true;
  option discriminator = "msgid";
  oneof payload {
    Inner only = 1;
  }
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        sf = Path(tmp) / "env_msgid_missing.sf"
        sf.write_text(proto)
        result = _run(str(sf))
    return _report("envelope_msgid_discriminator_without_msgid", _rejected(result), expected_reject=True)


def test_invalid_discriminator_value() -> bool:
    """An envelope with an unknown `discriminator` value must be rejected."""
    proto = """\
package invalid_disc_test;

message Inner { option msgid = 2; uint32 v = 1; }

message Outer {
  option msgid = 1;
  option envelope = true;
  option discriminator = "not_a_real_discriminator";
  oneof payload {
    Inner only = 1;
  }
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        sf = Path(tmp) / "invalid_disc.sf"
        sf.write_text(proto)
        result = _run(str(sf))
    return _report("invalid_discriminator_value", _rejected(result), expected_reject=True)


def test_field_number_zero() -> bool:
    """Field numbers must be ≥ 1 (proto3 convention)."""
    proto = """\
package zero_field_num_test;

message Foo {
  option msgid = 1;
  uint32 a = 0;
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        sf = Path(tmp) / "zero_field_num.sf"
        sf.write_text(proto)
        result = _run(str(sf))
    return _report("field_number_zero", _rejected(result), expected_reject=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Running generator validation tests...\n")
    test_fns = [
        # Original three TODO cases + the working multi-package check
        test_duplicate_msgid,
        test_duplicate_pkgid,
        test_circular_import,
        test_multi_package_missing_pkgid,
        # Tier B §3 additions (10 new TODO cases from test-coverage.md §8)
        test_duplicate_field_numbers,
        test_array_missing_size,
        test_string_missing_size,
        test_string_array_missing_element_size,
        test_array_max_size_over_255_allowed,
        test_string_max_size_over_255_allowed,
        test_envelope_zero_oneofs,
        test_envelope_non_message_oneof_fields,
        test_envelope_msgid_discriminator_without_msgid,
        test_invalid_discriminator_value,
        test_field_number_zero,
    ]
    results = [fn() for fn in test_fns]
    passed = sum(results)
    total = len(results)
    todo_count = total - passed
    print(f"\n{passed}/{total} tests passed.")
    if todo_count > 0:
        print(f"{todo_count} test(s) marked TODO — generator does not yet reject these inputs.")
        print("These are known pending items, not regressions, but are tracked as failures.")
        print("Implement the corresponding generator checks to make them pass.")
    sys.exit(0 if todo_count == 0 else 1)
