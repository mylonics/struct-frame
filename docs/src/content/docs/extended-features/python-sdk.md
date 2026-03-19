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
from struct_frame_sdk.serial_transport import SerialTransport, SerialTransportConfig

config = SerialTransportConfig(port='/dev/ttyUSB0', baudrate=115200)
transport = SerialTransport(config)
transport.connect()
```

### TCP

```python
from struct_frame_sdk.tcp_transport import TcpTransport, TcpTransportConfig

config = TcpTransportConfig(host='192.168.1.100', port=8080)
transport = TcpTransport(config)
transport.connect()
```

### UDP

```python
from struct_frame_sdk.udp_transport import UdpTransport, UdpTransportConfig

config = UdpTransportConfig(remote_host='192.168.1.100', remote_port=8080)
transport = UdpTransport(config)
transport.connect()
```

## Async Support

```python
import asyncio
from struct_frame_sdk.async_serial_transport import AsyncSerialTransport, AsyncSerialTransportConfig

async def main():
    config = AsyncSerialTransportConfig(port='/dev/ttyUSB0', baud_rate=115200)
    transport = AsyncSerialTransport(config)
    await transport.connect()

asyncio.run(main())
```

