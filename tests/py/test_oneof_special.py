#!/usr/bin/env python3
"""
Test for oneof special cases: discriminator=none and multi-oneof messages.

Mirrors tests/rust/src/main.rs::run_oneof_special_tests(), scoped to what the
Python generator actually exposes: discriminator=none oneofs are not
auto-decoded on deserialize() (the app must already know the active variant),
so the payload is recovered by slicing the known union byte range out of the
serialized envelope and deserializing it directly. This works for
NoneDiscriminatorMessage and MultiOneofMessage.first_payload (both fixed-size
union members); MultiOneofMessage.second_payload pairs discriminator=none
with variable-length payload types (Message/VariableSingleArray), whose
variable-format encoding does not align with the fixed-size union byte
layout the way the fixed-size cases here do, so it is not covered here.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'generated', 'py'))

from struct_frame.generated.serialization_test import (
    NoneDiscriminatorMessage, MultiOneofMessage, BasicTypesMessage,
)

_passed = 0
_failed = 0


def expect(condition, name):
    global _passed, _failed
    if condition:
        print(f"  PASS  {name}")
        _passed += 1
    else:
        print(f"  FAIL  {name}")
        _failed += 1


def main():
    print("=== Python oneof special tests ===")

    # --- NoneDiscriminatorMessage: no discriminator field, data bytes preserved ---
    basic = BasicTypesMessage(small_int=-42, medium_uint=5000)
    msg1 = NoneDiscriminatorMessage(header=0xAB, data={"basic": basic}, data_which="basic")

    raw1 = msg1.serialize()
    dec1 = NoneDiscriminatorMessage.deserialize(raw1)
    expect(dec1.header == 0xAB, "NoneDiscriminator: header round-trips")
    # Without a discriminator the receiver must know which variant to use --
    # slice the known union byte range and decode it directly.
    basic1 = BasicTypesMessage.deserialize(raw1[1:1 + BasicTypesMessage.MAX_SIZE])
    expect(basic1.small_int == -42, "NoneDiscriminator: basic.small_int round-trips")
    expect(basic1.medium_uint == 5000, "NoneDiscriminator: basic.medium_uint round-trips")

    # --- MultiOneofMessage: msgid-discriminated first_payload round-trips normally ---
    basic2 = BasicTypesMessage(small_int=99)
    msg2 = MultiOneofMessage(
        selector=7,
        first_payload={"basic": basic2},
        first_payload_which="basic",
        first_payload_discriminator=BasicTypesMessage.MSG_ID,
    )
    raw2 = msg2.serialize()
    dec2 = MultiOneofMessage.deserialize(raw2)
    expect(dec2.selector == 7, "MultiOneof: selector round-trips")
    expect(dec2.first_payload_discriminator == BasicTypesMessage.MSG_ID,
           "MultiOneof: first_payload discriminator is BasicTypesMessage MSG_ID")
    expect(dec2.first_payload_which == "basic", "MultiOneof: first_payload_which resolved via discriminator")
    b2 = dec2.first_payload.get("basic")
    expect(b2 is not None, "MultiOneof: first_payload auto-decoded")
    if b2 is not None:
        expect(b2.small_int == 99, "MultiOneof: basic.small_int round-trips")

    print(f"\nSummary: {_passed} passed, {_failed} failed")
    return 1 if _failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
