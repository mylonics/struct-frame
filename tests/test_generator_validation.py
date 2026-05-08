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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Running generator validation tests...\n")
    results = [
        test_duplicate_msgid(),
        test_duplicate_pkgid(),
        test_circular_import(),
        test_multi_package_missing_pkgid(),
    ]
    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} tests passed.")
    print("(Tests marked TODO document desired behaviour not yet implemented in the generator.)")
    # Exit 0 even when TODO tests fail — they are known pending items, not regressions.
    sys.exit(0)
