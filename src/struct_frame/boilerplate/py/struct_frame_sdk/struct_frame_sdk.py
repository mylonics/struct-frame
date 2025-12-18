"""Struct Frame SDK Client
High-level interface for sending and receiving framed messages
"""

from typing import Callable, Dict, List, Optional, Any, Protocol
from dataclasses import dataclass
from .transport import ITransport


class IFrameParser(Protocol):
    """Frame parser interface - must be implemented by generated frame parsers"""

    def parse(self, data: bytes):
        """Parse incoming data and extract message
        Returns FrameMsgInfo with valid=True if message found
        """
        ...

    def frame(self, msg_id: int, data: bytes) -> bytes:
        """Frame a message for sending"""
        ...


class IMessageCodec(Protocol):
    """Message codec interface - deserializes raw bytes into message objects"""

    @property
    def msg_id(self) -> int:
        """Get message ID for this codec"""
        ...

    def create_unpack(self, data: bytes) -> Any:
        """Deserialize bytes into message object"""
        ...


MessageHandler = Callable[[Any, int], None]


@dataclass
class StructFrameSdkConfig:
    """Struct Frame SDK Configuration"""
    transport: ITransport
    frame_parser: IFrameParser
    debug: bool = False


class StructFrameSdk:
    """Main SDK Client for synchronous operations"""

    def __init__(self, config: StructFrameSdkConfig):
        self.transport = config.transport
        self.frame_parser = config.frame_parser
        self.debug = config.debug
        self.message_handlers: Dict[int, List[MessageHandler]] = {}
        self.message_codecs: Dict[int, IMessageCodec] = {}
        self.buffer = b''

        # Set up transport callbacks
        self.transport.set_data_callback(self._handle_incoming_data)
        self.transport.set_error_callback(self._handle_error)
        self.transport.set_close_callback(self._handle_close)

    def connect(self) -> None:
        """Connect to the transport"""
        self.transport.connect()
        self._log('Connected')

    def disconnect(self) -> None:
        """Disconnect from the transport"""
        self.transport.disconnect()
        self._log('Disconnected')

    def register_codec(self, codec: IMessageCodec) -> None:
        """Register a message codec for automatic deserialization"""
        self.message_codecs[codec.msg_id] = codec

    def subscribe(self, msg_id: int, handler: MessageHandler) -> Callable[[], None]:
        """Subscribe to messages with a specific message ID
        
        Returns an unsubscribe function
        """
        if msg_id not in self.message_handlers:
            self.message_handlers[msg_id] = []
        self.message_handlers[msg_id].append(handler)
        self._log(f'Subscribed to message ID {msg_id}')

        # Return unsubscribe function
        def unsubscribe():
            handlers = self.message_handlers.get(msg_id)
            if handlers and handler in handlers:
                handlers.remove(handler)

        return unsubscribe

    def send_raw(self, msg_id: int, data: bytes) -> None:
        """Send a raw message (already serialized)"""
        framed_data = self.frame_parser.frame(msg_id, data)
        self.transport.send(framed_data)
        self._log(f'Sent message ID {msg_id}, {len(data)} bytes')

    def send(self, message: Any) -> None:
        """Send a message object (requires pack() method and msg_id attribute)"""
        data = message.pack()
        self.send_raw(message.msg_id, data)

    def is_connected(self) -> bool:
        """Check if connected"""
        return self.transport.is_connected()

    def _handle_incoming_data(self, data: bytes) -> None:
        """Handle incoming data from transport"""
        # Append to buffer
        self.buffer += data

        # Try to parse messages from buffer
        self._parse_buffer()

    def _parse_buffer(self) -> None:
        """Parse messages from buffer"""
        while len(self.buffer) > 0:
            result = self.frame_parser.parse(self.buffer)

            if not result.valid:
                # No valid frame found, keep buffer as is
                break

            # Valid message found
            self._log(f'Received message ID {result.msg_id}, {result.msg_len} bytes')

            # Notify handlers
            handlers = self.message_handlers.get(result.msg_id, [])
            if handlers:
                # Try to deserialize with registered codec
                message: Any = result.msg_data
                codec = self.message_codecs.get(result.msg_id)
                if codec:
                    try:
                        message = codec.create_unpack(result.msg_data)
                    except Exception as e:
                        self._log(f'Failed to deserialize message ID {result.msg_id}: {e}')

                # Call all handlers
                for handler in handlers:
                    try:
                        handler(message, result.msg_id)
                    except Exception as e:
                        self._log(f'Handler error for message ID {result.msg_id}: {e}')

            # Remove parsed data from buffer
            total_frame_size = self._calculate_frame_size(result)
            self.buffer = self.buffer[total_frame_size:]

    def _calculate_frame_size(self, result) -> int:
        """Calculate total frame size including headers and footers
        
        Frame overhead by format:
        - BasicDefault: 2 start + 1 length + 1 msg_id + payload + 2 crc = 6 + payload
        - TinyDefault: 1 start + 1 length + 1 msg_id + payload + 2 crc = 5 + payload
        
        Using conservative estimate of 10 bytes to handle all frame formats.
        TODO: Query frame parser for exact overhead to avoid buffering issues.
        """
        return result.msg_len + 10

    def _handle_error(self, error: Exception) -> None:
        """Handle transport error"""
        self._log(f'Transport error: {error}')

    def _handle_close(self) -> None:
        """Handle transport close"""
        self._log('Transport closed')
        self.buffer = b''

    def _log(self, message: str) -> None:
        """Log debug message"""
        if self.debug:
            print(f'[StructFrameSdk] {message}')
