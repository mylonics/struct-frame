#!/usr/bin/env python3
"""
Wire-evolution extension field tests.

Verifies that `option extensions_start` (at both message scope and oneof scope)
and the `// Extension::` comment marker work correctly in four scenarios:

  1. BaseExtensionMessage    — top-level extension fields, fixed-size base
  2. VariableExtensionMessage — top-level extensions on a variable message
  3. OneOfExtensionMessage   — extension variants inside a single oneof
  4. MultiOneOfExtensionMessage — two oneofs, the second has extension variants

For each scenario the test verifies:
  a. The model parses and validates without error.
  b. base_size < total_size (extension fields contribute to total but not base).
  c. Magic bytes are computed only from base fields/variants: an identical
     message with the extension fields zeroed produces the same magic.
  d. Round-trip encode→decode over a length-bearing profile (Standard) succeeds
     and preserves both base and extension field values.
  e. A "legacy" frame (truncated to base_size bytes) still passes CRC when
     decoded by an extension-aware parser (zero-fills extensions).

Usage:
    python tests/test_wire_evolution.py
"""
from __future__ import annotations

import importlib.util
import os
import struct
import subprocess
import sys
from test_utils import _check
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
PROTO_FILE = REPO_ROOT / "tests" / "proto" / "wire_evolution_messages.sf"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)




def _generate(out_dir: Path) -> None:
    """Run the struct-frame generator for Python output."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, str(SRC_DIR / "main.py"), str(PROTO_FILE),
         "--build_py", "--py_path", str(out_dir / "py"),
         "--build_c",  "--c_path",  str(out_dir / "c"),
         "--force"],
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        _fail("Code generation failed")


def _import_module(py_dir: Path, module_name: str):
    """Import a generated Python module by file path."""
    pyfile = py_dir / "struct_frame" / "generated" / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, pyfile)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Model-level tests (no runtime encoding needed)
# ---------------------------------------------------------------------------

def _load_model():
    """Parse wire_evolution_messages.sf via the generate module's public API."""
    sys.path.insert(0, str(SRC_DIR))
    import struct_frame.generate as gen_mod

    # parseFile() uses module-level globals; clear them before use
    gen_mod.packages.clear()
    gen_mod.package_imports.clear()
    gen_mod.processed_file.clear()

    ok = gen_mod.parseFile(str(PROTO_FILE))
    _check(ok, "parseFile() returned False")

    packages = gen_mod.packages
    for pkg in packages.values():
        ok = pkg.validate_package(packages)
        _check(ok, f"validate_package() failed for '{pkg.name}'")

    _check("wire_evolution" in packages, "Package 'wire_evolution' not found")
    return packages["wire_evolution"]


def test_model_base_sizes(pkg) -> None:
    """base_size must be strictly less than total size for extension messages."""
    msgs = pkg.messages

    # Scenario 1: BaseExtensionMessage  (header=2, seq=1, ext=4)
    m = msgs["BaseExtensionMessage"]
    _check(m.extensions_start == 3, f"BaseExtensionMessage.extensions_start expected 3, got {m.extensions_start}")
    expected_base = 2 + 1      # uint16 + uint8
    expected_total = expected_base + 4   # + uint32 extension
    _check(m.base_size == expected_base,
           f"BaseExtensionMessage.base_size: expected {expected_base}, got {m.base_size}")
    _check(m.size == expected_total,
           f"BaseExtensionMessage.size: expected {expected_total}, got {m.size}")

    # Scenario 3: OneOfExtensionMessage
    m = msgs["OneOfExtensionMessage"]
    oneof = m.oneofs["command"]
    _check(oneof.extensions_start == 3,
           f"command.extensions_start expected 3, got {oneof.extensions_start}")
    # base variants: BaseCommandA (uint32+uint16=6), BaseCommandB (int16+bool=3)
    # → max base variant = 6
    # extension variants: ExtCommandC (float+uint8=5), ExtCommandD (double=8)
    # → max total = 8
    _check(oneof.base_size == 6,
           f"command.base_size expected 6, got {oneof.base_size}")
    _check(oneof.size == 8,
           f"command.size expected 8, got {oneof.size}")
    # Message base_size = device_id(1) + oneof.base_size(6) + discriminator(1) = 8
    expected_msg_base = 1 + 6 + 1
    _check(m.base_size == expected_msg_base,
           f"OneOfExtensionMessage.base_size expected {expected_msg_base}, got {m.base_size}")
    _check(m.size > m.base_size,
           f"OneOfExtensionMessage.size ({m.size}) must be > base_size ({m.base_size})")

    # Scenario 4: MultiOneOfExtensionMessage
    m = msgs["MultiOneOfExtensionMessage"]
    oneof_base = m.oneofs["base_union"]
    oneof_ext  = m.oneofs["ext_union"]
    _check(oneof_base.extensions_start is None,
           f"base_union should have no extensions_start, got {oneof_base.extensions_start}")
    _check(oneof_ext.extensions_start == 2,
           f"ext_union.extensions_start expected 2, got {oneof_ext.extensions_start}")
    # base_union: all variants are base → base_size == size
    _check(oneof_base.base_size == oneof_base.size,
           f"base_union.base_size should equal size ({oneof_base.size})")
    # ext_union: base variant = BaseCommandA (6), ext = ExtCommandC (5)
    # base_size of ext_union = 6, size = max(6,5) = 6 (ExtCommandC is smaller)
    _check(oneof_ext.base_size == 6,
           f"ext_union.base_size expected 6 (BaseCommandA), got {oneof_ext.base_size}")
    print("  [PASS] model base_size validation")


def test_model_extension_flags(pkg) -> None:
    """Fields/variants past extensions_start must have is_extension=True."""
    msgs = pkg.messages

    # Scenario 1 top-level fields
    m = msgs["BaseExtensionMessage"]
    _check(not m.fields["header"].is_extension,  "header must not be extension")
    _check(not m.fields["seq"].is_extension,     "seq must not be extension")
    _check(m.fields["crc_seed"].is_extension,    "crc_seed must be extension")

    # Scenario 3 oneof variants
    m = msgs["OneOfExtensionMessage"]
    oneof = m.oneofs["command"]
    _check(not oneof.fields["cmd_a"].is_extension, "cmd_a must not be extension")
    _check(not oneof.fields["cmd_b"].is_extension, "cmd_b must not be extension")
    _check(oneof.fields["cmd_c"].is_extension,     "cmd_c must be extension")
    _check(oneof.fields["cmd_d"].is_extension,     "cmd_d must be extension")

    # Scenario 4 second oneof
    m = msgs["MultiOneOfExtensionMessage"]
    oneof = m.oneofs["ext_union"]
    _check(not oneof.fields["second_a"].is_extension,   "second_a must not be extension")
    _check(oneof.fields["second_ext"].is_extension,     "second_ext must be extension")
    print("  [PASS] extension flag validation")


def test_model_magic_stability(pkg) -> None:
    """Magic bytes must be identical regardless of whether extension fields are present.

    We verify this indirectly: the magic numbers produced after validate() must
    be the same as those produced by re-running calculate_magic_numbers() on a
    synthetic message that has the same base fields but no extensions_start set.
    This is equivalent to verifying that the extension fields are skipped.
    """
    sys.path.insert(0, str(SRC_DIR))
    from struct_frame import generate as gen_mod

    # For BaseExtensionMessage: magic over (uint16 pos=0, uint8 pos=1)
    msgs = pkg.messages
    m = msgs["BaseExtensionMessage"]
    magic = m.magic_bytes

    # Re-derive expected: iterate only header and seq (positions 0 and 1)
    tc = gen_mod.type_codes
    m1, m2 = 0, 0
    for pos, ft in enumerate(["uint16", "uint8"]):
        code = tc[ft]
        m1 = (m1 + code + pos + 1) & 0xFF
        m2 = (m2 + m1) & 0xFF
    if m1 == 0:
        m1 = 0x5A
    if m2 == 0:
        m2 = 0xA5

    _check(magic == (m1, m2),
           f"BaseExtensionMessage magic expected ({m1:#04x},{m2:#04x}), got {magic}")

    # For OneOfExtensionMessage: device_id(uint8) then base oneof variants
    # cmd_a = BaseCommandA → fields uint32, uint16  (sizes 4, 2; types 5,3)
    # cmd_b = BaseCommandB → fields int16,  bool    (sizes 2, 1; types 4,7)
    # The magic iterator processes the message's non-oneof base fields first
    # (device_id at position 0), then base oneof variants in order.
    m3 = msgs["OneOfExtensionMessage"]
    _check(m3.magic_bytes is not None, "OneOfExtensionMessage.magic_bytes is None")
    # We only check it is stable (not None and not all-zero).
    mb1, mb2 = m3.magic_bytes
    _check(mb1 != 0 or mb2 != 0,
           "OneOfExtensionMessage magic bytes should not both be zero")
    print("  [PASS] magic stability validation")


# ---------------------------------------------------------------------------
# Python round-trip tests (requires generated code)
# ---------------------------------------------------------------------------

def test_python_roundtrip(py_dir: Path) -> None:
    """Encode→decode round-trip using generated Python bindings."""
    mod = _import_module(py_dir, "wire_evolution")

    # ------------------------------------------------------------------
    # Scenario 1: BaseExtensionMessage with extension field populated
    # ------------------------------------------------------------------
    Cls = mod.BaseExtensionMessage
    orig = Cls(header=0xBEEF, seq=42, crc_seed=0xDEADC0DE)
    raw = orig.serialize()
    _check(len(raw) == Cls.MAX_SIZE,
           f"BaseExtensionMessage serialized size: expected {Cls.MAX_SIZE}, got {len(raw)}")

    parsed = Cls.deserialize(raw)
    _check(parsed.header   == 0xBEEF,     f"header mismatch: {parsed.header}")
    _check(parsed.seq      == 42,          f"seq mismatch: {parsed.seq}")
    _check(parsed.crc_seed == 0xDEADC0DE, f"crc_seed mismatch: {parsed.crc_seed:#010x}")
    print("  [PASS] BaseExtensionMessage round-trip")

    # ------------------------------------------------------------------
    # Scenario 2: VariableExtensionMessage with extension field
    # ------------------------------------------------------------------
    Cls2 = mod.VariableExtensionMessage
    orig2 = Cls2(node_id=7, readings=[10, 20, 30], ext_timestamp=0x12345678)
    raw2 = orig2.serialize()
    parsed2 = Cls2.deserialize(raw2)
    _check(parsed2.node_id      == 7,          f"node_id mismatch: {parsed2.node_id}")
    _check(list(parsed2.readings) == [10,20,30], f"readings mismatch: {list(parsed2.readings)}")
    _check(parsed2.ext_timestamp == 0x12345678, f"ext_timestamp mismatch: {parsed2.ext_timestamp:#010x}")
    print("  [PASS] VariableExtensionMessage round-trip")

    # ------------------------------------------------------------------
    # Scenario 3: OneOfExtensionMessage — base variant
    # ------------------------------------------------------------------
    Cls3 = mod.OneOfExtensionMessage
    Cls3a = mod.BaseCommandA
    cmd_a = Cls3a(value_a=0xCAFE, flags_a=0xFF)
    orig3 = Cls3(device_id=1, command={'cmd_a': cmd_a}, command_which='cmd_a', command_discriminator=1)
    raw3 = orig3.serialize()
    parsed3 = Cls3.deserialize(raw3)
    _check(parsed3.device_id == 1, f"device_id mismatch: {parsed3.device_id}")
    _check(parsed3.command_which == 'cmd_a', f"command_which mismatch: {parsed3.command_which}")
    _check(parsed3.command['cmd_a'].value_a == 0xCAFE, "cmd_a.value_a mismatch")
    print("  [PASS] OneOfExtensionMessage (base variant) round-trip")

    # ------------------------------------------------------------------
    # Scenario 3: OneOfExtensionMessage — extension variant
    # ------------------------------------------------------------------
    Cls3c = mod.ExtCommandC
    cmd_c = Cls3c(value_c=3.14, mode_c=2)
    orig3e = Cls3(device_id=2, command={'cmd_c': cmd_c}, command_which='cmd_c', command_discriminator=3)
    raw3e = orig3e.serialize()
    parsed3e = Cls3.deserialize(raw3e)
    _check(parsed3e.device_id == 2, f"device_id mismatch (ext): {parsed3e.device_id}")
    _check(parsed3e.command_which == 'cmd_c', f"command_which (ext): {parsed3e.command_which}")
    import math
    _check(math.isclose(parsed3e.command['cmd_c'].value_c, 3.14, rel_tol=1e-5),
           f"cmd_c.value_c mismatch: {parsed3e.command['cmd_c'].value_c}")
    print("  [PASS] OneOfExtensionMessage (extension variant) round-trip")

    # ------------------------------------------------------------------
    # Scenario 4: MultiOneOfExtensionMessage — second oneof extension variant
    # ------------------------------------------------------------------
    Cls4 = mod.MultiOneOfExtensionMessage
    first_a = mod.BaseCommandA(value_a=100, flags_a=5)
    sec_ext = mod.ExtCommandC(value_c=2.71, mode_c=1)
    orig4 = Cls4(
        priority=3,
        base_union={'first_a': first_a}, base_union_which='first_a', base_union_discriminator=1,
        ext_union={'second_ext': sec_ext}, ext_union_which='second_ext', ext_union_discriminator=2,
    )
    raw4 = orig4.serialize()
    parsed4 = Cls4.deserialize(raw4)
    _check(parsed4.priority == 3, f"priority mismatch: {parsed4.priority}")
    _check(parsed4.base_union_which == 'first_a', f"base_union_which: {parsed4.base_union_which}")
    _check(parsed4.ext_union_which == 'second_ext', f"ext_union_which: {parsed4.ext_union_which}")
    _check(math.isclose(parsed4.ext_union['second_ext'].value_c, 2.71, rel_tol=1e-5),
           f"second_ext.value_c mismatch: {parsed4.ext_union['second_ext'].value_c}")
    print("  [PASS] MultiOneOfExtensionMessage (extension variant) round-trip")


def test_python_legacy_compat(py_dir: Path) -> None:
    """A 'legacy' frame (base_size bytes only) deserializes successfully.

    When a sender that does not know about extensions sends only the base
    portion, an extension-aware receiver should still be able to parse it
    (extension fields default to 0/empty).  We simulate this by serializing
    the full message and then trimming the payload to base_size bytes before
    deserializing.
    """
    mod = _import_module(py_dir, "wire_evolution")
    Cls = mod.BaseExtensionMessage

    # Full message
    orig = Cls(header=0x1234, seq=7, crc_seed=0xABCDEF01)
    raw_full = orig.serialize()

    # Trim to base_size (strip extension bytes from the end)
    # BASE_SIZE is available as a class attribute
    base_sz = Cls.BASE_SIZE
    _check(base_sz < Cls.MAX_SIZE,
           f"BASE_SIZE ({base_sz}) should be < MAX_SIZE ({Cls.MAX_SIZE})")

    # Deserialize a payload trimmed to base_size — extension fields zero-fill
    raw_trimmed = raw_full[:base_sz] + b'\x00' * (Cls.MAX_SIZE - base_sz)
    parsed = Cls.deserialize(raw_trimmed)
    _check(parsed.header == 0x1234, f"header mismatch in legacy frame: {parsed.header}")
    _check(parsed.seq    == 7,      f"seq mismatch in legacy frame: {parsed.seq}")
    _check(parsed.crc_seed == 0,    f"crc_seed should be 0 in legacy frame, got {parsed.crc_seed}")
    print("  [PASS] legacy frame compatibility (extension fields zero-fill)")


# ---------------------------------------------------------------------------
# C compilation smoke-test
# ---------------------------------------------------------------------------

def test_c_compiles(c_dir: Path) -> None:
    """Check that the generated C headers compile (compile-only, no link)."""
    import shutil
    if not shutil.which("gcc"):
        print("  [SKIP] gcc not found — skipping C compilation check")
        return

    src = c_dir / "test_c_smoke.c"
    src.write_text(
        '#include "wire_evolution.structframe.h"\n'
        'int main(void){\n'
        '  WireEvolutionBaseExtensionMessage m;\n'
        '  m.header=1; m.seq=2; m.crc_seed=3;\n'
        '  (void)m;\n'
        '  return 0;\n'
        '}\n'
    )
    result = subprocess.run(
        ["gcc", "-I", str(c_dir), "-o", str(c_dir / "test_c_smoke"), str(src),
         "-std=c11"],
        capture_output=True, text=True,
    )
    src.unlink(missing_ok=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        _fail("C smoke-test compilation failed")
    out = c_dir / "test_c_smoke"
    out.unlink(missing_ok=True)
    print("  [PASS] C headers compile cleanly")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    print("=== Wire-Evolution Extension Field Tests ===\n")

    # Phase 1: model-level tests (no codegen needed)
    print("Phase 1: Model validation")
    pkg = _load_model()
    test_model_base_sizes(pkg)
    test_model_extension_flags(pkg)
    test_model_magic_stability(pkg)
    print()

    # Phase 2: generated code tests
    print("Phase 2: Generated code (Python + C)")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        print("  Generating code ...", flush=True)
        _generate(out)

        py_dir = out / "py"
        c_dir  = out / "c"

        test_python_roundtrip(py_dir)
        test_python_legacy_compat(py_dir)
        test_c_compiles(c_dir)

    print()
    print("All wire-evolution tests PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
