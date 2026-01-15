# C++ SDK

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

Subscribe to messages using function pointers:

```cpp
#include "struct_frame_sdk/sdk_embedded.hpp"
#include "messages.sf.hpp"

void handle_status(const StatusMessage& msg, uint8_t msgId) {
    std::cout << "Status: " << msg.value << std::endl;
}

int main() {
    // Create SDK
    StructFrame::SDK sdk;
    
    // Subscribe to messages
    sdk.subscribe<StatusMessage>(handle_status);
    
    // Process incoming data
    sdk.process_byte(byte);
}
```

## Transports (Full SDK)

### Serial

```cpp
#include "struct_frame_sdk/transports/serial.hpp"

StructFrame::SerialTransport serial("/dev/ttyUSB0", 115200);
serial.connect();
serial.send(message_id, data, size);
```

### UDP

```cpp
#include "struct_frame_sdk/transports/udp.hpp"

StructFrame::UDPTransport udp("192.168.1.100", 8080);
udp.connect();
udp.send(message_id, data, size);
```

### TCP

```cpp
#include "struct_frame_sdk/transports/tcp.hpp"

StructFrame::TCPTransport tcp("192.168.1.100", 8080);
tcp.connect();
tcp.send(message_id, data, size);
```

## Frame Profiles

Use predefined frame profiles:

```cpp
#include "FrameProfiles.hpp"

using namespace FrameParsers;

// Standard profile (recommended)
uint8_t buffer[1024];
ProfileStandardWriter writer(buffer, sizeof(buffer));
ProfileStandardAccumulatingReader reader;

// Sensor profile (minimal overhead)
ProfileSensorWriter sensor_writer(buffer, sizeof(buffer));
ProfileSensorAccumulatingReader sensor_reader(get_message_info);
```

See [Framing Details](../basic-usage/framing-details.md) for more profiles.

