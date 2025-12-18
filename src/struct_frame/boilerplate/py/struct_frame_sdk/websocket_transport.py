"""WebSocket Transport implementation using websocket-client"""

import threading
from dataclasses import dataclass
from typing import Optional
try:
    import websocket
except ImportError:
    websocket = None

from .transport import BaseTransport, TransportConfig


@dataclass
class WebSocketTransportConfig(TransportConfig):
    """WebSocket transport configuration"""
    url: str = ''
    timeout: float = 5.0


class WebSocketTransport(BaseTransport):
    """WebSocket transport using websocket-client"""

    def __init__(self, config: WebSocketTransportConfig):
        super().__init__(config)
        if websocket is None:
            raise ImportError('websocket-client package is required. Install with: pip install websocket-client')
        self.ws_config = config
        self.ws: Optional[websocket.WebSocketApp] = None
        self.ws_thread: Optional[threading.Thread] = None

    def connect(self) -> None:
        """Connect WebSocket"""
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_config.url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Run WebSocket in separate thread
            self.ws_thread = threading.Thread(
                target=self.ws.run_forever,
                kwargs={'ping_interval': 30, 'ping_timeout': 10},
                daemon=True
            )
            self.ws_thread.start()
            
            # Wait for connection (with timeout)
            import time
            timeout = self.ws_config.timeout
            start = time.time()
            while not self.connected and time.time() - start < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                raise TimeoutError('WebSocket connection timeout')
                
        except Exception as e:
            self._handle_error(e)
            raise

    def disconnect(self) -> None:
        """Disconnect WebSocket"""
        if self.ws:
            self.ws.close()
            self.ws = None
        if self.ws_thread:
            self.ws_thread.join(timeout=1.0)
            self.ws_thread = None
        self.connected = False

    def send(self, data: bytes) -> None:
        """Send data via WebSocket"""
        if not self.ws or not self.connected:
            raise RuntimeError('WebSocket not connected')
        
        try:
            self.ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
        except Exception as e:
            self._handle_error(e)
            raise

    def _on_open(self, ws) -> None:
        """Called when WebSocket opens"""
        self.connected = True

    def _on_message(self, ws, message) -> None:
        """Called when WebSocket receives message"""
        if isinstance(message, bytes):
            self._handle_data(message)
        elif isinstance(message, str):
            self._handle_data(message.encode('utf-8'))

    def _on_error(self, ws, error) -> None:
        """Called when WebSocket encounters error"""
        if isinstance(error, Exception):
            self._handle_error(error)

    def _on_close(self, ws, close_status_code, close_msg) -> None:
        """Called when WebSocket closes"""
        self._handle_close()
