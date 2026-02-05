"""TCP Transport implementation using socket"""

import socket
from dataclasses import dataclass
from .transport import BaseSocketTransport, SocketTransportConfig


@dataclass
class TcpTransportConfig(SocketTransportConfig):
    """TCP transport configuration"""
    host: str = ''
    port: int = 0
    timeout: float = 5.0


class TcpTransport(BaseSocketTransport):
    """TCP transport using socket"""

    def __init__(self, config: TcpTransportConfig):
        super().__init__(config)
        self.tcp_config = config

    def connect(self) -> None:
        """Connect TCP socket"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.tcp_config.timeout)
            self.socket.connect((self.tcp_config.host, self.tcp_config.port))
            self.connected = True
            self._start_receive_thread()
        except Exception as e:
            self._handle_error(e)
            raise

    def _close_socket(self) -> None:
        """Close TCP socket with proper shutdown"""
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.socket.close()
            self.socket = None

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
                data = self.socket.recv(self.socket_config.buffer_size)
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
