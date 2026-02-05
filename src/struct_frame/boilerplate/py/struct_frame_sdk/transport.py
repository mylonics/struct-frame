"""Transport interface for struct-frame SDK
Provides abstraction for various communication channels
"""

import socket
import threading
from abc import ABC, abstractmethod
from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class TransportConfig:
    """Configuration for transport layer"""
    auto_reconnect: bool = False
    reconnect_delay: float = 1.0  # seconds
    max_reconnect_attempts: int = 0  # 0 = infinite


@dataclass
class SocketTransportConfig(TransportConfig):
    """Base configuration for socket-based transports"""
    buffer_size: int = 4096


class ITransport(ABC):
    """Transport interface for sending and receiving data"""

    @abstractmethod
    def connect(self) -> None:
        """Connect to the transport endpoint"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the transport endpoint"""
        pass

    @abstractmethod
    def send(self, data: bytes) -> None:
        """Send data through the transport"""
        pass

    @abstractmethod
    def set_data_callback(self, callback: Callable[[bytes], None]) -> None:
        """Set callback for receiving data"""
        pass

    @abstractmethod
    def set_error_callback(self, callback: Callable[[Exception], None]) -> None:
        """Set callback for connection errors"""
        pass

    @abstractmethod
    def set_close_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for connection close"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if transport is connected"""
        pass


class BaseTransport(ITransport):
    """Base transport with common functionality"""

    def __init__(self, config: Optional[TransportConfig] = None):
        self.config = config or TransportConfig()
        self.connected = False
        self.data_callback: Optional[Callable[[bytes], None]] = None
        self.error_callback: Optional[Callable[[Exception], None]] = None
        self.close_callback: Optional[Callable[[], None]] = None
        self.reconnect_attempts = 0

    def set_data_callback(self, callback: Callable[[bytes], None]) -> None:
        self.data_callback = callback

    def set_error_callback(self, callback: Callable[[Exception], None]) -> None:
        self.error_callback = callback

    def set_close_callback(self, callback: Callable[[], None]) -> None:
        self.close_callback = callback

    def is_connected(self) -> bool:
        return self.connected

    def _handle_data(self, data: bytes) -> None:
        """Internal method to handle received data"""
        if self.data_callback:
            self.data_callback(data)

    def _handle_error(self, error: Exception) -> None:
        """Internal method to handle errors"""
        if self.error_callback:
            self.error_callback(error)
        if self.config.auto_reconnect and self.connected:
            self._attempt_reconnect()

    def _handle_close(self) -> None:
        """Internal method to handle connection close"""
        self.connected = False
        if self.close_callback:
            self.close_callback()
        if self.config.auto_reconnect:
            self._attempt_reconnect()

    def _attempt_reconnect(self) -> None:
        """Attempt to reconnect with backoff"""
        import time
        
        if self.config.max_reconnect_attempts > 0 and \
           self.reconnect_attempts >= self.config.max_reconnect_attempts:
            return

        self.reconnect_attempts += 1
        time.sleep(self.config.reconnect_delay)

        try:
            self.connect()
            self.reconnect_attempts = 0
        except Exception as e:
            self._handle_error(e)


class BaseSocketTransport(BaseTransport):
    """
    Base class for socket-based transports (TCP, UDP).
    
    Consolidates common socket functionality like receive thread management,
    connection state, and error handling.
    """

    def __init__(self, config: SocketTransportConfig):
        super().__init__(config)
        self.socket_config = config
        self.socket: Optional[socket.socket] = None
        self.receive_thread: Optional[threading.Thread] = None
        self.running = False

    def _start_receive_thread(self) -> None:
        """Start the receive loop thread"""
        self.running = True
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()

    def _stop_receive_thread(self) -> None:
        """Stop the receive loop thread"""
        self.running = False
        if self.receive_thread:
            self.receive_thread.join(timeout=1.0)
            self.receive_thread = None

    def _close_socket(self) -> None:
        """Close the socket (override for protocol-specific cleanup)"""
        if self.socket:
            self.socket.close()
            self.socket = None

    def disconnect(self) -> None:
        """Disconnect the socket transport"""
        self._stop_receive_thread()
        self._close_socket()
        self.connected = False

    @abstractmethod
    def _receive_loop(self) -> None:
        """Receive loop running in separate thread (subclass must implement)"""
        pass
