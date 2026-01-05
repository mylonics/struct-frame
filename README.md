
# Struct Frame

A multi-language code generation framework that converts Protocol Buffer (.proto) files into serialization/deserialization code for C, C++, TypeScript, Python, and GraphQL. It provides framing and parsing utilities for structured message communication.

## Installation

Install from PyPI:

```bash
pip install struct-frame
```

**Note:** The package is named `struct-frame` (with hyphen) on PyPI, but the Python module uses an underscore: `struct_frame`. Use `python -m struct_frame` to run the code generator.

## Quick Start

### Basic Usage
```bash
# Generate code for Python
python -m struct_frame examples/robot.proto --build_py --py_path generated/py

# Generate code for multiple languages
python -m struct_frame examples/robot.proto --build_c --build_cpp --build_ts --build_py

# Get help
python -m struct_frame --help
```

### For Contributors

If you want to contribute or modify the code generator itself, see the [Development Guide](docs/reference/development.md) for instructions on cloning the repository and setting up a development environment.

### Test Suite

The project includes a test suite that validates code generation, compilation, and serialization across all supported languages:

```bash
# Run all tests
python test_all.py

# Run with verbose output
python tests/run_tests.py --verbose

# Skip specific languages
python tests/run_tests.py --skip-ts --skip-c --skip-cpp

# Generate code only (no compilation/execution)
python tests/run_tests.py --generate-only
```

See `tests/README.md` for detailed test documentation.

### Continuous Integration

The project uses GitHub Actions to automatically run the full test suite on:
- Every push to the `main` branch
- Every pull request targeting the `main` branch

The CI pipeline:
1. Sets up Python 3.11 and Node.js 20
2. Installs system dependencies (GCC, G++)
3. Installs Python dependencies (proto-schema-parser)
4. Installs Node.js dependencies
5. Runs the complete test suite (`python test_all.py`)
6. Uploads test artifacts for debugging

You can view test results in the "Actions" tab of the GitHub repository. Test artifacts (generated code and binary files) are available for download for 5 days after each run.

## Higher-Level SDK

Struct Frame provides high-level SDKs for simplified message communication:

- **TypeScript/JavaScript**: Promise-based with UDP, TCP, WebSocket, and Serial transports
- **Python**: Both sync and async implementations with socket, pyserial, websockets support
- **C++**: Header-only with observer/subscriber pattern, ideal for embedded systems
- **C#**: Async/await-based for .NET Core, Xamarin, and MAUI applications

See the [SDK Overview](https://struct-frame.mylonics.com/user-guide/sdk-overview/) for details.

## Framing System

Struct Frame provides a message framing system for reliable communication over serial links, network sockets, or any byte stream. Framing solves the fundamental problem of determining where messages begin and end in a continuous data stream.

### What is Message Framing?

When sending structured data over a communication channel, you need to:
1. **Identify message boundaries** - Where does one message end and the next begin?
2. **Validate message integrity** - Is the received data complete and uncorrupted?
3. **Route messages by type** - What kind of message is this and how should it be processed?

Struct Frame's framing system addresses these challenges with a cross-platform implementation.

### Framing Architecture

The framing system uses a two-level architecture:

1. **Frame Type** (Framer): Determines the number of start bytes for synchronization
   - **Basic**: 2 start bytes `[0x90] [0x70+PayloadType]`
   - **Tiny**: 1 start byte `[0x70+PayloadType]`
   - **None**: 0 start bytes (relies on external synchronization)

2. **Payload Type**: Defines the header/footer structure after start bytes
   - Minimal, Default, ExtendedMsgIds, ExtendedLength, Extended
   - SysComp, Seq, MultiSystemStream, ExtendedMultiSystemStream

### Basic Default Frame Format (Recommended)

The recommended frame format uses a simple but effective structure:

```
[Start1=0x90] [Start2=0x71] [Length] [Message ID] [Payload Data...] [CRC1] [CRC2]
```

**Frame Components:**
- **Start Bytes (0x90, 0x71)**: Synchronization markers to identify frame boundaries
- **Length**: Payload length (1 byte, up to 255 bytes)
- **Message ID**: Unique identifier (0-255) that maps to specific message types  
- **Payload**: The actual serialized message data (variable length)
- **Fletcher Checksum**: 2-byte error detection using Fletcher-16 algorithm

**Example Frame Breakdown:**
```
Message: vehicle_heartbeat (ID=42) with 4 bytes of data [0x01, 0x02, 0x03, 0x04]
Frame:   [0x90] [0x71] [0x04] [0x2A] [0x01, 0x02, 0x03, 0x04] [0x7F] [0x8A]
          Start1 Start2  Len   ID=42        Payload Data         Checksum
```

### Available Payload Types

| Payload Type | Structure | Overhead | Use Case |
|--------------|-----------|----------|----------|
| Minimal | `[MSG_ID] [PACKET]` | 1 | Fixed-size messages, trusted environments |
| Default | `[LEN] [MSG_ID] [PACKET] [CRC]` | 4 | Standard format (recommended) |
| ExtendedMsgIds | `[PKG_ID] [LEN] [MSG_ID] [PACKET] [CRC]` | 5 | Large systems with many message types |
| ExtendedLength | `[LEN16] [MSG_ID] [PACKET] [CRC]` | 5 | Large payloads (up to 64KB) |
| SysComp | `[SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC]` | 6 | Multi-vehicle networks |
| Seq | `[SEQ] [LEN] [MSG_ID] [PACKET] [CRC]` | 5 | Packet loss detection |
| MultiSystemStream | `[SEQ] [SYS] [COMP] [LEN] [MSG_ID] [PACKET] [CRC]` | 7 | Multi-vehicle streaming |

See [Framing Documentation](docs/framing.md) for the complete frame format reference.

### Parser State Machine

The frame parser implements a state machine to handle partial data and synchronization recovery:

```mermaid
stateDiagram-v2
    [*] --> LOOKING_FOR_START_BYTE
    LOOKING_FOR_START_BYTE --> GETTING_HEADER: Found 0x90
    GETTING_HEADER --> GETTING_PAYLOAD: Got Message ID
    GETTING_PAYLOAD --> LOOKING_FOR_START_BYTE: Complete Frame
    GETTING_HEADER --> LOOKING_FOR_START_BYTE: Invalid Message ID
    GETTING_PAYLOAD --> LOOKING_FOR_START_BYTE: Checksum Failure
```

**State Descriptions:**
- **LOOKING_FOR_START_BYTE**: Scanning for frame start marker (0x90)
- **GETTING_HEADER**: Processing message ID and calculating expected frame length
- **GETTING_PAYLOAD**: Collecting payload data and checksum bytes

This design handles common real-world issues like:
- **Partial frame reception** (data arrives in chunks)
- **Frame corruption** (invalid start bytes, checksum mismatches)
- **Synchronization loss** (automatic recovery when frames are corrupted)

### Language-Specific Examples

#### Python
```bash
python -m struct_frame examples/myl_vehicle.proto --build_py
# Use generated Python classes directly
```

#### TypeScript
```bash
python -m struct_frame examples/myl_vehicle.proto --build_ts
npx tsc examples/index.ts --outDir generated/
node generated/examples/index.js
```

#### C
```bash
python -m struct_frame examples/myl_vehicle.proto --build_c
gcc examples/main.c -I generated/c -o main
./main
```

#### C++
```bash
python -m struct_frame examples/myl_vehicle.proto --build_cpp
g++ -std=c++17 examples/main.cpp -I generated/cpp -o main
./main
```

#### GraphQL
```bash
python -m struct_frame examples/myl_vehicle.proto --build_gql
# Use generated .graphql schema files
```

## Feature Compatibility Matrix

| Feature | C | C++ | TypeScript | Python | C# | GraphQL | Status |
|---------|---|-----|------------|--------|----|---------|--------|
| **Core Types** | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | Stable |
| **String** | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | Stable |
| **Enums** | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | Stable |
| **Enum Classes** | N/A | ✓ | N/A | N/A | ✗ | N/A | Stable |
| **Nested Messages** | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | Stable |
| **Message IDs** | ✓ | ✓ | ✓ | ✓ | ✗ | N/A | Stable |
| **Message Serialization** | ✓ | ✓ | ✓ | ✓ | ✗ | N/A | Stable |
| **Flatten** | N/A | N/A | N/A | ✓ | ✗ | ✓ | Partial |
| **Arrays** | ✓ | ✓ | Partial | ✓ | ✗ | ✓ | Stable |

**Legend:**
- **✓** - Feature works as documented
- **Partial** - Basic functionality works, some limitations  
- **✗** - Feature not yet available
- **N/A** - Not applicable for this language

## Frame Format and Header Types

### Header Structure Details

The BasicDefault frame format (recommended) provides a robust framing protocol:

#### Header Layout (4 bytes)
```
Byte 0: Start Byte 1 (0x90)
  - Fixed synchronization marker
  - Allows parser to identify frame boundaries
  - Recovery point after frame corruption

Byte 1: Start Byte 2 (0x71 for Default payload type)
  - Second sync byte encodes payload type
  - 0x70 = Minimal, 0x71 = Default, 0x72 = ExtendedMsgIds, etc.
  - Allows different frame formats on same channel

Byte 2: Length (0x00-0xFF)
  - Payload length in bytes
  - Allows receiver to know frame size

Byte 3: Message ID (0x00-0xFF) 
  - Maps to specific message types in proto definitions
  - Used for routing and deserialization
  - Must match `option msgid = X` in proto message
```

#### Footer Layout (2 bytes)
```
Byte N+4: Fletcher Checksum Byte 1
Byte N+5: Fletcher Checksum Byte 2
  - Fletcher-16 checksum algorithm
  - Calculated over Length + Message ID + Payload
  - Provides error detection for corruption
```

### Frame Size Calculation

**Total Frame Size = Header + Payload + Footer**

For BasicDefault (recommended):
- **Header**: 4 bytes (2 start bytes + length + message ID)
- **Payload**: Variable (depends on message content)  
- **Footer**: 2 bytes (Fletcher checksum)

**Example Calculations:**
```proto
message SimpleHeartbeat {
  option msgid = 1;
  uint32 device_id = 1;    // 4 bytes
  bool alive = 2;          // 1 byte
}
// Total: 4 (header) + 5 (payload) + 2 (footer) = 11 bytes
```

### Framing Compatibility Matrix

| Feature | C | C++ | TypeScript | Python | C# | Status | Notes |
|---------|---|-----|------------|--------|----|---------|-------|
| **Frame Encoding** | ✓ | ✓ | ✓ | ✓ | ✗ | Stable | All languages can create frames |
| **Frame Parsing** | ✓ | ✓ | ✓ | ✓ | ✗ | Stable | State machine implementation |
| **Checksum Validation** | ✓ | ✓ | ✓ | ✓ | ✗ | Stable | Fletcher-16 algorithm |
| **Sync Recovery** | ✓ | ✓ | ✓ | ✓ | ✗ | Stable | Auto-recovery from corruption |
| **Partial Frame Handling** | ✓ | ✓ | ✓ | ✓ | ✗ | Stable | Handles chunked data streams |
| **Message ID Routing** | ✓ | ✓ | ✓ | ✓ | ✗ | Stable | Automatic message type detection |
| **Buffer Management** | ✓ | ✓ | ✓ | ✓ | ✗ | Stable | Fixed-size buffers prevent overflow |
| **Cross-Language Compatibility** | ✓ | ✓ | ✓ | ✓ | ✗ | Stable | Frames interoperate between languages |

### Extended Frame Format Options

Struct Frame supports multiple frame types and payload types for different use cases:

**Frame Types:**
- **Basic Frame**: 2 start bytes (0x90, 0x70+PayloadType) - Recommended for most applications
- **Tiny Frame**: 1 start byte (0x70+PayloadType) - Constrained environments
- **None Frame**: 0 start bytes - Trusted point-to-point links

**Payload Types:**
- **Default**: Length + Message ID + Payload + CRC - Recommended
- **Minimal**: Message ID + Payload only - Fixed-size messages
- **Extended**: Package ID + 2-byte length + Message ID + Payload + CRC - Large systems
- **SysComp**: System/Component IDs for multi-vehicle networks (MAVLink-style)
- **MultiSystemStream**: Sequence + SysComp for streaming with loss detection

See [Framing Documentation](docs/framing.md) for the complete format reference.

## Frame Format Examples and Usage

### Frame Breakdown Example

Let's trace through a message encoding and parsing example:

**Proto Definition:**
```proto
message VehicleStatus {
  option msgid = 42;
  uint32 vehicle_id = 1;
  float speed = 2;  
  bool engine_on = 3;
}
```

**Message Data:**
```
vehicle_id = 1234 (0x04D2)    -> [0xD2, 0x04, 0x00, 0x00] (little-endian)
speed = 65.5                  -> [0x00, 0x00, 0x83, 0x42] (IEEE 754 float)  
engine_on = true              -> [0x01]
Total payload: 9 bytes
```

**BasicDefault Frame Structure:**
```
Position: [0]  [1]  [2] [3] [4]  [5]  [6]  [7]  [8]  [9]  [10] [11] [12] [13] [14]
Data:      90   71   09  2A  D2   04   00   00   00   00   83   42   01   7E   C9
           │    │    │   │   └─────── Payload (9 bytes) ──────────────┘   │    │
           │    │    │   └─ Message ID (42 = 0x2A)                        │    │
           │    │    └─ Length (9 = 0x09)                                 │    │
           │    └─ Start Byte 2 (0x71 = Default payload type)             │    │
           └─ Start Byte 1 (0x90)                                         └────┘
                                                                        Checksum
```

**Checksum Calculation (Fletcher-16):**
```
Input: [0x09, 0x2A, 0xD2, 0x04, 0x00, 0x00, 0x00, 0x00, 0x83, 0x42, 0x01]
(calculated over length, message ID, and payload)
Result: [0x7E, 0xC9]
```

### Language-Specific Usage Examples

#### Python Frame Handling

```python
# Import generated classes  
from myl_vehicle_sf import VehicleStatus
from struct_frame_parser import FrameParser, BasicPacket

# Create message
msg = VehicleStatus()
msg.vehicle_id = 1234
msg.speed = 65.5  
msg.engine_on = True

# Encode to frame
packet = BasicPacket()
frame_bytes = packet.encode_msg(msg)
print(f"Frame: {[hex(b) for b in frame_bytes]}")

# Parse frame (simulate byte-by-byte reception)
parser = FrameParser({0x90: BasicPacket()}, {42: VehicleStatus})
for byte in frame_bytes:
    result = parser.parse_char(byte)
    if result:
        print(f"Parsed: vehicle_id={result.vehicle_id}, speed={result.speed}")
```

#### TypeScript Frame Handling

```typescript
import * as mv from './generated/ts/myl_vehicle.sf';
import { struct_frame_buffer, parse_char } from './generated/ts/struct_frame_parser';

// Create and encode message
let tx_buffer = new struct_frame_buffer(256);
let msg = new mv.VehicleStatus();
msg.vehicle_id = 1234;
msg.speed = 65.5;
msg.engine_on = true;
mv.VehicleStatus_encode(tx_buffer, msg);

// Parse frame  
let rx_buffer = new struct_frame_buffer(256);
for (let i = 0; i < tx_buffer.size; i++) {
  if (parse_char(rx_buffer, tx_buffer.data[i])) {
    let parsed = mv.VehicleStatus_decode(rx_buffer.msg_data);
    console.log(`Parsed: vehicle_id=${parsed.vehicle_id}, speed=${parsed.speed}`);
  }
}
```

#### C Frame Handling  

```c
#include "myl_vehicle.sf.h"
#include "struct_frame_parser.h"

// Create message
VehicleStatus msg = {0};
msg.vehicle_id = 1234;
msg.speed = 65.5f;
msg.engine_on = true;

// Encode to frame
uint8_t frame_buffer[256];
size_t frame_size = basic_frame_encode(frame_buffer, 42, (uint8_t*)&msg, sizeof(msg));

// Parse frame
packet_state_t parser = {0};
// ... initialize parser ...

for (size_t i = 0; i < frame_size; i++) {
  msg_info_t info = parse_char(&parser, frame_buffer[i]);
  if (info.valid) {
    VehicleStatus* parsed = (VehicleStatus*)info.msg_loc;
    printf("Parsed: vehicle_id=%d, speed=%.1f\n", parsed->vehicle_id, parsed->speed);
  }
}
```

#### C++ Frame Handling

```cpp
#include "myl_vehicle.sf.hpp"
#include "struct_frame.hpp"

// Create message
VehicleStatus msg{};
msg.vehicle_id = 1234;
msg.speed = 65.5f;
msg.engine_on = true;

// Encode to frame
uint8_t frame_buffer[256];
StructFrame::BasicPacket format;
StructFrame::EncodeBuffer encoder(frame_buffer, sizeof(frame_buffer));

bool success = encoder.encode(&format, VEHICLE_STATUS_MSG_ID, &msg, sizeof(msg));

// Parse frame using FrameParser
StructFrame::FrameParser parser(&format, [](size_t msg_id, size_t* size) {
    return StructFrame::get_message_length(msg_id, size);
});

for (size_t i = 0; i < encoder.size(); i++) {
    StructFrame::MessageInfo info = parser.parse_byte(frame_buffer[i]);
    if (info.valid) {
        VehicleStatus* parsed = reinterpret_cast<VehicleStatus*>(info.msg_location);
        std::cout << "Parsed: vehicle_id=" << parsed->vehicle_id 
                  << ", speed=" << parsed->speed << std::endl;
    }
}
```

### Real-World Integration Patterns

#### Serial Communication
```python
import serial
from struct_frame_parser import FrameParser

# Setup serial connection
ser = serial.Serial('/dev/ttyUSB0', 115200)
parser = FrameParser(packet_formats, message_definitions)

# Continuous parsing loop
while True:
    if ser.in_waiting:
        byte = ser.read(1)[0] 
        result = parser.parse_char(byte)
        if result:
            handle_message(result)
```

#### TCP Socket Communication  
```typescript
import * as net from 'net';
import { struct_frame_buffer, parse_char } from './struct_frame_parser';

const client = net.createConnection({port: 8080}, () => {
  console.log('Connected to server');
});

let rx_buffer = new struct_frame_buffer(1024);
client.on('data', (data: Buffer) => {
  for (let byte of data) {
    if (parse_char(rx_buffer, byte)) {
      // Process complete message
      handleMessage(rx_buffer.msg_data);
    }
  }
});
```

## Project Structure

- `src/struct_frame/` - Core code generation framework
  - `generate.py` - Main parser and validation logic
  - `*_gen.py` - Language-specific code generators
  - `boilerplate/` - Runtime libraries for each language
- `examples/` - Example .proto files and usage demos
  - `main.c` - C API demonstration (encoding/decoding, parsing)
  - `index.ts` - TypeScript API demonstration (similar functionality)  
  - `*.proto` - Protocol Buffer definitions for examples
- `generated/` - Output directory for generated code (git-ignored)

## Protocol Buffer Schema Reference

### Supported Data Types

| Type | Size (bytes) | Description | Range/Notes |
|------|--------------|-------------|-------------|
| **Integers** |
| `int8` | 1 | Signed 8-bit integer | -128 to 127 |
| `uint8` | 1 | Unsigned 8-bit integer | 0 to 255 |
| `int16` | 2 | Signed 16-bit integer | -32,768 to 32,767 |
| `uint16` | 2 | Unsigned 16-bit integer | 0 to 65,535 |
| `int32` | 4 | Signed 32-bit integer | -2.1B to 2.1B |
| `uint32` | 4 | Unsigned 32-bit integer | 0 to 4.3B |
| `int64` | 8 | Signed 64-bit integer | Large integers |
| `uint64` | 8 | Unsigned 64-bit integer | Large positive integers |
| **Floating Point** |
| `float` | 4 | Single precision (IEEE 754) | 7 decimal digits |
| `double` | 8 | Double precision (IEEE 754) | 15-17 decimal digits |
| **Other** |
| `bool` | 1 | Boolean value | `true` or `false` |
| `string` | Variable | UTF-8 encoded string | Length-prefixed |
| `EnumType` | 1 | Custom enumeration | Defined in .proto |
| `MessageType` | Variable | Nested message | User-defined structure |

> **Note:** All types use little-endian byte order for cross-platform compatibility.

### Array Support

Arrays (repeated fields) support all data types - primitives, enums, and messages across all target languages.

| Array Type | Syntax | Memory Usage | Use Case |
|------------|--------|--------------|----------|
| **Fixed** | `repeated type field = N [size=X];` | `sizeof(type) * X` | Matrices, buffers (always full) |  
| **Bounded** | `repeated type field = N [max_size=X];` | 1 byte (count) + `sizeof(type) * X` | Dynamic lists with limits |
| **String Arrays** | `repeated string field = N [max_size=X, element_size=Y];` | 1 byte (count) + `X * Y` bytes | Text collections with size limits |

```proto
message ArrayExample {
  repeated float matrix = 1 [size=9];                        // 3x3 matrix (always 9 elements)
  repeated string names = 2 [max_size=10, element_size=32];  // Up to 10 strings, each max 32 chars
  repeated int32 values = 3 [max_size=100];                  // Up to 100 integers (variable count)
}
```

**Generated Output** (all languages now supported):
- **Python**: `matrix: list[float]`, `names: list[str]`, `values: list[int]`
- **C**: `float matrix[9]`, `struct { uint8_t count; char data[10][32]; } names`
- **C++**: `float matrix[9]`, `struct { uint8_t count; char data[10][32]; } names` (with enum classes)
- **TypeScript**: `Array('matrix', 'Float32LE', 9)`, `Array('names_data', 'String', 10)`  
- **GraphQL**: `matrix: [Float!]!`, `names: [String!]!`, `values: [Int!]!`

> **Important**: String arrays require both `max_size` (or `size`) AND `element_size` parameters because they are "arrays of arrays" - you need to specify both how many strings AND the maximum size of each individual string. This ensures predictable memory layout and prevents buffer overflows.

### String Type

Strings are a special case of bounded character arrays with built-in UTF-8 encoding and null-termination handling across all target languages.

| String Type | Syntax | Memory Usage | Use Case |
|-------------|--------|--------------|----------|
| **Fixed String** | `string field = N [size=X];` | `X` bytes | Fixed-width text fields |
| **Variable String** | `string field = N [max_size=X];` | 1 byte (length) + `X` bytes | Text with known maximum length |

```proto
message StringExample {
  string device_name = 1 [size=16];              // Exactly 16 characters (pad with nulls)
  string description = 2 [max_size=256];         // Up to 256 characters (length-prefixed)
  string error_msg = 3 [max_size=128];           // Up to 128 characters for error messages
}
```

**String Features:**
- **Simplified Schema**: No need to specify `repeated uint8` for text data
- **Automatic Encoding**: UTF-8 encoding/decoding handled by generators  
- **Null Handling**: Proper null-termination and padding for fixed strings
- **Type Safety**: Clear distinction between binary data and text
- **Cross-Language**: Consistent string handling across C, TypeScript, and Python

### Message Options

**Message ID (`msgid`)** - Required for serializable messages:
```proto
message MyMessage {
  option msgid = 42;  // Must be unique within package (0-65535)
  string content = 1;
}
```

### Field Options

**Flatten (`flatten=true`)** - Merge nested message fields into parent:
```proto
message Position {
  double lat = 1;
  double lon = 2;
}

message Status {
  Position pos = 1 [flatten=true];  // lat, lon become direct fields  
  float battery = 2;
}
```

**Array Options** - Control array behavior:
```proto
message Data {
  repeated int32 fixed_buffer = 1 [size=256];                       // Always 256 integers  
  repeated int32 var_buffer = 2 [max_size=256];                     // Up to 256 integers
  repeated string messages = 3 [max_size=10, element_size=64];      // Up to 10 strings, each max 64 chars
  string device_name = 4 [size=32];                                 // Always 32 characters
  string description = 5 [max_size=256];                            // Up to 256 characters
}
```

## Usage Example

```proto
package sensor_system;

enum SensorType {
  TEMPERATURE = 0;
  HUMIDITY = 1;
  PRESSURE = 2;
}

message Position {
  double lat = 1;
  double lon = 2;
  float alt = 3;
}

message SensorReading {
  option msgid = 1;
  
  uint32 device_id = 1;
  int64 timestamp = 2;
  SensorType type = 3;
  
  // Device name (fixed 16-character string)  
  string device_name = 4 [size=16];
  
  // Sensor location (flattened)
  Position location = 5 [flatten=true];
  
  // Measurement values (up to 8 readings)
  repeated float values = 6 [max_size=8];
  
  // Calibration matrix (always 3x3 = 9 elements)
  repeated float calibration = 7 [size=9];
  
  // Error message (up to 128 characters)
  string error_msg = 8 [max_size=128];
  
  bool valid = 9;
}

message DeviceStatus {
  option msgid = 2;
  
  uint32 device_id = 1;
  repeated SensorReading recent_readings = 2 [max_size=10];
  float battery_level = 3;
}
```

## Schema Validation Rules

- **Message IDs**: Must be unique within package (0-65535)
- **Field numbers**: Must be unique within message  
- **Array requirements**: All `repeated` fields must specify `[size=X]` (fixed) or `[max_size=X]` (bounded)
- **String requirements**: All `string` fields must specify `[size=X]` (fixed) or `[max_size=X]` (variable)
- **String array requirements**: `repeated string` fields must specify both array size AND `[element_size=Y]`
- **Flatten constraints**: No field name collisions after flattening
- **Size limits**: Arrays limited to 255 elements maximum

## Code Generation

```bash
# Generate all languages
python -m struct_frame schema.proto --build_c --build_cpp --build_ts --build_py --build_gql

# Language-specific paths
python -m struct_frame schema.proto --build_py --py_path output/python/
python -m struct_frame schema.proto --build_c --c_path output/c/
python -m struct_frame schema.proto --build_cpp --cpp_path output/cpp/
python -m struct_frame schema.proto --build_ts --ts_path output/typescript/
python -m struct_frame schema.proto --build_gql --gql_path output/graphql/
```

## C++ Implementation

The C++ implementation provides modern C++ features while maintaining compatibility with the same binary message formats used by the C implementation:

### Key Features

- **Enum Classes**: Enums are generated as strongly-typed `enum class` types instead of plain enums
- **Modern C++ Style**: Uses classes, namespaces, templates, and RAII patterns
- **Binary Compatibility**: Generated structs use the same memory layout as C (via `__attribute__((packed))`)
- **Type Safety**: Leverages C++ templates for type-safe message helpers
- **STL Integration**: Uses standard library features like `<cstdint>`, `<functional>`, and `<span>`

### Example

```proto
package robot;

enum RobotStatus : uint8_t {
  IDLE = 0;
  MOVING = 1;
  ERROR = 2;
}

message RobotState {
  option msgid = 10;
  uint32 robot_id = 1;
  RobotStatus status = 2;
  float battery_level = 3;
}
```

**Generated C++ Code:**

```cpp
// Enum class instead of plain enum
enum class RobotRobotStatus : uint8_t {
    IDLE = 0,
    MOVING = 1,
    ERROR = 2
};

// Packed struct compatible with C
struct RobotRobotState {
    uint32_t robot_id;
    RobotRobotStatus status;
    float battery_level;
} __attribute__((packed));

constexpr size_t ROBOT_ROBOT_STATE_MAX_SIZE = 9;
constexpr size_t ROBOT_ROBOT_STATE_MSG_ID = 10;

// Helper function in namespace
namespace StructFrame {
inline bool get_message_length(size_t msg_id, size_t* size) {
    switch (msg_id) {
        case ROBOT_ROBOT_STATE_MSG_ID: 
            *size = ROBOT_ROBOT_STATE_MAX_SIZE; 
            return true;
        default: break;
    }
    return false;
}
}  // namespace StructFrame
```

**Usage:**

```cpp
#include "robot.sf.hpp"
#include "struct_frame.hpp"

// Create and initialize message
RobotRobotState state{};
state.robot_id = 123;
state.status = RobotRobotStatus::MOVING;  // Type-safe enum class
state.battery_level = 85.5f;

// Encode with modern C++ API
uint8_t buffer[256];
StructFrame::BasicPacket format;
StructFrame::EncodeBuffer encoder(buffer, sizeof(buffer));

if (encoder.encode(&format, ROBOT_ROBOT_STATE_MSG_ID, &state, sizeof(state))) {
    // Frame encoded successfully
    std::cout << "Encoded " << encoder.size() << " bytes\n";
}

// Parse with lambda callback
StructFrame::FrameParser parser(&format, [](size_t msg_id, size_t* size) {
    return StructFrame::get_message_length(msg_id, size);
});

// Process received bytes
for (size_t i = 0; i < encoder.size(); i++) {
    auto info = parser.parse_byte(buffer[i]);
    if (info.valid) {
        auto* msg = reinterpret_cast<RobotRobotState*>(info.msg_location);
        std::cout << "Robot ID: " << msg->robot_id 
                  << ", Status: " << static_cast<int>(msg->status) << "\n";
    }
}
```

## Wireshark Dissector (Experimental)

An experimental Wireshark Lua dissector is available for protocol analysis and debugging of struct-frame packets. See [wireshark/README.md](wireshark/README.md) for installation and usage instructions.

## Additional Documentation

- **[Array Implementation Guide](ARRAY_IMPLEMENTATION.md)** - Documentation of array features, syntax, and generated code examples across all languages
