"""TCP Transport implementation using socket"""

import socket
import threading
from dataclasses import dataclass
from typing import Optional
from .transport import BaseTransport, TransportConfig


@dataclass
class TcpTransportConfig(TransportConfig):
    """TCP transport configuration"""
    host: str = ''
    port: int = 0
    timeout: float = 5.0
    buffer_size: int = 4096


class TcpTransport(BaseTransport):
    """TCP transport using socket"""

    def __init__(self, config: TcpTransportConfig):
        super().__init__(config)
        self.tcp_config = config
        self.socket: Optional[socket.socket] = None
        self.receive_thread: Optional[threading.Thread] = None
        self.running = False

    def connect(self) -> None:
        """Connect TCP socket"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.tcp_config.timeout)
            self.socket.connect((self.tcp_config.host, self.tcp_config.port))
            self.connected = True
            
            # Start receive thread
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
        except Exception as e:
            self._handle_error(e)
            raise

    def disconnect(self) -> None:
        """Disconnect TCP socket"""
        self.running = False
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.socket.close()
            self.socket = None
        if self.receive_thread:
            self.receive_thread.join(timeout=1.0)
            self.receive_thread = None
        self.connected = False

    def send(self, data: bytes) -> None:
        """Send data via TCP"""
        if not self.socket or not self.connected:
            raise RuntimeError('TCP socket not connected')
        
        try:
            self.socket.sendall(data)
        except Exception as e:
            self._handle_error(e)
            raise

    def _receive_loop(self) -> None:
        """Receive loop running in separate thread"""
        while self.running and self.socket:
            try:
                data = self.socket.recv(self.tcp_config.buffer_size)
                if not data:
                    # Connection closed
                    self._handle_close()
                    break
                self._handle_data(data)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:  # Only handle error if still running
                    self._handle_error(e)
                break
