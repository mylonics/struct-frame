# Python SDK

The Python SDK provides both synchronous and asynchronous interfaces for structured message communication.

## Installation

Generate Python code with SDK:

```bash
python -m struct_frame your_messages.proto --build_py --py_path generated/py --sdk
```

**Note**: The SDK is not included by default. Use the `--sdk` flag to generate SDK files.

## Available Transports

### Synchronous Transports

#### UDP Transport

```python
from struct_frame_sdk import UdpTransport, UdpTransportConfig

transport = UdpTransport(UdpTransportConfig(
    remote_host='192.168.1.100',
    remote_port=5000,
    local_port=5001,
    local_address='0.0.0.0',
    enable_broadcast=False,
    auto_reconnect=True,
    reconnect_delay=1.0,
    max_reconnect_attempts=5,
))
```

#### TCP Transport

```python
from struct_frame_sdk import TcpTransport, TcpTransportConfig

transport = TcpTransport(TcpTransportConfig(
    host='192.168.1.100',
    port=5000,
    timeout=5.0,
    auto_reconnect=True,
))
```

#### WebSocket Transport

Requires `websocket-client` package:

```python
from struct_frame_sdk import WebSocketTransport, WebSocketTransportConfig

transport = WebSocketTransport(WebSocketTransportConfig(
    url='ws://localhost:8080',
    timeout=5.0,
))
```

#### Serial Transport

Requires `pyserial` package:

```python
from struct_frame_sdk import SerialTransport, SerialTransportConfig

transport = SerialTransport(SerialTransportConfig(
    port='/dev/ttyUSB0',  # or 'COM3' on Windows
    baudrate=115200,
    bytesize=8,
    parity='N',
    stopbits=1,
))
```

### Asynchronous Transports

All transports have async versions with `Async` prefix:

```python
from struct_frame_sdk import (
    AsyncUdpTransport, AsyncUdpTransportConfig,
    AsyncTcpTransport, AsyncTcpTransportConfig,
    AsyncWebSocketTransport, AsyncWebSocketTransportConfig,
    AsyncSerialTransport, AsyncSerialTransportConfig,
)
```

## Synchronous SDK Usage

### Creating the SDK

```python
from struct_frame_sdk import StructFrameSdk, StructFrameSdkConfig
from basic_default import BasicDefault

sdk = StructFrameSdk(StructFrameSdkConfig(
    transport=transport,
    frame_parser=BasicDefault(),
    debug=True,
))
```

### Connecting and Disconnecting

```python
# Connect
sdk.connect()

# Check connection status
if sdk.is_connected():
    print('Connected!')

# Disconnect
sdk.disconnect()
```

### Subscribing to Messages

```python
from my_messages import StatusMessage

def on_status(message, msg_id):
    print(f'Temperature: {message.temperature}')
    print(f'Battery: {message.battery}')

# Subscribe
unsubscribe = sdk.subscribe(StatusMessage.msg_id, on_status)

# Unsubscribe when done
unsubscribe()
```

### Sending Messages

```python
from my_messages import CommandMessage

# Create and send message
cmd = CommandMessage(command='START', value=100)
sdk.send(cmd)

# Or send raw bytes
raw_data = b'\x01\x02\x03\x04'
sdk.send_raw(CommandMessage.msg_id, raw_data)
```

### Complete Synchronous Example

```python
import time
from struct_frame_sdk import StructFrameSdk, StructFrameSdkConfig, TcpTransport, TcpTransportConfig
from basic_default import BasicDefault
from robot_messages import StatusMessage, CommandMessage

def main():
    # Create transport
    transport = TcpTransport(TcpTransportConfig(
        host='localhost',
        port=8080,
        auto_reconnect=True,
        reconnect_delay=2.0,
    ))

    # Create SDK
    sdk = StructFrameSdk(StructFrameSdkConfig(
        transport=transport,
        frame_parser=BasicDefault(),
        debug=True,
    ))

    # Subscribe to status messages
    def on_status(msg, msg_id):
        print(f'[Status] Temp: {msg.temperature}°C, Battery: {msg.battery}%')

    sdk.subscribe(StatusMessage.msg_id, on_status)

    # Connect
    sdk.connect()
    print('Connected to robot')

    # Send command
    cmd = CommandMessage(command='MOVE_FORWARD', speed=50)
    sdk.send(cmd)

    # Keep running
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        sdk.disconnect()

if __name__ == '__main__':
    main()
```

## Asynchronous SDK Usage

### Creating the Async SDK

```python
import asyncio
from struct_frame_sdk import AsyncStructFrameSdk, AsyncStructFrameSdkConfig
from basic_default import BasicDefault

async def main():
    sdk = AsyncStructFrameSdk(AsyncStructFrameSdkConfig(
        transport=transport,
        frame_parser=BasicDefault(),
        debug=True,
    ))
```

### Async Operations

```python
# Connect
await sdk.connect()

# Send message
cmd = CommandMessage(command='START', value=100)
await sdk.send(cmd)

# Disconnect
await sdk.disconnect()
```

### Complete Asynchronous Example

```python
import asyncio
from struct_frame_sdk import (
    AsyncStructFrameSdk,
    AsyncStructFrameSdkConfig,
    AsyncTcpTransport,
    AsyncTcpTransportConfig,
)
from basic_default import BasicDefault
from robot_messages import StatusMessage, CommandMessage

async def main():
    # Create transport
    transport = AsyncTcpTransport(AsyncTcpTransportConfig(
        host='localhost',
        port=8080,
        auto_reconnect=True,
    ))

    # Create SDK
    sdk = AsyncStructFrameSdk(AsyncStructFrameSdkConfig(
        transport=transport,
        frame_parser=BasicDefault(),
        debug=True,
    ))

    # Subscribe to status messages
    def on_status(msg, msg_id):
        print(f'[Status] Temp: {msg.temperature}°C, Battery: {msg.battery}%')

    sdk.subscribe(StatusMessage.msg_id, on_status)

    # Connect
    await sdk.connect()
    print('Connected to robot')

    # Send command
    cmd = CommandMessage(command='MOVE_FORWARD', speed=50)
    await sdk.send(cmd)

    # Keep running
    try:
        while True:
            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        await sdk.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
```

## Automatic Message Deserialization

Register codecs for automatic deserialization:

```python
from my_messages import StatusMessage

# The message class itself can act as a codec
sdk.register_codec(StatusMessage)

# Now messages are automatically deserialized
sdk.subscribe(StatusMessage.msg_id, lambda msg, id: print(msg))
```

## Error Handling

```python
# Synchronous
try:
    sdk.connect()
except Exception as e:
    print(f'Failed to connect: {e}')

# Asynchronous
try:
    await sdk.connect()
except Exception as e:
    print(f'Failed to connect: {e}')

# Transport-level error handling
def on_error(error):
    print(f'Transport error: {error}')

transport.set_error_callback(on_error)
```

## Dependencies

Install optional dependencies based on transports used:

```bash
# WebSocket support
pip install websocket-client  # Sync
pip install websockets        # Async

# Serial port support
pip install pyserial
```

## Type Hints

The SDK is fully type-hinted for better IDE support:

```python
from typing import Callable, Protocol
from abc import ABC, abstractmethod

class ITransport(ABC):
    @abstractmethod
    def connect(self) -> None: ...
    
    @abstractmethod
    def disconnect(self) -> None: ...
    
    @abstractmethod
    def send(self, data: bytes) -> None: ...

class IFrameParser(Protocol):
    def parse(self, data: bytes): ...
    def frame(self, msg_id: int, data: bytes) -> bytes: ...

MessageHandler = Callable[[Any, int], None]
```

## Threading Considerations

The synchronous SDK uses background threads for receiving data. This is handled automatically, but be aware:

- Callbacks are executed in the receive thread
- Use thread-safe operations in callbacks if needed
- The async SDK uses asyncio event loop instead of threads

```python
import threading

def on_message(msg, msg_id):
    # This runs in a background thread
    print(f'Thread: {threading.current_thread().name}')
    # Use locks if accessing shared data
```

## Best Practices

1. **Always disconnect properly**:
   ```python
   try:
       sdk.connect()
       # ... use SDK
   finally:
       sdk.disconnect()
   ```

2. **Use async SDK for async applications**:
   - Web servers (FastAPI, aiohttp)
   - Concurrent I/O operations
   - Better resource usage

3. **Use sync SDK for**:
   - Simple scripts
   - Legacy codebases
   - Easier debugging

4. **Error handling**:
   - Always handle connection errors
   - Set error callbacks for transport issues
   - Implement reconnection logic if needed
