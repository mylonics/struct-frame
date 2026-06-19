#!/usr/bin/env python3
"""
Subscribe / dispatch tests for the Python StructFrameSdk (section 6.3)

Uses a MockTransport and real frame encoding to verify that subscribed handlers
are invoked with the correct raw payload bytes when framed data arrives over
the transport.
"""

import sys
import os

# Generated code path (contains frame_profiles.py, struct_frame package, etc.)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'generated', 'py'))

# StructFrameSdk and ITransport live in the boilerplate source directory.
# Import them directly from their submodules to avoid pulling in optional
# transport dependencies (serial, network, etc.) that may not be installed.
_sdk_dir = os.path.join(
    os.path.dirname(__file__), '..', '..', 'src', 'struct_frame', 'boilerplate', 'py'
)
sys.path.insert(0, _sdk_dir)

from struct_frame_sdk.struct_frame_sdk import StructFrameSdk, StructFrameSdkConfig
from struct_frame_sdk.transport import ITransport

from frame_profiles import (
    BufferWriter,
    PROFILE_STANDARD_CONFIG,
    parse_frame_buffer,
    encode_message,
)
from struct_frame.generated.serialization_test import (
    BasicTypesMessage,
    get_message_info,
)

# ---------------------------------------------------------------------------
# Mock transport
# ---------------------------------------------------------------------------

class MockTransport(ITransport):
    """Records all sends and lets tests push incoming data."""

    def __init__(self):
        self._data_cb = None
        self._error_cb = None
        self._close_cb = None
        self._connected = False
        self.sent_data = []

    def connect(self):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def send(self, data: bytes):
        self.sent_data.append(bytes(data))
        return len(data)

    def set_data_callback(self, callback):
        self._data_cb = callback

    def set_error_callback(self, callback):
        self._error_cb = callback

    def set_close_callback(self, callback):
        self._close_cb = callback

    def is_connected(self) -> bool:
        return self._connected

    def inject_data(self, data: bytes):
        """Simulate data arriving from the peer."""
        if self._data_cb:
            self._data_cb(data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_unknown_frame(msg_id: int, data: bytes) -> bytes:
    """Frame raw bytes under a ProfileStandard frame for an arbitrary msg_id."""
    raw_cls = type('_RawMsg', (), {
        'MSG_ID': msg_id,
        'MAGIC1': 0,
        'MAGIC2': 0,
        'serialize': lambda self_: bytes(data),
    })
    return bytes(encode_message(PROFILE_STANDARD_CONFIG, raw_cls()))


def encode_basic_types(msg: BasicTypesMessage) -> bytes:
    """Encode a BasicTypesMessage into a ProfileStandard frame."""
    writer = BufferWriter(PROFILE_STANDARD_CONFIG)
    writer.write(msg)
    return bytes(writer.data())


def make_sdk(transport: MockTransport) -> StructFrameSdk:
    config = StructFrameSdkConfig(
        transport=transport,
        profile=PROFILE_STANDARD_CONFIG,
        get_message_info=get_message_info,
    )
    return StructFrameSdk(config)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

tests_run = 0
tests_passed = 0
tests_failed = 0


def run_test(name: str, result: bool):
    global tests_run, tests_passed, tests_failed
    tests_run += 1
    status = "PASS" if result else "FAIL"
    print(f"  {status}  {name}")
    if result:
        tests_passed += 1
    else:
        tests_failed += 1


def test_subscribe_dispatch_raw_bytes():
    """Handler receives the raw payload bytes when a frame arrives."""
    transport = MockTransport()
    sdk = make_sdk(transport)

    received_payload = []
    received_msg_id = []

    unsubscribe = sdk.subscribe(BasicTypesMessage.MSG_ID,
                                lambda payload, msg_id: (
                                    received_payload.append(payload),
                                    received_msg_id.append(msg_id),
                                ))

    msg = BasicTypesMessage()
    msg.regular_int = 42
    msg.flag = True
    transport.inject_data(encode_basic_types(msg))

    run_test("subscribe: handler invoked on incoming frame",
             len(received_payload) == 1)
    run_test("subscribe: msg_id matches",
             received_msg_id and received_msg_id[0] == BasicTypesMessage.MSG_ID)

    # Deserialise the raw bytes to verify field round-trip
    if received_payload:
        decoded = BasicTypesMessage.deserialize(received_payload[0])
        run_test("subscribe: regular_int round-trips correctly",
                 decoded.regular_int == 42)
        run_test("subscribe: flag round-trips correctly",
                 decoded.flag is True)
        run_test("subscribe: payload byte-for-byte matches serialize()",
                 received_payload[0] == msg.serialize())
    else:
        run_test("subscribe: regular_int round-trips correctly", False)
        run_test("subscribe: flag round-trips correctly", False)
        run_test("subscribe: payload byte-for-byte matches serialize()", False)

    unsubscribe()
    transport.inject_data(encode_basic_types(msg))
    run_test("subscribe: unsubscribe callback stops delivery",
             len(received_payload) == 1)


def test_multiple_handlers_same_id():
    """All registered handlers for a message ID are invoked."""
    transport = MockTransport()
    sdk = make_sdk(transport)

    count_a, count_b = [0], [0]
    sdk.subscribe(BasicTypesMessage.MSG_ID, lambda *_: count_a.__setitem__(0, count_a[0] + 1))
    sdk.subscribe(BasicTypesMessage.MSG_ID, lambda *_: count_b.__setitem__(0, count_b[0] + 1))

    msg = BasicTypesMessage()
    transport.inject_data(encode_basic_types(msg))

    run_test("multiple handlers: first fires", count_a[0] == 1)
    run_test("multiple handlers: second fires", count_b[0] == 1)


def test_unsubscribe_removes_handler():
    """The unsubscribe function returned by subscribe() stops delivery."""
    transport = MockTransport()
    sdk = make_sdk(transport)

    count = [0]
    unsubscribe = sdk.subscribe(BasicTypesMessage.MSG_ID,
                                lambda *_: count.__setitem__(0, count[0] + 1))

    msg = BasicTypesMessage()
    transport.inject_data(encode_basic_types(msg))
    run_test("unsubscribe: handler fires before unsubscribe", count[0] == 1)

    unsubscribe()  # remove handler

    transport.inject_data(encode_basic_types(msg))
    run_test("unsubscribe: handler silent after unsubscribe", count[0] == 1)


def test_no_handler_for_unknown_id():
    """An incoming frame with a subscribed ID fires; unknown ID is silently ignored."""
    transport = MockTransport()
    sdk = make_sdk(transport)

    fired = [False]
    sdk.subscribe(BasicTypesMessage.MSG_ID, lambda *_: fired.__setitem__(0, True))

    # Test 1: known ID fires the handler
    msg = BasicTypesMessage()
    transport.inject_data(encode_basic_types(msg))
    run_test("known id: handler fires", fired[0] is True)

    # Test 2: unknown ID does not fire the handler
    fired[0] = False
    # Encode a frame with a message ID that has no subscriber
    UNKNOWN_MSG_ID = 0xFE
    unknown_frame = make_unknown_frame(UNKNOWN_MSG_ID, b'\x00' * 4)
    transport.inject_data(unknown_frame)
    run_test("unknown id: handler does not fire", fired[0] is False)


def test_send_raw_frames_through_transport():
    """sdk.send_raw() encodes and emits data through the transport."""
    transport = MockTransport()
    sdk = make_sdk(transport)

    payload = BasicTypesMessage().serialize()
    send_result = sdk.send_raw(BasicTypesMessage.MSG_ID, payload)

    run_test("send_raw: transport received data", len(transport.sent_data) == 1)
    run_test("send_raw: result.success is true", send_result.success is True)
    run_test("send_raw: attempted_bytes equals bytes_written",
             send_result.attempted_bytes == send_result.bytes_written)
    run_test("send_raw: frame is non-empty", len(transport.sent_data[0]) > 0)

    frame = transport.sent_data[0]
    parsed = parse_frame_buffer(PROFILE_STANDARD_CONFIG, frame, get_message_info)
    run_test("send_raw: emitted frame parses as valid", parsed.valid)
    run_test("send_raw: emitted frame msg_id preserved",
             parsed.msg_id == BasicTypesMessage.MSG_ID)
    run_test("send_raw: emitted frame payload preserved",
             parsed.msg_data == payload)


def test_codec_registration_and_message_decoding():
    """Registered codecs are used before notifying handlers."""
    transport = MockTransport()
    sdk = make_sdk(transport)

    class _Codec:
        msg_id = BasicTypesMessage.MSG_ID

        def deserialize(self, data: bytes):
            msg = BasicTypesMessage.deserialize(data)
            return {
                "regular_int": msg.regular_int,
                "flag": msg.flag,
            }

    received = []
    sdk.register_codec(_Codec())
    sdk.subscribe(BasicTypesMessage.MSG_ID,
                  lambda payload, _msg_id: received.append(payload))

    msg = BasicTypesMessage()
    msg.regular_int = 77
    msg.flag = True
    transport.inject_data(encode_basic_types(msg))

    run_test("codec: handler invoked", len(received) == 1)
    run_test("codec: handler receives decoded object", isinstance(received[0], dict))
    run_test("codec: decoded regular_int preserved", received[0].get("regular_int") == 77)
    run_test("codec: decoded flag preserved", received[0].get("flag") is True)


def test_close_callback_clears_buffer_state():
    """Transport close callback resets SDK parse buffer."""
    transport = MockTransport()
    sdk = make_sdk(transport)

    # Inject a truncated frame so the reader retains unread (partial) bytes.
    msg = BasicTypesMessage()
    msg.regular_int = 5
    encoded = encode_basic_types(msg)
    transport.inject_data(encoded[: max(1, len(encoded) // 2)])
    run_test("close: reader holds partial frame before close", sdk.reader.has_partial())

    if transport._close_cb:
        transport._close_cb()
    run_test("close: reader partial state cleared after close callback",
             not sdk.reader.has_partial())


def test_throwing_handler_does_not_stop_siblings():
    """A handler that raises must not prevent sibling handlers from running.

    Lifecycle parity with the C# `TestThrowingHandlerDoesNotStopSiblings`
    test: the SDK isolates each handler in try/except so one bad subscriber
    cannot starve the others or escape into the transport callback.
    """
    transport = MockTransport()
    sdk = make_sdk(transport)

    sibling_fired = [False]

    def _throwing(*_):
        raise RuntimeError("boom")

    sdk.subscribe(BasicTypesMessage.MSG_ID, _throwing)
    sdk.subscribe(BasicTypesMessage.MSG_ID,
                  lambda *_: sibling_fired.__setitem__(0, True))

    raised = False
    try:
        transport.inject_data(encode_basic_types(BasicTypesMessage()))
    except Exception:
        raised = True

    run_test("handler isolation: throwing handler does not propagate", not raised)
    run_test("handler isolation: sibling handler still fires", sibling_fired[0] is True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print()
    print("========================================")
    print("SDK SUBSCRIBE/DISPATCH TESTS - Python")
    print("========================================")
    print()

    test_subscribe_dispatch_raw_bytes()
    test_multiple_handlers_same_id()
    test_unsubscribe_removes_handler()
    test_no_handler_for_unknown_id()
    test_send_raw_frames_through_transport()
    test_codec_registration_and_message_decoding()
    test_close_callback_clears_buffer_state()
    test_throwing_handler_does_not_stop_siblings()

    print()
    print("========================================")
    print(f"Summary: {tests_passed}/{tests_run} tests passed")
    print("========================================")
    print()

    return 1 if tests_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
