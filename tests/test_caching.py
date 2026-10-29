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
5. Documentation comments are part of the cache key: changing a leading,
   trailing or file-level comment regenerates and the generated docs change.
6. Field and oneof-variant declaration order is part of the cache key.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from test_utils import _check, run_generator, PROTO_FILE

HASH_FILENAME = ".structframe.hash"


def _run_generator(proto: Path, out_dir: Path, force: bool = False,
                   lang: str = "py") -> tuple[int, str]:
    flags = [f"--build_{lang}", f"--{lang}_path", str(out_dir) + os.sep]
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


def test_changed_default_value_invalidates_hash():
    """Changing only a field's [default=...] value must change the hash and
    trigger regeneration -- same field, same type, same size/offset, only the
    default literal differs."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        out = tmp_path / "gen"

        proto_v1 = (
            "package default_hash_test;\n"
            "message MsgA {\n"
            "  option msgid = 1;\n"
            "  uint32 retry_ms = 1 [default = 1000];\n"
            "}\n"
        )
        proto_v2 = (
            "package default_hash_test;\n"
            "message MsgA {\n"
            "  option msgid = 1;\n"
            "  uint32 retry_ms = 1 [default = 2000];\n"
            "}\n"
        )
        proto_copy = tmp_path / "default_hash_test.sf"
        proto_copy.write_text(proto_v1, encoding="utf-8")

        code, _ = _run_generator(proto_copy, out, force=True)
        _check(code == 0, "First generation should succeed")
        hash_file = out / HASH_FILENAME
        original_hash = hash_file.read_text().strip()

        proto_copy.write_text(proto_v2, encoding="utf-8")

        code2, output2 = _run_generator(proto_copy, out, force=False)
        _check(code2 == 0, f"Generation after default change should succeed, got {code2}")
        new_hash = hash_file.read_text().strip()
        _check("no changes detected" not in output2.lower(),
               f"Changing only a default value should NOT be skipped, got:\n{output2}")
        _check(new_hash != original_hash,
               f"Hash should change when a field's default changes; was {original_hash}, still {new_hash}")


def test_default_vs_no_default_hash_differs_but_deterministic():
    """A schema with a default and the identical schema without one must hash
    differently (defaults are part of the hashed schema), while regenerating
    the *same* schema twice (with or without a default) is deterministic."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        proto_no_default = (
            "package default_hash_determinism_test;\n"
            "message MsgA {\n"
            "  option msgid = 1;\n"
            "  uint32 value = 1;\n"
            "}\n"
        )
        proto_with_default = (
            "package default_hash_determinism_test;\n"
            "message MsgA {\n"
            "  option msgid = 1;\n"
            "  uint32 value = 1 [default = 5];\n"
            "}\n"
        )

        out_a = tmp_path / "gen_a"
        proto_a = tmp_path / "a.sf"
        proto_a.write_text(proto_no_default, encoding="utf-8")
        code, _ = _run_generator(proto_a, out_a, force=True)
        _check(code == 0, "no-default generation should succeed")
        hash_no_default = (out_a / HASH_FILENAME).read_text().strip()

        out_b = tmp_path / "gen_b"
        proto_b = tmp_path / "b.sf"
        proto_b.write_text(proto_with_default, encoding="utf-8")
        code, _ = _run_generator(proto_b, out_b, force=True)
        _check(code == 0, "with-default generation should succeed")
        hash_with_default = (out_b / HASH_FILENAME).read_text().strip()

        _check(hash_no_default != hash_with_default,
               "Adding a default should change the hash even though size/layout are identical")

        # Regenerating the same schema into the same output dir again (the
        # hash also covers CLI args like --py_path, so reuse out_b rather
        # than a fresh directory) must produce the identical hash --
        # deterministic, not e.g. dict-ordering-dependent.
        code, _ = _run_generator(proto_b, out_b, force=True)
        _check(code == 0, "repeat with-default generation should succeed")
        hash_repeat = (out_b / HASH_FILENAME).read_text().strip()
        _check(hash_repeat == hash_with_default,
               f"Hashing the same schema twice should be deterministic: {hash_with_default} != {hash_repeat}")


def _generate(proto: Path, out_dir: Path, source: str, force: bool = False):
    """Write *source* to *proto*, run the generator and return (code, output, hash)."""
    proto.write_text(source, encoding="utf-8")
    code, output = _run_generator(proto, out_dir, force=force, lang="cpp")
    hash_file = out_dir / HASH_FILENAME
    stored = hash_file.read_text().strip() if hash_file.exists() else None
    return code, output, stored


def _generated_text(out_dir: Path) -> str:
    """Concatenated C++ output (C++ emits file, message, enum and field docs)."""
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(out_dir.rglob("*.hpp")))


def _assert_regenerates(tmp_path: Path, v1: str, v2: str, what: str):
    """Generate *v1*, then *v2* without --force; the second run must not be skipped
    and must rewrite the stored hash and generated output."""
    out = tmp_path / "gen"
    proto = tmp_path / "doc_cache_test.sf"
    code, output, hash1 = _generate(proto, out, v1, force=True)
    _check(code == 0, f"First generation should succeed:\n{output}")
    text1 = _generated_text(out)

    code, output, hash2 = _generate(proto, out, v2)
    _check(code == 0, f"Generation after {what} should succeed:\n{output}")
    _check("no changes detected" not in output.lower(),
           f"Changing {what} must NOT be reported as 'no changes detected':\n{output}")
    _check(hash1 != hash2, f"Hash should change after {what}")
    return text1, _generated_text(out)


def test_changed_leading_comment_invalidates_hash():
    """Regression: editing only a declaration comment used to print
    'no changes detected' and leave the generated docs stale."""
    with tempfile.TemporaryDirectory() as tmp:
        v1 = (
            "package doc_cache_test;\n"
            "// Original message docs\n"
            "message MsgA {\n"
            "  option msgid = 1;\n"
            "  uint32 value = 1;\n"
            "}\n"
        )
        v2 = v1.replace("Original message docs", "Updated message docs")
        before, after = _assert_regenerates(Path(tmp), v1, v2, "a leading comment")
        _check("Original message docs" in before, "First run should emit the original docs")
        _check("Updated message docs" in after, "Regenerated output should contain the updated docs")
        _check("Original message docs" not in after, "Stale docs must not remain after regeneration")


def test_changed_trailing_comment_invalidates_hash():
    """Trailing (same-line) comments document the preceding field and are cached too."""
    with tempfile.TemporaryDirectory() as tmp:
        v1 = (
            "package doc_cache_test;\n"
            "message MsgA {\n"
            "  option msgid = 1;\n"
            "  uint32 value = 1; // Counts widgets\n"
            "}\n"
        )
        v2 = v1.replace("Counts widgets", "Counts gadgets")
        before, after = _assert_regenerates(Path(tmp), v1, v2, "a trailing comment")
        _check("Counts widgets" in before and "Counts gadgets" in after,
               "Trailing comment edit should be reflected in generated output")


def test_changed_file_header_comment_invalidates_hash():
    """File-level docs (comments before the package statement) are cached too."""
    with tempfile.TemporaryDirectory() as tmp:
        v1 = (
            "// Header describing the file\n"
            "package doc_cache_test;\n"
            "message MsgA {\n"
            "  option msgid = 1;\n"
            "  uint32 value = 1;\n"
            "}\n"
        )
        v2 = v1.replace("describing the file", "describing the module")
        before, after = _assert_regenerates(Path(tmp), v1, v2, "a file header comment")
        _check("describing the file" in before and "describing the module" in after,
               "File header edit should be reflected in generated output")


def test_unchanged_comments_still_skip():
    """Whitespace-only edits that keep every comment identical must still hit the cache."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        out = tmp_path / "gen"
        proto = tmp_path / "doc_cache_test.sf"
        v1 = (
            "package doc_cache_test;\n"
            "// Docs\n"
            "message MsgA {\n"
            "  option msgid = 1;\n"
            "  uint32 value = 1;\n"
            "}\n"
        )
        code, output, _ = _generate(proto, out, v1, force=True)
        _check(code == 0, f"First generation should succeed:\n{output}")
        code, output, _ = _generate(proto, out, v1.replace("{\n  option", "{\n\n\n  option"))
        _check(code == 0, f"Second generation should succeed:\n{output}")
        _check("no changes detected" in output.lower(),
               f"Formatting-only edits should be skipped, got:\n{output}")


def test_field_order_change_invalidates_hash():
    """Reordering same-typed fields (fields are numbered in declaration order)
    changes the generated layout/accessors, so it must invalidate the cache."""
    with tempfile.TemporaryDirectory() as tmp:
        v1 = (
            "package doc_cache_test;\n"
            "message MsgA {\n"
            "  option msgid = 1;\n"
            "  uint32 first = 1;\n"
            "  uint32 second = 2;\n"
            "}\n"
        )
        v2 = v1.replace("first = 1;\n  uint32 second = 2;", "second = 1;\n  uint32 first = 2;")
        _assert_regenerates(Path(tmp), v1, v2, "field order")


def test_oneof_variant_order_change_invalidates_hash():
    """Oneof variant order is significant (field_order discriminators)."""
    with tempfile.TemporaryDirectory() as tmp:
        v1 = (
            "package doc_cache_test;\n"
            "message MsgA {\n"
            "  option msgid = 1;\n"
            "  oneof payload {\n"
            "    uint32 alpha = 1;\n"
            "    uint32 beta = 2;\n"
            "  }\n"
            "}\n"
        )
        v2 = v1.replace("uint32 alpha = 1;\n    uint32 beta = 2;", "uint32 beta = 1;\n    uint32 alpha = 2;")
        _assert_regenerates(Path(tmp), v1, v2, "oneof variant order")


def test_oneof_declaration_order_change_invalidates_hash():
    """Oneofs are laid out in declaration order, so swapping them changes the wire."""
    with tempfile.TemporaryDirectory() as tmp:
        one = "  oneof first { option discriminator = field_order; uint8 a = 1; }\n"
        two = "  oneof second { option discriminator = field_order; uint32 c = 1; }\n"
        head = "package doc_cache_test;\nmessage M {\n  option msgid = 1;\n  option variable = true;\n"
        _assert_regenerates(Path(tmp), head + one + two + "}\n", head + two + one + "}\n",
                            "oneof declaration order")


def test_generate_tests_flag_invalidates_hash():
    """Toggling --generate_tests changes the generated output, so it is part of the key."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "gen"
        base = ["--build_py", "--py_path", str(out) + os.sep]
        r1 = run_generator(PROTO_FILE, *base, "--force")
        _check(r1.returncode == 0, r1.stdout + r1.stderr)
        r2 = run_generator(PROTO_FILE, *base, "--generate_tests")
        _check(r2.returncode == 0, r2.stdout + r2.stderr)
        _check("no changes" not in (r2.stdout + r2.stderr).lower(),
               "--generate_tests toggle must not hit the cache")
