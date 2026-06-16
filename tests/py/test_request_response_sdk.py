#!/usr/bin/env python3
"""
Request / response tests for the Python StructFrameSdk.

Each test drives a single SDK instance against a MockTransport.  A background
thread injects the response frame after a short delay to let request() block
first, then unblocks it.  This mirrors real async I/O without requiring a real
network connection.

Test matrix
-----------
- Basic request/response: request() returns the first matching response.
- Timeout: request() raises TimeoutError when no response arrives.
- match predicate: concurrent requests with different correlation IDs are
  resolved independently.
- request_raw(): returns raw payload bytes when no response class is needed.
- Subscription cleanup: the one-shot handler is removed after a successful
  request and after a timeout.
"""

import sys
import os
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'generated', 'py'))

_sdk_dir = os.path.join(
    os.path.dirname(__file__), '..', '..', 'src', 'struct_frame', 'boilerplate', 'py'
)
sys.path.insert(0, _sdk_dir)

from struct_frame_sdk.struct_frame_sdk import StructFrameSdk, StructFrameSdkConfig
from struct_frame_sdk.transport import ITransport

from frame_profiles import (
    BufferWriter,
    PROFILE_STANDARD_CONFIG,
)
from struct_frame.generated.serialization_test import (
    BasicTypesMessage,
    SerializationTestMessage,
    get_message_info,
)


# ---------------------------------------------------------------------------
# Mock transport
# ---------------------------------------------------------------------------

class MockTransport(ITransport):
    def __init__(self):
        self._data_cb = None
        self._error_cb = None
        self._close_cb = None
        self._connected = False
        self.sent_data = []

    def connect(self): self._connected = True
    def disconnect(self): self._connected = False
    def send(self, data: bytes): self.sent_data.append(bytes(data)); return len(data)
    def set_data_callback(self, cb): self._data_cb = cb
    def set_error_callback(self, cb): self._error_cb = cb
    def set_close_callback(self, cb): self._close_cb = cb
    def is_connected(self): return self._connected

    def inject_data(self, data: bytes):
        if self._data_cb:
            self._data_cb(data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_sdk(transport):
    return StructFrameSdk(StructFrameSdkConfig(
        transport=transport,
        profile=PROFILE_STANDARD_CONFIG,
        get_message_info=get_message_info,
    ))


class _BasicTypesCodec:
    msg_id = BasicTypesMessage.MSG_ID

    def deserialize(self, data: bytes):
        return BasicTypesMessage.deserialize(data)


def make_sdk_with_codec(transport):
    """SDK with a BasicTypesMessage codec so handlers receive typed objects."""
    sdk = make_sdk(transport)
    sdk.register_codec(_BasicTypesCodec())
    return sdk


def encode(msg) -> bytes:
    writer = BufferWriter(PROFILE_STANDARD_CONFIG)
    writer.write(msg)
    return bytes(writer.data())


def inject_after(transport, msg, delay=0.05):
    """Inject a framed message into the transport after *delay* seconds."""
    def _work():
        time.sleep(delay)
        transport.inject_data(encode(msg))
    t = threading.Thread(target=_work, daemon=True)
    t.start()
    return t


# ---------------------------------------------------------------------------
# Test infrastructure
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_basic_request_response():
    """request() returns the first response with the matching msg_id."""
    transport = MockTransport()
    sdk = make_sdk_with_codec(transport)

    req = BasicTypesMessage()
    req.regular_int = 10

    resp = BasicTypesMessage()
    resp.regular_int = 10
    resp.flag = True

    t = inject_after(transport, resp)
    result = sdk.request(req, BasicTypesMessage, timeout=2.0)
    t.join()

    run_test("basic: request() returns a result", result is not None)
    run_test("basic: returned object is the response type",
             isinstance(result, BasicTypesMessage))
    run_test("basic: response field value correct", result.flag is True)
    run_test("basic: request was sent through transport", len(transport.sent_data) == 1)


def test_timeout():
    """request() raises TimeoutError when no response arrives."""
    transport = MockTransport()
    sdk = make_sdk_with_codec(transport)

    req = BasicTypesMessage()
    req.regular_int = 99

    raised = False
    try:
        sdk.request(req, BasicTypesMessage, timeout=0.1)
    except TimeoutError:
        raised = True

    run_test("timeout: TimeoutError raised", raised)
    run_test("timeout: request was still sent", len(transport.sent_data) == 1)


def test_match_predicate_filters_responses():
    """match predicate lets caller correlate by a field value."""
    transport = MockTransport()
    sdk = make_sdk_with_codec(transport)

    req = BasicTypesMessage()
    req.regular_int = 7

    # Inject a response that does NOT match first, then one that does.
    wrong = BasicTypesMessage()
    wrong.regular_int = 99
    wrong.flag = False

    correct = BasicTypesMessage()
    correct.regular_int = 7
    correct.flag = True

    def _inject():
        time.sleep(0.03)
        transport.inject_data(encode(wrong))
        time.sleep(0.03)
        transport.inject_data(encode(correct))

    t = threading.Thread(target=_inject, daemon=True)
    t.start()
    result = sdk.request(
        req, BasicTypesMessage,
        match=lambda r: r.regular_int == 7,
        timeout=2.0,
    )
    t.join()

    run_test("match: non-matching response is ignored", result is not None)
    run_test("match: correct response returned", result.regular_int == 7)
    run_test("match: flag field is from matching response", result.flag is True)


def test_concurrent_requests_with_match():
    """Two in-flight requests with different correlation IDs resolve independently."""
    transport = MockTransport()
    sdk = make_sdk_with_codec(transport)

    results = {}
    errors = {}

    def _do_request(key, match_val, timeout=2.0):
        req = BasicTypesMessage()
        req.regular_int = match_val
        try:
            results[key] = sdk.request(
                req, BasicTypesMessage,
                match=lambda r, v=match_val: r.regular_int == v,
                timeout=timeout,
            )
        except Exception as e:
            errors[key] = e

    t1 = threading.Thread(target=_do_request, args=('a', 1), daemon=True)
    t2 = threading.Thread(target=_do_request, args=('b', 2), daemon=True)
    t1.start()
    t2.start()

    # Let both requests block, then inject responses in reverse order.
    time.sleep(0.05)
    resp_b = BasicTypesMessage(); resp_b.regular_int = 2; resp_b.flag = False
    resp_a = BasicTypesMessage(); resp_a.regular_int = 1; resp_a.flag = True
    transport.inject_data(encode(resp_b))
    transport.inject_data(encode(resp_a))

    t1.join(timeout=3.0)
    t2.join(timeout=3.0)

    run_test("concurrent: both requests resolved", len(results) == 2)
    run_test("concurrent: request 'a' got correct response",
             results.get('a') is not None and results['a'].regular_int == 1)
    run_test("concurrent: request 'b' got correct response",
             results.get('b') is not None and results['b'].regular_int == 2)
    run_test("concurrent: no errors", len(errors) == 0)


def test_request_raw_returns_bytes():
    """request_raw() returns raw payload bytes without a response class."""
    transport = MockTransport()
    sdk = make_sdk(transport)

    req = BasicTypesMessage()
    req.regular_int = 55

    resp = BasicTypesMessage()
    resp.regular_int = 55
    resp.medium_int = 123

    t = inject_after(transport, resp)
    raw = sdk.request_raw(req, BasicTypesMessage.MSG_ID, timeout=2.0)
    t.join()

    run_test("request_raw: returns bytes", isinstance(raw, (bytes, bytearray)))
    decoded = BasicTypesMessage.deserialize(raw)
    run_test("request_raw: payload round-trips correctly", decoded.medium_int == 123)


def test_request_raw_timeout():
    """request_raw() raises TimeoutError when no response arrives."""
    transport = MockTransport()
    sdk = make_sdk(transport)

    req = BasicTypesMessage()
    raised = False
    try:
        sdk.request_raw(req, BasicTypesMessage.MSG_ID, timeout=0.1)
    except TimeoutError:
        raised = True

    run_test("request_raw timeout: TimeoutError raised", raised)


def test_subscription_removed_after_success():
    """The one-shot subscription is cleaned up after request() returns."""
    transport = MockTransport()
    sdk = make_sdk_with_codec(transport)

    req = BasicTypesMessage()
    req.regular_int = 3

    resp = BasicTypesMessage()
    resp.regular_int = 3

    t = inject_after(transport, resp)
    sdk.request(req, BasicTypesMessage, timeout=2.0)
    t.join()

    # After request() the internal handler list should be empty (or only
    # contain handlers registered outside of request()).
    handlers_after = sdk.message_handlers.get(BasicTypesMessage.MSG_ID, [])
    run_test("cleanup: one-shot subscription removed after success",
             len(handlers_after) == 0)


def test_subscription_removed_after_timeout():
    """The one-shot subscription is cleaned up even after a timeout."""
    transport = MockTransport()
    sdk = make_sdk_with_codec(transport)

    req = BasicTypesMessage()
    try:
        sdk.request(req, BasicTypesMessage, timeout=0.05)
    except TimeoutError:
        pass

    handlers_after = sdk.message_handlers.get(BasicTypesMessage.MSG_ID, [])
    run_test("cleanup: one-shot subscription removed after timeout",
             len(handlers_after) == 0)


def test_with_codec():
    """If a codec is registered for the response msg_id, request() returns the decoded object."""
    transport = MockTransport()
    sdk = make_sdk(transport)

    class _Codec:
        msg_id = BasicTypesMessage.MSG_ID

        def deserialize(self, data: bytes):
            msg = BasicTypesMessage.deserialize(data)
            return {"regular_int": msg.regular_int, "flag": msg.flag}

    sdk.register_codec(_Codec())

    req = BasicTypesMessage()
    req.regular_int = 0

    resp = BasicTypesMessage()
    resp.regular_int = 0
    resp.flag = True

    t = inject_after(transport, resp)
    result = sdk.request(req, BasicTypesMessage, timeout=2.0)
    t.join()

    run_test("codec: handler receives decoded object", isinstance(result, dict))
    run_test("codec: flag field preserved", result.get("flag") is True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print()
    print("========================================")
    print("REQUEST/RESPONSE TESTS - Python (sync)")
    print("========================================")
    print()

    test_basic_request_response()
    test_timeout()
    test_match_predicate_filters_responses()
    test_concurrent_requests_with_match()
    test_request_raw_returns_bytes()
    test_request_raw_timeout()
    test_subscription_removed_after_success()
    test_subscription_removed_after_timeout()
    test_with_codec()

    print()
    print("========================================")
    print(f"Summary: {tests_passed}/{tests_run} tests passed")
    print("========================================")
    print()

    return 1 if tests_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
