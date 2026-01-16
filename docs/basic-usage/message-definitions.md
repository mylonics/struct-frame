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

**variable** (optional, enables variable-length encoding)

```proto
message SensorData {
  option msgid = 1;
  option variable = true;  // Encode only used bytes
  repeated uint8 readings = 1 [max_size=100];
}
```

With variable encoding, arrays and strings only transmit actual used bytes instead of the full max_size. This reduces bandwidth when fields are partially filled.

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

All repeated fields must specify a size. Arrays can contain primitive types, enums, strings, or nested messages.

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

**Arrays of nested messages**

```proto
message Waypoint {
  double lat = 1;
  double lon = 2;
}

message Route {
  option msgid = 5;
  string name = 1 [size=32];
  repeated Waypoint waypoints = 2 [max_size=20];
}
```

Array of up to 20 waypoint messages. Each Waypoint is embedded inline.

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

### Enum to String Conversion

Each enum automatically generates a helper function to convert enum values to their string representation. This makes enums easy to use across different languages while maintaining simple integer serialization.

**C**
```c
SerializationTestSensorType type = SENSOR_TYPE_TEMPERATURE;
const char* type_str = SerializationTestSensorType_to_string(type);
// Returns: "TEMPERATURE"
```

**C++**
```cpp
SerializationTestSensorType type = SerializationTestSensorType::TEMPERATURE;
const char* type_str = SerializationTestSensorType_to_string(type);
// Returns: "TEMPERATURE"
```

**Python**
```python
from sensor_system import SerializationTestSensorType

type = SerializationTestSensorType.SENSOR_TYPE_TEMPERATURE
type_str = SerializationTestSensorType.to_string(type)
# Returns: "TEMPERATURE"

# Also works with integer values
type_str = SerializationTestSensorType.to_string(0)
# Returns: "TEMPERATURE"
```

**TypeScript**
```typescript
import { SerializationTestSensorType, SerializationTestSensorType_to_string } from './sensor_system.structframe';

const type = SerializationTestSensorType.TEMPERATURE;
const typeStr = SerializationTestSensorType_to_string(type);
// Returns: "TEMPERATURE"
```

**JavaScript**
```javascript
const { SerializationTestSensorType, SerializationTestSensorType_to_string } = require('./sensor_system.structframe');

const type = SerializationTestSensorType.TEMPERATURE;
const typeStr = SerializationTestSensorType_to_string(type);
// Returns: "TEMPERATURE"
```

**C#**
```csharp
using StructFrame.SensorSystem;

SerializationTestSensorType type = SerializationTestSensorType.TEMPERATURE;
string typeStr = type.ToString();
// Returns: "TEMPERATURE"
```

All enum to string functions return `"UNKNOWN"` for invalid enum values.

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

## Import Statements

Import proto definitions from other files:

```proto
// types.proto
package common;

message Position {
  double lat = 1;
  double lon = 2;
}
```

```proto
// vehicle.proto
import "types.proto";

package fleet;

message Vehicle {
  option msgid = 1;
  uint32 id = 1;
  common.Position pos = 2;
}
```

## Flatten Option

Flatten nested message fields into the parent (Python/GraphQL only):

```proto
message Status {
  Position pos = 1 [flatten=true];
  float battery = 2;
}
```

Access: `status.lat` instead of `status.pos.lat`

## Validation Rules

The generator enforces:

- Message IDs unique within package (0-255)
- Package IDs unique across packages (0-255)
- Field numbers unique within message
- All arrays must have size or max_size
- All strings must have size or max_size
- String arrays need both max_size and element_size
- Array max_size limited to 255 (count fits in 1 byte)

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

