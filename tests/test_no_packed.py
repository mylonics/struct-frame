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

        # 6. Wire-size equivalence: for messages that contain only fixed-size
        #    fields (no bounded arrays / variable strings), the variable
        #    encoding emitted with --no_packed must produce the EXACT same
        #    wire bytes (and therefore the same wire size) as the packed
        #    baseline encoding. This guarantees binary compatibility on the
        #    wire when only --no_packed flips between the two modes.
        _wire_size_parity(baseline_dir / "c", nopacked_dir / "c")

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


def _wire_size_parity(baseline_c_dir: Path, nopacked_c_dir: Path) -> None:
    """For a fully-fixed-size message, packed and --no_packed must produce
    the same wire size and the same wire bytes.

    Uses ``Sensor`` (uint8 + float + enum + fixed string[16]), which has no
    bounded arrays or variable strings. The baseline build encodes such a
    message with ``memcpy`` of the packed struct; the --no_packed build
    encodes it field-by-field via ``_serialize_variable``. Both encodings
    must be byte-for-byte identical.
    """
    # Baseline: dump the packed in-memory struct (which IS the wire format
    # for non-variable messages) into a binary file.
    baseline_src = baseline_c_dir / "_wire_dump.c"
    baseline_src.write_text(
        '#include <stdio.h>\n'
        '#include <string.h>\n'
        '#include "serialization_test.structframe.h"\n'
        "int main(int argc, char** argv) {\n"
        "    SerializationTestSensor s;\n"
        "    memset(&s, 0, sizeof(s));\n"
        "    s.id = 7;\n"
        "    s.value = 3.14f;\n"
        "    s.status = (SerializationTestStatus)1;\n"
        "    const char name[] = \"sensor-alpha-12\";\n"
        "    memcpy(s.name, name, sizeof(name));\n"
        "    FILE* f = fopen(argv[1], \"wb\");\n"
        "    if (!f) return 1;\n"
        "    /* Packed wire encoding == raw struct memory */\n"
        "    fwrite(&s, 1, SERIALIZATION_TEST_SENSOR_MAX_SIZE, f);\n"
        "    fclose(f);\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    baseline_out = baseline_c_dir / "_wire_dump.out"
    subprocess.check_call(
        ["gcc", "-std=c99", "-I", str(baseline_c_dir), str(baseline_src), "-o", str(baseline_out)],
    )
    baseline_bin = baseline_c_dir / "_wire.bin"
    subprocess.check_call([str(baseline_out), str(baseline_bin)])

    # --no_packed: encode the same logical message via the generated
    # _serialize_variable path.
    nopacked_src = nopacked_c_dir / "_wire_dump.c"
    nopacked_src.write_text(
        '#include <stdio.h>\n'
        '#include <string.h>\n'
        '#include "serialization_test.structframe.h"\n'
        "int main(int argc, char** argv) {\n"
        "    SerializationTestSensor s;\n"
        "    memset(&s, 0, sizeof(s));\n"
        "    s.id = 7;\n"
        "    s.value = 3.14f;\n"
        "    s.status = (SerializationTestStatus)1;\n"
        "    const char name[] = \"sensor-alpha-12\";\n"
        "    memcpy(s.name, name, sizeof(name));\n"
        "    uint8_t buf[256];\n"
        "    size_t n = SerializationTestSensor_serialize(&s, buf);\n"
        "    FILE* f = fopen(argv[1], \"wb\");\n"
        "    if (!f) return 1;\n"
        "    fwrite(buf, 1, n, f);\n"
        "    fclose(f);\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    nopacked_out = nopacked_c_dir / "_wire_dump.out"
    subprocess.check_call(
        ["gcc", "-std=c99", "-I", str(nopacked_c_dir), str(nopacked_src), "-o", str(nopacked_out)],
    )
    nopacked_bin = nopacked_c_dir / "_wire.bin"
    subprocess.check_call([str(nopacked_out), str(nopacked_bin)])

    baseline_bytes = baseline_bin.read_bytes()
    nopacked_bytes = nopacked_bin.read_bytes()

    _check(
        len(baseline_bytes) == len(nopacked_bytes),
        f"wire size mismatch for fixed-size Sensor: packed={len(baseline_bytes)} "
        f"!= no_packed={len(nopacked_bytes)}",
    )
    _check(
        baseline_bytes == nopacked_bytes,
        f"wire bytes mismatch for fixed-size Sensor: packed={baseline_bytes.hex()} "
        f"!= no_packed={nopacked_bytes.hex()}",
    )


if __name__ == "__main__":
    test_no_packed_flag()
