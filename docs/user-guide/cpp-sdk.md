# C++ SDK

The C++ SDK is a header-only library that provides structured message communication with an observer/subscriber pattern for message handling.

## Features

- **Header-only**: No linking required, just include headers
- **Zero dependencies in embedded mode**: Core SDK has no external dependencies when using `--sdk_embedded`
- **Observer pattern**: Type-safe message subscription using function pointers (no `std::function`, no `std::vector`)
- **Embedded-friendly**: Generic serial interface for bare-metal systems
- **Cross-platform**: Works on Windows, macOS, and Linux
- **Network support**: UDP, TCP, WebSocket via ASIO (included with `--sdk` flag)

## Installation

### Full SDK (with network transports)

Generate C++ code with full SDK including ASIO:

```bash
python -m struct_frame your_messages.proto --build_cpp --cpp_path generated/cpp --sdk
```

This includes:
- ASIO standalone headers (v1.30.2)
- UDP, TCP, Serial transports using ASIO
- Network transports implementation
- All SDK features

### Embedded SDK (serial only, no dependencies)

For embedded/bare-metal systems, use the minimal SDK:

```bash
python -m struct_frame your_messages.proto --build_cpp --cpp_path generated/cpp --sdk_embedded
```

This includes:
- Observer pattern with function pointers (no STL dependencies)
- Generic serial transport interface
- No ASIO headers
- Minimal footprint

### Without SDK (default)

Generate only message serialization code:

```bash
python -m struct_frame your_messages.proto --build_cpp --cpp_path generated/cpp
```

## Including the SDK

For full SDK:
```cpp
#include "struct_frame_sdk/sdk.hpp"
```

For embedded SDK:
```cpp
#include "struct_frame_sdk/sdk_embedded.hpp"
```

## Observer/Subscriber Pattern

The C++ SDK uses an observer pattern for handling messages, providing type-safe subscriptions without dynamic allocation overhead.

### Basic Observer

```cpp
#include "struct_frame_sdk/observer.hpp"
#include "my_messages.hpp"

using namespace StructFrame;

class StatusObserver : public IObserver<StatusMessage> {
public:
    void onMessage(const StatusMessage& message, uint8_t msgId) override {
        // Handle message
        std::cout << "Temperature: " << message.temperature << std::endl;
    }
};

// Usage
StatusObserver observer;
auto* observable = sdk.getObservable<StatusMessage>(StatusMessage::msg_id);
observable->subscribe(&observer);
```

### Function Pointer Observer (Embedded)

For embedded systems without STL dependencies, use function pointer observers:

```cpp
#include "struct_frame_sdk/observer.hpp"
#include "my_messages.hpp"

using namespace StructFrame;

// Define handler function
void onStatusMessage(const StatusMessage& message, uint8_t msgId) {
    // Handle message
}

// Usage with function pointer
auto* observer = new FunctionObserver<StatusMessage>(onStatusMessage);
auto* observable = sdk.getObservable<StatusMessage>(StatusMessage::msg_id);
observable->subscribe(observer);
```

### RAII Subscription

The `Subscription<T>` class provides automatic unsubscription:

```cpp
{
    auto subscription = sdk.subscribe<StatusMessage>(
        StatusMessage::msg_id,
        [](const StatusMessage& msg, uint8_t msgId) {
            // Handle message
        }
    );
    
    // subscription automatically unsubscribes when it goes out of scope
}
```

## Frame Parsing API

The C++ SDK provides two parsing APIs to suit different performance requirements:

### Byte-by-Byte Parsing (Traditional)

The byte-by-byte API processes one byte at a time, maintaining parser state across calls. This is suitable for streaming data from serial ports or network sockets.

```cpp
#include "frame_parsers.hpp"

using namespace FrameParsers;

// Create parser with internal buffer (using profile alias)
uint8_t buffer[512];
ProfileStandard parser(buffer, sizeof(buffer));  // Profile.STANDARD

// Parse incoming bytes one at a time
void onSerialByte(uint8_t byte) {
    FrameMsgInfo result = parser.parse_byte(byte);
    
    if (result.valid) {
        // Complete frame received
        process_message(result.msg_id, result.msg_data, result.msg_len);
    }
}
```

### Buffer Parsing (High Performance)

The buffer parsing API scans entire byte buffers efficiently, ideal for batch processing or ring buffer scenarios. This eliminates byte-by-byte state machine overhead.

**Key Benefits:**
- **Zero-copy**: Returns pointer into original buffer (no intermediate copies)
- **Fast**: Scans memory directly instead of processing byte-by-byte
- **Ring buffer support**: Works seamlessly with circular buffers
- **No std library**: Pure C++, no std::span or std::string_view needed

```cpp
#include "frame_parsers.hpp"

using namespace FrameParsers;

// Create parser (using profile alias)
uint8_t internal_buffer[512];
ProfileStandard parser(internal_buffer, sizeof(internal_buffer));  // Profile.STANDARD

// Parse from DMA buffer or ring buffer
void processBuffer(const uint8_t* data, size_t length) {
    size_t consumed = 0;
    
    // Scan buffer for frames
    FrameMsgInfo result = parser.parse_buffer(data, length, &consumed);
    
    if (result.valid) {
        // result.msg_data points directly into 'data' buffer (zero-copy!)
        // Process immediately or copy if needed for async
        process_message(result.msg_id, result.msg_data, result.msg_len);
        
        // Advance buffer pointer
        data += consumed;
        length -= consumed;
    } else if (consumed > 0) {
        // Skipped junk bytes, keep trying
        data += consumed;
        length -= consumed;
    } else {
        // Not enough data for complete frame, wait for more
    }
}
```

### Ring Buffer Example

The buffer API works great with ring buffers from UART/SPI peripherals:

```cpp
class RingBufferParser {
private:
    ProfileStandard parser_;  // Profile.STANDARD
    uint8_t internal_buffer_[512];
    
public:
    RingBufferParser() : parser_(internal_buffer_, sizeof(internal_buffer_)) {}
    
    void processRingBuffer(const uint8_t* ring_start, size_t available) {
        size_t consumed = 0;
        
        while (available > 0) {
            FrameMsgInfo result = parser_.parse_buffer(ring_start, available, &consumed);
            
            if (result.valid) {
                // Message found - handle it
                // result.msg_data points into ring buffer (zero-copy)
                handleMessage(result.msg_id, result.msg_data, result.msg_len);
                
                // Advance ring buffer
                ring_start += consumed;
                available -= consumed;
            } else if (consumed > 0) {
                // Skipped junk bytes
                ring_start += consumed;
                available -= consumed;
            } else {
                // Incomplete frame, wait for more data
                break;
            }
        }
    }
};
```

### When to Use Each API

**Use `parse_buffer()`** when:
- Processing data in batches (DMA, network packets)
- High throughput is required
- Working with ring buffers
- Zero-copy operation is beneficial

**Use `parse_byte()`** when:
- Processing streaming data byte-by-byte
- Low latency is more important than throughput
- Integration with existing byte-oriented code

### Profile-Specific Parsers

All parsers are profile-specific (optimized for a single frame format):

```cpp
// Profile aliases for convenience
using ProfileStandard = BasicDefaultParser;  // General Serial/UART
using ProfileSensor = TinyMinimalParser;     // Low-Bandwidth/Radio
using ProfileBulk = BasicExtendedParser;     // Firmware/File Transfer
using ProfileNetwork = BasicExtendedMultiSystemStreamParser;  // Multi-Node Mesh

// Use the profile that matches your application
ProfileStandard parser(buffer, sizeof(buffer));
```

For more details on parsers and performance, see the [Parser Feature Matrix](parser-feature-matrix.md).

### Parsing Minimal Frames

Minimal frames (`TinyMinimalParser`, `BasicMinimalParser`, `NoneMinimalParser`) don't include a length field or CRC. To parse them, you must provide a callback function that returns the expected message length for each message ID:

**Note**: The exact API depends on the generated parser code. This example shows the general pattern.

```cpp
#include "frame_parsers.hpp"

using namespace FrameParsers;

// Define message size lookup callback
bool get_msg_length(uint8_t msg_id, size_t* length) {
    switch (msg_id) {
        case 1: *length = 10; return true;  // Status message is 10 bytes
        case 2: *length = 20; return true;  // Command message is 20 bytes
        case 3: *length = 5;  return true;  // Sensor reading is 5 bytes
        default: return false;
    }
}

// Create parser with callback
// The actual constructor signature depends on generated code
uint8_t buffer[256];
TinyMinimalParser parser(buffer, sizeof(buffer), get_msg_length);

// Parse incoming bytes
for (uint8_t byte : incoming_data) {
    FrameMsgInfo result = parser.parse_byte(byte);
    if (result.valid) {
        printf("Received msg_id=%d, len=%zu\n", result.msg_id, result.msg_len);
        // Process result.msg_data (points into buffer - zero-copy!)
    }
}

// Encode a minimal frame
uint8_t msg_data[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
uint8_t output[256];
size_t frame_len = parser.encode(1, msg_data, 10, output, sizeof(output));
// Result: [0x70] [0x01] [0x01 0x02 ... 0x0A]
```

**Why use minimal frames?**
- ✅ Minimal overhead: 1-3 bytes total
- ✅ Fast: No CRC calculation/validation
- ✅ Perfect for fixed-size messages on trusted links
- ❌ No error detection
- ❌ Requires message size lookup

See the [Minimal Frames Guide](minimal-frames.md) for complete examples and best practices.

## Recommended Encoding/Decoding Patterns

**The patterns shown in this section are the recommended way to encode and decode messages, as demonstrated in the test suite (`tests/cpp/test_codec.cpp`).** These high-level APIs handle common use cases efficiently and are the gold standard for library usage.

### BufferWriter - Encode Multiple Frames

`BufferWriter` encodes multiple frames into a buffer with automatic offset tracking. This is the recommended way to encode messages.

```cpp
#include "FrameProfiles.hpp"
#include "my_messages.sf.hpp"

// Create a BufferWriter for your chosen profile
uint8_t buffer[2048];
ProfileStandardWriter writer(buffer, sizeof(buffer));

// Encode multiple messages - writer tracks offset automatically
StatusMessage status{};
status.temperature = 25.5f;
status.battery = 95;

size_t bytes_written = writer.write(status);
if (bytes_written == 0) {
    // Buffer full or encoding error
}

CommandMessage cmd{};
cmd.action = 1;
cmd.value = 42;

bytes_written = writer.write(cmd);
if (bytes_written == 0) {
    // Buffer full or encoding error
}

// Get total encoded size
size_t total_size = writer.size();

// Get pointer to encoded data
const uint8_t* encoded_data = buffer;

// Send encoded_data over your transport (UART, TCP, etc.)
serial_send(encoded_data, total_size);
```

**Available Profile Writers:**
- `ProfileStandardWriter` - Basic header + Default payload (general purpose, CRC protected)
- `ProfileSensorWriter` - Tiny header + Minimal payload (low bandwidth, no CRC)
- `ProfileIPCWriter` - No header + Minimal payload (trusted IPC, minimal overhead)
- `ProfileBulkWriter` - Basic header + Extended payload (file transfers, includes package ID)
- `ProfileNetworkWriter` - Basic header + Extended Multi-System Stream (networked systems)

### BufferReader - Parse Multiple Frames from a Buffer

`BufferReader` iterates through a buffer containing one or more frames, automatically tracking the offset:

```cpp
#include "FrameProfiles.hpp"

// Received data from transport
uint8_t recv_buffer[2048];
size_t recv_size = serial_receive(recv_buffer, sizeof(recv_buffer));

// Create a BufferReader for your chosen profile
ProfileStandardReader reader(recv_buffer, recv_size);

// Parse all messages in the buffer
while (reader.has_more()) {
    auto result = reader.next();
    
    if (!result.valid) {
        // No more valid frames
        break;
    }
    
    // Process the message based on msg_id
    switch (result.msg_id) {
        case StatusMessage::MSG_ID: {
            auto* msg = reinterpret_cast<const StatusMessage*>(result.msg_data);
            process_status(*msg);
            break;
        }
        case CommandMessage::MSG_ID: {
            auto* msg = reinterpret_cast<const CommandMessage*>(result.msg_data);
            process_command(*msg);
            break;
        }
        default:
            // Unknown message type
            break;
    }
}
```

**Available Profile Readers:**
- `ProfileStandardReader` - Basic + Default (general purpose)
- `ProfileSensorReader` - Tiny + Minimal (requires `get_message_length` callback)
- `ProfileIPCReader` - None + Minimal (requires `get_message_length` callback)
- `ProfileBulkReader` - Basic + Extended
- `ProfileNetworkReader` - Basic + Extended Multi-System Stream

### AccumulatingReader - Unified Buffer and Streaming Parser

`AccumulatingReader` is the **recommended parser for production use**. It handles both buffer mode (processing chunks) and streaming mode (byte-by-byte), with automatic handling of partial messages across buffer boundaries.

**Buffer Mode** - Processing chunks of data:

```cpp
#include "FrameProfiles.hpp"

// Create reader with internal buffer (default 1024 bytes)
AccumulatingReader<ProfileStandardConfig> reader;

// Process incoming chunks (e.g., from network or DMA)
void on_data_received(const uint8_t* chunk, size_t size) {
    reader.add_data(chunk, size);
    
    // Extract all complete messages
    while (auto result = reader.next()) {
        if (!result.valid) {
            break;
        }
        process_message(result.msg_id, result.msg_data, result.msg_len);
    }
    
    // Partial message state is automatically preserved
    // Next call to add_data() will continue where we left off
}
```

**Stream Mode** - Byte-by-byte processing (UART/serial):

```cpp
#include "FrameProfiles.hpp"

// Create reader with internal buffer
AccumulatingReader<ProfileStandardConfig> reader;

// Process incoming bytes one at a time
void on_serial_byte(uint8_t byte) {
    if (auto result = reader.push_byte(byte)) {
        // Complete message received
        process_message(result.msg_id, result.msg_data, result.msg_len);
    }
}
```

**Using with Minimal Profiles** (requires message length callback):

```cpp
#include "FrameProfiles.hpp"
#include "my_messages.sf.hpp"

// For minimal profiles, provide get_message_length callback
AccumulatingReader<ProfileSensorConfig> reader(get_message_length);

// Use add_data() or push_byte() as shown above
void on_data_received(const uint8_t* chunk, size_t size) {
    reader.add_data(chunk, size);
    while (auto result = reader.next()) {
        if (!result.valid) break;
        process_message(result.msg_id, result.msg_data, result.msg_len);
    }
}
```

**Key Features of AccumulatingReader:**
- **Stack-allocated internal buffer** (configurable size via template parameter)
- **State machine tracks parsing progress** - avoids re-parsing on partial messages
- **Handles partial messages** across buffer boundaries automatically
- **Works in both buffer and streaming modes** with the same API

**Available Profile AccumulatingReaders:**
- `AccumulatingReader<ProfileStandardConfig>` - Basic + Default
- `AccumulatingReader<ProfileSensorConfig>` - Tiny + Minimal (requires callback)
- `AccumulatingReader<ProfileIPCConfig>` - None + Minimal (requires callback)
- `AccumulatingReader<ProfileBulkConfig>` - Basic + Extended
- `AccumulatingReader<ProfileNetworkConfig>` - Basic + Extended Multi-System Stream

**See the test suite for complete examples:** The file `tests/cpp/test_codec.cpp` demonstrates production-ready usage of these APIs, including handling of mixed message types, partial message scenarios, and validation patterns.

## Transport Layers

### Generic Serial Transport (Embedded Systems)

The generic serial interface allows you to implement platform-specific serial I/O:

```cpp
#include "struct_frame_sdk/serial_transport.hpp"

// Implement for your platform
class STM32SerialPort : public StructFrame::ISerialPort {
private:
    UART_HandleTypeDef* huart_;
    
public:
    STM32SerialPort(UART_HandleTypeDef* huart) : huart_(huart) {}
    
    bool open() override {
        // Already initialized in HAL_UART_MspInit
        return true;
    }
    
    void close() override {
        // Optionally deinitialize
    }
    
    size_t write(const uint8_t* data, size_t length) override {
        HAL_StatusTypeDef status = HAL_UART_Transmit(
            huart_, 
            const_cast<uint8_t*>(data), 
            length, 
            HAL_MAX_DELAY
        );
        return (status == HAL_OK) ? length : 0;
    }
    
    size_t read(uint8_t* buffer, size_t maxLength) override {
        // Non-blocking read
        size_t available = __HAL_UART_GET_FLAG(huart_, UART_FLAG_RXNE) ? 1 : 0;
        if (available > 0 && maxLength > 0) {
            HAL_UART_Receive(huart_, buffer, 1, 0);
            return 1;
        }
        return 0;
    }
    
    bool isOpen() const override {
        return true;
    }
    
    size_t available() const override {
        return __HAL_UART_GET_FLAG(huart_, UART_FLAG_RXNE) ? 1 : 0;
    }
};

// Usage
STM32SerialPort serialPort(&huart1);
StructFrame::SerialTransport transport(&serialPort);
```

### Poll-Based Operation (Embedded)

For embedded systems without threading, use poll-based message handling:

```cpp
#include "struct_frame_sdk/struct_frame_sdk.hpp"
#include "BasicDefault.hpp"
#include "my_messages.hpp"

using namespace StructFrame;

int main() {
    // Setup
    STM32SerialPort serialPort(&huart1);
    SerialTransport transport(&serialPort);
    BasicDefault frameParser;
    
    StructFrameSdk sdk({
        .transport = &transport,
        .frameParser = &frameParser,
        .debug = false,
    });
    
    // Subscribe to messages
    auto sub = sdk.subscribe<StatusMessage>(
        StatusMessage::msg_id,
        [](const StatusMessage& msg, uint8_t id) {
            // Handle status
        }
    );
    
    sdk.connect();
    
    // Main loop
    while (1) {
        // Poll for incoming data
        transport.poll();
        
        // Your other application logic
        HAL_Delay(1);
    }
}
```

## Network Transports (ASIO)

For desktop/server applications, network transports use ASIO. These require external libraries.

### UDP Transport (with ASIO)

```cpp
// Requires: ASIO standalone or Boost.Asio
// Not included in generated code - implement based on network_transports.hpp

#include <asio.hpp>
#include "struct_frame_sdk/transport.hpp"

class UdpTransport : public StructFrame::BaseTransport {
private:
    asio::io_context io_context_;
    asio::ip::udp::socket socket_;
    asio::ip::udp::endpoint remote_endpoint_;
    
public:
    UdpTransport(const std::string& host, uint16_t port)
        : socket_(io_context_, asio::ip::udp::endpoint(asio::ip::udp::v4(), 0)) {
        remote_endpoint_ = asio::ip::udp::endpoint(
            asio::ip::address::from_string(host), port);
    }
    
    void connect() override {
        connected_ = true;
        startReceive();
    }
    
    void send(const uint8_t* data, size_t length) override {
        socket_.send_to(asio::buffer(data, length), remote_endpoint_);
    }
    
    // ... implement startReceive() with async operations
};
```

### TCP Transport (with ASIO)

See `network_transports.hpp` for implementation guidelines.

### WebSocket Transport (with Simple-WebSocket-Server)

```cpp
// Requires: Simple-WebSocket-Server and ASIO
#include "client_ws.hpp"

using WsClient = SimpleWeb::SocketClient<SimpleWeb::WS>;

class WebSocketTransport : public StructFrame::BaseTransport {
    // Implement based on Simple-WebSocket-Server documentation
};
```

## Complete Example

```cpp
#include "struct_frame_sdk/sdk.hpp"
#include "BasicDefault.hpp"
#include "robot_messages.hpp"

using namespace StructFrame;
using namespace RobotMessages;

int main() {
    // Platform-specific serial port
    MySerialPort serialPort("/dev/ttyUSB0", 115200);
    SerialTransport transport(&serialPort);
    
    // Frame parser
    BasicDefault frameParser;
    
    // Create SDK
    StructFrameSdk sdk({
        .transport = &transport,
        .frameParser = &frameParser,
        .debug = true,
        .maxBufferSize = 8192,
    });
    
    // Subscribe to status messages
    auto statusSub = sdk.subscribe<StatusMessage>(
        StatusMessage::msg_id,
        [](const StatusMessage& msg, uint8_t msgId) {
            std::cout << "Temp: " << msg.temperature << "°C" << std::endl;
            std::cout << "Battery: " << msg.battery << "%" << std::endl;
        }
    );
    
    // Subscribe to telemetry
    auto telemetrySub = sdk.subscribe<TelemetryMessage>(
        TelemetryMessage::msg_id,
        [](const TelemetryMessage& msg, uint8_t msgId) {
            std::cout << "Position: (" << msg.x << ", " << msg.y << ")" << std::endl;
        }
    );
    
    // Connect
    sdk.connect();
    
    // Send command
    CommandMessage cmd;
    cmd.command = Command::MOVE_FORWARD;
    cmd.speed = 50;
    
    std::vector<uint8_t> packed(cmd.msg_size);
    cmd.pack(packed.data());
    sdk.sendRaw(CommandMessage::msg_id, packed.data(), packed.size());
    
    // Main loop (embedded systems)
    while (true) {
        transport.poll();
        
        // ... other application logic
    }
    
    return 0;
}
```

## Memory Considerations

The C++ SDK is designed for resource-constrained systems:

- **No dynamic allocation in message handling**: Observer pattern uses vectors allocated at initialization
- **Configurable buffer size**: Set `maxBufferSize` based on your requirements
- **Header-only**: No linking overhead
- **Small footprint**: Core SDK is ~10KB compiled

```cpp
// Configure buffer size for your application
StructFrameSdk sdk({
    .transport = &transport,
    .frameParser = &frameParser,
    .maxBufferSize = 1024,  // Smaller buffer for constrained systems
});
```

## Platform Support

The SDK works on:

- **Embedded**: ARM Cortex-M, AVR, ESP32, etc.
- **Desktop**: Linux, Windows, macOS
- **Real-time OS**: FreeRTOS, Zephyr, etc.
- **Bare-metal**: Any platform with C++14 support

## Dependencies

### Core SDK
- C++14 or later
- No external dependencies

### Network Transports (Optional)
- **UDP/TCP**: ASIO standalone or Boost.Asio
- **WebSocket**: Simple-WebSocket-Server (requires ASIO)
- **Serial (ASIO)**: ASIO standalone or Boost.Asio

```bash
# Install ASIO (standalone, header-only)
wget https://github.com/chriskohlhoff/asio/archive/asio-1-28-0.tar.gz
tar xzf asio-1-28-0.tar.gz
cp -r asio-asio-1-28-0/asio/include/asio* /usr/local/include/

# Or use package manager
# Ubuntu/Debian:
sudo apt-get install libasio-dev

# macOS:
brew install asio
```

## Compiler Flags

```bash
# Minimum flags
g++ -std=c++14 main.cpp -o app

# With ASIO
g++ -std=c++14 -DASIO_STANDALONE main.cpp -o app -lpthread

# Optimized for embedded
arm-none-eabi-g++ -std=c++14 -Os -fno-exceptions -fno-rtti main.cpp -o app.elf
```

## Best Practices

1. **Use RAII**: Let `Subscription<T>` handle unsubscription automatically
2. **Minimize copies**: Pass messages by const reference in observers
3. **Poll regularly**: Call `transport.poll()` frequently in main loop for embedded systems
4. **Buffer management**: Size buffer appropriately for your message sizes
5. **Error handling**: Check connection status and handle errors in callbacks

## Example Platform Implementations

### Arduino/ESP32

```cpp
#include <HardwareSerial.h>
#include "struct_frame_sdk/serial_transport.hpp"

class ArduinoSerialPort : public StructFrame::ISerialPort {
private:
    HardwareSerial* serial_;
    
public:
    ArduinoSerialPort(HardwareSerial* serial) : serial_(serial) {}
    
    bool open() override {
        // Already opened in setup()
        return true;
    }
    
    size_t write(const uint8_t* data, size_t length) override {
        return serial_->write(data, length);
    }
    
    size_t read(uint8_t* buffer, size_t maxLength) override {
        return serial_->readBytes(buffer, maxLength);
    }
    
    size_t available() const override {
        return serial_->available();
    }
};

void setup() {
    Serial.begin(115200);
    ArduinoSerialPort port(&Serial);
    // ... setup SDK
}

void loop() {
    transport.poll();
    delay(1);
}
```

### Linux

```cpp
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>

class LinuxSerialPort : public StructFrame::ISerialPort {
    // Implement using POSIX serial I/O
    // See termios documentation
};
```
