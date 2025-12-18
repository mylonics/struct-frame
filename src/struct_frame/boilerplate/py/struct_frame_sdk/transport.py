"""Transport interface for struct-frame SDK
Provides abstraction for various communication channels
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class TransportConfig:
    """Configuration for transport layer"""
    auto_reconnect: bool = False
    reconnect_delay: float = 1.0  # seconds
    max_reconnect_attempts: int = 0  # 0 = infinite


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
