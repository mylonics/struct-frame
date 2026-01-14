# Variable Length Messages

Variable length messages allow efficient wire encoding for messages with variable-length arrays or strings. Instead of always sending the full maximum size, only the actual used bytes are transmitted.

## Overview

By default, struct-frame messages use fixed-size encoding. An array field with `max_size=200` will always serialize as 201 bytes (1 byte count + 200 bytes data), even if only 4 elements are used.

With the `variable` option enabled, the same field would only serialize the count byte plus the actual data bytes used. This can significantly reduce bandwidth in scenarios where:

- Arrays are often partially filled
- Multiple variable-length fields exist in the same message
- Network bandwidth is constrained

## Defining Variable Messages

Add `option variable = true;` to your message definition:

```proto
message SensorData {
  option msgid = 1;
  option variable = true;   // Enable variable-length encoding
  
  uint32 sensor_id = 1;
  repeated uint8 readings = 2 [max_size=100];  // Up to 100 bytes
  string label = 3 [max_size=32];               // Up to 32 chars
}
```

## Generated Code

For variable messages, additional methods are generated alongside the standard pack/unpack methods:

### Constants

| Constant | Description |
|----------|-------------|
| `MAX_SIZE` | Maximum possible size (same as standard messages) |
| `MIN_SIZE` | Minimum size when all variable fields are empty |
| `IS_VARIABLE` | Boolean indicating this is a variable message |

### Methods

| Method | Description |
|--------|-------------|
| `pack_size()` | Calculate the actual packed size based on current data |
| `pack_variable()` | Pack message using variable-length encoding |
| `unpack_variable()` | Unpack message from variable-length encoded buffer |

## Language-Specific Usage

### C

```c
#include "my_messages.structframe.h"

// Create message
MySensorData msg = {0};
msg.sensor_id = 42;
msg.readings.count = 4;
msg.readings.data[0] = 10;
msg.readings.data[1] = 20;
msg.readings.data[2] = 30;
msg.readings.data[3] = 40;

// Calculate size and pack
size_t size = MySensorData_pack_size(&msg);
uint8_t buffer[MY_SENSOR_DATA_MAX_SIZE];
size_t packed = MySensorData_pack_variable(&msg, buffer);
// packed == size == MIN_SIZE + 4 (data bytes)

// Unpack
MySensorData received;
size_t read = MySensorData_unpack_variable(buffer, packed, &received);
```

### C++

```cpp
#include "my_messages.structframe.hpp"

// Create message
MySensorData msg;
msg.sensor_id = 42;
msg.readings.count = 4;
msg.readings.data[0] = 10;
// ...

// Calculate size and pack
size_t size = msg.pack_size();
std::vector<uint8_t> buffer(size);
msg.pack_variable(buffer.data());

// Unpack
MySensorData received;
received.unpack_variable(buffer.data(), buffer.size());
```

### Python

```python
from my_messages import MySensorData

# Create message
msg = MySensorData()
msg.sensor_id = 42
msg.readings = [10, 20, 30, 40]

# Calculate size and pack
size = msg.pack_size()  # Returns actual packed size
packed = msg.pack_variable()  # Returns bytes with only used data

# Compare to fixed pack
fixed = msg.pack()  # Always returns MAX_SIZE bytes
print(f"Variable: {len(packed)}, Fixed: {len(fixed)}")

# Unpack
received = MySensorData.unpack_variable(packed)
```

### TypeScript

```typescript
import { MySensorData } from './my_messages.structframe';

// Create message
const msg = new MySensorData();
msg.message_id = 42;
msg.data_count = 4;
msg.data_data = [10, 20, 30, 40];

// Calculate size and pack
const size = msg.packSize();
const packed = msg.packVariable();

// Unpack
const received = MySensorData.unpackVariable(packed);
```

### C#

```csharp
using StructFrame.MyMessages;

// Create message
var msg = new MySensorData();
msg.SensorId = 42;
msg.ReadingsCount = 4;
msg.ReadingsData = new byte[] { 10, 20, 30, 40 };

// Calculate size and pack
int size = msg.PackSize();
byte[] packed = msg.PackVariable();

// Unpack
var received = MySensorData.UnpackVariable(packed);
```

## Wire Format

Variable messages use the same field ordering as fixed messages. The difference is in how variable-length fields are encoded:

| Field Type | Fixed Encoding | Variable Encoding |
|------------|----------------|-------------------|
| Fixed fields (uint8, etc.) | Same size | Same size |
| Fixed arrays (`size=N`) | N elements | N elements |
| Bounded arrays (`max_size=N`) | 1 + N × elem_size bytes | 1 + count × elem_size bytes |
| Fixed strings (`size=N`) | N bytes | N bytes |
| Variable strings (`max_size=N`) | 1 + N bytes | 1 + length bytes |

### Example

For a message with:
- `uint32 id` (4 bytes)
- `repeated uint8 data [max_size=100]` (count: 4)
- `uint16 checksum` (2 bytes)

**Fixed encoding:** 4 + 1 + 100 + 2 = 107 bytes (always)

**Variable encoding:** 4 + 1 + 4 + 2 = 11 bytes (when count=4)

## Compatibility Notes

1. **Framing**: Variable messages require the receiver to know the message type before unpacking, since the size is not fixed. Use framing protocols that include the payload length.

2. **Versioning**: Adding fields to variable messages follows the same rules as fixed messages. New fields at the end are backwards compatible.

3. **Default methods**: The standard `pack()` and `unpack()` methods still work and produce fixed-size output. Use `pack_variable()` and `unpack_variable()` only when you need the bandwidth savings.

4. **Mixed messages**: You can mix fixed and variable messages in the same package. Only messages with `option variable = true;` get the variable encoding methods.

## Best Practices

1. **Use for large bounded arrays**: The benefits are greatest when you have arrays with large `max_size` that are typically partially filled.

2. **Consider minimum size**: If your arrays are usually full, the overhead of variable encoding (count bytes) may outweigh the benefits.

3. **Test with real data**: Profile your actual message sizes to determine if variable encoding helps your use case.

4. **Document the protocol**: When using variable messages, document that receivers must parse the length field to determine message boundaries.
