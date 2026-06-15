#!/usr/bin/env python3
"""
Tests for the hash-based generation caching and ``--force`` flag.

When the generator is invoked twice with the same inputs (proto file, CLI
flags, and struct-frame version) it should skip regeneration on the second
run and print a "no changes detected" message.  Passing ``--force`` must
bypass the cache and regenerate every time regardless of the stored hash.

Covered behaviours:
1. First run writes a ``.structframe.hash`` file to the output directory.
2. Second run without ``--force`` detects a matching hash and skips.
3. Second run with ``--force`` ignores the hash and regenerates.
4. Changing the proto content invalidates the hash and forces regeneration.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from test_utils import _check, run_generator, PROTO_FILE

HASH_FILENAME = ".structframe.hash"


def _run_generator(proto: Path, out_dir: Path, force: bool = False) -> tuple[int, str]:
    flags = ["--build_py", "--py_path", str(out_dir) + os.sep]
    if force:
        flags.append("--force")
    result = run_generator(proto, *flags)
    return result.returncode, result.stdout + result.stderr


def test_hash_file_created():
    """First generation must write a .structframe.hash file."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "gen"
        code, output = _run_generator(PROTO_FILE, out, force=True)
        _check(code == 0, f"Generator failed (exit {code}):\n{output}")
        hash_file = out / HASH_FILENAME
        _check(hash_file.exists(),
               f".structframe.hash should be created after first generation")
        stored_hash = hash_file.read_text().strip()
        _check(len(stored_hash) == 64,
               f"Hash should be a 64-char hex SHA256, got: {stored_hash!r}")


def test_skip_on_unchanged_inputs():
    """Second run with same inputs must skip regeneration (hash matches)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "gen"
        # First run
        code, _ = _run_generator(PROTO_FILE, out, force=True)
        _check(code == 0, "First generation should succeed")

        # Second run (no --force)
        code2, output2 = _run_generator(PROTO_FILE, out, force=False)
        _check(code2 == 0, f"Second generation should succeed, got {code2}")
        _check("no changes detected" in output2.lower(),
               f"Second run should report 'no changes detected', got:\n{output2}")


def test_force_bypasses_cache():
    """--force must regenerate even when the hash matches."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "gen"
        # First run
        code, _ = _run_generator(PROTO_FILE, out, force=True)
        _check(code == 0, "First generation should succeed")

        # Second run with --force
        code2, output2 = _run_generator(PROTO_FILE, out, force=True)
        _check(code2 == 0, f"Forced regeneration should succeed, got {code2}")
        _check("no changes detected" not in output2.lower(),
               f"--force run must NOT skip generation, got:\n{output2}")
        _check("successfully" in output2.lower() or "completed" in output2.lower(),
               f"--force run should report success, got:\n{output2}")


def test_changed_proto_invalidates_hash():
    """Modifying the proto structure causes the hash to change and triggers regen."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        out = tmp_path / "gen"

        # Start with a minimal proto
        proto_v1 = (
            "package cache_test;\n"
            "message MsgA {\n"
            "  option msgid = 1;\n"
            "  uint32 value = 1;\n"
            "}\n"
        )
        proto_v2 = (
            "package cache_test;\n"
            "message MsgA {\n"
            "  option msgid = 1;\n"
            "  uint32 value = 1;\n"
            "  uint32 extra = 2;\n"  # new field
            "}\n"
        )
        proto_copy = tmp_path / "cache_test.sf"
        proto_copy.write_text(proto_v1, encoding="utf-8")

        # First run
        code, _ = _run_generator(proto_copy, out, force=True)
        _check(code == 0, "First generation should succeed")
        hash_file = out / HASH_FILENAME
        original_hash = hash_file.read_text().strip()

        # Modify proto: add a field (changes parsed structure -> new hash)
        proto_copy.write_text(proto_v2, encoding="utf-8")

        # Second run without --force: should regenerate because hash changed
        code2, output2 = _run_generator(proto_copy, out, force=False)
        _check(code2 == 0, f"Generation after proto change should succeed, got {code2}")
        new_hash = hash_file.read_text().strip()
        _check("no changes detected" not in output2.lower(),
               f"Modified proto should NOT be skipped, got:\n{output2}")
        _check(new_hash != original_hash,
               f"Hash should change after proto modification; was {original_hash}, still {new_hash}")
