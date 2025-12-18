"""Serial Port Transport implementation using pyserial"""

import threading
from dataclasses import dataclass
from typing import Optional
try:
    import serial
except ImportError:
    serial = None

from .transport import BaseTransport, TransportConfig


@dataclass
class SerialTransportConfig(TransportConfig):
    """Serial transport configuration"""
    port: str = ''
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = 'N'  # 'N', 'E', 'O', 'M', 'S'
    stopbits: float = 1  # 1, 1.5, 2
    timeout: float = 1.0
    xonxoff: bool = False
    rtscts: bool = False
    dsrdtr: bool = False


class SerialTransport(BaseTransport):
    """Serial transport using pyserial"""

    def __init__(self, config: SerialTransportConfig):
        super().__init__(config)
        if serial is None:
            raise ImportError('pyserial package is required. Install with: pip install pyserial')
        self.serial_config = config
        self.serial_port: Optional[serial.Serial] = None
        self.receive_thread: Optional[threading.Thread] = None
        self.running = False

    def connect(self) -> None:
        """Connect serial port"""
        try:
            self.serial_port = serial.Serial(
                port=self.serial_config.port,
                baudrate=self.serial_config.baudrate,
                bytesize=self.serial_config.bytesize,
                parity=self.serial_config.parity,
                stopbits=self.serial_config.stopbits,
                timeout=self.serial_config.timeout,
                xonxoff=self.serial_config.xonxoff,
                rtscts=self.serial_config.rtscts,
                dsrdtr=self.serial_config.dsrdtr
            )
            
            if not self.serial_port.is_open:
                self.serial_port.open()
            
            self.connected = True
            
            # Start receive thread
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
        except Exception as e:
            self._handle_error(e)
            raise

    def disconnect(self) -> None:
        """Disconnect serial port"""
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            self.serial_port = None
        if self.receive_thread:
            self.receive_thread.join(timeout=1.0)
            self.receive_thread = None
        self.connected = False

    def send(self, data: bytes) -> None:
        """Send data via serial port"""
        if not self.serial_port or not self.connected or not self.serial_port.is_open:
            raise RuntimeError('Serial port not connected')
        
        try:
            self.serial_port.write(data)
            self.serial_port.flush()
        except Exception as e:
            self._handle_error(e)
            raise

    def _receive_loop(self) -> None:
        """Receive loop running in separate thread"""
        while self.running and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    if data:
                        self._handle_data(data)
            except Exception as e:
                if self.running:  # Only handle error if still running
                    self._handle_error(e)
                break
