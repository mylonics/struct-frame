#!/usr/bin/env python3
"""
Cross-language x cross-version wire-evolution interop (hub matrix).

``test_wire_evolution_interop.py`` proves cross-VERSION interop (v1<->v2)
entirely within Python; every per-language interop runner
(``tests/{c,cpp,ts,js,csharp,rust}/test_wire_evolution_interop.*``) proves
the same thing entirely within its own language, in-process. None of them
prove that a v1 frame encoded by language X is correctly read by language
Y's v2 decoder (or vice versa) -- every existing check runs in a single
process, never through a real subprocess + file handoff between two
different languages' implementations.

This test drives each language's ``test_wire_evolution_file_io`` helper
(``tests/{c,cpp,ts,js,csharp,rust}/test_wire_evolution_file_io.*``) as a
real subprocess with real file interchange, for the canonical
``BaseExtensionMessage`` (v1: {header, seq}; v2 adds the {crc_seed}
extension). Rather than running every language against every other
language directly (an O(n^2) matrix), it mirrors the hub-and-spoke design
``tests/run_tests.py`` already uses for the main standard-messages matrix:
C++ is the reference encoder, and pairwise compatibility is established
transitively --

  1. every language's v1/v2 encoding is byte-compared against the C++
     reference encoding, and
  2. every language decodes the C++ reference bytes in both cross-version
     directions (v1 bytes read as v2 => extension zero-filled; v2 bytes
     read as v1 => degrades gracefully to the base fields).

Since (1) proves every language's bytes are identical to C++'s, and (2)
proves every language can correctly cross-version-decode C++'s bytes, any
two languages are transitively guaranteed to interoperate without ever
being executed back-to-back -- the same reasoning that makes the main
matrix sound (see tests/coverage_spec.py section 4).

Each language's helper validates its own decoded header/seq/crc_seed
against the shared canonical constants (HEADER/SEQ/CRC_SEED below) and
exits non-zero on any mismatch, so a clean exit code from a decode call
already proves the zero-fill/degrade semantics held -- no fragile
per-language stdout parsing needed.

Skips entirely if the C++ helper isn't built (it anchors the whole
matrix); any other language's helper that isn't built is individually
skipped with a note, not failed, so this test degrades gracefully when
run without a full ``test_all.py``/``run_tests.py`` pass. In CI,
``test_all.py`` always compiles every language first, so the matrix is
fully enforced there.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import pytest

from test_utils import _check, run_generator, load_generated_module, REPO_ROOT

PROTO_V1 = REPO_ROOT / "tests" / "proto" / "wire_evolution_v1.sf"
PROTO_V2 = REPO_ROOT / "tests" / "proto" / "wire_evolution_v2.sf"

# Fixed canonical values every language's file_io helper always uses.
HEADER = 0x1234
SEQ = 42
CRC_SEED = 0xDEADBEEF

_EXE = ".exe" if sys.platform == "win32" else ""


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


class _Runner:
    """One language's file_io helper. ``command`` is None if not built."""

    def __init__(self, lang_id: str, command: Optional[List[str]]):
        self.lang_id = lang_id
        self.command = command

    @property
    def available(self) -> bool:
        return self.command is not None

    def run(self, mode: str, version: str, path: Path) -> Tuple[int, str, str]:
        result = subprocess.run(self.command + [mode, version, str(path)],
                                 capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr


def _cpp_runner() -> _Runner:
    exe = REPO_ROOT / "tests" / "cpp" / "build" / f"test_wire_evolution_file_io{_EXE}"
    return _Runner("cpp", [str(exe)] if exe.exists() else None)


def _c_runner() -> _Runner:
    exe = REPO_ROOT / "tests" / "c" / "build" / f"test_wire_evolution_file_io{_EXE}"
    return _Runner("c", [str(exe)] if exe.exists() else None)


def _rust_runner() -> _Runner:
    exe = REPO_ROOT / "tests" / "rust" / "target" / "debug" / f"test_wire_evolution_file_io{_EXE}"
    return _Runner("rust", [str(exe)] if exe.exists() else None)


def _ts_runner() -> _Runner:
    js = REPO_ROOT / "tests" / "ts" / "build" / "ts" / "test_wire_evolution_file_io.js"
    return _Runner("ts", ["node", str(js)] if js.exists() else None)


def _js_runner() -> _Runner:
    js = REPO_ROOT / "tests" / "js" / "test_wire_evolution_file_io.js"
    return _Runner("js", ["node", str(js)] if js.exists() else None)


def _csharp_runner() -> _Runner:
    base = REPO_ROOT / "tests" / "csharp" / "bin" / "Release"
    dll = None
    if base.exists():
        # Multiple TFM dirs (net8.0, net10.0, ...) may exist; any built DLL works.
        for candidate in sorted(base.iterdir()):
            if (candidate / "StructFrameTests.dll").exists():
                dll = candidate / "StructFrameTests.dll"
                break
    if dll is None:
        return _Runner("csharp", None)
    return _Runner("csharp", ["dotnet", str(dll), "--runner", "test_wire_evolution_file_io"])


def test_wire_evolution_cross_lang_matrix(tmp_path: Path) -> None:
    """Hub-based cross-language x cross-version matrix, anchored on C++."""
    cpp = _cpp_runner()
    if not cpp.available:
        pytest.skip("C++ test_wire_evolution_file_io not built -- run test_all.py or run_tests.py first")

    _generate(tmp_path)
    v1 = _load(tmp_path / "py", "wire_evolution_v1")
    v2 = _load(tmp_path / "py", "wire_evolution_v2")

    # --- C++ reference bytes (every other language is checked against these) ---
    cpp_v1_file = tmp_path / "cpp_v1.bin"
    cpp_v2_file = tmp_path / "cpp_v2.bin"
    rc, out, err = cpp.run("encode", "v1", cpp_v1_file)
    _check(rc == 0, f"C++ reference v1 encode failed:\n{out}{err}")
    rc, out, err = cpp.run("encode", "v2", cpp_v2_file)
    _check(rc == 0, f"C++ reference v2 encode failed:\n{out}{err}")
    cpp_v1_bytes = cpp_v1_file.read_bytes()
    cpp_v2_bytes = cpp_v2_file.read_bytes()

    checked = ["cpp"]
    skipped: List[str] = []

    for runner in (_c_runner(), _ts_runner(), _js_runner(), _csharp_runner(), _rust_runner()):
        if not runner.available:
            skipped.append(runner.lang_id)
            continue
        checked.append(runner.lang_id)

        # Encode: byte-identical to the C++ reference, both versions.
        f1, f2 = tmp_path / f"{runner.lang_id}_v1.bin", tmp_path / f"{runner.lang_id}_v2.bin"
        rc, out, err = runner.run("encode", "v1", f1)
        _check(rc == 0, f"{runner.lang_id}: v1 encode failed:\n{out}{err}")
        _check(f1.read_bytes() == cpp_v1_bytes,
               f"{runner.lang_id}: v1 encoding does not match the C++ reference byte-for-byte")
        rc, out, err = runner.run("encode", "v2", f2)
        _check(rc == 0, f"{runner.lang_id}: v2 encode failed:\n{out}{err}")
        _check(f2.read_bytes() == cpp_v2_bytes,
               f"{runner.lang_id}: v2 encoding does not match the C++ reference byte-for-byte")

        # Decode the C++ reference bytes in both cross-version directions.
        # A clean exit code already proves the zero-fill/degrade semantics
        # held, since each helper validates header/seq/crc_seed internally.
        rc, out, err = runner.run("decode", "v2", cpp_v1_file)
        _check(rc == 0,
               f"{runner.lang_id}: failed to decode the C++ v1 reference bytes as v2 "
               f"(extension should zero-fill):\n{out}{err}")
        rc, out, err = runner.run("decode", "v1", cpp_v2_file)
        _check(rc == 0,
               f"{runner.lang_id}: failed to decode the C++ v2 reference bytes as v1 "
               f"(should degrade gracefully to base fields):\n{out}{err}")

    # Python has no subprocess helper (none is needed) -- exercise the exact
    # same four checks directly against the generated Python module.
    checked.append("py")
    py_v1 = v1.BaseExtensionMessage(header=HEADER, seq=SEQ)
    _check(py_v1.serialize() == cpp_v1_bytes,
           "py: v1 encoding does not match the C++ reference byte-for-byte")
    py_v2 = v2.BaseExtensionMessage(header=HEADER, seq=SEQ, crc_seed=CRC_SEED)
    _check(py_v2.serialize() == cpp_v2_bytes,
           "py: v2 encoding does not match the C++ reference byte-for-byte")
    decoded_as_v2 = v2.BaseExtensionMessage.deserialize(cpp_v1_bytes)
    _check(decoded_as_v2.header == HEADER and decoded_as_v2.seq == SEQ and decoded_as_v2.crc_seed == 0,
           f"py: failed to decode the C++ v1 reference bytes as v2 (zero-fill expected), got {decoded_as_v2}")
    decoded_as_v1 = v1.BaseExtensionMessage.deserialize(cpp_v2_bytes)
    _check(decoded_as_v1.header == HEADER and decoded_as_v1.seq == SEQ,
           f"py: failed to decode the C++ v2 reference bytes as v1, got {decoded_as_v1}")

    print(f"[wire-evolution cross-lang matrix] checked: {sorted(checked)}"
          + (f"; not built, skipped: {sorted(skipped)}" if skipped else ""))
