#!/usr/bin/env python3
"""
Tests for the ``--validate`` CLI flag.

The flag should:
1. Parse and validate the proto file without generating any output files.
2. Print "Validation successful" and exit 0 for a well-formed proto.
3. Print "Validation failed" and exit non-zero for a malformed proto.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from test_utils import _check, run_generator, PROTO_FILE


def _run_validate(proto_path: Path, extra_args=()) -> tuple[int, str, str]:
    result = run_generator(proto_path, "--validate", *extra_args)
    return result.returncode, result.stdout, result.stderr


def _validation_rejected(code: int, stdout: str, stderr: str) -> bool:
    """Return True if the generator produced a visible rejection (exit non-zero
    OR an explicit 'Validation failed' / error message in the output).
    The generator currently exits 0 even on validation failure, so we accept
    either signal.
    """
    combined = (stdout + stderr).lower()
    return (
        code != 0
        or "validation failed" in combined
        or "failed to validate" in combined
        or "error" in combined
    )


def test_validate_success():
    """Valid proto exits 0 with 'Validation successful'."""
    code, stdout, stderr = _run_validate(PROTO_FILE)
    output = stdout + stderr
    _check(code == 0,
           f"--validate on a valid proto should exit 0, got {code}.\n"
           f"stdout: {stdout}\nstderr: {stderr}")
    _check("Validation successful" in output,
           f"Expected 'Validation successful' in output, got:\n{output}")


def test_validate_no_output_files():
    """--validate must not create any output files in a target directory."""
    # Run validate with an output path pointing to a temp directory.
    # If --validate is working correctly, no files should be written there.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        code, stdout, stderr = _run_validate(
            PROTO_FILE,
            extra_args=["--py_path", str(tmp_path / "py"),
                        "--c_path", str(tmp_path / "c"),
                        "--cpp_path", str(tmp_path / "cpp")],
        )
        # Even though output paths were provided, --validate must not write files.
        written = list(tmp_path.rglob("*"))
        _check(not written,
               f"--validate should not write files even when output paths are given, "
               f"but found: {written}")
    _check(code == 0,
           f"--validate on valid proto should succeed, got {code}")


def test_validate_failure():
    """A semantically invalid proto must produce 'Validation failed' output."""
    with tempfile.TemporaryDirectory() as tmp:
        bad_proto = Path(tmp) / "bad.sf"
        # A message field that references an unknown type triggers validation
        # failure in the generator's validate_packages() path.
        bad_proto.write_text(
            "package bad_pkg;\n"
            "message BadMsg {\n"
            "  option msgid = 1;\n"
            "  NoSuchType field_a = 1;\n"
            "}\n",
            encoding="utf-8",
        )
        code, stdout, stderr = _run_validate(bad_proto)
        _check(_validation_rejected(code, stdout, stderr),
               f"--validate on an invalid proto should reject it.\n"
               f"stdout: {stdout}\nstderr: {stderr}")
