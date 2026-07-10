#!/usr/bin/env python3
"""
Test for envelope SDK interface: msgid-discriminator (CommandEnvelope) and
field_order-discriminator (RawDataEnvelope) round-trips.

Mirrors tests/rust/src/main.rs::run_envelope_sdk_tests().
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'generated', 'py'))

from struct_frame.generated.envelope_test import (
    CommandEnvelope, ADCCommand, RawDataEnvelope, RawSamplePayload,
    RawDataEnvelopePayloadField, get_message_info,
)
from frame_profiles import BufferWriter, AccumulatingReader, PROFILE_STANDARD_CONFIG, PROFILE_BULK_CONFIG

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
    print("=== Python EnvelopeSdk tests ===")

    # --- CommandEnvelope with msgid discriminator ---
    adc = ADCCommand(channel=2, sample_rate=1000, enable=True)
    env = CommandEnvelope.wrap(adc, 42, 5, True)

    expect(env.command_discriminator == ADCCommand.MSG_ID,
           "CommandEnvelope: discriminator == ADCCommand.MSG_ID")

    writer = BufferWriter(PROFILE_STANDARD_CONFIG, capacity=2048)
    written = writer.write(env)
    expect(written > 0, "CommandEnvelope: write returned > 0")

    reader = AccumulatingReader(PROFILE_STANDARD_CONFIG, get_message_info=get_message_info, buffer_size=4096)
    reader.add_data(bytes(writer.data())[:written])
    frame = reader.next()
    expect(frame.valid, "CommandEnvelope: frame valid")
    if frame.valid:
        expect(frame.msg_id == CommandEnvelope.MSG_ID, "CommandEnvelope: msg_id matches")
        decoded = CommandEnvelope.deserialize(frame)
        expect(decoded is not None, "CommandEnvelope: deserialize succeeded")
        expect(decoded.sequence_number == 42, "CommandEnvelope: sequence_number round-trips")
        expect(decoded.priority == 5, "CommandEnvelope: priority round-trips")
        expect(decoded.run_immediately, "CommandEnvelope: run_immediately round-trips")
        expect(decoded.command_discriminator == ADCCommand.MSG_ID,
               "CommandEnvelope: discriminator round-trips")
        adc2 = decoded.unwrap()
        expect(adc2 is not None, "CommandEnvelope: unwrap() returns payload")
        if adc2 is not None:
            expect(adc2.channel == 2, "CommandEnvelope: adc.channel round-trips")
            expect(adc2.sample_rate == 1000, "CommandEnvelope: adc.sample_rate round-trips")
            expect(adc2.enable, "CommandEnvelope: adc.enable round-trips")

    # --- RawDataEnvelope with field_order discriminator ---
    sample = RawSamplePayload(channel=7, value=2.718, flags=0xBE)
    raw_env = RawDataEnvelope.wrap(sample, 3, 999000)

    # field_order discriminator: sample is 1st field -> discriminator == 1
    expect(raw_env.payload_discriminator == RawDataEnvelopePayloadField.SAMPLE,
           "RawDataEnvelope: field_order discriminator == SAMPLE (1) for first variant")

    raw_writer = BufferWriter(PROFILE_BULK_CONFIG, capacity=2048)
    raw_written = raw_writer.write(raw_env)
    expect(raw_written > 0, "RawDataEnvelope: write returned > 0")

    raw_reader = AccumulatingReader(PROFILE_BULK_CONFIG, get_message_info=get_message_info, buffer_size=4096)
    raw_reader.add_data(bytes(raw_writer.data())[:raw_written])
    raw_frame = raw_reader.next()
    expect(raw_frame.valid, "RawDataEnvelope: frame valid")
    if raw_frame.valid:
        raw_decoded = RawDataEnvelope.deserialize(raw_frame)
        expect(raw_decoded is not None, "RawDataEnvelope: deserialize succeeded")
        expect(raw_decoded.priority == 3, "RawDataEnvelope: priority round-trips")
        expect(raw_decoded.timestamp_us == 999000, "RawDataEnvelope: timestamp_us round-trips")
        expect(raw_decoded.payload_discriminator == RawDataEnvelopePayloadField.SAMPLE,
               "RawDataEnvelope: discriminator round-trips == SAMPLE")
        s2 = raw_decoded.unwrap()
        expect(s2 is not None, "RawDataEnvelope: unwrap() returns payload")
        if s2 is not None:
            expect(s2.channel == 7, "RawDataEnvelope: sample.channel round-trips")
            expect(abs(s2.value - 2.718) < 1e-4, "RawDataEnvelope: sample.value round-trips")
            expect(s2.flags == 0xBE, "RawDataEnvelope: sample.flags round-trips")

    print(f"\nSummary: {_passed} passed, {_failed} failed")
    return 1 if _failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
