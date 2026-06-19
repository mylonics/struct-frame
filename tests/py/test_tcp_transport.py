#!/usr/bin/env python3
"""TCP transport loopback tests for the Python SDK.

Unlike the mock-transport SDK tests, this suite exercises the *concrete*
``TcpTransport`` over a real localhost socket: ephemeral-port connect, the
background receive thread, ``send()``, peer-initiated close, and a full
``StructFrameSdk`` frame dispatch over the live connection. This closes the
"TCP transport (end to end)" gap called out in the Test Coverage reference.

A tiny single-connection ``LoopbackServer`` plays the peer. All waits are
bounded so the suite cannot hang if a socket misbehaves.
"""

import os
import socket
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'generated', 'py'))

_sdk_dir = os.path.join(
    os.path.dirname(__file__), '..', '..', 'src', 'struct_frame', 'boilerplate', 'py'
)
sys.path.insert(0, _sdk_dir)

from struct_frame_sdk.tcp_transport import TcpTransport, TcpTransportConfig
from struct_frame_sdk.struct_frame_sdk import StructFrameSdk, StructFrameSdkConfig

from frame_profiles import BufferWriter, PROFILE_STANDARD_CONFIG
from struct_frame.generated.serialization_test import (
    BasicTypesMessage,
    get_message_info,
)


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

tests_run = 0
tests_passed = 0
tests_failed = 0


def run_test(name: str, result: bool):
    global tests_run, tests_passed, tests_failed
    tests_run += 1
    print(f"  {'PASS' if result else 'FAIL'}  {name}")
    if result:
        tests_passed += 1
    else:
        tests_failed += 1


def wait_until(predicate, timeout=2.0, interval=0.01) -> bool:
    """Poll *predicate* until true or *timeout* elapses."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


class LoopbackServer:
    """Single-connection localhost TCP server used as the transport peer."""

    def __init__(self):
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind(('127.0.0.1', 0))
        self._srv.listen(1)
        self.port = self._srv.getsockname()[1]
        self.conn = None
        self.received = bytearray()
        self._accepted = threading.Event()
        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def _accept_loop(self):
        self._srv.settimeout(3.0)
        try:
            conn, _ = self._srv.accept()
        except OSError:
            return
        self.conn = conn
        self._accepted.set()
        conn.settimeout(0.2)
        while self._running:
            try:
                data = conn.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if not data:
                break
            self.received.extend(data)

    def wait_accepted(self, timeout=2.0) -> bool:
        return self._accepted.wait(timeout)

    def send(self, data: bytes):
        self._accepted.wait(2.0)
        self.conn.sendall(data)

    def close_client(self):
        if self.conn:
            try:
                self.conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.conn.close()

    def stop(self):
        self._running = False
        self.close_client()
        try:
            self._srv.close()
        except OSError:
            pass


def make_transport(port: int) -> TcpTransport:
    return TcpTransport(TcpTransportConfig(host='127.0.0.1', port=port))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_connect_and_state():
    """connect() opens the socket and is_connected() tracks lifecycle."""
    server = LoopbackServer()
    transport = make_transport(server.port)
    try:
        transport.connect()
        run_test("tcp: is_connected() true after connect", transport.is_connected())
        run_test("tcp: server accepted the connection", server.wait_accepted())
    finally:
        transport.disconnect()
        server.stop()
    run_test("tcp: is_connected() false after disconnect", not transport.is_connected())


def test_receive_from_peer():
    """Bytes the peer sends are delivered to the data callback."""
    server = LoopbackServer()
    received = bytearray()
    transport = make_transport(server.port)
    transport.set_data_callback(lambda d: received.extend(d))
    try:
        transport.connect()
        server.wait_accepted()
        payload = bytes(range(32))
        server.send(payload)
        got = wait_until(lambda: len(received) >= len(payload))
        run_test("tcp: data callback received peer bytes",
                 got and bytes(received) == payload)
    finally:
        transport.disconnect()
        server.stop()


def test_send_to_peer():
    """send() writes bytes the peer actually receives."""
    server = LoopbackServer()
    transport = make_transport(server.port)
    try:
        transport.connect()
        server.wait_accepted()
        payload = b'hello-struct-frame'
        n = transport.send(payload)
        run_test("tcp: send() returns full byte count", n == len(payload))
        got = wait_until(lambda: bytes(server.received) == payload)
        run_test("tcp: peer received sent bytes", got)
    finally:
        transport.disconnect()
        server.stop()


def test_sdk_dispatch_over_socket():
    """A real frame from the peer is dispatched by the SDK over a live socket."""
    server = LoopbackServer()
    transport = make_transport(server.port)
    sdk = StructFrameSdk(StructFrameSdkConfig(
        transport=transport,
        profile=PROFILE_STANDARD_CONFIG,
        get_message_info=get_message_info,
    ))

    received = []
    sdk.subscribe(BasicTypesMessage.MSG_ID, lambda msg, msg_id: received.append(msg))
    try:
        sdk.connect()
        server.wait_accepted()

        msg = BasicTypesMessage()
        msg.regular_int = 7
        msg.flag = True
        writer = BufferWriter(PROFILE_STANDARD_CONFIG)
        writer.write(msg)
        server.send(bytes(writer.data()))

        got = wait_until(lambda: len(received) == 1)
        run_test("tcp+sdk: frame dispatched to subscriber over socket", got)
    finally:
        sdk.disconnect()
        server.stop()


def test_close_callback_on_peer_disconnect():
    """When the peer drops the connection the close callback fires."""
    server = LoopbackServer()
    transport = make_transport(server.port)
    closed = threading.Event()
    transport.set_close_callback(lambda: closed.set())
    try:
        transport.connect()
        server.wait_accepted()
        server.close_client()  # peer drops the connection
        run_test("tcp: close callback fires when peer disconnects", closed.wait(2.0))
        run_test("tcp: is_connected() false after peer disconnect",
                 wait_until(lambda: not transport.is_connected()))
    finally:
        transport.disconnect()
        server.stop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print()
    print("========================================")
    print("TCP TRANSPORT LOOPBACK TESTS - Python")
    print("========================================")
    print()

    test_connect_and_state()
    test_receive_from_peer()
    test_send_to_peer()
    test_sdk_dispatch_over_socket()
    test_close_callback_on_peer_disconnect()

    print()
    print("========================================")
    print(f"Summary: {tests_passed}/{tests_run} tests passed")
    print("========================================")
    print()

    return 1 if tests_failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
