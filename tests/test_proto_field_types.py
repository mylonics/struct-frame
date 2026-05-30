#!/usr/bin/env python3
"""
Tests for Proto Field Type coverage gaps (section 2 of test-coverage.md).

Verifies:
- Enum-to-string helpers (C, C++, Python)
- flatten=true option: Python to_dict() inlines child fields
- discriminator=none oneof: no discriminator field generated
- Multiple oneof fields in one message

Usage:
    python tests/test_proto_field_types.py
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from test_utils import _check
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
PROTO_FILE = REPO_ROOT / "tests" / "proto" / "test_messages.sf"




def _generate(out_dir: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.check_call(
        [sys.executable, str(SRC_DIR / "main.py"), str(PROTO_FILE),
         "--build_py", "--py_path", str(out_dir / "py"),
         "--build_c", "--c_path", str(out_dir / "c"),
         "--build_cpp", "--cpp_path", str(out_dir / "cpp"),
         "--force"],
        env=env,
    )


def _import_generated_module(py_dir: Path):
    """Import the generated serialization_test Python module."""
    pyfile = py_dir / "struct_frame" / "generated" / "serialization_test.py"
    spec = importlib.util.spec_from_file_location("serialization_test", pyfile)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Python enum-to-string
# ---------------------------------------------------------------------------

def test_python_enum_to_string(mod) -> None:
    """Python enums expose .name for string conversion."""
    Priority = mod.Priority
    Status = mod.Status

    _check(Priority.HIGH.name == "HIGH",
           f"Priority.HIGH.name expected 'HIGH', got '{Priority.HIGH.name}'")
    _check(Priority.LOW.name == "LOW",
           f"Priority.LOW.name expected 'LOW', got '{Priority.LOW.name}'")
    _check(Priority.MEDIUM.name == "MEDIUM",
           f"Priority.MEDIUM.name expected 'MEDIUM', got '{Priority.MEDIUM.name}'")
    _check(Priority.CRITICAL.name == "CRITICAL",
           f"Priority.CRITICAL.name expected 'CRITICAL', got '{Priority.CRITICAL.name}'")

    _check(Status.ACTIVE.name == "ACTIVE",
           f"Status.ACTIVE.name expected 'ACTIVE', got '{Status.ACTIVE.name}'")
    _check(Status.INACTIVE.name == "INACTIVE",
           f"Status.INACTIVE.name expected 'INACTIVE', got '{Status.INACTIVE.name}'")


# ---------------------------------------------------------------------------
# C enum-to-string
# ---------------------------------------------------------------------------

_C_ENUM_TEST_SRC = r"""
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include "serialization_test.structframe.h"

int main(void) {
    assert(strcmp(SerializationTestPriority_to_string(SERIALIZATION_TEST_PRIORITY_HIGH), "HIGH") == 0);
    assert(strcmp(SerializationTestPriority_to_string(SERIALIZATION_TEST_PRIORITY_LOW), "LOW") == 0);
    assert(strcmp(SerializationTestPriority_to_string(SERIALIZATION_TEST_PRIORITY_MEDIUM), "MEDIUM") == 0);
    assert(strcmp(SerializationTestPriority_to_string(SERIALIZATION_TEST_PRIORITY_CRITICAL), "CRITICAL") == 0);
    assert(strcmp(SerializationTestStatus_to_string(SERIALIZATION_TEST_STATUS_ACTIVE), "ACTIVE") == 0);
    assert(strcmp(SerializationTestStatus_to_string(SERIALIZATION_TEST_STATUS_INACTIVE), "INACTIVE") == 0);
    printf("C enum-to-string: OK\n");
    return 0;
}
"""


def test_c_enum_to_string(c_dir: Path) -> None:
    """C generates {Pkg}{Enum}_to_string helpers; verify they return correct strings."""
    src = c_dir / "_enum_test.c"
    src.write_text(_C_ENUM_TEST_SRC, encoding="utf-8")
    out = c_dir / "_enum_test.out"
    try:
        subprocess.check_call(
            ["gcc", "-std=c99", "-I", str(c_dir), str(src), "-o", str(out)],
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        print("SKIP: gcc not available - skipping C enum-to-string test")
        return
    result = subprocess.run([str(out)], capture_output=True, text=True)
    _check(result.returncode == 0,
           f"C enum-to-string binary failed:\n{result.stdout}{result.stderr}")
    # Verify actual constant names in generated header
    header = (c_dir / "serialization_test.structframe.h").read_text()
    _check("SERIALIZATION_TEST_PRIORITY_HIGH" in header,
           "C header missing SERIALIZATION_TEST_PRIORITY_HIGH constant")
    _check("SerializationTestPriority_to_string" in header,
           "C header missing SerializationTestPriority_to_string function")


# ---------------------------------------------------------------------------
# C++ enum-to-string
# ---------------------------------------------------------------------------

_CPP_ENUM_TEST_SRC = r"""
#include <cstring>
#include <cassert>
#include <cstdio>
#include "serialization_test.structframe.hpp"
using namespace structframe::serialization_test;

int main() {
    assert(std::strcmp(Priority_to_string(Priority::High), "HIGH") == 0);
    assert(std::strcmp(Priority_to_string(Priority::Low), "LOW") == 0);
    assert(std::strcmp(Priority_to_string(Priority::Medium), "MEDIUM") == 0);
    assert(std::strcmp(Priority_to_string(Priority::Critical), "CRITICAL") == 0);
    assert(std::strcmp(Status_to_string(Status::Active), "ACTIVE") == 0);
    assert(std::strcmp(Status_to_string(Status::Inactive), "INACTIVE") == 0);
    printf("C++ enum-to-string: OK\n");
    return 0;
}
"""


def test_cpp_enum_to_string(cpp_dir: Path) -> None:
    """C++ generates {Enum}_to_string helpers; verify they return correct strings."""
    src = cpp_dir / "_enum_test.cpp"
    src.write_text(_CPP_ENUM_TEST_SRC, encoding="utf-8")
    out = cpp_dir / "_enum_test.out"
    try:
        subprocess.check_call(
            ["g++", "-std=c++20", "-I", str(cpp_dir), str(src), "-o", str(out)],
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        print("SKIP: g++ not available - skipping C++ enum-to-string test")
        return
    result = subprocess.run([str(out)], capture_output=True, text=True)
    _check(result.returncode == 0,
           f"C++ enum-to-string binary failed:\n{result.stdout}{result.stderr}")
    header = (cpp_dir / "serialization_test.structframe.hpp").read_text()
    _check("Priority_to_string" in header,
           "C++ header missing Priority_to_string function")
    _check("Status_to_string" in header,
           "C++ header missing Status_to_string function")


# ---------------------------------------------------------------------------
# Python flatten=true
# ---------------------------------------------------------------------------

def test_python_flatten(mod) -> None:
    """flatten=true causes inner fields to be inlined in to_dict() output."""
    FlattenMessage = mod.FlattenMessage
    FlattenInner = mod.FlattenInner

    inner = FlattenInner(a=7, b=300)
    msg = FlattenMessage(seq=42, inner=inner)
    d = msg.to_dict(include_name=False, include_id=False)

    # seq should be present at the top level
    _check("seq" in d, "flatten: 'seq' missing from to_dict() output")
    _check(d["seq"] == 42, f"flatten: seq expected 42, got {d['seq']}")

    # inner fields should be inlined (flatten=true) - no 'inner' key
    _check("inner" not in d,
           f"flatten: 'inner' key should not appear in to_dict() when flatten=true, got keys: {list(d.keys())}")

    # inner.a and inner.b should appear at the top level
    _check("a" in d, f"flatten: 'a' (from inner) missing from to_dict() output, got keys: {list(d.keys())}")
    _check("b" in d, f"flatten: 'b' (from inner) missing from to_dict() output, got keys: {list(d.keys())}")
    _check(d["a"] == 7, f"flatten: inner.a expected 7, got {d['a']}")
    _check(d["b"] == 300, f"flatten: inner.b expected 300, got {d['b']}")

    # Round-trip: serialize → deserialize preserves field values
    raw = msg.serialize()
    msg2 = FlattenMessage.deserialize(raw)
    _check(msg2.seq == 42, f"flatten round-trip: seq expected 42, got {msg2.seq}")
    _check(msg2.inner.a == 7, f"flatten round-trip: inner.a expected 7, got {msg2.inner.a}")
    _check(msg2.inner.b == 300, f"flatten round-trip: inner.b expected 300, got {msg2.inner.b}")


# ---------------------------------------------------------------------------
# Python discriminator=none
# ---------------------------------------------------------------------------

def test_python_discriminator_none(mod) -> None:
    """discriminator=none oneof: no discriminator field; encode/decode works."""
    NoneDiscriminatorMessage = mod.NoneDiscriminatorMessage
    BasicTypesMessage = mod.BasicTypesMessage

    # Verify no discriminator attribute exists
    msg = NoneDiscriminatorMessage()
    _check(not hasattr(msg, "data_discriminator"),
           "discriminator=none: 'data_discriminator' attribute should not exist")

    # Set the oneof to 'basic' variant and serialize
    basic = BasicTypesMessage()
    basic.small_int = -42
    basic.medium_uint = 5000

    msg.header = 0xAB
    msg.data = {"basic": basic}
    msg.data_which = "basic"

    raw = msg.serialize()
    _check(len(raw) == NoneDiscriminatorMessage.msg_size,
           f"discriminator=none: serialized size {len(raw)} != msg_size {NoneDiscriminatorMessage.msg_size}")
    # The header byte (0xAB) should be at offset 0 in the wire format
    _check(raw[0] == 0xAB,
           f"discriminator=none: header byte at offset 0 expected 0xAB, got {raw[0]:#x}")

    # Deserialize - without discriminator, variant is unknown; header round-trips
    msg2 = NoneDiscriminatorMessage.deserialize(raw)
    _check(msg2.header == 0xAB,
           f"discriminator=none round-trip: header expected 0xAB, got {msg2.header:#x}")
    # data_which should be None after deserialization (no discriminator to guide it)
    _check(msg2.data_which is None,
           f"discriminator=none: data_which should be None after deserialize, got {msg2.data_which!r}")


# ---------------------------------------------------------------------------
# Python multiple oneof
# ---------------------------------------------------------------------------

def test_python_multi_oneof(mod) -> None:
    """MultiOneofMessage has two independent oneof fields that encode/decode correctly."""
    MultiOneofMessage = mod.MultiOneofMessage
    BasicTypesMessage = mod.BasicTypesMessage
    SerializationTestMessage = mod.SerializationTestMessage

    msg = MultiOneofMessage()
    msg.selector = 3

    # Set first_payload to 'basic'
    basic = BasicTypesMessage()
    basic.small_int = 99
    msg.first_payload = {"basic": basic}
    msg.first_payload_which = "basic"
    msg.first_payload_discriminator = BasicTypesMessage.msg_id

    # Leave second_payload empty (discriminator=none, so no tracking needed)

    raw = msg.serialize()
    _check(len(raw) == MultiOneofMessage.msg_size,
           f"multi-oneof: serialized size {len(raw)} != msg_size {MultiOneofMessage.msg_size}")

    msg2 = MultiOneofMessage.deserialize(raw)
    _check(msg2.selector == 3,
           f"multi-oneof round-trip: selector expected 3, got {msg2.selector}")

    # first_payload should decode via msgid discriminator
    _check(msg2.first_payload_which == "basic",
           f"multi-oneof: first_payload_which expected 'basic', got {msg2.first_payload_which!r}")
    _check(msg2.first_payload["basic"].small_int == 99,
           f"multi-oneof: basic.small_int expected 99, got {msg2.first_payload['basic'].small_int}")

    # second_payload has discriminator=none, so variant unknown after round-trip
    _check(msg2.second_payload_which is None,
           f"multi-oneof: second_payload_which should be None, got {msg2.second_payload_which!r}")

    # Verify both oneof fields are present as attributes
    _check(hasattr(msg, "first_payload"), "multi-oneof: 'first_payload' attribute missing")
    _check(hasattr(msg, "second_payload"), "multi-oneof: 'second_payload' attribute missing")


# ---------------------------------------------------------------------------
# C discriminator=none and multi-oneof
# ---------------------------------------------------------------------------

_C_ONEOF_TEST_SRC = r"""
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <stdint.h>
#include "serialization_test.structframe.h"

int main(void) {
    /* ---- NoneDiscriminatorMessage: no discriminator field, header round-trips ---- */
    SerializationTestNoneDiscriminatorMessage msg1;
    memset(&msg1, 0, sizeof(msg1));
    msg1.header = 0xAB;

    /* Write a recognisable pattern into the union (BasicTypesMessage variant) */
    msg1.data.basic.small_int = -42;
    msg1.data.basic.medium_uint = 5000;

    uint8_t buf1[SERIALIZATION_TEST_NONE_DISCRIMINATOR_MESSAGE_MAX_SIZE];
    size_t n1 = SerializationTestNoneDiscriminatorMessage_serialize(&msg1, buf1);
    assert(n1 == SERIALIZATION_TEST_NONE_DISCRIMINATOR_MESSAGE_MAX_SIZE);

    SerializationTestNoneDiscriminatorMessage dec1;
    size_t r1 = SerializationTestNoneDiscriminatorMessage_deserialize(buf1, n1, &dec1);
    assert(r1 == n1);
    assert(dec1.header == 0xAB);
    /* With discriminator=none the receiver keeps the raw union bytes */
    assert(dec1.data.basic.small_int == -42);
    assert(dec1.data.basic.medium_uint == 5000);

    /* ---- MultiOneofMessage: two oneofs — first has msgid discriminator ---- */
    SerializationTestMultiOneofMessage msg2;
    memset(&msg2, 0, sizeof(msg2));
    msg2.selector = 7;
    /* first_payload: use the BasicTypesMessage variant; set discriminator */
    msg2.first_payload_discriminator = SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID;
    msg2.first_payload.basic.small_int = 99;
    /* second_payload: discriminator=none; use msg_payload variant (Message type) */
    msg2.second_payload.msg_payload.severity = SERIALIZATION_TEST_MSG_SEVERITY_SEV_WARN;

    uint8_t buf2[SERIALIZATION_TEST_MULTI_ONEOF_MESSAGE_MAX_SIZE];
    size_t n2 = SerializationTestMultiOneofMessage_serialize(&msg2, buf2);
    assert(n2 == SERIALIZATION_TEST_MULTI_ONEOF_MESSAGE_MAX_SIZE);

    SerializationTestMultiOneofMessage dec2;
    size_t r2 = SerializationTestMultiOneofMessage_deserialize(buf2, n2, &dec2);
    assert(r2 == n2);
    assert(dec2.selector == 7);
    assert(dec2.first_payload_discriminator == SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID);
    assert(dec2.first_payload.basic.small_int == 99);
    /* second_payload bytes preserved (discriminator=none) */
    assert(dec2.second_payload.msg_payload.severity == SERIALIZATION_TEST_MSG_SEVERITY_SEV_WARN);

    printf("C discriminator=none and multi-oneof: OK\n");
    return 0;
}
"""


def test_c_oneof(c_dir: Path) -> None:
    """C: discriminator=none oneof and multiple oneof fields both round-trip correctly."""
    src = c_dir / "_oneof_test.c"
    src.write_text(_C_ONEOF_TEST_SRC, encoding="utf-8")
    out = c_dir / "_oneof_test.out"
    try:
        result = subprocess.run(
            ["gcc", "-std=c99", "-I", str(c_dir), str(src), "-o", str(out)],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        print("SKIP: gcc not available - skipping C oneof tests")
        return
    _check(result.returncode == 0,
           f"C oneof test failed to compile:\n{result.stdout}{result.stderr}")
    run = subprocess.run([str(out)], capture_output=True, text=True)
    _check(run.returncode == 0,
           f"C oneof test binary failed:\n{run.stdout}{run.stderr}")


# ---------------------------------------------------------------------------
# C++ discriminator=none and multi-oneof
# ---------------------------------------------------------------------------

_CPP_ONEOF_TEST_SRC = r"""
#include <cstring>
#include <cassert>
#include <cstdio>
#include "serialization_test.structframe.hpp"
using namespace structframe::serialization_test;

int main() {
    // ---- NoneDiscriminatorMessage: no discriminator field, header round-trips ----
    NoneDiscriminatorMessage msg1{};
    msg1.header = 0xAB;
    msg1.data.basic.small_int = -42;
    msg1.data.basic.medium_uint = 5000;

    uint8_t buf1[NoneDiscriminatorMessage::MAX_SIZE];
    size_t n1 = msg1.serialize(buf1);
    assert(n1 == NoneDiscriminatorMessage::MAX_SIZE);

    NoneDiscriminatorMessage dec1{};
    size_t r1 = dec1.deserialize(buf1, n1);
    assert(r1 == n1);
    assert(dec1.header == 0xAB);
    assert(dec1.data.basic.small_int == -42);
    assert(dec1.data.basic.medium_uint == 5000);

    // ---- MultiOneofMessage: two oneofs — first has msgid discriminator ----
    MultiOneofMessage msg2{};
    msg2.selector = 7;
    msg2.first_payload_discriminator = BasicTypesMessage::MSG_ID;
    msg2.first_payload.basic.small_int = 99;
    // second_payload: discriminator=none; use msg_payload variant (Message type)
    msg2.second_payload.msg_payload.severity = MsgSeverity::SevWarn;

    uint8_t buf2[MultiOneofMessage::MAX_SIZE];
    size_t n2 = msg2.serialize(buf2);
    assert(n2 == MultiOneofMessage::MAX_SIZE);

    MultiOneofMessage dec2{};
    size_t r2 = dec2.deserialize(buf2, n2);
    assert(r2 == n2);
    assert(dec2.selector == 7);
    assert(dec2.first_payload_discriminator == BasicTypesMessage::MSG_ID);
    assert(dec2.first_payload.basic.small_int == 99);
    assert(dec2.second_payload.msg_payload.severity == MsgSeverity::SevWarn);

    printf("C++ discriminator=none and multi-oneof: OK\n");
    return 0;
}
"""


def test_cpp_oneof(cpp_dir: Path) -> None:
    """C++: discriminator=none oneof and multiple oneof fields both round-trip correctly."""
    src = cpp_dir / "_oneof_test.cpp"
    src.write_text(_CPP_ONEOF_TEST_SRC, encoding="utf-8")
    out = cpp_dir / "_oneof_test.out"
    try:
        result = subprocess.run(
            ["g++", "-std=c++20", "-I", str(cpp_dir), str(src), "-o", str(out)],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        print("SKIP: g++ not available - skipping C++ oneof tests")
        return
    _check(result.returncode == 0,
           f"C++ oneof test failed to compile:\n{result.stdout}{result.stderr}")
    run = subprocess.run([str(out)], capture_output=True, text=True)
    _check(run.returncode == 0,
           f"C++ oneof test binary failed:\n{run.stdout}{run.stderr}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        _generate(tmp_path)

        py_dir = tmp_path / "py"
        c_dir = tmp_path / "c"
        cpp_dir = tmp_path / "cpp"

        mod = _import_generated_module(py_dir)

        test_python_enum_to_string(mod)
        test_c_enum_to_string(c_dir)
        test_cpp_enum_to_string(cpp_dir)
        test_python_flatten(mod)
        test_python_discriminator_none(mod)
        test_python_multi_oneof(mod)
        test_c_oneof(c_dir)
        test_cpp_oneof(cpp_dir)

    print("PASS: Proto field type coverage tests")


if __name__ == "__main__":
    main()
