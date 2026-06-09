---
title: C++ SDK
description: C++ SDK with transport layers and message routing using the observer/subscriber pattern.
---

The C++ SDK provides transport layers and message routing with an observer/subscriber pattern.

## Installation

### Full SDK (with network transports)

```bash
python -m struct_frame messages.proto --build_cpp --cpp_path generated/ --sdk
```

Includes ASIO for UDP, TCP, Serial, and WebSocket transports.

### Embedded SDK (no external dependencies)

```bash
python -m struct_frame messages.proto --build_cpp --cpp_path generated/ --sdk_embedded
```

Minimal footprint for embedded systems. Serial transport only.

## Observer Pattern

Subscribe to messages using function pointers or lambdas:

```cpp
#include "struct_frame_sdk/sdk_embedded.hpp"
#include "messages.structframe.hpp"

void handle_status(const StatusMessage& msg, uint8_t msgId) {
    std::cout << "Status: " << msg.value << std::endl;
}

int main() {
    // Create SDK with transport and message-info callback.
    // The only template argument is the frame profile config.
    StructFrame::StructFrameSdkT<StructFrame::ProfileStandardConfig>
        sdk(&my_transport, &get_message_info);

    // Subscribe to messages by message ID
    sdk.subscribe<StatusMessage>(StatusMessage::MSG_ID, handle_status);

    // Connect the transport (incoming data is handled via callbacks)
    sdk.Connect();
}
```

## FrameMsgInfo Subscription And Forwarding

You can subscribe to every complete parsed frame directly as `FrameMsgInfo`:

```cpp
StructFrame::StructFrameSdkT<StructFrame::ProfileStandardConfig>
    sdk(&transport, &get_message_info);

auto all_frames = sdk.subscribeFrameInfo(
    [](const StructFrame::FrameMsgInfo& frame) {
        // Complete frame metadata is available even for CRC-failed frames.
        std::cout << "msg_id=" << frame.msg_id
                  << " len=" << frame.msg_len
                  << " valid=" << frame.valid << std::endl;
    });
```

To bridge two SDKs, use one of two forwarding modes:

- `SendDirect(frame_info)` for same-profile forwarding (most efficient, no re-encode)
- `Send(frame_info)` for cross-profile forwarding (re-encodes for destination profile)

Most efficient same-profile bridge:

```cpp
StructFrame::StructFrameSdkT<StructFrame::ProfileStandardConfig>
    source_sdk(&transport_a, &get_message_info);

StructFrame::StructFrameSdkT<StructFrame::ProfileStandardConfig>
    target_sdk(&transport_b, &get_message_info);

auto forward = source_sdk.subscribeFrameInfo(
    [&](const StructFrame::FrameMsgInfo& frame) {
        target_sdk.SendDirect(frame);  // fastest: forwards original frame bytes
    });

// Encode once on source side and inject/send as needed
StatusMessage msg{};
msg.value = 42;

uint8_t wire[512];
size_t wire_len = StructFrame::FrameEncoderWithCrc<StructFrame::ProfileStandardConfig>::encode(
    wire, sizeof(wire), msg);

// Feed encoded bytes into source SDK parse path:
source_sdk.Feed(wire, wire_len);
```

Cross-profile bridge (re-encode on destination):

```cpp
auto forward_cross_profile = source_sdk.subscribeFrameInfo(
    [&](const StructFrame::FrameMsgInfo& frame) {
        target_sdk.Send(frame);  // profile-aware re-encode
    });
```

Use the same type for other profiles by changing only the config:

```cpp
StructFrame::StructFrameSdkT<StructFrame::ProfileSensorConfig>
    sensor_sdk(&transport, &get_message_info);

StructFrame::StructFrameSdkT<StructFrame::ProfileIPCConfig>
    ipc_sdk(&transport, &get_message_info);

StructFrame::StructFrameSdkT<StructFrame::ProfileBulkConfig>
    bulk_sdk(&transport, &get_message_info);
```

## Transports (Full SDK)

### Serial

```cpp
#include "struct_frame_sdk/serial_transport.hpp"

// SerialTransport requires a platform-specific ISerialPort implementation.
// Provide your own class that implements the ISerialPort interface
// (open, close, write, read, is_open methods).
StructFrame::SerialTransportConfig config;
StructFrame::SerialTransport serial(&my_serial_port, config);
serial.connect();
```

### Network (UDP, TCP, WebSocket)

```cpp
#include "struct_frame_sdk/network_transports.hpp"

// UDP
StructFrame::UdpTransportConfig udp_config{.remoteHost = "192.168.1.100", .remotePort = 8080};
StructFrame::UdpTransport udp(udp_config);
udp.connect();

// TCP
StructFrame::TcpTransportConfig tcp_config{.host = "192.168.1.100", .port = 8080};
StructFrame::TcpTransport tcp(tcp_config);
tcp.connect();
```

## Frame Profiles

Use predefined frame profiles:

```cpp
#include "frame_profiles.hpp"

using namespace FrameParsers;

// Standard profile (recommended)
uint8_t buffer[1024];
ProfileStandardWriter writer(buffer, sizeof(buffer));
ProfileStandardAccumulatingReader reader;

// Sensor profile (minimal overhead)
ProfileSensorWriter sensor_writer(buffer, sizeof(buffer));
ProfileSensorAccumulatingReader sensor_reader(get_message_info);
```

See [Framing Details](/basic-usage/framing-details/) for more profiles.

