# Message Definitions

Messages are defined in Protocol Buffer (.proto) files. Struct Frame uses these definitions to generate serialization code for each target language.

## Why Proto Files

Proto files provide:
- Language-neutral message definitions
- Type safety across language boundaries
- Familiar syntax for developers who know Protocol Buffers
- Tooling support (syntax highlighting, linting)

Struct Frame uses the proto syntax but generates different code than Google's Protocol Buffers. Messages are fixed-size packed structs, not variable-length encoded.

## Packages

Packages group related messages and prevent name collisions.

```proto
package sensor_system;

message SensorReading {
  // ...
}
```

Generated code uses the package name as a prefix or namespace depending on language.

### Package IDs (Extended Message IDs)

Package IDs enable extended message addressing with 16-bit message IDs instead of 8-bit. This allows up to 256 packages, each with up to 256 messages, for a total of 65,536 unique message IDs.

```proto
package sensor_system;

// Define package ID (0-255)
option pkgid = 5;

message SensorReading {
  option msgid = 1;
  // ...
}
```

**When to use Package IDs:**
- Systems with more than 255 messages
- Multi-package systems that need message namespace separation
- Projects requiring explicit package versioning

**Generated code behavior with Package IDs:**

- **C++**: Messages are generated inside a namespace matching the package name (e.g., `sensor_system::SensorReading`)
- **C**: Package ID is defined as a constant (e.g., `SENSOR_SYSTEM_PACKAGE_ID`)
- **TypeScript/JavaScript**: Package ID exported as constant `PACKAGE_ID`
- **Python**: Package ID available as `PACKAGE_ID` constant
- **C#**: Package ID in `PackageInfo.PackageId`

**Message ID encoding:**
- Without pkgid: 8-bit message ID (0-255)
- With pkgid: 16-bit message ID = `(package_id << 8) | msg_id`

**Frame format compatibility:**
- Use EXTENDED_MSG_IDS, EXTENDED, or EXTENDED_MULTI_SYSTEM_STREAM frame formats
- These formats include a package_id field in the frame header

## Messages

Messages define the structure of data to be serialized.

```proto
message DeviceStatus {
  uint32 device_id = 1;
  float battery = 2;
  bool online = 3;
}
```

Field numbers (1, 2, 3) must be unique within a message. They are used for documentation and proto compatibility but do not affect serialization order.

### Message Options

**msgid**

Required for messages that will be serialized and sent over a frame.

```proto
message Heartbeat {
  option msgid = 42;
  // ...
}
```

Message IDs must be unique within a package. Range is 0-255 for both basic and extended frame formats (extended formats use package_id for the upper 8 bits).


## Enums

Enums define a set of named integer constants.

```proto
enum SensorType {
  TEMPERATURE = 0;
  HUMIDITY = 1;
  PRESSURE = 2;
}
```

Enum values are stored as a single byte (uint8). Use them in messages like any other type:

```proto
message SensorReading {
  SensorType type = 1;
  float value = 2;
}
```

## Basic Data Types

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

Always uses the specified number of bytes, padded with nulls if shorter.

```proto
string device_name = 1 [size=16];
```

**Variable-size string**

Stores up to max_size characters plus a length prefix byte.

```proto
string description = 1 [max_size=256];
```

Memory layout for variable string:
- 1 byte length
- N bytes data (up to max_size)

## Arrays

All repeated fields must specify a size.

**Fixed arrays**

Always contain exactly the specified number of elements.

```proto
repeated float matrix = 1 [size=9];      // 3x3 matrix, always 9 floats
repeated bool flags = 2 [size=8];        // Always 8 booleans
```

Use for data that always has the same count (matrices, fixed sensor arrays).

**Bounded arrays**

Variable count up to a maximum. Includes a count byte prefix.

```proto
repeated int32 readings = 1 [max_size=100];    // 0-100 integers
repeated float temps = 2 [max_size=16];        // 0-16 floats
```

Memory layout for bounded array:
- 1 byte count
- N elements (up to max_size)

**String arrays**

Arrays of strings require both array size and element size:

```proto
repeated string names = 1 [max_size=10, element_size=32];
```

This creates an array of up to 10 strings, each up to 32 characters.

## Nested Messages

Messages can contain other messages.

```proto
message Position {
  double lat = 1;
  double lon = 2;
  float alt = 3;
}

message Vehicle {
  option msgid = 1;
  uint32 id = 1;
  Position pos = 2;
  float speed = 3;
}
```

Nested messages are embedded inline. The Vehicle message contains the full Position struct.

### Flatten Option

The flatten option merges nested message fields into the parent.

```proto
message Status {
  Position pos = 1 [flatten=true];
  float battery = 2;
}
```

Without flatten, access is `status.pos.lat`. With flatten, access is `status.lat`.

Flatten is supported in Python and GraphQL only.

## Validation Rules

The generator enforces these rules:

- Message IDs must be unique within a package (0-255)
- Package IDs must be unique across all packages in a system (0-255)
- Package IDs cannot be used in combination with message IDs > 255
- Field numbers must be unique within a message
- All repeated fields must have size or max_size
- All string fields must have size or max_size
- String arrays must have both max_size and element_size
- Flattened fields must not cause name collisions
- Array max_size limited to 255 elements (count fits in 1 byte)

## Complete Example

```proto
package robot_control;

// Optional: Use package ID for extended message addressing
option pkgid = 1;

enum RobotState {
  IDLE = 0;
  MOVING = 1;
  CHARGING = 2;
  ERROR = 3;
}

message Position {
  double lat = 1;
  double lon = 2;
  float altitude = 3;
}

message WaypointList {
  repeated Position waypoints = 1 [max_size=20];
}

message RobotStatus {
  option msgid = 1;
  
  uint32 robot_id = 1;
  string name = 2 [size=16];
  RobotState state = 3;
  Position current_pos = 4;
  float battery_percent = 5;
  int64 uptime_ms = 6;
  repeated float joint_angles = 7 [size=6];
  string error_msg = 8 [max_size=128];
}

message RobotCommand {
  option msgid = 2;
  
  uint32 target_robot = 1;
  RobotState desired_state = 2;
  Position target_pos = 3;
  repeated float joint_targets = 4 [size=6];
}
```
