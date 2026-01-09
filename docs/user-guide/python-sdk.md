# Python SDK

The Python SDK provides both synchronous and asynchronous interfaces for structured message communication.

## Installation

Generate Python code with SDK:

```bash
python -m struct_frame your_messages.proto --build_py --py_path generated/py --sdk
```

**Note**: The SDK is not included by default. Use the `--sdk` flag to generate SDK files.

## Using the Parser

The `Parser` class can parse multiple frame types (Basic, Tiny, None) from a byte stream. It automatically detects the frame format and extracts message data.

### Basic Usage

```python
from parser import Parser, HeaderType, PayloadType

# Create a parser instance
parser = Parser()

# Parse bytes from a stream
for byte in incoming_data:
    result = parser.parse_byte(byte)
    if result.valid:
        print(f"Received message ID: {result.msg_id}")
        print(f"Frame type: {result.header_type}")
        print(f"Payload type: {result.payload_type}")
        print(f"Data: {result.msg_data}")
```

### Encoding Messages

```python
from parser import Parser, HeaderType, PayloadType

parser = Parser()

# Encode a message with Basic header and Default payload
frame = parser.encode(
    msg_id=42,
    msg=b"Hello, World!",
    header_type=HeaderType.BASIC,
    payload_type=PayloadType.DEFAULT
)

# Or use convenience methods
frame = parser.encode_basic(msg_id=42, msg=b"Hello, World!")
frame = parser.encode_tiny(msg_id=42, msg=b"Hello, World!")
```

### Configuring Enabled Frame Types

```python
from parser import Parser, HeaderType, PayloadType

# Only accept Basic and Tiny frames with Default payload
parser = Parser(
    enabled_headers=[HeaderType.BASIC, HeaderType.TINY],
    enabled_payloads=[PayloadType.DEFAULT, PayloadType.EXTENDED]
)
```

### Using with Minimal Payloads

For Minimal payloads (which don't include a length field), struct-frame automatically generates a `get_msg_length` function based on your message definitions:

```python
from parser import Parser, PayloadType
# Import the auto-generated get_msg_length function
from my_messages_sf import get_msg_length

parser = Parser(
    get_msg_length=get_msg_length,
    enabled_payloads=[PayloadType.MINIMAL]
)
```

**Manual callback** (if you need custom logic):
```python
def get_msg_length(msg_id: int) -> int:
    """Return the expected message length for a given msg_id"""
    msg_lengths = {
        1: 10,  # Message ID 1 is 10 bytes
        2: 20,  # Message ID 2 is 20 bytes
    }
    return msg_lengths.get(msg_id, 0)

parser = Parser(
    get_msg_length=get_msg_length,
    enabled_payloads=[PayloadType.MINIMAL]
)
```

### Parsing Mixed Frame Streams

The Parser can handle streams containing multiple frame types:

```python
from parser import Parser

parser = Parser()

# Process a mixed stream of Basic and Tiny frames
stream = basic_frame_bytes + tiny_frame_bytes + another_basic_frame
messages = []

for byte in stream:
    result = parser.parse_byte(byte)
    if result.valid:
        messages.append({
            'msg_id': result.msg_id,
            'header_type': result.header_type,
            'payload_type': result.payload_type,
            'data': result.msg_data
        })

print(f"Parsed {len(messages)} messages from mixed stream")
```

## Profile-Based Parsing API

The Python SDK provides high-performance parsing classes that match the C++ gold standard implementation. These are optimized for specific frame profiles and provide convenient factory functions.

### Available Profiles

| Profile | Header | Payload | Use Case |
|---------|--------|---------|----------|
| `ProfileStandard` | Basic | Default | General serial/UART communication |
| `ProfileSensor` | Tiny | Minimal | Low-bandwidth sensors, radio links |
| `ProfileIPC` | None | Minimal | Trusted inter-process communication |
| `ProfileBulk` | Basic | Extended | Firmware/file transfers |
| `ProfileNetwork` | Basic | ExtendedMultiSystemStream | Multi-node mesh networks |

### BufferReader - Parse Multiple Frames from a Buffer

`BufferReader` iterates through a buffer containing one or more frames, automatically tracking the offset:

```python
from frame_profiles import (
    create_profile_standard_reader,
    create_profile_sensor_reader,
)

# Parse a buffer containing multiple ProfileStandard frames
reader = create_profile_standard_reader(buffer_data)
while reader.has_more():
    result = reader.next()
    if not result.valid:
        break
    print(f"Message ID: {result.msg_id}, Length: {result.msg_len}")
    process_message(result.msg_data)

print(f"Processed {reader.offset} bytes, {reader.remaining} remaining")
```

For minimal profiles (no length field), provide a message length callback:

```python
from my_messages_sf import get_message_length

# Parse ProfileSensor frames (minimal payload)
reader = create_profile_sensor_reader(buffer_data, get_message_length)
while reader.has_more():
    result = reader.next()
    if result.valid:
        process_message(result.msg_id, result.msg_data)
```

### BufferWriter - Encode Multiple Frames

`BufferWriter` encodes multiple frames into a buffer with automatic offset tracking:

```python
from frame_profiles import (
    create_profile_standard_writer,
    create_profile_network_writer,
)

# Create writer with capacity
writer = create_profile_standard_writer(capacity=4096)

# Write multiple messages
writer.write(msg_id=1, payload=msg1_data)
writer.write(msg_id=2, payload=msg2_data)
writer.write(msg_id=3, payload=msg3_data)

# Get the encoded data
encoded_buffer = writer.data()
print(f"Encoded {writer.size()} bytes with {writer.count()} messages")
```

For network profiles with extra header fields:

```python
writer = create_profile_network_writer(capacity=4096)
writer.write(msg_id=1, payload=data, seq=1, sys_id=10, comp_id=1)
```

### AccumulatingReader - Unified Buffer and Streaming Parser

`AccumulatingReader` handles both buffer mode and byte-by-byte streaming, with support for partial messages across buffer boundaries:

**Buffer Mode** - Processing chunks of data:

```python
from frame_profiles import create_profile_standard_accumulating_reader

reader = create_profile_standard_accumulating_reader()

# Process incoming chunks (e.g., from network or file)
reader.add_data(chunk1)
while True:
    result = reader.next()
    if not result.valid:
        break
    process_message(result.msg_id, result.msg_data)

# Add more data (handles partial messages automatically)
reader.add_data(chunk2)
while True:
    result = reader.next()
    if not result.valid:
        break
    process_message(result.msg_id, result.msg_data)
```

**Stream Mode** - Byte-by-byte processing (UART/serial):

```python
from frame_profiles import create_profile_sensor_accumulating_reader
from my_messages_sf import get_message_length

reader = create_profile_sensor_accumulating_reader(get_message_length)

# Process incoming bytes one at a time
while True:
    byte = serial_port.read(1)
    if not byte:
        break
    result = reader.push_byte(byte[0])
    if result.valid:
        # Complete message received
        process_message(result.msg_id, result.msg_data)
```

### Factory Functions

All profiles have factory functions for creating readers and writers:

```python
from frame_profiles import (
    # BufferReader factories
    create_profile_standard_reader,
    create_profile_sensor_reader,
    create_profile_ipc_reader,
    create_profile_bulk_reader,
    create_profile_network_reader,
    
    # BufferWriter factories
    create_profile_standard_writer,
    create_profile_sensor_writer,
    create_profile_ipc_writer,
    create_profile_bulk_writer,
    create_profile_network_writer,
    
    # AccumulatingReader factories
    create_profile_standard_accumulating_reader,
    create_profile_sensor_accumulating_reader,
    create_profile_ipc_accumulating_reader,
    create_profile_bulk_accumulating_reader,
    create_profile_network_accumulating_reader,
)
```

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
