#!/usr/bin/env python3
"""
Request / response tests for the Python AsyncStructFrameSdk.

Mirrors test_request_response_sdk.py but exercises AsyncStructFrameSdk.request().
Responses are injected via asyncio.create_task so they arrive after request()
has had a chance to register its subscription and await the future.

Test matrix
-----------
- Basic request/response: awaiting request() returns the matching response.
- Timeout: request() raises TimeoutError when no response arrives.
- match predicate: responses are filtered by a correlation field.
- Concurrent requests: two in-flight requests resolve independently.
- Subscription cleanup: handler removed after success and after timeout.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'generated', 'py'))

_sdk_dir = os.path.join(
    os.path.dirname(__file__), '..', '..', 'src', 'struct_frame', 'boilerplate', 'py'
)
sys.path.insert(0, _sdk_dir)

from struct_frame_sdk.async_struct_frame_sdk import AsyncStructFrameSdk, AsyncStructFrameSdkConfig
from struct_frame_sdk.async_transport import IAsyncTransport

from frame_profiles import (
    BufferWriter,
    PROFILE_STANDARD_CONFIG,
)
from struct_frame.generated.serialization_test import (
    BasicTypesMessage,
    get_message_info,
)


# ---------------------------------------------------------------------------
# Mock async transport
# ---------------------------------------------------------------------------

class MockAsyncTransport(IAsyncTransport):
    def __init__(self):
        self._data_cb = None
        self._error_cb = None
        self._close_cb = None
        self._connected = False
        self.sent_data = []

    async def connect(self): self._connected = True
    async def disconnect(self): self._connected = False
    async def send(self, data: bytes) -> int:
        self.sent_data.append(bytes(data)); return len(data)
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
    return AsyncStructFrameSdk(AsyncStructFrameSdkConfig(
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


async def inject_after(transport, msg, delay=0.05):
    """Coroutine: sleep then inject a framed message."""
    await asyncio.sleep(delay)
    transport.inject_data(encode(msg))


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

async def test_basic_request_response():
    """await request() returns the first response with the matching msg_id."""
    transport = MockAsyncTransport()
    sdk = make_sdk_with_codec(transport)

    req = BasicTypesMessage()
    req.regular_int = 10

    resp = BasicTypesMessage()
    resp.regular_int = 10
    resp.flag = True

    inject_task = asyncio.create_task(inject_after(transport, resp))
    result = await sdk.request(req, BasicTypesMessage, timeout=2.0)
    await inject_task

    run_test("basic: request() returns a result", result is not None)
    run_test("basic: returned object is the response type",
             isinstance(result, BasicTypesMessage))
    run_test("basic: response field value correct", result.flag is True)
    run_test("basic: request was sent through transport",
             len(transport.sent_data) == 1)


async def test_timeout():
    """request() raises TimeoutError when no response arrives."""
    transport = MockAsyncTransport()
    sdk = make_sdk_with_codec(transport)

    req = BasicTypesMessage()
    req.regular_int = 99

    raised = False
    try:
        await sdk.request(req, BasicTypesMessage, timeout=0.1)
    except TimeoutError:
        raised = True

    run_test("timeout: TimeoutError raised", raised)
    run_test("timeout: request was still sent", len(transport.sent_data) == 1)


async def test_match_predicate_filters_responses():
    """match predicate allows correlation by a field value."""
    transport = MockAsyncTransport()
    sdk = make_sdk_with_codec(transport)

    req = BasicTypesMessage()
    req.regular_int = 7

    async def _inject():
        await asyncio.sleep(0.03)
        wrong = BasicTypesMessage()
        wrong.regular_int = 99
        wrong.flag = False
        transport.inject_data(encode(wrong))
        await asyncio.sleep(0.03)
        correct = BasicTypesMessage()
        correct.regular_int = 7
        correct.flag = True
        transport.inject_data(encode(correct))

    inject_task = asyncio.create_task(_inject())
    result = await sdk.request(
        req, BasicTypesMessage,
        match=lambda r: r.regular_int == 7,
        timeout=2.0,
    )
    await inject_task

    run_test("match: non-matching response is ignored", result is not None)
    run_test("match: correct response returned", result.regular_int == 7)
    run_test("match: flag field is from matching response", result.flag is True)


async def test_concurrent_requests_with_match():
    """Two concurrent requests with different correlation IDs resolve independently."""
    transport = MockAsyncTransport()
    sdk = make_sdk_with_codec(transport)

    async def _do_request(match_val):
        req = BasicTypesMessage()
        req.regular_int = match_val
        return await sdk.request(
            req, BasicTypesMessage,
            match=lambda r, v=match_val: r.regular_int == v,
            timeout=2.0,
        )

    # Start both requests, then inject responses in reverse order.
    req_a = asyncio.create_task(_do_request(1))
    req_b = asyncio.create_task(_do_request(2))

    await asyncio.sleep(0.05)

    resp_b = BasicTypesMessage(); resp_b.regular_int = 2; resp_b.flag = False
    resp_a = BasicTypesMessage(); resp_a.regular_int = 1; resp_a.flag = True
    transport.inject_data(encode(resp_b))
    transport.inject_data(encode(resp_a))

    result_a, result_b = await asyncio.gather(req_a, req_b)

    run_test("concurrent: request A resolved correctly", result_a.regular_int == 1)
    run_test("concurrent: request B resolved correctly", result_b.regular_int == 2)


async def test_subscription_removed_after_success():
    """The one-shot subscription is removed after request() resolves."""
    transport = MockAsyncTransport()
    sdk = make_sdk_with_codec(transport)

    req = BasicTypesMessage()
    req.regular_int = 3
    resp = BasicTypesMessage()
    resp.regular_int = 3

    inject_task = asyncio.create_task(inject_after(transport, resp))
    await sdk.request(req, BasicTypesMessage, timeout=2.0)
    await inject_task

    handlers_after = sdk.message_handlers.get(BasicTypesMessage.MSG_ID, [])
    run_test("cleanup: subscription removed after success",
             len(handlers_after) == 0)


async def test_subscription_removed_after_timeout():
    """The one-shot subscription is removed even after a timeout."""
    transport = MockAsyncTransport()
    sdk = make_sdk_with_codec(transport)

    req = BasicTypesMessage()
    try:
        await sdk.request(req, BasicTypesMessage, timeout=0.05)
    except TimeoutError:
        pass

    handlers_after = sdk.message_handlers.get(BasicTypesMessage.MSG_ID, [])
    run_test("cleanup: subscription removed after timeout",
             len(handlers_after) == 0)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print()
    print("========================================")
    print("REQUEST/RESPONSE TESTS - Python (async)")
    print("========================================")
    print()

    asyncio.run(test_basic_request_response())
    asyncio.run(test_timeout())
    asyncio.run(test_match_predicate_filters_responses())
    asyncio.run(test_concurrent_requests_with_match())
    asyncio.run(test_subscription_removed_after_success())
    asyncio.run(test_subscription_removed_after_timeout())

    print()
    print("========================================")
    print(f"Summary: {tests_passed}/{tests_run} tests passed")
    print("========================================")
    print()

    return 1 if tests_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
