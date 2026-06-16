#!/usr/bin/env python3
"""
Subscribe / dispatch tests for the Python AsyncStructFrameSdk (section 6.3)

Mirrors test_sdk.py but exercises AsyncStructFrameSdk:
  - subscribe / _dispatch routing (synchronous parsing, registered handlers)
  - unsubscribe stops delivery
  - send_raw / send framing through a mock async transport
  - register_codec + auto-deserialize before handler call
  - close callback resets reader partial-frame state
  - async context manager (__aenter__ / __aexit__)

All async calls are driven with asyncio.run() so the file can run as a
plain Python script without a test framework.
"""

import asyncio
import sys
import os

# Generated code path (contains frame_profiles.py, struct_frame package, etc.)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'generated', 'py'))

# SDK and transport interfaces live in the boilerplate source directory.
_sdk_dir = os.path.join(
    os.path.dirname(__file__), '..', '..', 'src', 'struct_frame', 'boilerplate', 'py'
)
sys.path.insert(0, _sdk_dir)

from struct_frame_sdk.async_struct_frame_sdk import AsyncStructFrameSdk, AsyncStructFrameSdkConfig
from struct_frame_sdk.async_transport import IAsyncTransport

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
# Mock async transport
# ---------------------------------------------------------------------------

class MockAsyncTransport(IAsyncTransport):
    """Records all sends and lets tests push incoming data synchronously."""

    def __init__(self):
        self._data_cb = None
        self._error_cb = None
        self._close_cb = None
        self._connected = False
        self.sent_data = []

    async def connect(self):
        self._connected = True

    async def disconnect(self):
        self._connected = False

    async def send(self, data: bytes) -> int:
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
        """Simulate data arriving from the peer (synchronous push)."""
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


def make_sdk(transport: MockAsyncTransport) -> AsyncStructFrameSdk:
    config = AsyncStructFrameSdkConfig(
        transport=transport,
        profile=PROFILE_STANDARD_CONFIG,
        get_message_info=get_message_info,
    )
    return AsyncStructFrameSdk(config)


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
    """Handler receives raw payload bytes when a frame arrives via inject_data."""
    transport = MockAsyncTransport()
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
    """All registered handlers for the same message ID are invoked."""
    transport = MockAsyncTransport()
    sdk = make_sdk(transport)

    count_a, count_b = [0], [0]
    sdk.subscribe(BasicTypesMessage.MSG_ID, lambda *_: count_a.__setitem__(0, count_a[0] + 1))
    sdk.subscribe(BasicTypesMessage.MSG_ID, lambda *_: count_b.__setitem__(0, count_b[0] + 1))

    transport.inject_data(encode_basic_types(BasicTypesMessage()))

    run_test("multiple handlers: first fires", count_a[0] == 1)
    run_test("multiple handlers: second fires", count_b[0] == 1)


def test_unsubscribe_removes_handler():
    """The unsubscribe function returned by subscribe() stops delivery."""
    transport = MockAsyncTransport()
    sdk = make_sdk(transport)

    count = [0]
    unsubscribe = sdk.subscribe(BasicTypesMessage.MSG_ID,
                                lambda *_: count.__setitem__(0, count[0] + 1))

    transport.inject_data(encode_basic_types(BasicTypesMessage()))
    run_test("unsubscribe: handler fires before unsubscribe", count[0] == 1)

    unsubscribe()
    transport.inject_data(encode_basic_types(BasicTypesMessage()))
    run_test("unsubscribe: handler silent after unsubscribe", count[0] == 1)


def test_no_handler_for_unknown_id():
    """Known ID dispatches; unknown ID is silently ignored."""
    transport = MockAsyncTransport()
    sdk = make_sdk(transport)

    fired = [False]
    sdk.subscribe(BasicTypesMessage.MSG_ID, lambda *_: fired.__setitem__(0, True))

    transport.inject_data(encode_basic_types(BasicTypesMessage()))
    run_test("known id: handler fires", fired[0] is True)

    fired[0] = False
    transport.inject_data(make_unknown_frame(0xFE, b'\x00' * 4))
    run_test("unknown id: handler does not fire", fired[0] is False)


async def test_send_raw_frames_through_transport():
    """await sdk.send_raw() encodes and emits data through the async transport."""
    transport = MockAsyncTransport()
    sdk = make_sdk(transport)

    payload = BasicTypesMessage().serialize()
    send_result = await sdk.send_raw(BasicTypesMessage.MSG_ID, payload)

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


async def test_send_message_through_transport():
    """await sdk.send(msg) serializes and frames a message object."""
    transport = MockAsyncTransport()
    sdk = make_sdk(transport)

    msg = BasicTypesMessage()
    msg.regular_int = 99
    msg.flag = True
    send_result = await sdk.send(msg)

    run_test("send: transport received data", len(transport.sent_data) == 1)
    run_test("send: result.success is true", send_result.success is True)

    frame = transport.sent_data[0]
    parsed = parse_frame_buffer(PROFILE_STANDARD_CONFIG, frame, get_message_info)
    run_test("send: emitted frame parses as valid", parsed.valid)
    run_test("send: emitted frame msg_id preserved",
             parsed.msg_id == BasicTypesMessage.MSG_ID)
    decoded = BasicTypesMessage.deserialize(parsed.msg_data)
    run_test("send: regular_int field preserved", decoded.regular_int == 99)
    run_test("send: flag field preserved", decoded.flag is True)


def test_codec_registration_and_message_decoding():
    """Registered codecs are applied before notifying handlers."""
    transport = MockAsyncTransport()
    sdk = make_sdk(transport)

    class _Codec:
        msg_id = BasicTypesMessage.MSG_ID

        def deserialize(self, data: bytes):
            msg = BasicTypesMessage.deserialize(data)
            return {"regular_int": msg.regular_int, "flag": msg.flag}

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
    transport = MockAsyncTransport()
    sdk = make_sdk(transport)

    msg = BasicTypesMessage()
    msg.regular_int = 5
    encoded = encode_basic_types(msg)
    transport.inject_data(encoded[: max(1, len(encoded) // 2)])
    run_test("close: reader holds partial frame before close", sdk.reader.has_partial())

    if transport._close_cb:
        transport._close_cb()
    run_test("close: reader partial state cleared after close callback",
             not sdk.reader.has_partial())


async def test_async_context_manager():
    """async with AsyncStructFrameSdk(...) connects on entry and disconnects on exit."""
    transport = MockAsyncTransport()
    sdk = make_sdk(transport)

    async with sdk:
        run_test("context manager: connected after __aenter__",
                 transport.is_connected())

    run_test("context manager: disconnected after __aexit__",
             not transport.is_connected())


async def test_is_connected_reflects_transport():
    """sdk.is_connected() delegates to the underlying transport state."""
    transport = MockAsyncTransport()
    sdk = make_sdk(transport)

    run_test("is_connected: false before connect", not sdk.is_connected())
    await sdk.connect()
    run_test("is_connected: true after connect", sdk.is_connected())
    await sdk.disconnect()
    run_test("is_connected: false after disconnect", not sdk.is_connected())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print()
    print("========================================")
    print("ASYNC SDK SUBSCRIBE/DISPATCH TESTS - Python")
    print("========================================")
    print()

    # Synchronous tests (no await needed — parsing is synchronous)
    test_subscribe_dispatch_raw_bytes()
    test_multiple_handlers_same_id()
    test_unsubscribe_removes_handler()
    test_no_handler_for_unknown_id()
    test_codec_registration_and_message_decoding()
    test_close_callback_clears_buffer_state()

    # Async tests driven through asyncio.run()
    asyncio.run(test_send_raw_frames_through_transport())
    asyncio.run(test_send_message_through_transport())
    asyncio.run(test_async_context_manager())
    asyncio.run(test_is_connected_reflects_transport())

    print()
    print("========================================")
    print(f"Summary: {tests_passed}/{tests_run} tests passed")
    print("========================================")
    print()

    return 1 if tests_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
