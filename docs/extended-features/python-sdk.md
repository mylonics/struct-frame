# Python SDK

The Python SDK provides both synchronous and asynchronous interfaces for message communication.

## Installation

Generate with SDK:

```bash
python -m struct_frame messages.proto --build_py --py_path generated/ --sdk
```

## Parser Usage

```python
from struct_frame_parser import Parser, HeaderType, PayloadType
from messages_sf import Status

# Create parser
parser = Parser()

# Encode
frame = parser.encode_basic(msg_id=1, msg=Status(value=42).to_bytes())

# Decode
for byte in frame:
    result = parser.parse_byte(byte)
    if result.valid:
        msg = Status.from_bytes(result.msg_data)
        print(f"Status: {msg.value}")
```

## Message Router

```python
from struct_frame_sdk import MessageRouter
from messages_sf import Status

router = MessageRouter()

# Subscribe to messages
@router.subscribe(Status)
def handle_status(msg: Status):
    print(f"Status: {msg.value}")

# Process incoming data
router.process_byte(byte)
```

## Transports

### Serial

```python
import serial
from struct_frame_sdk.transports import SerialTransport

transport = SerialTransport('/dev/ttyUSB0', 115200)
transport.connect()
transport.send(msg_id, data)
```

### Socket

```python
import socket
from struct_frame_sdk.transports import SocketTransport

transport = SocketTransport('192.168.1.100', 8080)
transport.connect()
transport.send(msg_id, data)
```

## Async Support

```python
import asyncio
from struct_frame_sdk.async_transports import AsyncSerialTransport

async def main():
    transport = AsyncSerialTransport('/dev/ttyUSB0', 115200)
    await transport.connect()
    await transport.send(msg_id, data)

asyncio.run(main())
```

