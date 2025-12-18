"""Struct Frame SDK - Python
Export all SDK components for both sync and async usage
"""

# Sync transports
from .transport import ITransport, TransportConfig, BaseTransport
from .udp_transport import UdpTransport, UdpTransportConfig
from .tcp_transport import TcpTransport, TcpTransportConfig
from .websocket_transport import WebSocketTransport, WebSocketTransportConfig
from .serial_transport import SerialTransport, SerialTransportConfig

# Async transports
from .async_transport import IAsyncTransport, AsyncTransportConfig, BaseAsyncTransport
from .async_udp_transport import AsyncUdpTransport, AsyncUdpTransportConfig
from .async_tcp_transport import AsyncTcpTransport, AsyncTcpTransportConfig
from .async_websocket_transport import AsyncWebSocketTransport, AsyncWebSocketTransportConfig
from .async_serial_transport import AsyncSerialTransport, AsyncSerialTransportConfig

# SDK clients
from .struct_frame_sdk import (
    StructFrameSdk,
    StructFrameSdkConfig,
    IFrameParser,
    IMessageCodec,
    MessageHandler,
)
from .async_struct_frame_sdk import (
    AsyncStructFrameSdk,
    AsyncStructFrameSdkConfig,
)

__all__ = [
    # Sync
    'ITransport',
    'TransportConfig',
    'BaseTransport',
    'UdpTransport',
    'UdpTransportConfig',
    'TcpTransport',
    'TcpTransportConfig',
    'WebSocketTransport',
    'WebSocketTransportConfig',
    'SerialTransport',
    'SerialTransportConfig',
    'StructFrameSdk',
    'StructFrameSdkConfig',
    # Async
    'IAsyncTransport',
    'AsyncTransportConfig',
    'BaseAsyncTransport',
    'AsyncUdpTransport',
    'AsyncUdpTransportConfig',
    'AsyncTcpTransport',
    'AsyncTcpTransportConfig',
    'AsyncWebSocketTransport',
    'AsyncWebSocketTransportConfig',
    'AsyncSerialTransport',
    'AsyncSerialTransportConfig',
    'AsyncStructFrameSdk',
    'AsyncStructFrameSdkConfig',
    # Common
    'IFrameParser',
    'IMessageCodec',
    'MessageHandler',
]
