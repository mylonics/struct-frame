---
title: Message Definitions
description: The struct-frame schema language — packages, messages, structs, enums, sized types, defaults, oneofs, extensions and constants.
---

Messages are defined in `.sf` files written in the **struct-frame schema language**. The generator turns them into fixed-layout structs, serializers and frame parsers for C, C++, Python, TypeScript, JavaScript, C# and Rust.

```sf
/// Robot telemetry.
package robot @1;

const uint8 NAME_LEN = 16;

enum Mode {
  IDLE = 0;
  DRIVING = 1;
}

struct Position {
  double lat;
  double lon;
}

message Status @1 {
  uint32                 uptime_ms = 1000;
  fixed_string<NAME_LEN> name      = "robot";
  Mode                   mode      = IDLE;
  Position               pos;
  vector<float, 6>       joints;
}
```

Every declaration ends with `;` or a `{ ... }` block. Field order is wire order: fields are encoded in the order they are written.

:::note[Coming from the old syntax?]
Earlier versions used proto-style syntax (`option msgid = 1;`, `repeated`, `[size = N]`, field numbers). Convert a schema, and the files it imports, with:

```bash
struct-frame migrate robot.sf --in-place --recursive
```

The converted file builds exactly the same messages, magic bytes and generated code. See [Migrating from the old syntax](#migrating-from-the-old-syntax).
:::

## Packages

Every file starts with a `package` declaration. A package groups messages and provides the namespace (or name prefix) in generated code. Several files may belong to the same package.

```sf
package sensors;
```

A package can have a **package ID** (0–255), written after the name:

```sf
package sensors @5;
```

With a package ID, message IDs are 0–255 and the full 16-bit wire ID is `(package_id << 8) | message_id`. IDs above 255 only fit profiles that carry a package-ID byte (Bulk and Network); encoding such a message with a 1-byte-ID profile (Standard, Sensor, IPC) fails instead of truncating the ID.

When several packages are compiled together, every package needs an ID — except a package without one that is imported by a package with one, which inherits its importer's ID. The *effective* IDs must be unique across all packages.

## Messages and structs

A **message** is a type that can be sent in a frame on its own. It has a message ID, written after its name with `@`:

```sf
message DeviceStatus @1 {
  uint32 device_id;
  float  battery;
  bool   online;
}
```

Without a package ID the message ID range is 0–65535; with one it is 0–255. IDs may be written in decimal, hex (`@0x1F`) or binary (`@0b101`).

A **struct** is a type that is only embedded in other messages. It has no ID:

```sf
struct Position {
  double lat;
  double lon;
}

message Vehicle @2 {
  uint32   id;
  Position pos;   // embedded inline
}
```

Messages can be embedded too (that is how `oneof` variants and envelopes work), but a struct can never be sent on its own.

### Attributes

Attributes go in square brackets after a declaration's name (and ID). A bare attribute name means `true`:

```sf
message SensorData @3 [variable] {
  vector<uint8, 100> readings;
}
```

| Attribute | Applies to | Meaning |
|-----------|------------|---------|
| `variable` | message, struct | Variable-length encoding: arrays and strings only send the bytes in use |
| `envelope` | message | Envelope message (see [Envelope messages](#envelope-messages)) |
| `magic = [B1, B2]` | message | Fixed magic bytes instead of the computed ones (see [Magic bytes](#magic-bytes)) |
| `flatten` | field | Flatten a struct field's members into the parent in `to_dict()` and GraphQL |
| `discriminator = MODE` | oneof | How the active variant is identified (see [Oneof](#oneof-unions)) |
| `variable` | oneof | Length-prefixed variant payload |
| `min_size = N`, `max_size = N` | oneof | Minimum wire payload / reserved union size |
| `idempotent` | rpc | The call may be executed more than once |

An unknown attribute is an error, with a suggestion when it looks like a typo.

**Variable encoding.** With `[variable]`, arrays and strings transmit only the bytes in use instead of their full capacity. To make *every* message variable at generation time, pass `--no-packed`; it also drops the packed-struct (`#pragma pack(1)`) wrappers in the generated C/C++ code, for platforms without struct packing. It does not change byte order: all multi-byte values are little-endian on the wire, and the generated C/C++ code assumes a little-endian host.

## Types

### Primitive types

Every primitive type has a long and a short name. They are the same type; use whichever you prefer (`struct-frame fmt --types long|short` normalizes a file).

| Type | Short name | Size | Range / format |
|------|------------|------|----------------|
| `uint8` | `u8` | 1 | 0 – 255 |
| `int8` | `i8` | 1 | −128 – 127 |
| `uint16` | `u16` | 2 | 0 – 65535 |
| `int16` | `i16` | 2 | −32768 – 32767 |
| `uint32` | `u32` | 4 | 0 – 2³²−1 |
| `int32` | `i32` | 4 | −2³¹ – 2³¹−1 |
| `uint64` | `u64` | 8 | 0 – 2⁶⁴−1 |
| `int64` | `i64` | 8 | −2⁶³ – 2⁶³−1 |
| `float` | `f32` | 4 | IEEE 754 single precision |
| `double` | `f64` | 8 | IEEE 754 double precision |
| `bool` | | 1 | `true` / `false` |

All multi-byte types are little-endian on the wire. Enums are stored in one byte.

### Strings, bytes and arrays

Sized types follow C++/ETL naming: the type name says whether the size is fixed or a maximum.

| Type | Short name | Wire format |
|------|------------|-------------|
| `fixed_string<N>` | `fstring<N>` | Exactly N bytes, zero-padded |
| `string<N>` | | Length prefix + up to N bytes |
| `fixed_bytes<N>` | `fbytes<N>` | Exactly N bytes, zero-padded |
| `bytes<N>` | | Length prefix + up to N bytes |
| `array<T, N>` | `arr<T, N>` | Exactly N elements |
| `vector<T, N>` | `vec<T, N>` | Count prefix + up to N elements |

```sf
struct Waypoint {
  double lat;
  double lon;
}

message Inventory @4 {
  fixed_string<16>             device_name;   // always 16 bytes
  string<256>                  description;   // 2-byte length + up to 256 bytes
  array<float, 9>              matrix;        // always 9 floats
  vector<int32, 100>           readings;      // 1-byte count + up to 100 values
  vector<fixed_string<32>, 10> names;         // up to 10 strings of 32 bytes each
  vector<Waypoint, 20>         route;         // up to 20 embedded structs
}
```

- N is 1–65535; it may be an integer or a [constant](#constants).
- The length/count prefix is 1 byte when N ≤ 255 and 2 bytes (`uint16`) when N is larger.
- Array elements can be primitives, enums, structs, messages, `fixed_string<N>` or `fixed_bytes<N>`. Elements are always stored at full size, so a bounded `string<N>` cannot be an element, and arrays of arrays are not supported (wrap the inner array in a struct).
- Sizes count bytes of UTF-8, not characters, and longer values are truncated to fit.

In Python, string fields accept `str` (encoded as UTF-8) or `bytes` and always hold `bytes`; decoded messages return `bytes`, so call `.decode()` (and `.rstrip(b"\0")` for fixed-size strings) to get text:

```python no-compile
msg = Status(device_name="sensor-1")      # or b"sensor-1"
name = Status.deserialize(data).device_name.rstrip(b"\0").decode()
```

## Default values

A field can have a default value, written after its name:

```sf
enum PowerMode {
  SLEEP = 0;
  ACTIVE = 1;
}

message DeviceConfig @1 {
  uint32           retry_ms = 1000;
  bool             enabled  = true;
  PowerMode        mode     = ACTIVE;
  fixed_string<16> name     = "device";
  float            gain     = 1.5;
  int16            offset   = -40;
  uint32           mask     = 0xFF00_FF00;
}
```

Defaults are typed: an integer field takes an integer (decimal, hex, binary, `_` separators), a `float`/`double` field takes a number (including `inf`, `-inf` and `nan`), a `bool` field takes `true` or `false`, a string field takes a string literal, a bytes field takes a string literal or a list of byte values, and an enum field takes a member name (`ACTIVE`, or qualified `Mode.ACTIVE`). The value is checked against the field's type and range, and a string must fit the field's size.

String literals use double quotes and support the escapes `\n \r \t \0 \\ \" \' \xNN` (ASCII) and `\uNNNN`.

Arrays, vectors and struct-typed fields take composite values:

```sf
struct Point {
  float x = 1.5;
  float y;
}

message Path @2 {
  array<uint8, 4>              mask   = [1, 2, 3];        // the 4th element is 0
  vector<uint16, 8>            ticks  = [100, 200];       // starts with 2 elements
  array<PowerMode, 2>          modes  = [ACTIVE];
  vector<fixed_string<4>, 3>   names  = ["ab", "cd"];
  fixed_bytes<4>               magic  = [0xCA, 0xFE];
  Point                        origin = { y: 2.5 };        // x keeps Point's default, 1.5
  array<Point, 2>              ends   = [{ x: 7 }];        // ends[1] is a Point at its defaults
}
```

- An array literal may list fewer elements than the array holds. The rest of a fixed array, and the unused capacity of a vector, hold the element type's default: zero for scalars, the struct's own defaults for struct elements. A vector starts with as many elements as the literal lists.
- A struct value `{ field: value, ... }` sets only the fields it names; the others keep the struct's own defaults. Values nest: `{ lo: { x: 3 }, tag: "bx" }`.
- Oneof variants cannot have defaults.

### Default helpers

Every message also gets helpers built on its defaults. "Is default" compares the encoding, so it means the same in every language (a `nan` default is still a default).

| Language | New message at defaults | Reset to defaults | Whole message at defaults? | One field at its default? |
|----------|-------------------------|-------------------|----------------------------|---------------------------|
| C | `Msg_init(&m)` | `Msg_reset(&m)` | `Msg_is_default(&m)` | `Msg_<field>_is_default(&m)` |
| C++ | `Msg m{};` | `m.reset()` | `m.is_default()` | `m.<field>_is_default()` |
| Python | `Msg.defaults()` | `m.reset()` | `m.is_default()` | `m.is_default("field")` |
| TypeScript / JavaScript | `Msg.defaults()` | `m.reset()` | `m.isDefault()` | `m.isDefault("field")` |
| C# | `Msg.Defaults()` | `m.Reset()` | `m.IsDefault()` | `m.Is<Field>Default()` |
| Rust | `Msg::default()` | `m.reset()` | `m.is_default()` | `m.<field>_is_default()` |

In C, C++, C# and Rust the helpers are generated for messages (types with an `@id`); in Python, TypeScript and JavaScript for structs too. A field cannot be named like one of these helpers (for example `reset`): the generator reports the collision.

**What a default changes:**
- A freshly constructed message (or one built with a constructor/init argument omitted) gets the default value for that field instead of the type's zero value.
- Decoding an older or truncated payload (see [Wire evolution](#wire-evolution-extensions)) applies the default to any field the sender didn't transmit.
- A value **explicitly** set to zero/`false`/empty — whether at construction or because the sender actually transmitted it — is never overwritten back to the default.

**What a default does *not* change:** wire layout, field offsets, message size, magic bytes or CRC behaviour. A field with a default is always present on the wire and always serialized.

### Getting a message with its defaults, per language

For `DefaultsMessage` in package `default_values` with `uint8 u8_val = 200;`:

| Language | Construct with defaults | Read the field |
|----------|-------------------------|----------------|
| C | `DefaultValuesDefaultsMessage m; DefaultValuesDefaultsMessage_init(&m);` (a bare declaration is **not** initialised) | `m.u8_val` |
| C++ | `default_values::DefaultsMessage m;` (default member initialisers; `= {}` also works) | `m.u8_val` |
| Python | `DefaultsMessage()`; pass a keyword to override one field, e.g. `DefaultsMessage(u8_val=5)` | `m.u8_val` |
| TypeScript / JavaScript | `new DefaultsMessage()` or `new DefaultsMessage({ u8Val: 5 })` | `m.u8Val` |
| C# | `new DefaultsMessage()` (property initialisers) | `m.U8Val` |
| Rust | `DefaultsMessage::default()`, or `DefaultsMessage { u8_val: 5, ..Default::default() }` | `m.u8_val` |

Decoding applies the same values: a field that a shorter, older payload did not carry is filled from the schema default in every language, and a field the sender did transmit is never replaced. In C, `Msg_deserialize` runs `Msg_init` first and then overlays the received bytes, so no caller-side padding is needed.

## Constants

A constant is a typed, named value. It can be used as a size and as a default value, and is emitted into the generated code of every language:

```sf
const uint8  NAME_LEN    = 16;
const uint16 MAX_SAMPLES = 512;
const float  NOMINAL_V   = 3.3;
const string VERSION     = "1.4.0";

message Report @7 {
  fixed_string<NAME_LEN>        name;
  vector<uint16, MAX_SAMPLES>   samples;
  float                         voltage = NOMINAL_V;
}
```

The type is a primitive or `string`, and the value must fit it. Constants of an imported package are referenced with the package name, e.g. `common.NAME_LEN`.

Every package also gets a generated `WIRE_HASH` constant (`uint32`): a fingerprint of its wire contract (message ids, magic bytes and sizes) that heartbeats report, so two nodes can tell that they were built from different schemas. It stays the same when you rename things, add documentation or add extension fields, and changes when you make a change that breaks the wire. `WIRE_HASH` is therefore a reserved constant name; see [Conformance § 9.4](/struct-frame/reference/conformance/#94-wire-hash).

## Enums

```sf
enum SensorType {
  TEMPERATURE = 0;
  HUMIDITY = 1;
  PRESSURE = 2;
}

message SensorReading @1 {
  SensorType type;
  float value;
}
```

Every entry has an explicit value (0–255; enums are stored in one byte), and values must be unique. Values are never assigned implicitly, so inserting an entry can never renumber the others.

Enums can also be declared inside a message, scoping them to it:

```sf
message MotorCommand @42 {
  enum Direction {
    FORWARD = 0;
    REVERSE = 1;
    BRAKE = 2;
  }

  Direction dir;
  uint16 speed_rpm;
}
```

### Enum to string conversion

Enums can be converted to strings with language built-ins or generated helpers. The examples assume the schema above is in a file with `package sensor_system;`. Only C prefixes the type with the package name; the other languages put it in a namespace or module. TypeScript and JavaScript spell enum members in PascalCase, so their string is `Temperature`; the other languages give `TEMPERATURE`.

**C** (generated helper function)
```c
#include "sensor_system.structframe.h"

SensorSystemSensorType type = SENSOR_TYPE_TEMPERATURE;
const char* type_str = SensorSystemSensorType_to_string(type);
// Returns: "TEMPERATURE"
```

**C++** (generated helper function)
```cpp
#include "sensor_system.structframe.hpp"
using namespace structframe::sensor_system;

SensorType type = SensorType::Temperature;
const char* type_str = SensorType_to_string(type);
// Returns: "TEMPERATURE"
```

**Python** (built-in Enum)
```python
from structframe.sensor_system import SensorType

type = SensorType.TEMPERATURE
type_str = type.name
# Returns: "TEMPERATURE"
```

**TypeScript** (built-in reverse mapping)
```typescript
import { SensorType } from './sensor-system.structframe';

const type = SensorType.Temperature;
const typeStr = SensorType[type];
// Returns: "Temperature"
```

**JavaScript** (Object.keys lookup)
```javascript
const { SensorType } = require('./sensor-system.structframe');

const type = SensorType.Temperature;
const typeStr = Object.keys(SensorType).find(
  key => SensorType[key] === type
);
// Returns: "Temperature"
```

**C#** (built-in ToString)
```csharp
using StructFrame.SensorSystem;

SensorType type = SensorType.TEMPERATURE;
string typeStr = type.ToString();
// Returns: "TEMPERATURE"
```

## Imports

Import the definitions of another file with `import`, after the `package` declaration:

```sf
// types.sf
package common;

struct Position {
  double lat;
  double lon;
}
```

```sf
// vehicle.sf
package fleet @2;

import "types.sf";

message Vehicle @1 {
  uint32 id;
  common.Position pos;
}
```

Imports are resolved relative to the directory of the schema given on the command line first, then relative to the importing file. A type is looked up in its own package and then in the packages that file imports directly; qualify it (`other.Type`) when two imported packages define the same name.

## Flatten

`[flatten]` on a struct-typed field flattens the struct's members into the parent. Only the Python `to_dict()` output and the GraphQL schema are flattened; the generated classes and structs in every language keep the nested field:

```sf
message Status @9 {
  Position pos [flatten];
  float battery;
}
```

In the dictionary and in GraphQL the keys are `lat`, `lon`, … instead of `pos.lat`; in code you still access `status.pos.lat`. Flattening is rejected when a child field name collides with a field of the parent.

## Oneof (unions)

A `oneof` holds exactly one of several variants. All variants share the same memory; the union is as large as its largest variant.

```sf
message SensorReading @10 {
  uint32 timestamp;

  oneof value {
    float  temperature;
    int32  pressure;
    uint16 humidity;
  }
}
```

**Memory layout:**
- The `value` union occupies 4 bytes (the size of the largest type, `float` or `int32`).
- A `uint8` discriminator is generated automatically; it holds 1, 2 or 3 for the active variant (its position in the oneof).

Oneofs are always encoded after the message's fields, so they must be declared after them.

### Oneofs of messages

When every variant is a message with an ID, the discriminator is the active variant's message ID:

```sf
message CommandA @100 {
  uint8 param1;
}

message CommandB @101 {
  uint16 param1;
  uint16 param2;
}

message CommandWrapper @200 {
  uint32 sequence;

  oneof command {
    CommandA cmd_a;
    CommandB cmd_b;
  }
}
```

**Memory layout:**
- `command_discriminator` (`uint16_t`) — auto-generated, holds the message ID of the active variant
- `command` union — the size of the largest variant

### The discriminator attribute

```sf
struct CmdA {
  uint8 a;
}

struct CmdB {
  uint16 b;
}

message Commands @201 {
  oneof payload [discriminator = field_order] {
    CmdA cmd_a;
    CmdB cmd_b;
  }
}
```

| Value | Discriminator type | Size | Description |
|-------|--------------------|------|-------------|
| `auto` (default) | depends on the variants | varies | `msgid` if every variant is a message with an ID, otherwise `field_order` |
| `msgid` | message ID | `uint16` (2 bytes) | Forces message IDs. **Error** if a variant has no ID |
| `field_order` | variant position (1-based) | `uint8` (1 byte) | 1st variant = 1, 2nd = 2, … |
| `none` | none | 0 bytes | No discriminator; the application tracks the active variant |

Variants are numbered by their position in the oneof, so reordering variants changes the wire format of a `field_order` discriminator (`struct-frame diff` reports it).

### Using discriminators

**With a msgid discriminator:**
```cpp no-compile
// C++ - check which message is active by message ID
if (wrapper.command_discriminator == CommandA::MSG_ID) {
    // Access wrapper.command.cmd_a
}
```

**With a field_order discriminator**, a typed enum named `{MessageName}{OneofName}Field` is generated:

```cpp no-compile
// C++ - use the generated enum for type-safe discriminator checks
if (sensor.value_discriminator == SensorValueField::TEMPERATURE) {
    // temperature is active
} else if (sensor.value_discriminator == SensorValueField::PRESSURE) {
    // pressure is active
}
```

### Multiple oneofs

A message can contain several oneofs; each contributes its own union to the message:

```sf
message MultiUnionMessage @50 {
  oneof input {
    float analog_value;
    bool  digital_value;
  }

  oneof output {
    uint16 pwm_duty;
    bool   relay_state;
  }
}
```

## Variable oneofs

When the parent message is `[variable]`, any oneof with a discriminator is serialized in **trimmed** mode by default: only the active variant's bytes are transmitted. For forward-compatible protocols, the oneof can also be marked `[variable]` to add a length prefix.

> **Requirement:** the parent message must be `[variable]` for either mode to take effect.

### Trimmed mode (default for variable messages)

A discriminated oneof inside a variable message transmits only the active variant's bytes; the receiver derives the size from the discriminator.

**Wire format:**
```
[discriminator: 1–2 bytes] [variant_bytes: active variant size]
```

```sf
struct SmallPayload {
  uint8 a;
  uint16 b;
}

struct LargePayload {
  array<uint8, 32> data;
}

message SensorCommand @30 [variable] {
  uint8 header;

  oneof data [discriminator = field_order] {
    SmallPayload small;   // 3 bytes on the wire when active
    LargePayload large;   // 32 bytes on the wire when active
  }
}
```

### Variable mode (length-prefixed)

Add `[variable]` to the oneof for a fully forward-compatible format: a `uint16` little-endian length is inserted before the variant bytes, so receivers can skip unknown variants.

**Wire format:**
```
[discriminator: 1–2 bytes] [payload_length: uint16 LE] [variant_bytes: payload_length bytes]
```

```sf
message CommandMessage @20 [variable] {
  uint8 header;

  oneof data [discriminator = field_order, variable] {
    SmallPayload small;   // 3 bytes on the wire
    LargePayload large;   // 32 bytes on the wire
  }
}
```

### Oneof size controls

#### `max_size = N` — reserve space for future variants

**Valid for trimmed (non-variable) oneofs only.** Increases the in-memory union buffer to at least N bytes without changing the wire size of existing variants. Use it when you plan to add larger variants later.

```sf
message Reserved @31 [variable] {
  oneof data [discriminator = field_order, max_size = 64] {
    SmallPayload small;   // still 3 bytes on the wire
  }
}
```

`max_size` does not apply to variable oneofs, because they transmit each variant at its own size regardless of the union buffer.

#### `min_size = N` — guarantee a minimum wire payload size

**Valid when the parent message is `[variable]` and either the oneof is `[variable]`, or the oneof is the only variable-length member of the message.** Pads the serialized payload to at least N bytes, for receivers built against an older schema that expect a fixed-length payload.

On a variable oneof the padding is inside the length prefix; the receiver reads `payload_length` and ignores trailing zeros:

```sf
message Padded @32 [variable] {
  oneof data [discriminator = field_order, variable, min_size = 8] {
    SmallPayload small;   // 3 bytes -> [disc][0x08 0x00][3 bytes + 5 zero bytes]
    LargePayload large;   // 32 bytes -> transmitted as-is
  }
}
```

On a trimmed oneof the padding extends the trimmed payload; the receiver derives the length from the known variant size.

**Rules:**
- `min_size` must be ≤ the oneof's buffer size (the largest variant, or `max_size` if set).
- Padding bytes are always zero.

**Wire evolution of variants in a trimmed oneof:**
- A variant struct may grow through its own `extensions` block. Older senders omit the new bytes (a newer receiver fills them with schema defaults, or zero); newer senders add bytes that an older receiver ignores.
- This works only for the **last** oneof of a variable message: its payload runs to the end of the frame, so the receiver treats every remaining byte as the active variant. The buffer passed to `deserialize` must therefore be exactly the message payload (frame parsers already guarantee this).
- A trimmed oneof followed by another oneof cannot evolve, because the receiver cannot tell where its payload ends. Do not add extension fields to variants of a non-trailing trimmed oneof.
- `MIN_SIZE` is the smallest valid payload across the known variants. `struct-frame diff` reports growth of a trailing trimmed oneof through variant extension fields as wire-compatible.

| Attribute | Applies to | Effect |
|-----------|------------|--------|
| `variable` | any discriminated oneof in a variable message | Adds a `uint16 LE` length prefix before the variant bytes |
| `max_size = N` | trimmed (non-variable) oneofs | Sets the minimum in-memory union buffer size |
| `min_size = N` | variable oneofs, or a trimmed oneof that is the only variable-length member | Pads the wire payload to at least N bytes |

## Envelope messages

Envelope messages wrap other messages for unified handling: a single message ID for routing, plus envelope-level metadata (sequence numbers, timestamps, priorities) and generated wrap/unwrap helpers.

```sf
// Individual command messages (each has an ID)
message ADCCommand @112 {
  uint8  channel;
  uint16 sample_rate;
  bool   enable;
}

message DACCommand @113 {
  uint8  channel;
  uint16 output_value;
  bool   enable;
}

message CommandEnvelope @200 [envelope] {
  // Envelope-level fields (metadata)
  uint32 sequence_number;
  uint8  priority;
  bool   run_immediately;

  // Exactly one of the commands
  oneof command {
    ADCCommand adc;
    DACCommand dac;
  }
}
```

### Validation rules

- An envelope has exactly one `oneof`.
- Every variant is a message or struct (not a primitive or enum).
- With the `msgid` discriminator (the default when every variant has an ID), every variant must be a message with an ID.

### Discriminator behaviour

Envelopes use the same discriminator system as ordinary oneofs, with these defaults:

| Discriminator mode | When used | Size | Value |
|--------------------|-----------|------|-------|
| `msgid` (default) | every variant has an ID | 2 bytes (`uint16`) | message ID of the wrapped payload |
| `field_order` | a variant has no ID | 1 byte (`uint8`) | 1-based variant position |

**Wire format:**
```
[envelope fields...] [discriminator (1-2 bytes)] [union payload (largest variant)]
```

The discriminator is set by the generated `wrap()` helper and read during deserialization.

### Generated SDK helper methods

**C++ (msgid discriminator)**
```cpp no-compile
// Wrap a command into an envelope - template ensures type safety
envelope_test::ADCCommand adc_cmd{.channel = 1, .sample_rate = 1000, .enable = true};
auto envelope = envelope_test::CommandEnvelope::wrap(
    42,      // sequence_number
    1,       // priority
    true,    // run_immediately
    adc_cmd  // payload (type validated at compile-time via T::MSG_ID)
);

// Only valid payload types are accepted - invalid types cause compile error:
// auto bad = envelope_test::CommandEnvelope::wrap(42, 1, true, some_other_msg); // Won't compile!

// Get payload message ID to determine which type was wrapped
uint16_t payload_id = envelope.getPayloadMessageId();

// Access the wrapped payload directly via the oneof field
if (payload_id == envelope_test::ADCCommand::MSG_ID) {
    auto& adc = envelope.command.adc;
    // Use adc.channel, adc.sample_rate, etc.
}
```

**C++ (field_order discriminator)**
```cpp no-compile
// Separate wrap() overloads for each payload type
auto envelope = MyEnvelope::wrap(42, 1, true, adc_cmd);  // Sets discriminator to 1
auto envelope2 = MyEnvelope::wrap(42, 1, true, dac_cmd); // Sets discriminator to 2

// Get field order (1-based) of the wrapped payload
uint8_t field_order = envelope.getPayloadFieldOrder();
```

**Python**
```python
# Wrap a command into an envelope
adc_cmd = ADCCommand(channel=1, sample_rate=1000, enable=True)
envelope = CommandEnvelope.wrap(
    payload=adc_cmd,  # Runtime type check ensures valid payload
    sequence_number=42,
    priority=1,
    run_immediately=True
)

# Invalid payload types raise TypeError:
# envelope = CommandEnvelope.wrap(some_other_msg, ...)  # TypeError!

# Unwrap - returns the correct message type based on discriminator
payload = envelope.unwrap()
if payload:
    print(f"Got payload: {type(payload).__name__}")

# Get discriminator value (method name depends on discriminator type)
payload_id = envelope.get_payload_message_id()  # For msgid discriminator
# field_order = envelope.get_payload_field()  # For field_order discriminator
```

**TypeScript**
```typescript
// Wrap a command into an envelope - union type ensures type safety
const adcCmd = new ADCCommand();
adcCmd.channel = 1;
adcCmd.sampleRate = 1000;
adcCmd.enable = true;

// payload type is: ADCCommand | DACCommand | ...
const envelope = CommandEnvelope.wrap(adcCmd, 42, 1, true);

// Get payload message ID to determine which type was wrapped
const payloadId = envelope.getPayloadMessageId();
```

**C#** (namespace `StructFrame.EnvelopeTest`)
```csharp no-compile
// Wrap a command into an envelope - overloads provide type safety
var adcCmd = new ADCCommand { Channel = 1, SampleRate = 1000, Enable = true };
var envelope = CommandEnvelope.Wrap(adcCmd, 42, 1, true);

// Get payload message ID to determine which type was wrapped
var payloadId = envelope.GetPayloadMessageId();
```

## Magic bytes

The generator computes two magic bytes for every message from the types, positions and sizes of its base fields. They seed the checksum and act as a structural fingerprint: a receiver built against a different layout rejects the frame.

`[magic = [B1, B2]]` overrides the computed bytes. Use it when an existing message must stay wire-compatible across a schema change that would otherwise alter the magic bytes — for example, renaming a struct that the message embeds, or moving an enum definition into the message.

```sf
message JobStatusMessage @53 [magic = [0xA3, 0x7F]] {
  enum Status {
    JOB_START = 0;
    JOB_END = 1;
    JOB_ABORT = 2;
    extensions {
      JOB_FAILED = 3;
      JOB_END_WARN = 4;
    }
  }

  Status status;
  uint8  id;
  uint8  job_type;
  double time;
}
```

**Rules:**
- Exactly two values, each 1–255 (zero is reserved: it is the seed for messages the receiver does not know).
- Values may be written in hex (`0xAB`) or decimal (`171`).
- Changing the override regenerates the code (it is part of the generation hash).

> **When to use this:** prefer the computed magic bytes — they validate the structure automatically. Only override them when you intentionally need two schema revisions to be treated as wire-compatible by existing parsers, and you have verified that the wire layout is genuinely unchanged.

The computed magic bytes include the *name* of every embedded struct or message type, so renaming a type that other messages embed changes their magic bytes; `struct-frame diff` reports this.

## Wire evolution (extensions)

An `extensions { ... }` block at the end of a message (or struct) holds fields added in later schema versions. Older receivers still accept the frames of newer senders, and newer receivers accept the shorter frames of older senders.

```sf
message StatusReport @10 {
  // Base fields (always on the wire)
  uint32 device_id;
  uint8  status_code;
  uint16 error_flags;

  // Added in firmware v2
  extensions {
    uint32     uptime_seconds;
    float      cpu_temperature;
    string<32> firmware_version;
  }
}
```

### How it works

- Fields before the block are **base fields** — always present on the wire, always covered by the magic bytes.
- Fields in the block are **extension fields** — newer senders include them; a receiver that gets a shorter payload fills them with their [default](#default-values) (zero if the field has none).
- The magic bytes are computed only from base fields, so adding extension fields never changes them.
- Extension bytes are still covered by the frame's CRC (after the magic seed), so corruption of extension data is detected.
- Later versions append to the same block. A field must never move into or out of the block — that changes the base layout.

> **Profile requirement:** truncated or extended payloads can only be detected when the frame carries a length field. Use a length-bearing profile (Standard, Bulk or Network). On profiles without a length field (Sensor, IPC) extension fields are ordinary fixed bytes and both sides must agree on the full message size.

| Sender | Receiver | Result |
|--------|----------|--------|
| v1 (base only) | v1 (base only) | ✓ Normal frame |
| v2 (base + ext) | v1 (base only) | ✓ Receiver ignores the extra trailing bytes |
| v1 (base only) | v2 (base + ext) | ✓ Receiver fills extension fields with their defaults |
| v2 (base + ext) | v2 (base + ext) | ✓ Full round trip |

A message with oneofs cannot have a message-level `extensions` block: oneofs are encoded after the fields, so extension fields would not be trailing. Add extension *variants* to the oneof instead.

### Oneof extensions (extension variants)

An `extensions` block inside a oneof holds variants added later. Receivers that do not know a new variant report an unknown discriminator and skip its payload.

```sf
message AdcCommand @100 {
  uint8 channel;
}

message DacCommand @101 {
  uint8 channel;
}

message PwmCommand @102 {   // added in v2
  uint8  channel;
  uint16 duty_cycle;
}

message I2cCommand @103 {   // added in v3
  uint8 address;
  uint8 reg;
}

message JobMessage @200 {
  bool run_immediately;

  oneof job [discriminator = field_order] {
    // Base variants - understood by every receiver version
    AdcCommand adc;
    DacCommand dac;

    extensions {
      PwmCommand pwm;
      I2cCommand i2c;
    }
  }
}
```

- The message's base size uses the largest *base* variant, not the largest extension variant.
- The magic bytes are computed from base variants only.
- The discriminator is always a base field (present in every frame).

### Enum extensions

An `extensions` block in an enum marks values added in later versions. It does not change the wire representation (enums stay one byte) and every value is still generated; values in the block are excluded from the generation hash. They must be larger than every base value.

```sf
enum JobStatus {
  UNKNOWN = 0;
  QUEUED = 1;
  RUNNING = 2;

  extensions {
    COMPLETE = 3;
    FAILED = 4;
  }
}
```

### `BASE_SIZE`

Every message has a `BASE_SIZE` constant next to `MAX_SIZE`. Without extensions they are equal; `BASE_SIZE` is how many bytes a sender without the extension fields transmits.

**C**
```c
// WIRE_EVOLUTION_STATUS_REPORT_BASE_SIZE — non-extension payload bytes
// WIRE_EVOLUTION_STATUS_REPORT_MAX_SIZE  — full payload with all extensions
```

**Python**
```python
from structframe.my_package import StatusReport

print(StatusReport.BASE_SIZE)  # 7  (device_id + status_code + error_flags)
print(StatusReport.MAX_SIZE)   # 48 (+ uptime_seconds 4 + cpu_temperature 4 + firmware_version 33)
```

### Checking wire compatibility

Run [`struct-frame diff OLD.sf NEW.sf`](/reference/cli-reference/#schema-diff-wire-compatibility-check) in CI to verify that a new revision only adds extensions. It reports changed message IDs, magic bytes, field types and order, enum values, extension blocks and order-sensitive oneof variants, and lists source-only renames and file moves separately.

## Comments and documentation

Comments come in two kinds:

| Comment | Kind |
|---------|------|
| `/// text` and `/** text */` | **Doc comment** — documents a declaration and is copied into the generated code |
| `// text` and `/* text */` | **Private comment** — stays in the schema |

Every doc comment has exactly one owner, decided by where it is written:

| Where | Documents |
|-------|-----------|
| Before the `package` declaration | The file (license headers, overviews); emitted at the top of each generated file |
| On the lines directly before a declaration | That declaration (message, struct, enum, entry, field, oneof, variant, constant, service, rpc) |
| On the same line, after a declaration | That declaration (for a block, the line of its `{` or `}`) |

```sf
/// Copyright (c) Example Corp.     <- file docs
/// Robot telemetry definitions.    <- file docs
package robot;

/// Current robot state.            <- docs of RobotState
enum RobotState {
  IDLE = 0;      /// Waiting         <- docs of IDLE
  // TODO: add CHARGING              <- private, not in generated code
  /// Driving.                       <- docs of MOVING
  MOVING = 1;
}
```

A doc comment that documents nothing (for example one before an `import`, or at the end of a block) gets a warning. Multi-line doc comments keep their line order in every generated language.

Documentation takes part in incremental generation: changing a doc comment regenerates the files even though the schema structure is unchanged. Private comments never trigger regeneration. Use `--force` only to regenerate unchanged input.

## Services

A `service` declares request/response calls between nodes:

```sf
service Config {
  /// Read the device configuration.
  rpc get(GetConfig) -> DeviceConfig;
  /// Restart the device; acknowledged without a response message.
  rpc reboot(Reboot) [idempotent];
}
```

The request and response are messages with IDs. An `rpc` without `->` is acknowledged with a status only.

:::caution
Service declarations are parsed and checked, but code generation for them is not available yet: a schema that declares a service is rejected for now.
:::

## Generated names

Source identifiers are converted to each language's conventions with one shared tokenizer. It splits on `_`, `-`, lower→upper transitions and acronym boundaries (`BLEHost` → `BLE` + `Host`), so mixed-case names keep their acronyms instead of being flattened:

| Source name | PascalCase name (C++/TS enum entries, C# properties, JS enum keys, type names) | SCREAMING_SNAKE name (C#/Python/Rust enum entries, C constants) |
|-------------|------|------|
| `BleMCuHost` | `BleMCuHost` | `BLE_M_CU_HOST` |
| `BleHost` | `BleHost` | `BLE_HOST` |
| `GateCurrent` | `GateCurrent` | `GATE_CURRENT` |
| `BLEHost` | `BLEHost` | `BLE_HOST` |
| `gate_current` | `GateCurrent` | `GATE_CURRENT` |

TypeScript/JavaScript property accessors start with a lower-case letter (`gateCurrent`, `bleHostId`) but keep the remaining acronym casing (`BLEHost` stays `BLEHost`).

Names written entirely in one case (`BLE_HOST_OK`, `ble_host`) carry no acronym information, so they are title-cased (`BleHostOk`).

Field, oneof and variant names that are reserved words in a target language (for example `class`, `self`, `delete`, `fn`) are rejected with an error naming the language; rename the field or map it with `--name-overrides`. The struct-frame keywords themselves (`message`, `extensions`, `rpc`, …) are valid field names.

When no heuristic can produce the name you want, pass `--name-overrides FILE` with a JSON file. Overrides are keyed by `all` or a language (`c`, `cpp`, `ts`, `js`, `py`, `gql`, `csharp`, `rust`); each entry maps a source name path to the exact generated name:

```json
{
  "all": { "BleMCuHost": "BleMcuHost" },
  "csharp": { "Telemetry.gate_current": "GateCurrentAmps" },
  "cpp": { "demo.Mode.RUN": "Running" }
}
```

Keys are dotted source paths (`Name`, `Message.field`, `Message.oneof.variant`, `Enum.ENTRY`, `Message.Nested`, `Message.Nested.ENTRY`), optionally prefixed with the package. A language entry wins over `all`, and a package-qualified key wins over an unqualified one. Unknown keys, invalid identifiers and collisions are errors. Overrides only rename generated symbols: message IDs, magic bytes and the wire layout are unchanged, and the overrides file is part of the generation hash.

## Output ordering

Generated output does not depend on the order in which files were imported or declarations were written, so reorganizing a schema into several files produces a reviewable diff:

- Packages are emitted dependency-first (imported packages before importers).
- Within a package, enums are sorted by name and messages are emitted dependencies-first, with ties broken by name.
- **Order-sensitive content is never reordered:** fields, oneof variants (their `field_order` discriminator values are their 1-based position), enum entries and message-nested enums keep their declaration order.

## Errors

Errors and warnings name the file, line and column, show the source line and usually suggest a fix:

```
robot.sf:12:3: error[SF0320]: 'string' needs a capacity
   12 |   string name;
      |   ^^^^^^
  = hint: write string<N> (up to N bytes) or fixed_string<N> (exactly N)
```

The generator rejects, among others:

- syntax errors, unknown types, attributes and constants, and duplicate declarations;
- message IDs that are not unique within a package (0–65535, or 0–255 with a package ID) or across packages once package IDs are applied;
- package IDs that are not unique, and missing package IDs when several packages are compiled together (unless inherited);
- ambiguous type names (a name defined in two imported packages must be qualified);
- enum values outside 0–255 or not unique;
- sizes outside 1–65535;
- defaults of the wrong type, out of range, too long, or on unsupported fields;
- a oneof without variants, or with `min_size` greater than `max_size`;
- variants of a `msgid`-discriminated oneof that share a message ID;
- envelopes without exactly one oneof, or with variants that are not messages;
- an `extensions` block that is not last, that has no base field before it, or that is combined with a oneof at message level;
- generated names that collide or are reserved words in a target language (see [Generated names](#generated-names)).

## Migrating from the old syntax

`struct-frame migrate` converts schemas written in the earlier proto-style syntax. It needs the optional `migrate` extra:

```bash
pip install 'struct-frame[migrate]'
struct-frame migrate robot.sf --in-place --recursive   # convert robot.sf and its imports
struct-frame migrate robot.sf                          # print the converted file
struct-frame migrate *.sf --check                      # exit 1 if any file uses the old syntax
```

The converted file builds exactly the same model: the same messages, message and package IDs, field layout, magic bytes, defaults and generated code. Comments that documented a declaration become `///` doc comments; comments the old front end ignored stay as `//` comments. Constructs that struct-frame never supported (`map`, `reserved`, nested messages, `service` in the old syntax) are reported and left as comments.

| Old syntax | New syntax |
|------------|------------|
| `option pkgid = 5;` | `package name @5;` |
| `message M { option msgid = 1; ... }` | `message M @1 { ... }` |
| `message P { ... }` without `msgid` | `struct P { ... }` |
| `uint32 x = 1;` (field number) | `uint32 x;` |
| `uint32 x = 1 [default = 5];` | `uint32 x = 5;` |
| `string s = 1 [size = 16];` | `fixed_string<16> s;` |
| `string s = 1 [max_size = 64];` | `string<64> s;` |
| `repeated uint8 a = 1 [size = 8];` | `array<uint8, 8> a;` |
| `repeated uint8 a = 1 [max_size = 100];` | `vector<uint8, 100> a;` |
| `repeated string n = 1 [max_size = 10, element_size = 32];` | `vector<fixed_string<32>, 10> n;` |
| `option variable = true;` | `[variable]` attribute |
| `option is_envelope = true;` | `[envelope]` attribute |
| `option magic_bytes = "0xA3, 0x7F";` | `[magic = [0xA3, 0x7F]]` |
| `option discriminator = field_order;` | `oneof o [discriminator = field_order] { ... }` |
| `option extensions_start = N;` / `// Extension::` | `extensions { ... }` block |
| `[flatten = true]` | `[flatten]` |
| `// comment` documenting a declaration | `/// comment` |

To compare a schema from before the change with one after it, `struct-frame diff` reads old-syntax files too when the `migrate` extra is installed.

## Grammar

```
file       = package import* decl*
package    = "package" NAME ("@" value)? ";"
import     = "import" STRING ";"
decl       = const | enum | struct | message | service
const      = "const" type NAME "=" value ";"
enum       = "enum" NAME "{" (entry | "extensions" "{" entry* "}")* "}"
entry      = NAME "=" value ";"
struct     = "struct" NAME attrs? "{" member* "}"
message    = "message" NAME "@" value attrs? "{" member* "}"
member     = field | oneof | enum | "extensions" "{" field* "}"
field      = type NAME attrs? ("=" value)? ";"
oneof      = "oneof" NAME attrs? "{" (variant | "extensions" "{" variant* "}")* "}"
variant    = type NAME attrs? ";"
service    = "service" NAME "{" rpc* "}"
rpc        = "rpc" NAME "(" type ")" ("->" type)? attrs? ";"
type       = ("array" | "arr" | "vector" | "vec") "<" type "," size ">"
           | ("string" | "bytes" | "fixed_string" | "fstring" | "fixed_bytes" | "fbytes") "<" size ">"
           | QUALIFIED_NAME
size       = INTEGER | QUALIFIED_NAME
attrs      = "[" attr ("," attr)* ","? "]"
attr       = NAME ("=" value)?
value      = INTEGER | FLOAT | STRING | "true" | "false" | QUALIFIED_NAME | "-" value
           | "[" (value ("," value)* ","?)? "]"
           | "{" (NAME ":" value ("," NAME ":" value)* ","?)? "}"
```

`QUALIFIED_NAME` is one or more names joined by `.`. Integers are decimal, hex (`0x`), binary (`0b`) or octal (`0o`), with optional `_` separators; a decimal integer has no leading zeros. A `;` after a closing `}` is accepted; `struct-frame fmt` removes it.
