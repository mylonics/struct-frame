"""Async Struct Frame SDK Client
High-level interface for sending and receiving framed messages using asyncio.

Like the synchronous SDK, this drives the profile-based ``AccumulatingReader``
directly (mirroring the TypeScript SDK). Frame parsing is synchronous and cheap;
only the transport I/O (connect/disconnect/send) is awaited. The reader owns a
bounded internal buffer and resyncs past corrupt or partial frames on its own.
"""

from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass

from .async_transport import IAsyncTransport
from .transport import SendResult

try:
    from frame_profiles import ProfileConfig, MessageInfo, AccumulatingReader, encode_message
except ImportError:  # pragma: no cover - import shim for packaged layout
    from ..frame_profiles import ProfileConfig, MessageInfo, AccumulatingReader, encode_message


GetMessageInfo = Callable[[int], Optional[MessageInfo]]
MessageHandler = Callable[[Any, int], None]


class MessageCodec:
    """Message codec interface - deserializes raw bytes into message objects."""

    msg_id: int

    def deserialize(self, data: bytes) -> Any:
        raise NotImplementedError


@dataclass
class AsyncStructFrameSdkConfig:
    """Async Struct Frame SDK Configuration.

    Attributes:
        transport: Async transport layer (IAsyncTransport).
        profile: Frame profile configuration (e.g. PROFILE_STANDARD_CONFIG).
        get_message_info: Callback for looking up message metadata by ID. Required
            for minimal profiles; recommended for CRC profiles.
        buffer_size: Size of the reader's internal accumulation buffer.
        debug: Enable debug logging.
    """
    transport: IAsyncTransport
    profile: ProfileConfig
    get_message_info: Optional[GetMessageInfo] = None
    buffer_size: int = 4096
    debug: bool = False


class AsyncStructFrameSdk:
    """Main SDK Client for async operations."""

    def __init__(self, config: AsyncStructFrameSdkConfig):
        self.transport = config.transport
        self.profile = config.profile
        self.get_message_info = config.get_message_info
        self.debug = config.debug
        self.message_handlers: Dict[int, List[MessageHandler]] = {}
        self.message_codecs: Dict[int, MessageCodec] = {}
        self.reader = AccumulatingReader(
            config.profile,
            get_message_info=config.get_message_info,
            buffer_size=config.buffer_size,
        )

        # Transport callbacks are synchronous; parsing is synchronous and cheap.
        self.transport.set_data_callback(self._handle_incoming_data)
        self.transport.set_error_callback(self._handle_error)
        self.transport.set_close_callback(self._handle_close)

    async def connect(self) -> None:
        """Connect to the transport"""
        await self.transport.connect()
        self._log('Connected')

    async def disconnect(self) -> None:
        """Disconnect from the transport"""
        await self.transport.disconnect()
        self._log('Disconnected')

    async def __aenter__(self) -> 'AsyncStructFrameSdk':
        """Async context manager entry: connect and return self."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit: always disconnect."""
        await self.disconnect()
        return False

    def register_codec(self, codec: MessageCodec) -> None:
        """Register a message codec for automatic deserialization"""
        self.message_codecs[codec.msg_id] = codec

    def subscribe(self, msg_id: int, handler: MessageHandler) -> Callable[[], None]:
        """Subscribe to messages with a specific message ID.

        Returns an unsubscribe function.
        """
        if msg_id not in self.message_handlers:
            self.message_handlers[msg_id] = []
        self.message_handlers[msg_id].append(handler)
        self._log(f'Subscribed to message ID {msg_id}')

        def unsubscribe():
            handlers = self.message_handlers.get(msg_id)
            if handlers and handler in handlers:
                handlers.remove(handler)

        return unsubscribe

    async def send_raw(self, msg_id: int, data: bytes,
                       seq: int = 0, sys_id: int = 0, comp_id: int = 0) -> SendResult:
        """Frame a pre-serialized payload with the configured profile and send it."""
        info = self.get_message_info(msg_id) if self.get_message_info else None
        magic1 = info.magic1 if info is not None else 0
        magic2 = info.magic2 if info is not None else 0
        payload = bytes(data)

        raw_cls = type('_RawMessage', (), {
            'MSG_ID': msg_id,
            'MAGIC1': magic1,
            'MAGIC2': magic2,
            'serialize': lambda self_: payload,
        })
        framed = encode_message(self.profile, raw_cls(), seq=seq, sys_id=sys_id, comp_id=comp_id)
        attempted = len(framed)
        written = await self.transport.send(framed)
        self._log(f'Sent message ID {msg_id}, {len(payload)} payload bytes')
        return SendResult(success=written == attempted, attempted_bytes=attempted, bytes_written=written)

    async def send(self, message: Any,
                   seq: int = 0, sys_id: int = 0, comp_id: int = 0) -> SendResult:
        """Send a generated message object (exposes MSG_ID/msg_id and serialize())."""
        framed = encode_message(self.profile, message, seq=seq, sys_id=sys_id, comp_id=comp_id)
        attempted = len(framed)
        written = await self.transport.send(framed)
        msg_id = getattr(message, 'MSG_ID', None) or getattr(message, 'msg_id', None)
        self._log(f'Sent message ID {msg_id}, {attempted} frame bytes')
        return SendResult(success=written == attempted, attempted_bytes=attempted, bytes_written=written)

    def is_connected(self) -> bool:
        """Check if connected"""
        return self.transport.is_connected()

    def _handle_incoming_data(self, data: bytes) -> None:
        """Feed incoming bytes to the reader and dispatch every complete frame."""
        self.reader.add_data(data)
        while True:
            result = self.reader.next()
            if not result.valid:
                break
            self._dispatch(result)

    def _dispatch(self, result) -> None:
        """Deserialize (if a codec is registered) and notify handlers."""
        self._log(f'Received message ID {result.msg_id}, {result.msg_len} bytes')
        handlers = self.message_handlers.get(result.msg_id)
        if not handlers:
            return

        message: Any = result.msg_data
        codec = self.message_codecs.get(result.msg_id)
        if codec:
            try:
                message = codec.deserialize(result.msg_data)
            except Exception as e:
                self._log(f'Failed to deserialize message ID {result.msg_id}: {e}')

        for handler in list(handlers):
            try:
                handler(message, result.msg_id)
            except Exception as e:
                self._log(f'Handler error for message ID {result.msg_id}: {e}')

    def _handle_error(self, error: Exception) -> None:
        """Handle transport error"""
        self._log(f'Transport error: {error}')

    def _handle_close(self) -> None:
        """Handle transport close - discard any partial frame state."""
        self._log('Transport closed')
        self.reader.reset()

    def _log(self, message: str) -> None:
        """Log debug message"""
        if self.debug:
            print(f'[AsyncStructFrameSdk] {message}')
