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

Enums can be converted to strings using language built-in features or generated helper functions.

**C** (generated helper function)
```c
SerializationTestSensorType type = SENSOR_TYPE_TEMPERATURE;
const char* type_str = SerializationTestSensorType_to_string(type);
// Returns: "TEMPERATURE"
```

**C++** (generated helper function)
```cpp
SerializationTestSensorType type = SerializationTestSensorType::TEMPERATURE;
const char* type_str = SerializationTestSensorType_to_string(type);
// Returns: "TEMPERATURE"
```

**Python** (built-in Enum)
```python
from sensor_system import SerializationTestSensorType

type = SerializationTestSensorType.TEMPERATURE
# Use the built-in .name property
type_str = type.name
# Returns: "TEMPERATURE"
```

**TypeScript** (built-in reverse mapping)
```typescript
import { SerializationTestSensorType } from './sensor_system.structframe';

const type = SerializationTestSensorType.TEMPERATURE;
// TypeScript numeric enums support reverse mapping
const typeStr = SerializationTestSensorType[type];
// Returns: "TEMPERATURE"
```

**JavaScript** (Object.keys lookup)
```javascript
const { SerializationTestSensorType } = require('./sensor_system.structframe');

const type = SerializationTestSensorType.TEMPERATURE;
// Find the key by value
const typeStr = Object.keys(SerializationTestSensorType).find(
  key => SerializationTestSensorType[key] === type
);
// Returns: "TEMPERATURE"
```

**C#** (built-in ToString)
```csharp
using StructFrame.SensorSystem;

SerializationTestSensorType type = SerializationTestSensorType.TEMPERATURE;
// Use the built-in enum ToString method
string typeStr = type.ToString();
// Returns: "TEMPERATURE"
```

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

## Oneof (Union Types)

The `oneof` construct creates a union type where only one of the fields can be populated at a time. All fields within the `oneof` share the same memory, with the total size equal to the largest field.

### Basic Oneof

```proto
message SensorReading {
  option msgid = 10;
  uint32 timestamp = 1;
  
  oneof value {
    float temperature = 2;
    int32 pressure = 3;
    uint16 humidity = 4;
  }
}
```

**Memory Layout:**
- The `value` union occupies 4 bytes (size of the largest type: `float` or `int32`)
- Only one field (`temperature`, `pressure`, or `humidity`) should be set at a time
- A `uint8` field order discriminator is automatically generated (stores 1, 2, or 3 based on which field is active)

### Oneof with Message Types

When all fields in a `oneof` are messages with `msgid`, an auto-discriminator using message IDs is generated:

```proto
message CommandA {
  option msgid = 100;
  uint8 param1 = 1;
}

message CommandB {
  option msgid = 101;
  uint16 param1 = 1;
  uint16 param2 = 2;
}

message CommandWrapper {
  option msgid = 200;
  uint32 sequence = 1;
  
  oneof command {
    CommandA cmd_a = 2;
    CommandB cmd_b = 3;
  }
}
```

**Memory Layout:**
- `command_discriminator` (uint16_t) - auto-generated, stores the message ID of the active field
- `command` union - size of the largest message type

### Discriminator Option

You can control discriminator behavior with the `discriminator` option inside a `oneof`:

```proto
oneof payload {
  option discriminator = field_order;  // or: msgid, none, auto
  CmdA cmd_a = 1;
  CmdB cmd_b = 2;
}
```

| Option | Discriminator Type | Size | Description |
|--------|-------------------|------|-------------|
| `auto` (default) | Depends on fields | varies | Uses `msgid` if all fields are messages with msgid, otherwise `field_order` |
| `msgid` | Message ID | uint16 (2 bytes) | Forces use of message IDs. **Error** if any field lacks msgid |
| `field_order` | Field order (1-based) | uint8 (1 byte) | Uses declaration order: 1st field = 1, 2nd = 2, etc. |
| `none` | No discriminator | 0 bytes | Disables discriminator. Application must track active field |

### Default Auto-Discriminator Behavior

| Oneof Field Types | Default Discriminator | Size |
|-------------------|----------------------|------|
| All messages with `msgid` | msgid (uint16) | 2 bytes |
| Mixed or all primitives/enums | field_order (uint8) | 1 byte |

**Examples:**

```proto
// Auto: Uses msgid discriminator (uint16) - all fields have msgid
oneof command {
  CommandA cmd_a = 1;  // msgid = 100
  CommandB cmd_b = 2;  // msgid = 101
}

// Auto: Uses field_order discriminator (uint8) - primitives don't have msgid
oneof value {
  float temperature = 1;  // discriminator = 1
  int32 pressure = 2;     // discriminator = 2
}

// Explicit: Force field_order even with messages that have msgid
oneof payload {
  option discriminator = field_order;
  CommandA cmd_a = 1;  // discriminator = 1
  CommandB cmd_b = 2;  // discriminator = 2
}

// Explicit: Disable discriminator entirely
oneof data {
  option discriminator = none;
  uint32 integer_val = 1;
  float float_val = 2;
}
```

### Using Discriminators

**With msgid discriminator:**
```cpp
// C++ - check which message is active by message ID
if (wrapper.command_discriminator == CommandA::MSG_ID) {
    // Access wrapper.command.cmd_a
}
```

**With field_order discriminator:**

For `field_order` discriminators, a typed enum is generated named `{MessageName}{OneofName}Field`:

```cpp
// C++ - use the generated enum for type-safe discriminator checks
if (sensor.value_discriminator == SensorValueField::TEMPERATURE) {
    // temperature is active
} else if (sensor.value_discriminator == SensorValueField::PRESSURE) {
    // pressure is active
}
```

### Multiple Oneofs

A message can contain multiple `oneof` fields:

```proto
message MultiUnionMessage {
  option msgid = 50;
  
  oneof input {
    float analog_value = 1;
    bool digital_value = 2;
  }
  
  oneof output {
    uint16 pwm_duty = 3;
    bool relay_state = 4;
  }
}
```

Each `oneof` is independent and contributes its own union size to the message.

## Envelope Messages (Oneof with is_envelope)

Envelope messages are container messages that wrap other messages for unified handling. They use the `is_envelope` option along with a `oneof` field to contain different message types.

### Why Envelope Messages?

Envelope messages are useful when:

- You have multiple command/response types but want a single message ID for routing
- You need envelope-level metadata (sequence numbers, timestamps, priorities)
- You want type-safe wrappers with SDK helper methods
- You're implementing a command/response protocol with multiple operation types

### Defining Envelope Messages

```proto
// Individual command messages (each must have a msgid)
message ADCCommand {
  option msgid = 112;
  uint8 channel = 1;
  uint16 sample_rate = 2;
  bool enable = 3;
}

message DACCommand {
  option msgid = 113;
  uint8 channel = 1;
  uint16 output_value = 2;
  bool enable = 3;
}

// Envelope message
message CommandEnvelope {
  option msgid = 200;
  option is_envelope = true;  // Enables envelope helper methods
  
  // Envelope-level fields (metadata)
  uint32 sequence_number = 1;
  uint8 priority = 2;
  bool run_immediately = 3;
  
  // Union of all command types - exactly one will be populated
  oneof command {
    ADCCommand adc = 5;
    DACCommand dac = 6;
  }
}
```

### Validation Rules

Envelope messages have these requirements:

- Must have `option is_envelope = true`
- Must have exactly one `oneof` field
- All types in the `oneof` must be message types (not primitives or enums)
- If using `msgid` discriminator (auto or explicit), all message types must have `msgid`

### Discriminator Behavior

Envelope messages use the same discriminator system as regular `oneof` fields (see [Discriminator Options](#discriminator-options) above), but with the following defaults:

| Discriminator Mode | When Used | Size | Value |
|-------------------|-----------|------|-------|
| `msgid` (default) | All inner messages have `msgid` | 2 bytes (uint16) | Message ID of wrapped payload |
| `field_order` | Any inner message lacks `msgid` | 1 byte (uint8) | 1-based field order index |

You can explicitly set the discriminator mode on the oneof:

```proto
message CommandEnvelope {
  option is_envelope = true;
  
  oneof command {
    option discriminator = "field_order";  // Force field_order even if all have msgid
    ADCCommand adc = 5;
    DACCommand dac = 6;
  }
}
```

**Wire Format:**
```
[envelope fields...] [discriminator (1-2 bytes)] [union payload (max field size)]
```

The discriminator is automatically set by the `wrap()` method and read during deserialization.

### Generated SDK Helper Methods

The SDK generates convenient helper methods for envelope messages:

**C++ (msgid discriminator)**
```cpp
// Wrap a command into an envelope - template ensures type safety
EnvelopeTestADCCommand adc_cmd{.channel = 1, .sample_rate = 1000, .enable = true};
auto envelope = EnvelopeTestCommandEnvelope::wrap(
    42,      // sequence_number
    1,       // priority
    true,    // run_immediately
    adc_cmd  // payload (type validated at compile-time via T::MSG_ID)
);

// Only valid payload types are accepted - invalid types cause compile error:
// auto bad = EnvelopeTestCommandEnvelope::wrap(42, 1, true, some_other_msg); // Won't compile!

// Get payload message ID to determine which type was wrapped
uint16_t payload_id = envelope.getPayloadMessageId();

// Access the wrapped payload directly via the oneof field
if (payload_id == EnvelopeTestADCCommand::MSG_ID) {
    auto& adc = envelope.command.adc;
    // Use adc.channel, adc.sample_rate, etc.
}
```

**C++ (field_order discriminator)**
```cpp
// Separate wrap() overloads for each payload type
auto envelope = MyEnvelope::wrap(42, 1, true, adc_cmd);  // Sets discriminator to 1
auto envelope2 = MyEnvelope::wrap(42, 1, true, dac_cmd); // Sets discriminator to 2

// Get field order (1-based) of the wrapped payload
uint8_t field_order = envelope.getPayloadFieldOrder();
```

**Python**
```python
# Wrap a command into an envelope
adc_cmd = EnvelopeTestADCCommand(channel=1, sample_rate=1000, enable=True)
envelope = EnvelopeTestCommandEnvelope.wrap(
    payload=adc_cmd,  # Runtime type check ensures valid payload
    sequence_number=42,
    priority=1,
    run_immediately=True
)

# Invalid payload types raise TypeError:
# envelope = EnvelopeTestCommandEnvelope.wrap(some_other_msg, ...)  # TypeError!

# Unwrap - returns the correct message type based on discriminator
payload = envelope.unwrap()
if payload:
    print(f"Got payload: {type(payload).__name__}")

# Get discriminator value (method name depends on discriminator type)
payload_id = envelope.get_payload_message_id()  # For msgid discriminator
# field_order = envelope.get_payload_field_order()  # For field_order discriminator
```

**TypeScript**
```typescript
// Wrap a command into an envelope - union type ensures type safety
const adcCmd = new EnvelopeTestADCCommand();
adcCmd.channel = 1;
adcCmd.sample_rate = 1000;
adcCmd.enable = true;

// payload type is: EnvelopeTestADCCommand | EnvelopeTestDACCommand | ...
const envelope = EnvelopeTestCommandEnvelope.wrap(adcCmd, 42, 1, true);

// Get payload message ID to determine which type was wrapped
const payloadId = envelope.getPayloadMessageId();
```

**C#**
```csharp
// Wrap a command into an envelope - overloads provide type safety
var adcCmd = new EnvelopeTestADCCommand { Channel = 1, SampleRate = 1000, Enable = true };
var envelope = EnvelopeTestCommandEnvelope.Wrap(adcCmd, 42, 1, true);

// Get payload message ID to determine which type was wrapped
var payloadId = envelope.GetPayloadMessageId();
```

## Validation Rules

The generator enforces:

- Message IDs unique within package (0-255)
- Package IDs unique across packages (0-255)
- Field numbers unique within message
- All arrays must have size or max_size
- All strings must have size or max_size
- String arrays need both max_size and element_size
- Array max_size limited to 255 (count fits in 1 byte)
- Envelope messages must have exactly one oneof field
- Envelope oneof fields must be message types (not primitives/enums)
- Envelope oneof using `msgid` discriminator must have messages with msgid

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

