"""Async WebSocket Transport implementation using websockets"""

import asyncio
from dataclasses import dataclass
from typing import Optional
try:
    import websockets
except ImportError:
    websockets = None

from .async_transport import BaseAsyncTransport, AsyncTransportConfig


@dataclass
class AsyncWebSocketTransportConfig(AsyncTransportConfig):
    """Async WebSocket transport configuration"""
    url: str = ''
    timeout: float = 5.0


class AsyncWebSocketTransport(BaseAsyncTransport):
    """Async WebSocket transport using websockets"""

    def __init__(self, config: AsyncWebSocketTransportConfig):
        super().__init__(config)
        if websockets is None:
            raise ImportError('websockets package is required. Install with: pip install websockets')
        self.ws_config = config
        self.websocket = None
        self.receive_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Connect WebSocket"""
        try:
            self.websocket = await asyncio.wait_for(
                websockets.connect(self.ws_config.url),
                timeout=self.ws_config.timeout
            )
            self.connected = True
            
            # Start receive task
            self.receive_task = asyncio.create_task(self._receive_loop())
            
        except Exception as e:
            self._handle_error(e)
            raise

    async def disconnect(self) -> None:
        """Disconnect WebSocket"""
        self.connected = False
        
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
            self.receive_task = None
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None

    async def send(self, data: bytes) -> None:
        """Send data via WebSocket"""
        if not self.websocket or not self.connected:
            raise RuntimeError('WebSocket not connected')
        
        try:
            await self.websocket.send(data)
        except Exception as e:
            self._handle_error(e)
            raise

    async def _receive_loop(self) -> None:
        """Receive loop"""
        while self.connected and self.websocket:
            try:
                message = await self.websocket.recv()
                if isinstance(message, bytes):
                    self._handle_data(message)
                elif isinstance(message, str):
                    self._handle_data(message.encode('utf-8'))
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.connected:
                    self._handle_error(e)
                break
