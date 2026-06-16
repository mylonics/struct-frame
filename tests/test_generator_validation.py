#!/usr/bin/env python3
"""Generator-validation tests for semantically invalid .sf inputs.

Each case calls the generator with --validate and asserts that the observed
result matches the expected accept/reject behaviour. These are regression
tests, not TODO markers.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from test_utils import _check, run_generator, SRC_DIR

MAIN_PY = SRC_DIR / "main.py"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(sf_path: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    return run_generator(Path(sf_path), "--validate")


def _rejected(result: subprocess.CompletedProcess) -> bool:
    return result.returncode != 0


def _output(result: subprocess.CompletedProcess) -> str:
    return (result.stdout or "") + "\n" + (result.stderr or "")


def _report(name: str, result: subprocess.CompletedProcess, expected_reject: bool,
            expected_msg: str | None = None) -> None:
    """Assert the generator accepted/rejected as expected; call _check on failure."""
    rejected = _rejected(result)
    if rejected != expected_reject:
        adjective = "reject" if expected_reject else "accept"
        _check(False, f"{name} -- generator should {adjective} this input")
    if expected_reject and expected_msg is not None:
        if expected_msg.lower() not in _output(result).lower():
            _check(False,
                   f"{name} -- rejected, but not for the expected reason "
                   f"(expected substring {expected_msg!r} in output)")


# ---------------------------------------------------------------------------
# Test 1 - Duplicate message IDs within a package
# ---------------------------------------------------------------------------

def test_duplicate_msgid() -> None:
    """Two messages in one package with identical msgid must be rejected."""
    proto = """\
package dup_id_test;

message Alpha {
  option msgid = 42;
  uint32 value = 1;
}

// Intentional duplicate -- same msgid as Alpha
message Beta {
  option msgid = 42;
  uint32 value = 1;
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        sf = Path(tmp) / "dup_msgid.sf"
        sf.write_text(proto)
        result = _run(str(sf))
    _report("duplicate_msgid", result, expected_reject=True,
            expected_msg="duplicate msgid")


# ---------------------------------------------------------------------------
# Test 2 - Duplicate package IDs across imported packages
# ---------------------------------------------------------------------------

def test_duplicate_pkgid() -> None:
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
    _report("duplicate_pkgid", result, expected_reject=True,
            expected_msg="duplicate package ID")


# ---------------------------------------------------------------------------
# Test 3 - Circular imports
# ---------------------------------------------------------------------------

def test_circular_import() -> None:
    """A -> B -> A circular import chain must be rejected."""
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
        result = _run(str(Path(tmp) / "circ_a.sf"))
    _report("circular_import", result, expected_reject=True,
            expected_msg="circular")


# ---------------------------------------------------------------------------
# Bonus: currently-working validation (generator already rejects these)
# ---------------------------------------------------------------------------

def test_multi_package_missing_pkgid() -> None:
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
    _report("multi_package_missing_pkgid", result, expected_reject=True,
            expected_msg="Multiple packages are being compiled")


# =============================================================================
# Tier B §3 additions -- generator-validation regression cases from
# docs/.../test-coverage.md §8.
# =============================================================================

def test_duplicate_field_numbers() -> None:
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
    _report("duplicate_field_numbers", result, expected_reject=True,
            expected_msg="must be numbered 1..N")


def test_array_missing_size() -> None:
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
    _report("array_missing_size_or_max_size", result, expected_reject=True,
            expected_msg="missing required size or max_size")


def test_string_missing_size() -> None:
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
    _report("string_missing_size_or_max_size", result, expected_reject=True,
            expected_msg="missing required size or max_size")


def test_string_array_missing_element_size() -> None:
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
    _report("string_array_missing_element_size", result, expected_reject=True,
            expected_msg="missing required element_size")


def test_array_max_size_over_255_allowed() -> None:
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
    _report("array_max_size_greater_than_255_allowed", result, expected_reject=False)


def test_string_max_size_over_255_allowed() -> None:
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
    _report("string_max_size_greater_than_255_allowed", result, expected_reject=False)


def test_envelope_zero_oneofs() -> None:
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
    _report("envelope_with_zero_oneofs", result, expected_reject=True,
            expected_msg="must have exactly one oneof")


def test_envelope_non_message_oneof_fields() -> None:
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
    _report("envelope_non_message_oneof_field", result, expected_reject=True,
            expected_msg="must be a message type")


def test_envelope_msgid_discriminator_without_msgid() -> None:
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
    _report("envelope_msgid_discriminator_without_msgid", result, expected_reject=True,
            expected_msg="not all fields are messages with msgid")


def test_invalid_discriminator_value() -> None:
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
    _report("invalid_discriminator_value", result, expected_reject=True,
            expected_msg="Invalid discriminator option")


def test_field_number_zero() -> None:
    """Field numbers must be >= 1 (proto3 convention)."""
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
    _report("field_number_zero", result, expected_reject=True,
            expected_msg="must be numbered 1..N")
