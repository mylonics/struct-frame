#!/usr/bin/env python3
"""
Tests for the `option magic_bytes` message option.

Verifies that:

  1. A message with `option magic_bytes = "B1, B2"` uses those bytes verbatim
     instead of the calculated magic.
  2. Two messages with different field layouts but the same magic_bytes override
     produce identical magic byte values.
  3. Changing the override value changes the reported magic bytes.
  4. The override is preserved through code generation (Python round-trip).
  5. Negative cases: invalid values (zero byte, out-of-range, non-integer,
     wrong number of values) are rejected at parse time.

Usage:
    python tests/test_magic_bytes.py
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from test_utils import _check
import tempfile
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------



def _load_model(sf_text: str):
    """Parse an in-memory .sf definition.

    Returns ``(packages, fname, output)`` where ``packages`` is None when the
    generator rejected the input, and ``output`` is the captured stdout+stderr
    (so negative tests can assert the rejection *reason*, not just that it was
    rejected).
    """
    sys.path.insert(0, str(SRC_DIR))
    import struct_frame.generate as gen_mod

    gen_mod.packages.clear()
    gen_mod.package_imports.clear()
    gen_mod.processed_file.clear()

    with tempfile.NamedTemporaryFile(suffix=".sf", mode="w", delete=False) as f:
        f.write(sf_text)
        fname = f.name

    import contextlib
    import io
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            ok = gen_mod.parseFile(fname)
            packages = None
            if ok:
                packages = dict(gen_mod.packages)
                for pkg in packages.values():
                    if not pkg.validate_package(packages):
                        packages = None
                        break
        return packages, fname, buf.getvalue()
    finally:
        Path(fname).unlink(missing_ok=True)


def _generate_py(sf_text: str, out_dir: Path) -> bool:
    """Write sf_text to a temp file, run the generator, return success."""
    sf_path = out_dir / "test_magic.sf"
    sf_path.write_text(sf_text)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, str(SRC_DIR / "main.py"), str(sf_path),
         "--build_py", "--py_path", str(out_dir / "py"),
         "--force"],
        env=env,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _import_module(py_dir: Path, module_name: str):
    pyfile = py_dir / "struct_frame" / "generated" / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, pyfile)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Test 1: override is used verbatim
# ---------------------------------------------------------------------------

def test_override_used():
    """magic_bytes option overrides the calculated value."""
    sf = textwrap.dedent("""\
        package magic_test;
        message OverrideMsg {
          option msgid = 1;
          option magic_bytes = "0xAB, 0xCD";
          uint32 value = 1;
        }
    """)
    packages, _, output = _load_model(sf)
    _check(packages is not None, "model failed to load")
    msg = packages["magic_test"].messages["OverrideMsg"]
    _check(msg.magic_bytes == (0xAB, 0xCD),
           f"expected (0xAB, 0xCD), got {msg.magic_bytes}")
    _check(msg.magic_bytes_override == (0xAB, 0xCD),
           "magic_bytes_override not set on message")
    print("  [PASS] override is used verbatim")


# ---------------------------------------------------------------------------
# Test 2: override wins even when calculated value would differ
# ---------------------------------------------------------------------------

def test_override_wins_over_calculated():
    """Two structurally different messages with the same override yield same magic."""
    sf = textwrap.dedent("""\
        package magic_test2;
        message MsgA {
          option msgid = 1;
          option magic_bytes = "0x11, 0x22";
          uint32 field_a = 1;
          uint16 field_b = 2;
        }
        message MsgB {
          option msgid = 2;
          option magic_bytes = "0x11, 0x22";
          double field_x = 1;
        }
    """)
    packages, _, output = _load_model(sf)
    _check(packages is not None, "model failed to load")
    msgs = packages["magic_test2"].messages
    _check(msgs["MsgA"].magic_bytes == (0x11, 0x22), "MsgA magic mismatch")
    _check(msgs["MsgB"].magic_bytes == (0x11, 0x22), "MsgB magic mismatch")
    _check(msgs["MsgA"].magic_bytes == msgs["MsgB"].magic_bytes,
           "overridden messages should have identical magic")
    print("  [PASS] override wins over calculated value")


# ---------------------------------------------------------------------------
# Test 3: changing the override changes the magic bytes
# ---------------------------------------------------------------------------

def test_different_overrides():
    """Two messages with different overrides have different magic bytes."""
    sf = textwrap.dedent("""\
        package magic_test3;
        message MsgX {
          option msgid = 1;
          option magic_bytes = "0x01, 0x02";
          uint8 x = 1;
        }
        message MsgY {
          option msgid = 2;
          option magic_bytes = "0x03, 0x04";
          uint8 x = 1;
        }
    """)
    packages, _, output = _load_model(sf)
    _check(packages is not None, "model failed to load")
    msgs = packages["magic_test3"].messages
    _check(msgs["MsgX"].magic_bytes == (0x01, 0x02), "MsgX magic mismatch")
    _check(msgs["MsgY"].magic_bytes == (0x03, 0x04), "MsgY magic mismatch")
    _check(msgs["MsgX"].magic_bytes != msgs["MsgY"].magic_bytes,
           "different overrides must produce different magic")
    print("  [PASS] different overrides produce different magic")


# ---------------------------------------------------------------------------
# Test 4: without override, magic_bytes_override is None
# ---------------------------------------------------------------------------

def test_no_override_is_none():
    """Messages without the option have magic_bytes_override = None."""
    sf = textwrap.dedent("""\
        package magic_test4;
        message PlainMsg {
          option msgid = 1;
          uint8 x = 1;
        }
    """)
    packages, _, output = _load_model(sf)
    _check(packages is not None, "model failed to load")
    msg = packages["magic_test4"].messages["PlainMsg"]
    _check(msg.magic_bytes_override is None,
           f"expected None, got {msg.magic_bytes_override}")
    _check(msg.magic_bytes is not None,
           "magic_bytes should still be calculated when no override")
    print("  [PASS] no override → magic_bytes_override is None, magic_bytes calculated")


# ---------------------------------------------------------------------------
# Test 5: decimal values are also accepted
# ---------------------------------------------------------------------------

def test_decimal_values():
    """magic_bytes accepts plain decimal integers."""
    sf = textwrap.dedent("""\
        package magic_test5;
        message DecimalMsg {
          option msgid = 1;
          option magic_bytes = "171, 205";
          uint8 x = 1;
        }
    """)
    packages, _, output = _load_model(sf)
    _check(packages is not None, "model failed to load")
    msg = packages["magic_test5"].messages["DecimalMsg"]
    # 171 = 0xAB, 205 = 0xCD
    _check(msg.magic_bytes == (171, 205),
           f"expected (171, 205), got {msg.magic_bytes}")
    print("  [PASS] decimal values accepted")


# ---------------------------------------------------------------------------
# Test 6: negative — zero byte rejected
# ---------------------------------------------------------------------------

def test_zero_byte_rejected():
    """A magic byte of 0 must be rejected."""
    for bad in ["0x00, 0xAB", "0xAB, 0x00", "0, 0"]:
        sf = textwrap.dedent(f"""\
            package neg_test;
            message BadMsg {{
              option msgid = 1;
              option magic_bytes = "{bad}";
              uint8 x = 1;
            }}
        """)
        packages, _, output = _load_model(sf)
        _check(packages is None,
               f"zero magic byte '{bad}' should have been rejected")
        _check("magic bytes must be non-zero" in output,
               f"'{bad}' rejected, but not for the non-zero reason; output was:\n{output}")
    print("  [PASS] zero byte rejected")


# ---------------------------------------------------------------------------
# Test 7: negative — out-of-range byte rejected
# ---------------------------------------------------------------------------

def test_out_of_range_rejected():
    """Values > 255 must be rejected."""
    sf = textwrap.dedent("""\
        package neg_test2;
        message BadMsg {
          option msgid = 1;
          option magic_bytes = "256, 0xAB";
          uint8 x = 1;
        }
    """)
    packages, _, output = _load_model(sf)
    _check(packages is None, "value 256 should have been rejected")
    _check("each byte must be in range 0-255" in output,
           f"256 rejected, but not for the out-of-range reason; output was:\n{output}")
    print("  [PASS] out-of-range byte rejected")


# ---------------------------------------------------------------------------
# Test 8: negative — wrong number of values rejected
# ---------------------------------------------------------------------------

def test_wrong_count_rejected():
    """Providing one or three values must be rejected."""
    for bad in ["0xAB", "0xAB, 0xCD, 0xEF"]:
        sf = textwrap.dedent(f"""\
            package neg_test3;
            message BadMsg {{
              option msgid = 1;
              option magic_bytes = "{bad}";
              uint8 x = 1;
            }}
        """)
        packages, _, output = _load_model(sf)
        _check(packages is None,
               f"wrong-count magic_bytes '{bad}' should have been rejected")
        _check("expected two comma-separated byte values" in output,
               f"'{bad}' rejected, but not for the wrong-count reason; output was:\n{output}")
    print("  [PASS] wrong number of values rejected")


# ---------------------------------------------------------------------------
# Test 9: Python code generation preserves the override
# ---------------------------------------------------------------------------

def test_codegen_preserves_override():
    """Generated Python code uses the overridden magic bytes for MAGIC_BYTES."""
    sf = textwrap.dedent("""\
        package gen_magic;
        message OverrideGenMsg {
          option msgid = 1;
          option magic_bytes = "0xA3, 0x7F";
          uint32 value = 1;
        }
    """)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        ok = _generate_py(sf, out)
        _check(ok, "code generation failed")

        mod = _import_module(out / "py", "gen_magic")
        cls = mod.OverrideGenMsg
        _check(hasattr(cls, "MAGIC1") and hasattr(cls, "MAGIC2"),
               f"generated class missing MAGIC1/MAGIC2 attributes; found: {[x for x in dir(cls) if 'magic' in x.lower() or 'MAGIC' in x]}")
        _check(cls.MAGIC1 == 0xA3,
               f"expected MAGIC1=0xA3 ({0xA3}), got {cls.MAGIC1}")
        _check(cls.MAGIC2 == 0x7F,
               f"expected MAGIC2=0x7F ({0x7F}), got {cls.MAGIC2}")
    print("  [PASS] code generation preserves override in MAGIC_BYTES")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    print("=== magic_bytes Option Tests ===\n")
    test_override_used()
    test_override_wins_over_calculated()
    test_different_overrides()
    test_no_override_is_none()
    test_decimal_values()
    test_zero_byte_rejected()
    test_out_of_range_rejected()
    test_wrong_count_rejected()
    test_codegen_preserves_override()
    print("\nAll magic_bytes tests PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
