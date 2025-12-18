"""UDP Transport implementation using socket"""

import socket
import threading
from dataclasses import dataclass
from typing import Optional
from .transport import BaseTransport, TransportConfig


@dataclass
class UdpTransportConfig(TransportConfig):
    """UDP transport configuration"""
    local_port: int = 0
    local_address: str = '0.0.0.0'
    remote_host: str = ''
    remote_port: int = 0
    buffer_size: int = 4096
    enable_broadcast: bool = False


class UdpTransport(BaseTransport):
    """UDP transport using socket"""

    def __init__(self, config: UdpTransportConfig):
        super().__init__(config)
        self.udp_config = config
        self.socket: Optional[socket.socket] = None
        self.receive_thread: Optional[threading.Thread] = None
        self.running = False

    def connect(self) -> None:
        """Connect (bind) UDP socket"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            if self.udp_config.enable_broadcast:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            self.socket.bind((self.udp_config.local_address, self.udp_config.local_port))
            self.connected = True
            
            # Start receive thread
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
        except Exception as e:
            self._handle_error(e)
            raise

    def disconnect(self) -> None:
        """Disconnect UDP socket"""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.receive_thread:
            self.receive_thread.join(timeout=1.0)
            self.receive_thread = None
        self.connected = False

    def send(self, data: bytes) -> None:
        """Send data via UDP"""
        if not self.socket or not self.connected:
            raise RuntimeError('UDP socket not connected')
        
        try:
            self.socket.sendto(data, (self.udp_config.remote_host, self.udp_config.remote_port))
        except Exception as e:
            self._handle_error(e)
            raise

    def _receive_loop(self) -> None:
        """Receive loop running in separate thread"""
        while self.running and self.socket:
            try:
                data, addr = self.socket.recvfrom(self.udp_config.buffer_size)
                self._handle_data(data)
            except Exception as e:
                if self.running:  # Only handle error if still running
                    self._handle_error(e)
                break
