#!/usr/bin/env python3
"""Loopback tests for the Python SDK's serial, UDP and WebSocket transports (sync and asyncio).

``tests/py/test_tcp_transport.py`` covers TCP. These cover the rest against real endpoints:

* serial: pyserial's ``loop://`` URL, a port whose writes come straight back (no hardware);
* UDP: a plain socket on 127.0.0.1 as the peer;
* WebSocket: a ``websockets`` server on 127.0.0.1, for both the websocket-client based
  ``WebSocketTransport`` and the asyncio ``AsyncWebSocketTransport``.

Each optional package (pyserial, websocket-client, websockets) skips its tests when missing,
unless ``py`` is in SF_REQUIRE_LANGS.
"""
from __future__ import annotations

import asyncio
import os
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

SDK_DIR = Path(__file__).resolve().parents[1] / "src" / "struct_frame" / "boilerplate" / "py"
sys.path.insert(0, str(SDK_DIR))


def _need(module: str):
    try:
        return __import__(module)
    except ImportError:
        if "py" in os.environ.get("SF_REQUIRE_LANGS", "").split(","):
            raise
        pytest.skip(f"{module} not installed")


def _wait(predicate, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


async def _await(predicate, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        await asyncio.sleep(0.01)
    return predicate()


# ---------------------------------------------------------------------------------------- serial

def test_serial_transport_loopback():
    _need("serial")
    from struct_frame_sdk.serial_transport import SerialTransport, SerialTransportConfig

    t = SerialTransport(SerialTransportConfig(port="loop://", timeout=0.05))
    got = bytearray()
    t.set_data_callback(lambda d: got.extend(d))
    t.connect()
    try:
        assert t.is_connected()
        assert t.send(b"\x90\x71\x01\x02") == 4
        assert _wait(lambda: bytes(got) == b"\x90\x71\x01\x02"), bytes(got)
    finally:
        t.disconnect()
    assert not t.is_connected()


def test_serial_transport_rejects_send_when_closed():
    _need("serial")
    from struct_frame_sdk.serial_transport import SerialTransport, SerialTransportConfig

    t = SerialTransport(SerialTransportConfig(port="loop://"))
    with pytest.raises(Exception):
        t.send(b"\x01")


def test_async_serial_transport_loopback():
    _need("serial")
    from struct_frame_sdk.async_serial_transport import AsyncSerialTransport, AsyncSerialTransportConfig

    async def run():
        t = AsyncSerialTransport(AsyncSerialTransportConfig(port="loop://"))
        got = bytearray()
        t.set_data_callback(lambda d: got.extend(d))
        await t.connect()
        try:
            assert t.is_connected()
            await t.send(b"abc")
            assert await _await(lambda: bytes(got) == b"abc"), bytes(got)
        finally:
            await t.disconnect()
        assert not t.is_connected()

    asyncio.run(run())


# ------------------------------------------------------------------------------------------- UDP

def _udp_peer():
    peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    peer.bind(("127.0.0.1", 0))
    peer.settimeout(3.0)
    return peer


def test_udp_transport_loopback():
    from struct_frame_sdk.udp_transport import UdpTransport, UdpTransportConfig

    peer = _udp_peer()
    t = UdpTransport(UdpTransportConfig(local_address="127.0.0.1", remote_host="127.0.0.1",
                                        remote_port=peer.getsockname()[1]))
    got = bytearray()
    t.set_data_callback(lambda d: got.extend(d))
    t.connect()
    try:
        assert t.is_connected()
        assert t.send(b"\x05\x06\x07") == 3
        data, addr = peer.recvfrom(64)
        assert data == b"\x05\x06\x07"
        peer.sendto(b"\x28\x29", addr)
        assert _wait(lambda: bytes(got) == b"\x28\x29"), bytes(got)
    finally:
        t.disconnect()
        peer.close()
    assert not t.is_connected()


def test_intentional_disconnect_does_not_reconnect():
    from struct_frame_sdk.tcp_transport import TcpTransport, TcpTransportConfig

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(5)
    srv.settimeout(0.2)
    accepted = []

    def accept_loop():
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
                accepted.append(conn)
            except OSError:
                pass

    stop = threading.Event()
    th = threading.Thread(target=accept_loop, daemon=True)
    th.start()
    t = TcpTransport(TcpTransportConfig(host="127.0.0.1", port=srv.getsockname()[1],
                                        auto_reconnect=True, reconnect_delay=0.03))
    try:
        t.connect()
        assert _wait(lambda: len(accepted) == 1)
        t.disconnect()
        time.sleep(0.4)
        assert len(accepted) == 1, "the transport reconnected after an intentional disconnect()"
        assert not t.is_connected()
    finally:
        stop.set()
        th.join(2)
        for c in accepted:
            c.close()
        srv.close()


def test_async_udp_transport_loopback():
    from struct_frame_sdk.async_udp_transport import AsyncUdpTransport, AsyncUdpTransportConfig

    async def run():
        peer = _udp_peer()
        t = AsyncUdpTransport(AsyncUdpTransportConfig(local_address="127.0.0.1", remote_host="127.0.0.1",
                                                      remote_port=peer.getsockname()[1]))
        got = bytearray()
        t.set_data_callback(lambda d: got.extend(d))
        await t.connect()
        try:
            assert await t.send(b"xyz") == 3
            data, addr = await asyncio.get_running_loop().run_in_executor(None, peer.recvfrom, 64)
            assert data == b"xyz"
            peer.sendto(b"\x01\x02", addr)
            assert await _await(lambda: bytes(got) == b"\x01\x02"), bytes(got)
        finally:
            await t.disconnect()
            peer.close()

    asyncio.run(run())


# ------------------------------------------------------------------------------------- WebSocket

class _WsServer:
    """A websockets server on 127.0.0.1 in a background thread. Records what it receives and
    can push a binary message to (or close) the connected client."""

    def __init__(self):
        websockets = _need("websockets")
        self.received = bytearray()
        self.port = None
        self._conn = None
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._stop = None
        try:
            from websockets.asyncio.server import serve  # websockets >= 13
        except ImportError:  # pragma: no cover - older websockets
            serve = websockets.serve
        self._serve = serve
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        assert self._ready.wait(5), "WebSocket server did not start"

    def _run(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._main())

    async def _main(self):
        self._stop = asyncio.Event()

        async def handler(conn, *_):
            self._conn = conn
            try:
                async for message in conn:
                    self.received.extend(message if isinstance(message, bytes) else message.encode())
            except Exception:
                pass

        async with self._serve(handler, "127.0.0.1", 0) as server:
            self.port = list(server.sockets)[0].getsockname()[1]
            self._ready.set()
            await self._stop.wait()

    def push(self, data: bytes):
        _wait(lambda: self._conn is not None)
        asyncio.run_coroutine_threadsafe(self._conn.send(data), self._loop).result(3)

    def close_client(self):
        # Start the closing handshake; the caller waits for the client to notice.
        asyncio.run_coroutine_threadsafe(self._conn.close(), self._loop)

    def stop(self):
        self._loop.call_soon_threadsafe(self._stop.set)
        self._thread.join(5)


def test_websocket_transport_loopback():
    _need("websocket")  # websocket-client
    from struct_frame_sdk.websocket_transport import WebSocketTransport, WebSocketTransportConfig

    server = _WsServer()
    t = WebSocketTransport(WebSocketTransportConfig(url=f"ws://127.0.0.1:{server.port}", timeout=3.0))
    got = bytearray()
    closed = threading.Event()
    t.set_data_callback(lambda d: got.extend(d))
    t.set_close_callback(closed.set)
    try:
        t.connect()
        assert t.is_connected()
        t.send(b"\x0b\x0c\x0d")
        assert _wait(lambda: bytes(server.received) == b"\x0b\x0c\x0d"), bytes(server.received)
        server.push(b"\x15\x16")
        assert _wait(lambda: bytes(got) == b"\x15\x16"), bytes(got)
        server.close_client()
        assert closed.wait(3), "close callback not called when the server closed"
        assert _wait(lambda: not t.is_connected())
    finally:
        t.disconnect()
        server.stop()


def test_async_websocket_transport_loopback():
    _need("websockets")
    from struct_frame_sdk.async_websocket_transport import AsyncWebSocketTransport, AsyncWebSocketTransportConfig

    server = _WsServer()

    async def run():
        t = AsyncWebSocketTransport(AsyncWebSocketTransportConfig(url=f"ws://127.0.0.1:{server.port}"))
        got = bytearray()
        t.set_data_callback(lambda d: got.extend(d))
        await t.connect()
        try:
            assert t.is_connected()
            await t.send(b"hello")
            assert await _await(lambda: bytes(server.received) == b"hello"), bytes(server.received)
            await asyncio.get_running_loop().run_in_executor(None, server.push, b"\x01\x02\x03")
            assert await _await(lambda: bytes(got) == b"\x01\x02\x03"), bytes(got)
        finally:
            await t.disconnect()
        assert not t.is_connected()

    try:
        asyncio.run(run())
    finally:
        server.stop()
