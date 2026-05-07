#!/usr/bin/env python3
"""
Tests for the ``--no_packed`` CLI flag.

The flag should:
1. Cause every generated message to be treated as a variable-length message,
   so that field-by-field serialize/deserialize functions are emitted.
2. Cause the C and C++ generators to omit the ``#pragma pack(push, 1)`` /
   ``#pragma pack(pop)`` directives around struct definitions.
3. Produce code that round-trips successfully (encode → decode preserves
   field values) even when the host platform would otherwise rely on packed
   memory layout.

Usage:
    python tests/test_no_packed.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
PROTO_FILE = REPO_ROOT / "tests" / "proto" / "test_messages.sf"


def _run_generator(extra_args, out_dir: Path) -> None:
    cmd = [
        sys.executable,
        str(SRC_DIR / "main.py"),
        str(PROTO_FILE),
        "--build_c",
        "--c_path",
        str(out_dir / "c") + os.sep,
        "--build_cpp",
        "--cpp_path",
        str(out_dir / "cpp") + os.sep,
        "--force",
    ] + list(extra_args)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.check_call(cmd, env=env)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _check(condition, msg):
    if not condition:
        print(f"FAIL: {msg}")
        sys.exit(1)


def test_no_packed_flag():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        baseline_dir = tmp_path / "baseline"
        nopacked_dir = tmp_path / "nopacked"

        _run_generator([], baseline_dir)
        _run_generator(["--no_packed"], nopacked_dir)

        baseline_c = _read(baseline_dir / "c" / "serialization_test.structframe.h")
        nopacked_c = _read(nopacked_dir / "c" / "serialization_test.structframe.h")
        baseline_cpp = _read(baseline_dir / "cpp" / "serialization_test.structframe.hpp")
        nopacked_cpp = _read(nopacked_dir / "cpp" / "serialization_test.structframe.hpp")

        # 1. Pragma pack should be present in baseline output.
        _check("#pragma pack(push, 1)" in baseline_c,
               "baseline C output should contain #pragma pack(push, 1)")
        _check("#pragma pack(push, 1)" in baseline_cpp,
               "baseline C++ output should contain #pragma pack(push, 1)")

        # 2. Pragma pack should be absent in --no_packed output.
        _check("#pragma pack" not in nopacked_c,
               "--no_packed C output must not contain any #pragma pack directives")
        _check("#pragma pack" not in nopacked_cpp,
               "--no_packed C++ output must not contain any #pragma pack directives")

        # 3. With --no_packed every message should emit variable-length helpers.
        #    serialized_size + _serialize_variable + _deserialize_variable per message.
        _check(nopacked_c.count("_serialized_size(") > baseline_c.count("_serialized_size("),
               "--no_packed should emit serialized_size functions for more messages than the baseline")
        _check(nopacked_c.count("_serialize_variable(") > baseline_c.count("_serialize_variable("),
               "--no_packed should emit _serialize_variable functions for more messages than the baseline")
        _check(nopacked_cpp.count("size_t serialized_size()") >
               baseline_cpp.count("size_t serialized_size()"),
               "--no_packed should emit serialized_size() methods for more C++ structs than the baseline")

        # 4. The generated headers should still compile.
        try:
            _compile_c(nopacked_dir / "c")
            _compile_cpp(nopacked_dir / "cpp")
        except FileNotFoundError:
            print("SKIP: gcc/g++ not available, skipping compilation check")
            return

        # 5. Encode/decode round-trip with --no_packed succeeds.
        _roundtrip_c(nopacked_dir / "c")

    print("PASS: --no_packed flag tests")


def _compile_c(c_dir: Path) -> None:
    src = c_dir / "_compile_test.c"
    src.write_text(
        '#include "serialization_test.structframe.h"\n'
        "int main(void) { return 0; }\n",
        encoding="utf-8",
    )
    out = c_dir / "_compile_test.out"
    subprocess.check_call(
        ["gcc", "-std=c99", "-I", str(c_dir), str(src), "-o", str(out)],
    )


def _compile_cpp(cpp_dir: Path) -> None:
    src = cpp_dir / "_compile_test.cpp"
    src.write_text(
        '#include "serialization_test.structframe.hpp"\n'
        "int main() { return 0; }\n",
        encoding="utf-8",
    )
    out = cpp_dir / "_compile_test.out"
    subprocess.check_call(
        ["g++", "-std=c++20", "-I", str(cpp_dir), str(src), "-o", str(out)],
    )


def _roundtrip_c(c_dir: Path) -> None:
    src = c_dir / "_roundtrip.c"
    src.write_text(
        '#include <stdio.h>\n'
        '#include "serialization_test.structframe.h"\n'
        "int main(void) {\n"
        "    SerializationTestBasicTypesMessage m = {0}, m2 = {0};\n"
        "    m.small_int = -5; m.medium_int = 1000; m.regular_int = -123456;\n"
        "    m.large_int = 9000000000LL; m.small_uint = 200;\n"
        "    m.medium_uint = 50000; m.regular_uint = 4000000000U;\n"
        "    m.large_uint = 18000000000000ULL;\n"
        "    m.single_precision = 3.14f; m.double_precision = 2.71828;\n"
        "    m.flag = 1;\n"
        "    uint8_t buf[512];\n"
        "    size_t n = SerializationTestBasicTypesMessage_serialize(&m, buf);\n"
        "    if (n == 0) return 1;\n"
        "    size_t r = SerializationTestBasicTypesMessage_deserialize(buf, n, &m2);\n"
        "    if (r == 0) return 2;\n"
        "    if (m.small_int != m2.small_int || m.medium_int != m2.medium_int ||\n"
        "        m.regular_int != m2.regular_int || m.large_int != m2.large_int ||\n"
        "        m.small_uint != m2.small_uint || m.medium_uint != m2.medium_uint ||\n"
        "        m.regular_uint != m2.regular_uint || m.large_uint != m2.large_uint ||\n"
        "        m.flag != m2.flag) return 3;\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    out = c_dir / "_roundtrip.out"
    subprocess.check_call(
        ["gcc", "-std=c99", "-I", str(c_dir), str(src), "-o", str(out)],
    )
    subprocess.check_call([str(out)])


if __name__ == "__main__":
    test_no_packed_flag()
