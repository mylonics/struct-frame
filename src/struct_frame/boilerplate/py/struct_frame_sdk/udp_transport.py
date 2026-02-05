"""UDP Transport implementation using socket"""

import socket
from dataclasses import dataclass
from .transport import BaseSocketTransport, SocketTransportConfig


@dataclass
class UdpTransportConfig(SocketTransportConfig):
    """UDP transport configuration"""
    local_port: int = 0
    local_address: str = '0.0.0.0'
    remote_host: str = ''
    remote_port: int = 0
    enable_broadcast: bool = False


class UdpTransport(BaseSocketTransport):
    """UDP transport using socket"""

    def __init__(self, config: UdpTransportConfig):
        super().__init__(config)
        self.udp_config = config

    def connect(self) -> None:
        """Connect (bind) UDP socket"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            if self.udp_config.enable_broadcast:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            self.socket.bind((self.udp_config.local_address, self.udp_config.local_port))
            self.connected = True
            self._start_receive_thread()
        except Exception as e:
            self._handle_error(e)
            raise

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
        """Receive loop running in separate thread using pre-allocated buffer.
        
        Uses recvfrom_into to receive directly into the pre-allocated buffer,
        reducing socket-layer allocations. The bytes copy to pass to handler
        is necessary to maintain API compatibility with bytes-expecting callbacks.
        """
        while self.running and self.socket:
            try:
                # Use recvfrom_into with pre-allocated buffer to reduce socket-layer allocation
                nbytes, addr = self.socket.recvfrom_into(self._recv_view)
                # Copy received bytes for handler (maintains bytes-based callback API)
                self._handle_data(bytes(self._recv_buffer[:nbytes]))
            except Exception as e:
                if self.running:  # Only handle error if still running
                    self._handle_error(e)
                break
