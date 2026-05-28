#!/usr/bin/env python3
"""
Wire-format regression check.

Re-encodes the canonical test fixtures using the Python reference encoder
and compares the resulting bytes against the goldens committed under
``tests/golden/``. Any difference is a wire-format change and must be
either reverted or, if intentional, explicitly committed by re-running this
script with ``--update``.

See: docs/src/content/docs/reference/conformance.md

Usage:
    python tests/check_golden.py            # verify (default; CI mode)
    python tests/check_golden.py --update   # regenerate goldens
    python tests/check_golden.py --verbose  # show per-file pass/fail detail

Exit codes:
    0 — all goldens match
    1 — at least one golden differs (or is missing)
    2 — generator/encoder failed
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
TESTS_DIR = REPO_ROOT / "tests"
GOLDEN_DIR = TESTS_DIR / "golden"
GEN_PY_DIR = TESTS_DIR / "generated" / "py"

# (suite, profile) → name of the file under tests/golden/
SUITES: List[Tuple[str, str, str]] = [
    # encoder script,                  profile,    golden filename
    ("py/test_standard.py",            "standard", "standard_standard.bin"),
    ("py/test_standard.py",            "sensor",   "standard_sensor.bin"),
    ("py/test_standard.py",            "ipc",      "standard_ipc.bin"),
    ("py/test_standard.py",            "bulk",     "standard_bulk.bin"),
    ("py/test_standard.py",            "network",  "standard_network.bin"),
    ("py/test_extended.py",            "bulk",     "extended_bulk.bin"),
    ("py/test_extended.py",            "network",  "extended_network.bin"),
    ("py/test_variable_flag.py",       "bulk",     "variable_bulk.bin"),
]

PROTOS = [
    "test_messages.sf",
    "pkg_test_messages.sf",
    "extended_messages.sf",
    "envelope_messages.sf",
    "wire_evolution_messages.sf",
]


def _ensure_generated(verbose: bool) -> None:
    """Run the Python code generator if generated output is missing."""
    target = GEN_PY_DIR / "struct_frame" / "generated" / "serialization_test.py"
    if target.exists():
        if verbose:
            print(f"[skip] generated code already present at {target.parent}")
        return

    if verbose:
        print(f"[gen ] generating Python code into {GEN_PY_DIR} ...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    for proto in PROTOS:
        proto_path = TESTS_DIR / "proto" / proto
        cmd = [sys.executable, str(SRC_DIR / "main.py"), str(proto_path),
               "--build_py", "--py_path", str(GEN_PY_DIR),
               "--force"]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            print(f"[FAIL] code generation failed for {proto}", file=sys.stderr)
            sys.exit(2)


def _encode(script: str, profile: str, out_path: Path, verbose: bool) -> bool:
    """Run a Python encoder; return True on success."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, str(TESTS_DIR / script), "encode", profile, str(out_path)]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        print(f"[FAIL] encoding failed: {script} {profile}", file=sys.stderr)
        return False
    if verbose:
        print(f"[enc ] {script} {profile} -> {out_path} ({out_path.stat().st_size} bytes)")
    return True


def _hex_preview(data: bytes, limit: int = 32) -> str:
    head = data[:limit]
    return " ".join(f"{b:02x}" for b in head) + (" …" if len(data) > limit else "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--update", action="store_true",
                        help="overwrite goldens with freshly encoded bytes")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="show per-file detail")
    args = parser.parse_args()

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    _ensure_generated(args.verbose)

    failures: List[str] = []
    updated: List[str] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for script, profile, golden_name in SUITES:
            fresh_path = tmp / golden_name
            if not _encode(script, profile, fresh_path, args.verbose):
                return 2
            fresh_bytes = fresh_path.read_bytes()
            golden_path = GOLDEN_DIR / golden_name

            if args.update:
                golden_path.write_bytes(fresh_bytes)
                updated.append(golden_name)
                continue

            if not golden_path.exists():
                failures.append(f"MISSING: {golden_name} (run with --update)")
                continue

            golden_bytes = golden_path.read_bytes()
            if fresh_bytes != golden_bytes:
                msg = (
                    f"DRIFT: {golden_name}\n"
                    f"  expected ({len(golden_bytes)} bytes): {_hex_preview(golden_bytes)}\n"
                    f"  actual   ({len(fresh_bytes)} bytes): {_hex_preview(fresh_bytes)}"
                )
                failures.append(msg)
            elif args.verbose:
                print(f"[ ok ] {golden_name}")

    if args.update:
        print(f"\nUpdated {len(updated)} golden file(s) under {GOLDEN_DIR.relative_to(REPO_ROOT)}:")
        for name in updated:
            print(f"  {name}")
        print("\nReview the diff and commit deliberately. See conformance.md § 8.")
        return 0

    if failures:
        print(f"\n[FAIL] {len(failures)} wire-format regression(s) detected:\n")
        for msg in failures:
            print(msg + "\n")
        print("If this drift is intentional, re-run with --update and commit the "
              "regenerated goldens together with a CHANGELOG entry. See "
              "docs/src/content/docs/reference/conformance.md § 8.")
        return 1

    print(f"[PASS] all {len(SUITES)} golden(s) match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
