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
    // Create SDK with transport and frame parser
    StructFrame::StructFrameSdkConfig config{
        .transport = &my_transport,
        .frameParser = &my_frame_parser,
    };
    StructFrame::StructFrameSdk sdk(config);

    // Subscribe to messages by message ID
    sdk.subscribe<StatusMessage>(StatusMessage::MSG_ID, handle_status);

    // Connect the transport (incoming data is handled via callbacks)
    sdk.connect();
}
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

