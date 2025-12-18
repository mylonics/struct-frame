"""Async TCP Transport implementation using asyncio"""

import asyncio
from dataclasses import dataclass
from typing import Optional
from .async_transport import BaseAsyncTransport, AsyncTransportConfig


@dataclass
class AsyncTcpTransportConfig(AsyncTransportConfig):
    """Async TCP transport configuration"""
    host: str = ''
    port: int = 0
    timeout: float = 5.0


class AsyncTcpTransport(BaseAsyncTransport):
    """Async TCP transport using asyncio"""

    def __init__(self, config: AsyncTcpTransportConfig):
        super().__init__(config)
        self.tcp_config = config
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.receive_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Connect TCP socket"""
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.tcp_config.host, self.tcp_config.port),
                timeout=self.tcp_config.timeout
            )
            self.connected = True
            
            # Start receive task
            self.receive_task = asyncio.create_task(self._receive_loop())
            
        except Exception as e:
            self._handle_error(e)
            raise

    async def disconnect(self) -> None:
        """Disconnect TCP socket"""
        self.connected = False
        
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
            self.receive_task = None
        
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.writer = None
        
        self.reader = None

    async def send(self, data: bytes) -> None:
        """Send data via TCP"""
        if not self.writer or not self.connected:
            raise RuntimeError('TCP socket not connected')
        
        try:
            self.writer.write(data)
            await self.writer.drain()
        except Exception as e:
            self._handle_error(e)
            raise

    async def _receive_loop(self) -> None:
        """Receive loop"""
        while self.connected and self.reader:
            try:
                data = await self.reader.read(4096)
                if not data:
                    # Connection closed
                    self._handle_close()
                    break
                self._handle_data(data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.connected:
                    self._handle_error(e)
                break
