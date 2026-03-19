---
title: Python SDK
description: Python SDK with synchronous and asynchronous interfaces for message communication.
---

The Python SDK provides both synchronous and asynchronous interfaces for message communication.

## Installation

Generate with SDK:

```bash
python -m struct_frame messages.proto --build_py --py_path generated/ --sdk
```

## Parser Usage

```python
from frame_profiles import ProfileStandardWriter, ProfileStandardAccumulatingReader
from struct_frame.generated.messages import Status, get_message_info

# Encode
msg = Status(value=42)
writer = ProfileStandardWriter(1024)
writer.write(msg)
frame = writer.data()

# Decode
reader = ProfileStandardAccumulatingReader(get_message_info=get_message_info)
for byte in frame:
    result = reader.push_byte(byte)
    if result and result.valid:
        decoded = Status.deserialize(result)
        print(f"Status: {decoded.value}")
```

## Message Router

```python
from struct_frame_sdk.struct_frame_sdk import StructFrameSdk, StructFrameSdkConfig
from struct_frame_sdk.tcp_transport import TcpTransport
from struct_frame.generated.messages import Status

# Configure SDK with transport
config = StructFrameSdkConfig(
    transport=TcpTransport('192.168.1.100', 8080),
    frame_parser=...  # frame parser instance
)
sdk = StructFrameSdk(config)

# Subscribe to messages by ID
def handle_status(msg: Status, msg_id: int):
    print(f"Status: {msg.value}")

sdk.subscribe(Status.msg_id, handle_status)
sdk.connect()
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

