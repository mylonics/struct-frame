#!/usr/bin/env python3
"""
Wire-format regression check.

Re-encodes the canonical test fixtures using the Python reference encoder
and compares the resulting bytes against the goldens committed under
``tests/golden/``.  Also runs a **decode direction**: each golden file is
fed to the Python reference decoder and the parsed message count is
validated, confirming that the decoder can read its own encoder's output
byte-for-byte.  Any difference is a wire-format change and must be either
reverted or, if intentional, explicitly committed by re-running this script
with ``--update``.

Finally, runs a **cross-language decode** pass: every already-built
non-Python runner (C, C++, TypeScript, JavaScript, C#, Rust) decodes the
same committed golden files. Without this, the goldens are only ever
verified against the Python encoder/decoder pair that produced them --
nothing ties them to what the other six languages actually do with the
same bytes. If no other-language runners are built (fresh checkout with
no prior ``test_all.py``/``run_tests.py`` run), this pass is skipped with
a note rather than failing, since ``check_golden.py`` is also used
standalone; in CI, ``test_all.py`` always compiles every language first,
so the pass is fully enforced there.

See: docs/src/content/docs/reference/conformance.md

Usage:
    python tests/check_golden.py            # verify (default; CI mode)
    python tests/check_golden.py --update   # regenerate goldens
    python tests/check_golden.py --verbose  # show per-file pass/fail detail
    python tests/check_golden.py --no-decode  # deprecated (decode still runs)

Exit codes:
    0 — all goldens match (and all decodes pass)
    1 — at least one golden differs / decode fails (or is missing)
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


def _decode(script: str, profile: str, golden_path: Path, verbose: bool) -> bool:
    """Run the Python decoder against a golden file; return True on success."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, str(TESTS_DIR / script), "decode", profile, str(golden_path)]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        print(f"[FAIL] decode failed: {script} {profile} {golden_path.name}",
              file=sys.stderr)
        return False
    if verbose:
        print(f"[dec ] {script} {profile} <- {golden_path.name}")
    return True


# (script, profile, golden filename) -> (runner_name, expected message count).
# Mirrors SUITES above; kept separate so SUITES stays a pure golden-file table.
_CROSS_LANG_RUNNER: dict = {}


def _cross_lang_runner_info(script: str):
    """Map a golden's encoder script to (runner_name, expected_count) for
    decoding it with every other language's runner. Lazily imports
    run_tests.py's message-count constants to stay in sync with the
    canonical values instead of duplicating them here."""
    if not _CROSS_LANG_RUNNER:
        from run_tests import STANDARD_MESSAGE_COUNT, EXTENDED_MESSAGE_COUNT
        _CROSS_LANG_RUNNER.update({
            "py/test_standard.py": ("test_standard", STANDARD_MESSAGE_COUNT),
            "py/test_extended.py": ("test_extended", EXTENDED_MESSAGE_COUNT),
            "py/test_variable_flag.py": ("test_variable_flag", 7),
        })
    return _CROSS_LANG_RUNNER[script]


def _decode_cross_language(verbose: bool) -> List[str]:
    """Decode every committed golden with every already-built non-Python
    runner. Returns a list of failure messages (empty means all good, or
    nothing was built to check -- see the module docstring)."""
    from run_tests import TestRunner

    runner = TestRunner(verbose=verbose, quiet=not verbose)
    other_langs = [lang for lid, lang in runner.languages.items() if lid not in ("py", "gql")]

    failures: List[str] = []
    not_built: List[str] = []
    decoded_any = False

    for script, profile, golden_name in SUITES:
        golden_path = GOLDEN_DIR / golden_name
        if not golden_path.exists():
            continue
        runner_name, expected_count = _cross_lang_runner_info(script)
        for lang in other_langs:
            success, stdout, stderr = runner._run_test_runner(lang, "decode", profile, golden_path, runner_name)
            if not success and "not found" in stderr.lower():
                # Runner/script/DLL doesn't exist yet -- not built, not a
                # decode failure. _run_test_runner returns this distinct
                # reason string (vs. an actual decode error) in that case.
                if lang.id not in not_built:
                    not_built.append(lang.id)
                continue
            decoded_any = True
            count = runner._extract_message_count(stdout, stderr)
            if success and count == expected_count:
                if verbose:
                    print(f"[ ok ] {lang.id}: {golden_name} decoded ({count} messages)")
                continue
            failures.append(
                f"{lang.id}: FAILED to decode {golden_name} via {runner_name} "
                f"(expected {expected_count} messages, got {count}, success={success})"
            )

    if not decoded_any:
        print("[skip] no other-language runners are built; skipping cross-language "
              "golden decode (run test_all.py / run_tests.py first to enable it)")
        return []

    if not_built:
        print(f"[note] cross-language golden decode: {', '.join(sorted(not_built))} "
              f"not built, skipped (others still checked)")

    if not failures:
        checked = sorted(l.id for l in other_langs if l.id not in not_built)
        print(f"[PASS] cross-language golden decode: {', '.join(checked)} all decoded successfully.")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--update", action="store_true",
                        help="overwrite goldens with freshly encoded bytes")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="show per-file detail")
    parser.add_argument("--no-decode", action="store_true",
                        help="deprecated: decode phase is now always enforced")
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

    # -----------------------------------------------------------------
    # DECODE DIRECTION: each golden file is decoded by the Python
    # reference decoder to confirm the decoder accepts its own encoder's
    # byte sequences (conformance §6/§7 row 1).
    # -----------------------------------------------------------------
    if args.no_decode:
        print("[WARN] --no-decode is deprecated and ignored; decode verification is always enforced.")

    decode_failures: List[str] = []
    for script, profile, golden_name in SUITES:
        golden_path = GOLDEN_DIR / golden_name
        if not golden_path.exists():
            decode_failures.append(f"MISSING: {golden_name} (cannot decode)")
            continue
        if not _decode(script, profile, golden_path, args.verbose):
            decode_failures.append(f"DECODE FAIL: {golden_name} ({script} {profile})")

    if decode_failures:
        print(f"\n[FAIL] {len(decode_failures)} decode failure(s):\n")
        for msg in decode_failures:
            print(f"  {msg}")
        return 1

    print(f"[PASS] all {len(SUITES)} golden(s) decoded successfully.")

    # -----------------------------------------------------------------
    # CROSS-LANGUAGE DECODE: every other language's already-built runner
    # decodes the same committed golden files (conformance §6/§7 rows 2-7).
    # -----------------------------------------------------------------
    cross_lang_failures = _decode_cross_language(args.verbose)
    if cross_lang_failures:
        print(f"\n[FAIL] {len(cross_lang_failures)} cross-language decode failure(s):\n")
        for msg in cross_lang_failures:
            print(f"  {msg}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
