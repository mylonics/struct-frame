---
title: Python SDK
description: Python SDK with synchronous and asynchronous interfaces for message communication.
---

The Python SDK provides both synchronous and asynchronous interfaces for message communication.

## Installation

Generate with SDK:

```bash
python -m struct_frame messages.sf --build_py --py_path generated/ --sdk
```

The serial transport needs `pyserial`, and the WebSocket transports need `websockets`; install them separately if you use those transports.

## Parser Usage

Python profiles are configuration objects (`PROFILE_STANDARD_CONFIG`, `PROFILE_SENSOR_CONFIG`, `PROFILE_IPC_CONFIG`, `PROFILE_BULK_CONFIG`, `PROFILE_NETWORK_CONFIG`) that you pass to `BufferWriter` and `AccumulatingReader`:

```python
from frame_profiles import BufferWriter, AccumulatingReader, PROFILE_STANDARD_CONFIG
from struct_frame.generated.messages import Status, get_message_info

# Encode
msg = Status(value=42)
writer = BufferWriter(PROFILE_STANDARD_CONFIG, 1024)
writer.write(msg)
frame = writer.data()

# Decode
reader = AccumulatingReader(PROFILE_STANDARD_CONFIG, get_message_info=get_message_info)
for byte in frame:
    result = reader.push_byte(byte)
    if result and result.valid:
        decoded = Status.deserialize(result.msg_data)
        print(f"Status: {decoded.value}")
```

A message whose ID does not fit the profile (an ID above 255 on the Standard, Sensor or IPC profiles, which carry a 1-byte ID) raises `ValueError` when encoded; use a profile with a package ID (Bulk or Network) for those messages.

## Message Router

```python
from struct_frame_sdk.struct_frame_sdk import StructFrameSdk, StructFrameSdkConfig
from struct_frame_sdk.tcp_transport import TcpTransport, TcpTransportConfig
from frame_profiles import PROFILE_STANDARD_CONFIG
from struct_frame.generated.messages import Status, get_message_info

# Configure SDK with transport and frame profile
config = StructFrameSdkConfig(
    transport=TcpTransport(TcpTransportConfig(host='192.168.1.100', port=8080)),
    profile=PROFILE_STANDARD_CONFIG,
    get_message_info=get_message_info,
    on_error=lambda err: print(f"SDK error: {err}"),
)
sdk = StructFrameSdk(config)

# Register a codec so handlers receive decoded messages (without one they receive raw
# bytes). A generated message class is a valid codec: it has `msg_id` and `deserialize`.
sdk.register_codec(Status)

# Subscribe to messages by ID; subscribe() returns an unsubscribe callable
def handle_status(msg: Status, msg_id: int):
    print(f"Status: {msg.value}")

unsubscribe = sdk.subscribe(Status.MSG_ID, handle_status)
sdk.connect()

# Send a message
sdk.send(Status(value=1))

# Send a request and wait for the matching reply (see the SDK overview)
# reply = sdk.request(Ping(seq=1), Pong, timeout=2.0)
```

`on_error` receives transport errors, exceptions raised by handlers and deserialization failures. Without it they are only logged when `debug=True`.

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

### WebSocket

`struct_frame_sdk.websocket_transport` provides a synchronous WebSocket transport, and `struct_frame_sdk.async_websocket_transport` the asyncio one.

## Async Support

```python
import asyncio
from struct_frame_sdk.async_serial_transport import AsyncSerialTransport, AsyncSerialTransportConfig

async def main():
    config = AsyncSerialTransportConfig(port='/dev/ttyUSB0', baudrate=115200)
    transport = AsyncSerialTransport(config)
    await transport.connect()

asyncio.run(main())
```

`AsyncStructFrameSdk` (in `struct_frame_sdk.async_struct_frame_sdk`) mirrors `StructFrameSdk` with awaitable `request()` and `send()`.
