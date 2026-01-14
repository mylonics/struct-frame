# Advanced Features

This page covers advanced proto features and edge cases.

## Package IDs

Package IDs enable extended message addressing with 16-bit message IDs (256 packages × 256 messages = 65,536 total).

```proto
package sensors;
option pkgid = 5;

message Reading {
  option msgid = 1;
  float value = 1;
}
```

**Message ID encoding:**
- Without pkgid: 8-bit (0-255)
- With pkgid: 16-bit = `(package_id << 8) | msg_id`

**Frame compatibility:**
Use Extended or ExtendedMultiSystemStream payload types.

## Variable-Length Messages

Use bounded arrays and variable-length strings for messages that vary in size:

```proto
message LogEntry {
  option msgid = 10;
  uint64 timestamp = 1;
  string message = 2 [max_size=256];
  repeated uint8 data = 3 [max_size=128];
}
```

**Memory layout:**
- String: 1 byte length + up to max_size characters
- Array: 1 byte count + up to max_size elements

## Minimal Frames

For bandwidth-limited scenarios, use minimal frames (no length or checksum):

```proto
// All messages must be fixed-size for minimal frames
message SensorReading {
  option msgid = 1;
  uint32 sensor_id = 1;
  float value = 2;
}
```

Generate a message length lookup function:

```python
# Auto-generated in <name>_sf.py
def get_msg_length(msg_id: int) -> int:
    return MSG_LENGTHS.get(msg_id, 0)
```

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

## Flatten Option (Python/GraphQL only)

Flatten nested message fields into the parent:

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

## Edge Cases

### Empty Messages

```proto
message Heartbeat {
  option msgid = 99;
  // No fields - just the message ID
}
```

Valid for signaling or keepalive.

### Large Messages

For messages > 255 bytes, use Extended payload type:

```bash
python -m struct_frame large.proto --build_c
# Use BasicExtended or Network frame profile
```

### Mixed Message Sizes

In systems with both small and large messages:
- Use Extended payload (supports 0-65535 bytes)
- Or use separate frame profiles for different message types

