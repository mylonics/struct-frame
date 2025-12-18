"""Async Serial Port Transport implementation using asyncio and pyserial"""

import asyncio
from dataclasses import dataclass
from typing import Optional
try:
    import serial
except ImportError:
    serial = None

from .async_transport import BaseAsyncTransport, AsyncTransportConfig


@dataclass
class AsyncSerialTransportConfig(AsyncTransportConfig):
    """Async Serial transport configuration"""
    port: str = ''
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = 'N'  # 'N', 'E', 'O', 'M', 'S'
    stopbits: float = 1  # 1, 1.5, 2
    timeout: float = 0.1  # Short timeout for async operations
    xonxoff: bool = False
    rtscts: bool = False
    dsrdtr: bool = False


class AsyncSerialTransport(BaseAsyncTransport):
    """Async Serial transport using pyserial with asyncio"""

    def __init__(self, config: AsyncSerialTransportConfig):
        super().__init__(config)
        if serial is None:
            raise ImportError('pyserial package is required. Install with: pip install pyserial')
        self.serial_config = config
        self.serial_port: Optional[serial.Serial] = None
        self.receive_task: Optional[asyncio.Task] = None

    async def connect(self) -> None:
        """Connect serial port"""
        try:
            # Run serial port opening in executor to avoid blocking
            loop = asyncio.get_event_loop()
            self.serial_port = await loop.run_in_executor(
                None,
                self._open_serial_port
            )
            
            self.connected = True
            
            # Start receive task
            self.receive_task = asyncio.create_task(self._receive_loop())
            
        except Exception as e:
            self._handle_error(e)
            raise

    def _open_serial_port(self) -> serial.Serial:
        """Open serial port (blocking operation)"""
        port = serial.Serial(
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
        
        if not port.is_open:
            port.open()
        
        return port

    async def disconnect(self) -> None:
        """Disconnect serial port"""
        self.connected = False
        
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
            self.receive_task = None
        
        if self.serial_port and self.serial_port.is_open:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.serial_port.close)
            self.serial_port = None

    async def send(self, data: bytes) -> None:
        """Send data via serial port"""
        if not self.serial_port or not self.connected or not self.serial_port.is_open:
            raise RuntimeError('Serial port not connected')
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._write_serial, data)
        except Exception as e:
            self._handle_error(e)
            raise

    def _write_serial(self, data: bytes) -> None:
        """Write to serial port (blocking operation)"""
        if self.serial_port:
            self.serial_port.write(data)
            self.serial_port.flush()

    async def _receive_loop(self) -> None:
        """Receive loop"""
        loop = asyncio.get_event_loop()
        while self.connected and self.serial_port and self.serial_port.is_open:
            try:
                # Read in executor to avoid blocking
                data = await loop.run_in_executor(None, self._read_serial)
                if data:
                    self._handle_data(data)
                else:
                    # Small delay when no data available
                    await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.connected:
                    self._handle_error(e)
                break

    def _read_serial(self) -> bytes:
        """Read from serial port (blocking operation)"""
        if self.serial_port and self.serial_port.in_waiting > 0:
            return self.serial_port.read(self.serial_port.in_waiting)
        return b''
