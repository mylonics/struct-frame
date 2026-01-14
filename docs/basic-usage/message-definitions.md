# Message Definitions

Messages are defined in Protocol Buffer (.proto) files. Struct Frame uses these definitions to generate serialization code for each target language.

## Why Proto Files

Proto files provide:
- Language-neutral message definitions
- Type safety across language boundaries
- Familiar syntax for developers who know Protocol Buffers
- Tooling support (syntax highlighting, linting)

Struct Frame uses proto syntax but generates different code than Google's Protocol Buffers. Messages are fixed-size packed structs, not variable-length encoded.

## Packages

Packages group related messages and prevent name collisions:

```proto
package sensor_system;

message SensorReading {
  option msgid = 1;
  float value = 1;
}
```

Generated code uses the package name as a prefix or namespace depending on language.

## Messages

Messages define the structure of data to be serialized:

```proto
message DeviceStatus {
  option msgid = 1;
  uint32 device_id = 1;
  float battery = 2;
  bool online = 3;
}
```

### Message Options

**msgid** (required for top-level messages)

```proto
message Heartbeat {
  option msgid = 42;
  uint64 timestamp = 1;
}
```

Message IDs must be unique within a package (range 0-255).

**pkgid** (optional package-level option)

```proto
package sensors;
option pkgid = 5;
```

Enables extended message addressing with 16-bit message IDs (256 packages × 256 messages = 65,536 total).

## Data Types

| Type | Size | Description |
|------|------|-------------|
| int8 | 1 byte | Signed -128 to 127 |
| uint8 | 1 byte | Unsigned 0 to 255 |
| int16 | 2 bytes | Signed -32768 to 32767 |
| uint16 | 2 bytes | Unsigned 0 to 65535 |
| int32 | 4 bytes | Signed integer |
| uint32 | 4 bytes | Unsigned integer |
| int64 | 8 bytes | Signed large integer |
| uint64 | 8 bytes | Unsigned large integer |
| float | 4 bytes | IEEE 754 single precision |
| double | 8 bytes | IEEE 754 double precision |
| bool | 1 byte | true or false |

All types use little-endian byte order.

## Strings

Strings require a size specification.

**Fixed-size string**

```proto
string device_name = 1 [size=16];
```

Always uses 16 bytes, padded with nulls if shorter.

**Variable-size string**

```proto
string description = 1 [max_size=256];
```

Stores up to 256 characters plus a 1-byte length prefix.

## Arrays

All repeated fields must specify a size.

**Fixed arrays**

```proto
repeated float matrix = 1 [size=9];  // Always 9 floats (3x3 matrix)
```

**Bounded arrays (variable count)**

```proto
repeated int32 readings = 1 [max_size=100];  // 0-100 integers
```

Includes a 1-byte count prefix.

**String arrays**

```proto
repeated string names = 1 [max_size=10, element_size=32];
```

Array of up to 10 strings, each up to 32 characters.

## Enums

```proto
enum SensorType {
  TEMPERATURE = 0;
  HUMIDITY = 1;
  PRESSURE = 2;
}

message SensorReading {
  option msgid = 1;
  SensorType type = 1;
  float value = 2;
}
```

Enums are stored as uint8 (1 byte).

## Nested Messages

```proto
message Position {
  double lat = 1;
  double lon = 2;
}

message Vehicle {
  option msgid = 1;
  uint32 id = 1;
  Position pos = 2;
}
```

Nested messages are embedded inline.

## Complete Example

```proto
package robot_control;

enum RobotState {
  IDLE = 0;
  MOVING = 1;
  ERROR = 2;
}

message Position {
  double lat = 1;
  double lon = 2;
  float altitude = 3;
}

message RobotStatus {
  option msgid = 1;
  
  uint32 robot_id = 1;
  string name = 2 [size=16];
  RobotState state = 3;
  Position current_pos = 4;
  float battery_percent = 5;
  repeated float joint_angles = 6 [size=6];
  string error_msg = 7 [max_size=128];
}
```

