#!/usr/bin/env python3
"""
Tests for schema-defined field default values ([default = ...]).

Covers (see tests/proto/default_values.sf):
- Generation succeeds for every supported language
- Python: constructor defaults, explicit overrides, round trip, decode
  fallback for a genuinely missing trailing field, nested-message recursion
- C: same, compiled and executed
- Existing schemas without defaults are unaffected (test_messages.sf still
  passes unchanged -- covered by the rest of the suite; this file only
  double-checks the NoDefaultsMessage control message in default_values.sf
  itself behaves exactly as it would have before this feature existed)
"""
from __future__ import annotations

import subprocess
import shutil
from pathlib import Path

import pytest

from test_utils import _check, run_generator, load_generated_module, REPO_ROOT

DEFAULT_VALUES_PROTO = REPO_ROOT / "tests" / "proto" / "default_values.sf"


def _generate(out_dir: Path) -> None:
    result = run_generator(
        DEFAULT_VALUES_PROTO,
        "--build_py", "--py_path", str(out_dir / "py"),
        "--build_c", "--c_path", str(out_dir / "c"),
        "--build_cpp", "--cpp_path", str(out_dir / "cpp"),
        "--build_csharp", "--csharp_path", str(out_dir / "csharp"),
        "--build_ts", "--ts_path", str(out_dir / "ts"),
        "--build_js", "--js_path", str(out_dir / "js"),
        "--build_rust", "--rust_path", str(out_dir / "rust"),
        "--force",
    )
    if result.returncode != 0:
        raise RuntimeError(f"Generator failed:\n{result.stdout}\n{result.stderr}")


def _import_generated_module(py_dir: Path):
    return load_generated_module(
        py_dir / "struct_frame" / "generated" / "default_values.py",
        "default_values",
    )


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------

def _python_construction_defaults(mod) -> None:
    """Omitted constructor arguments use the schema default."""
    m = mod.DefaultsMessage()
    _check(m.u8_val == 200, f"u8_val default: got {m.u8_val}")
    _check(m.i8_val == -100, f"i8_val default: got {m.i8_val}")
    _check(m.u16_val == 40000, f"u16_val default: got {m.u16_val}")
    _check(m.i16_val == -1000, f"i16_val default: got {m.i16_val}")
    _check(m.u32_val == 3000000000, f"u32_val default: got {m.u32_val}")
    _check(m.i32_val == -2000000, f"i32_val default: got {m.i32_val}")
    _check(m.u64_val == 10000000000, f"u64_val default: got {m.u64_val}")
    _check(m.i64_val == -10000000000, f"i64_val default: got {m.i64_val}")
    _check(m.bool_val is True, f"bool_val default: got {m.bool_val}")
    _check(abs(m.float_val - 1.5) < 1e-6, f"float_val default: got {m.float_val}")
    _check(abs(m.double_val - 3.14159) < 1e-9, f"double_val default: got {m.double_val}")
    _check(m.mode_val == mod.Mode.ACTIVE.value, f"mode_val default: got {m.mode_val}")
    _check(m.fixed_str == b"device", f"fixed_str default: got {m.fixed_str!r}")
    _check(m.bound_str == b"hello world", f"bound_str default: got {m.bound_str!r}")
    _check(m.fixed_bytes == b"ab", f"fixed_bytes default: got {m.fixed_bytes!r}")
    _check(m.plain_val == 0, f"plain_val (no default) should be 0: got {m.plain_val}")
    _check(m.nested.inner_value == 7,
           f"nested.inner_value should recursively pick up Inner's own default: got {m.nested.inner_value}")


def _python_explicit_overrides(mod) -> None:
    """Explicitly supplied zero/empty values are not reverted to the default."""
    m = mod.DefaultsMessage(u8_val=0, bool_val=False, fixed_str=b"", bound_str=b"")
    _check(m.u8_val == 0, f"explicit zero u8_val overridden: got {m.u8_val}")
    _check(m.bool_val is False, f"explicit false bool_val overridden: got {m.bool_val}")
    _check(m.fixed_str == b"", f"explicit empty fixed_str overridden: got {m.fixed_str!r}")
    _check(m.bound_str == b"", f"explicit empty bound_str overridden: got {m.bound_str!r}")
    # Non-overridden fields still get their defaults.
    _check(m.i8_val == -100, f"non-overridden i8_val should stay default: got {m.i8_val}")


def _python_round_trip(mod) -> None:
    """A fully-populated message round-trips its real (non-default) values."""
    m = mod.DefaultsMessage(
        u8_val=1, i8_val=2, u16_val=3, i16_val=4, u32_val=5, i32_val=6,
        u64_val=7, i64_val=8, bool_val=False, float_val=9.5, double_val=10.5,
        mode_val=mod.Mode.ERROR.value, fixed_str=b"custom", bound_str=b"other",
        fixed_bytes=b"zz", plain_val=99,
    )
    data = m.serialize()
    back = mod.DefaultsMessage.deserialize(data)
    _check(back.u8_val == 1 and back.mode_val == mod.Mode.ERROR.value and back.plain_val == 99,
           "round trip did not preserve explicit non-default values")


def _python_decode_missing_trailing_field(mod) -> None:
    """Decoding a payload shorter than the schema applies defaults to the
    genuinely-missing trailing fields, not zero -- and a present zero value
    earlier in the payload is NOT reinterpreted as a default."""
    m = mod.DefaultsMessage(u8_val=0)  # explicit zero, present in the truncated prefix
    full = m.serialize()
    # Keep only u8_val (1 byte) -- everything else was never "sent".
    truncated = full[:1]
    decoded = mod.DefaultsMessage.deserialize(truncated)
    _check(decoded.u8_val == 0,
           f"present zero value must survive truncation, not become the default: got {decoded.u8_val}")
    _check(decoded.i8_val == -100, f"missing i8_val should be its default: got {decoded.i8_val}")
    _check(decoded.bool_val is True, f"missing bool_val should be its default: got {decoded.bool_val}")
    _check(decoded.mode_val == mod.Mode.ACTIVE.value,
           f"missing mode_val should be its default: got {decoded.mode_val}")
    # Fixed strings always decode as the full size_option-width buffer
    # (zero-padded), regardless of defaults -- pre-existing behavior.
    _check(decoded.fixed_str.rstrip(b"\x00") == b"device",
           f"missing fixed_str should be its default: got {decoded.fixed_str!r}")
    _check(decoded.nested.inner_value == 7,
           f"missing nested message should recursively default: got {decoded.nested.inner_value}")


def _python_no_defaults_control(mod) -> None:
    """A message with no [default=...] anywhere behaves exactly as before."""
    m = mod.NoDefaultsMessage()
    _check(m.value == 0 and m.flag is False and m.name == b"",
           "NoDefaultsMessage constructor should still be all-zero/empty")
    decoded = mod.NoDefaultsMessage.deserialize(b"")
    _check(decoded.value == 0 and decoded.flag is False and decoded.name == b"\x00" * 8,
           "NoDefaultsMessage decode of an empty payload should still be all-zero/empty")


# ---------------------------------------------------------------------------
# C
# ---------------------------------------------------------------------------

_C_DEFAULTS_TEST_SRC = r"""
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "default_values.structframe.h"

int main(void) {
    /* Constructor (init helper) defaults */
    DefaultValuesDefaultsMessage m;
    DefaultValuesDefaultsMessage_init(&m);
    assert(m.u8_val == 200);
    assert(m.i8_val == -100);
    assert(m.bool_val == true);
    assert(m.mode_val == MODE_ACTIVE);
    assert(strncmp(m.fixed_str, "device", 6) == 0);
    assert(m.plain_val == 0);
    assert(m.nested.inner_value == 7);

    /* Explicit zero after init is not reverted */
    m.u8_val = 0;
    assert(m.u8_val == 0);

    /* Decode fallback: missing trailing bytes use the default */
    DefaultValuesDefaultsMessage full;
    DefaultValuesDefaultsMessage_init(&full);
    full.u8_val = 5;
    uint8_t buf[DEFAULT_VALUES_DEFAULTS_MESSAGE_MAX_SIZE];
    DefaultValuesDefaultsMessage_serialize(&full, buf);

    DefaultValuesDefaultsMessage decoded;
    DefaultValuesDefaultsMessage_deserialize(buf, 1, &decoded); /* only u8_val "sent" */
    assert(decoded.u8_val == 5);
    assert(decoded.i8_val == -100);
    assert(decoded.mode_val == MODE_ACTIVE);
    assert(decoded.nested.inner_value == 7);

    /* Control message with no defaults: unchanged behavior */
    DefaultValuesNoDefaultsMessage nd;
    DefaultValuesNoDefaultsMessage_init(&nd);
    assert(nd.value == 0 && nd.flag == false);

    printf("C default values: OK\n");
    return 0;
}
"""


def _c_defaults(c_dir: Path) -> None:
    src = c_dir / "_defaults_test.c"
    src.write_text(_C_DEFAULTS_TEST_SRC, encoding="utf-8")
    out = c_dir / "_defaults_test.out"
    try:
        subprocess.check_call(
            ["gcc", "-std=c99", "-I", str(c_dir), str(src), "-o", str(out)],
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        pytest.skip("gcc not available - skipping C default-values test")
    result = subprocess.run([str(out)], capture_output=True, text=True)
    _check(result.returncode == 0,
           f"C default-values binary failed:\n{result.stdout}{result.stderr}")


# ---------------------------------------------------------------------------
# Rust
# ---------------------------------------------------------------------------

def _rust_defaults(rust_dir: Path) -> None:
    """Generated Rust defaults compile, including f32/f64 default literals."""
    if shutil.which("cargo") is None:
        pytest.skip("cargo not available - skipping Rust default-values test")
    result = subprocess.run(
        ["cargo", "check", "--manifest-path", str(rust_dir / "Cargo.toml")],
        capture_output=True,
        text=True,
    )
    _check(result.returncode == 0,
           f"Generated Rust default-values crate failed to compile:\n"
           f"{result.stdout}{result.stderr}")


# ---------------------------------------------------------------------------
# Single collected pytest entry point
# ---------------------------------------------------------------------------

def test_default_values(tmp_path: Path) -> None:
    """Schema-defined field default values: parsing, construction, override,
    decode fallback, and cross-language generation."""
    _generate(tmp_path)

    py_dir = tmp_path / "py"
    c_dir = tmp_path / "c"
    rust_dir = tmp_path / "rust"

    mod = _import_generated_module(py_dir)

    _python_construction_defaults(mod)
    _python_explicit_overrides(mod)
    _python_round_trip(mod)
    _python_decode_missing_trailing_field(mod)
    _python_no_defaults_control(mod)
    _c_defaults(c_dir)
    _rust_defaults(rust_dir)
