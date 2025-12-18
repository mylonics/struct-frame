"""Async UDP Transport implementation using asyncio"""

import asyncio
from dataclasses import dataclass
from typing import Optional
from .async_transport import BaseAsyncTransport, AsyncTransportConfig


@dataclass
class AsyncUdpTransportConfig(AsyncTransportConfig):
    """Async UDP transport configuration"""
    local_port: int = 0
    local_address: str = '0.0.0.0'
    remote_host: str = ''
    remote_port: int = 0
    enable_broadcast: bool = False


class AsyncUdpProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler"""

    def __init__(self, transport_obj):
        self.transport_obj = transport_obj
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self.transport_obj._handle_data(data)

    def error_received(self, exc):
        self.transport_obj._handle_error(exc)

    def connection_lost(self, exc):
        if exc:
            self.transport_obj._handle_error(exc)
        self.transport_obj._handle_close()


class AsyncUdpTransport(BaseAsyncTransport):
    """Async UDP transport using asyncio"""

    def __init__(self, config: AsyncUdpTransportConfig):
        super().__init__(config)
        self.udp_config = config
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.protocol: Optional[AsyncUdpProtocol] = None

    async def connect(self) -> None:
        """Connect (bind) UDP socket"""
        try:
            loop = asyncio.get_event_loop()
            self.transport, self.protocol = await loop.create_datagram_endpoint(
                lambda: AsyncUdpProtocol(self),
                local_addr=(self.udp_config.local_address, self.udp_config.local_port)
            )
            
            if self.udp_config.enable_broadcast:
                sock = self.transport.get_extra_info('socket')
                if sock:
                    import socket
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            self.connected = True
            
        except Exception as e:
            self._handle_error(e)
            raise

    async def disconnect(self) -> None:
        """Disconnect UDP socket"""
        if self.transport:
            self.transport.close()
            self.transport = None
        self.protocol = None
        self.connected = False

    async def send(self, data: bytes) -> None:
        """Send data via UDP"""
        if not self.transport or not self.connected:
            raise RuntimeError('UDP socket not connected')
        
        try:
            self.transport.sendto(data, (self.udp_config.remote_host, self.udp_config.remote_port))
        except Exception as e:
            self._handle_error(e)
            raise
