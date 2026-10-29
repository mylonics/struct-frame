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

Includes ASIO for UDP, TCP and Serial transports. (There is no WebSocket transport in the C++ SDK; use the Python, TypeScript, JavaScript or C# SDK for WebSocket.)

### Embedded SDK (no external dependencies)

```bash
python -m struct_frame messages.proto --build_cpp --cpp_path generated/ --sdk_embedded
```

Minimal footprint for embedded systems. Serial transport only.

## Observer Pattern

Subscribe to messages using function pointers or lambdas:

```cpp no-compile
#include "struct_frame_sdk/sdk_embedded.hpp"
#include "messages.structframe.hpp"

void handle_status(const StatusMessage& msg, uint16_t msgId) {
    std::cout << "Status: " << msg.value << std::endl;
}

int main() {
    // Create SDK with transport and message-info callback.
    // The only template argument is the frame profile config.
    structframe::sdk::StructFrameSdkT<structframe::ProfileStandardConfig>
        sdk(&my_transport, &get_message_info);

    // Subscribe to messages by message ID. subscribe() returns a [[nodiscard]]
    // handle that unsubscribes when destroyed, so keep it alive for as long as
    // you want to receive messages.
    auto status_subscription = sdk.subscribe<StatusMessage>(StatusMessage::MSG_ID, handle_status);

    // Connect the transport (incoming data is handled via callbacks)
    sdk.Connect();
}
```

## FrameMsgInfo Subscription And Forwarding

You can subscribe to every complete parsed frame directly as `FrameMsgInfo`:

```cpp no-compile
structframe::sdk::StructFrameSdkT<structframe::ProfileStandardConfig>
    sdk(&transport, &get_message_info);

auto all_frames = sdk.subscribeFrameInfo(
    [](const structframe::FrameMsgInfo& frame) {
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

```cpp no-compile
structframe::sdk::StructFrameSdkT<structframe::ProfileStandardConfig>
    source_sdk(&transport_a, &get_message_info);

structframe::sdk::StructFrameSdkT<structframe::ProfileStandardConfig>
    target_sdk(&transport_b, &get_message_info);

auto forward = source_sdk.subscribeFrameInfo(
    [&](const structframe::FrameMsgInfo& frame) {
        target_sdk.SendDirect(frame);  // fastest: forwards original frame bytes
    });

// Encode once on source side and inject/send as needed
StatusMessage msg{};
msg.value = 42;

uint8_t wire[512];
size_t wire_len = structframe::FrameEncoderWithCrc<structframe::ProfileStandardConfig>::encode(
    wire, sizeof(wire), msg);

// Feed encoded bytes into source SDK parse path:
source_sdk.Feed(wire, wire_len);
```

Cross-profile bridge (re-encode on destination):

```cpp no-compile
auto forward_cross_profile = source_sdk.subscribeFrameInfo(
    [&](const structframe::FrameMsgInfo& frame) {
        target_sdk.Send(frame);  // profile-aware re-encode
    });
```

Use the same type for other profiles by changing only the config:

```cpp no-compile
structframe::sdk::StructFrameSdkT<structframe::ProfileSensorConfig>
    sensor_sdk(&transport, &get_message_info);

structframe::sdk::StructFrameSdkT<structframe::ProfileIPCConfig>
    ipc_sdk(&transport, &get_message_info);

structframe::sdk::StructFrameSdkT<structframe::ProfileBulkConfig>
    bulk_sdk(&transport, &get_message_info);
```

## Transports (Full SDK)

### Serial

```cpp no-compile
#include "struct_frame_sdk/serial_transport.hpp"

// SerialTransport requires a platform-specific ISerialPort implementation.
// Provide your own class that implements the ISerialPort interface
// (open, close, write, read, is_open methods).
structframe::sdk::SerialTransportConfig config;
structframe::sdk::SerialTransport serial(&my_serial_port, config);
serial.Connect();
```

### Network (UDP, TCP)

```cpp no-compile
#include "struct_frame_sdk/network_transports.hpp"

// UDP
structframe::sdk::UdpTransportConfig udp_config{.remoteHost = "192.168.1.100", .remotePort = 8080};
structframe::sdk::UdpTransport udp(udp_config);
udp.Connect();

// TCP
structframe::sdk::TcpTransportConfig tcp_config{.host = "192.168.1.100", .port = 8080};
structframe::sdk::TcpTransport tcp(tcp_config);
tcp.Connect();
```

## Frame Profiles

Use predefined frame profiles:

```cpp no-compile
#include "frame_profiles.hpp"

using namespace structframe;

// Standard profile (recommended)
uint8_t buffer[1024];
ProfileStandardWriter writer(buffer, sizeof(buffer));
ProfileStandardAccumulatingReader reader;

// Sensor profile (minimal overhead)
ProfileSensorWriter sensor_writer(buffer, sizeof(buffer));
ProfileSensorAccumulatingReader sensor_reader(get_message_info);
```

### Contiguous buffer overloads

The C++ APIs retain their pointer-and-length overloads and also accept any
contiguous buffer exposing `data()` and `size()`. This includes
`std::array`, `std::span`, `etl::array`, and `etl::span` when those libraries
are available:

```cpp no-compile
#include <array>
#include <span>

std::array<uint8_t, 1024> storage{};
auto encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(storage, msg);

std::span<const uint8_t> frame(storage.data(), encoded);
auto parsed = BufferParserWithCrc<ProfileStandardConfig>::parse(frame, get_message_info);

BasicTypesMessage decoded{};
decoded.deserialize(frame.subspan(parsed.msg_data - frame.data(), parsed.msg_len));

ProfileStandardWriter writer(storage);
writer.write(msg);
ProfileStandardReader reader(frame, get_message_info);
```

The same overloads are available on generated message `serialize`/`deserialize`,
`BufferWriter`, `BufferReader`, `AccumulatingReader::add_data`, frame checksum
helpers, SDK `Feed`/`SendRaw`, and transport `Send`. These overloads do not
allocate or change the existing raw-pointer APIs, so ETL containers and views
can be used without conversions.

See [Framing Details](/basic-usage/framing-details/) for more profiles.
