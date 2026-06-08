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

You can subscribe to every valid parsed frame directly as `FrameMsgInfo`:

```cpp
StructFrame::StructFrameSdkT<StructFrame::ProfileStandardConfig>
    sdk(&transport, &get_message_info);

auto all_frames = sdk.subscribeFrameInfo(
    [](const StructFrame::FrameMsgInfo& frame) {
        std::cout << "msg_id=" << frame.msg_id
                  << " len=" << frame.msg_len << std::endl;
    });
```

And you can forward a parsed `FrameMsgInfo` directly through another SDK instance:

```cpp
StructFrame::StructFrameSdkT<StructFrame::ProfileStandardConfig>
    sdk_a(&transport_a, &get_message_info);

StructFrame::StructFrameSdkT<StructFrame::ProfileStandardConfig>
    sdk_b(&transport_b, &get_message_info);

auto forward = sdk_a.subscribeFrameInfo(
    [&](const StructFrame::FrameMsgInfo& frame) {
        sdk_b.Send(frame);  // Re-encode and forward through sdk_b transport
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

