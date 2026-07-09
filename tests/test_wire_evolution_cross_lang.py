#!/usr/bin/env python3
"""
Cross-language x cross-version wire-evolution interop.

``test_wire_evolution_interop.py`` proves cross-VERSION interop (v1<->v2)
entirely within Python; every per-language interop runner
(``tests/{c,cpp,ts,js,csharp,rust}/test_wire_evolution_interop.*``) proves
the same thing entirely within its own language, in-process. None of them
prove that a v1 frame encoded by language X is correctly read by language
Y's v2 decoder (or vice versa) -- every existing check runs in a single
process, never through a real subprocess + file handoff between two
different languages' implementations.

This test drives ``tests/cpp/build/test_wire_evolution_file_io(.exe)`` (see
that file) as a real subprocess with real file interchange, so
Python<->C++ is a genuine cross-language x cross-version proof point for
the canonical ``BaseExtensionMessage`` (v1: {header, seq}; v2 adds the
{crc_seed} extension field). Skips (does not fail) if the C++ binary
hasn't been built yet -- run ``test_all.py`` or ``run_tests.py`` first.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from test_utils import _check, run_generator, load_generated_module, REPO_ROOT

PROTO_V1 = REPO_ROOT / "tests" / "proto" / "wire_evolution_v1.sf"
PROTO_V2 = REPO_ROOT / "tests" / "proto" / "wire_evolution_v2.sf"
CPP_RUNNER = (REPO_ROOT / "tests" / "cpp" / "build" /
              ("test_wire_evolution_file_io.exe" if sys.platform == "win32"
               else "test_wire_evolution_file_io"))

# Fixed canonical values the C++ helper's encode mode always uses -- must
# match tests/cpp/test_wire_evolution_file_io.cpp.
HEADER = 0x1234
SEQ = 42
CRC_SEED = 0xDEADBEEF


def _generate(out_dir: Path) -> None:
    for proto in (PROTO_V1, PROTO_V2):
        result = run_generator(proto, "--build_py", "--py_path", str(out_dir / "py"), "--force")
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            _check(False, f"code generation failed for {proto.name}")


def _load(py_dir: Path, module_name: str):
    return load_generated_module(
        py_dir / "struct_frame" / "generated" / f"{module_name}.py",
        module_name,
    )


def _run_cpp(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([str(CPP_RUNNER), *args], capture_output=True, text=True)


def test_wire_evolution_cross_lang(tmp_path: Path) -> None:
    """Python <-> C++, v1 <-> v2: real subprocess + file interchange."""
    if not CPP_RUNNER.exists():
        pytest.skip(f"{CPP_RUNNER} not built -- run test_all.py or run_tests.py first")

    _generate(tmp_path)
    v1 = _load(tmp_path / "py", "wire_evolution_v1")
    v2 = _load(tmp_path / "py", "wire_evolution_v2")

    # --- Scenario A: Python encodes v1 -> C++ decodes as v2 (zero-fill) ---
    msg_v1 = v1.BaseExtensionMessage(header=HEADER, seq=SEQ)
    f_a = tmp_path / "py_v1.bin"
    f_a.write_bytes(msg_v1.serialize())
    result = _run_cpp("decode", "v2", str(f_a))
    _check(result.returncode == 0,
           f"C++ failed to decode Python-encoded v1 as v2:\n{result.stdout}{result.stderr}")
    _check("crc_seed=0x00000000" in result.stdout,
           f"C++ should zero-fill the extension for a legacy Python-encoded v1 frame, got: {result.stdout}")

    # --- Scenario B: C++ encodes v1 -> Python decodes as v2 (zero-fill) ---
    f_b = tmp_path / "cpp_v1.bin"
    result = _run_cpp("encode", "v1", str(f_b))
    _check(result.returncode == 0, f"C++ failed to encode v1:\n{result.stdout}{result.stderr}")
    decoded = v2.BaseExtensionMessage.deserialize(f_b.read_bytes())
    _check(decoded.header == HEADER and decoded.seq == SEQ,
           f"Python v2 decode of C++-encoded v1 base fields mismatch: {decoded.header:#x}, {decoded.seq}")
    _check(decoded.crc_seed == 0,
           f"Python v2 decode of a C++-encoded legacy v1 frame should zero-fill crc_seed, got {decoded.crc_seed:#x}")

    # --- Scenario C: Python encodes v2 (with extension) -> C++ decodes as v1 ---
    msg_v2 = v2.BaseExtensionMessage(header=HEADER, seq=SEQ, crc_seed=CRC_SEED)
    f_c = tmp_path / "py_v2.bin"
    f_c.write_bytes(msg_v2.serialize())
    result = _run_cpp("decode", "v1", str(f_c))
    _check(result.returncode == 0,
           "C++ v1 decoder should gracefully read only the base fields of a "
           f"Python-encoded v2 frame:\n{result.stdout}{result.stderr}")
    _check(f"header=0x{HEADER:04x} seq={SEQ}" in result.stdout,
           f"C++ v1 base-field decode mismatch: {result.stdout}")

    # --- Scenario D: C++ encodes v2 (with extension) -> Python decodes as v1 ---
    f_d = tmp_path / "cpp_v2.bin"
    result = _run_cpp("encode", "v2", str(f_d))
    _check(result.returncode == 0, f"C++ failed to encode v2:\n{result.stdout}{result.stderr}")
    decoded_v1 = v1.BaseExtensionMessage.deserialize(f_d.read_bytes())
    _check(decoded_v1.header == HEADER and decoded_v1.seq == SEQ,
           f"Python v1 decode of C++-encoded v2 base fields mismatch: {decoded_v1.header:#x}, {decoded_v1.seq}")
