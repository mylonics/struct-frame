# Framing Details

This page covers the technical details of the framing system.

## Frame Components

Frames consist of two parts:

1. **Header**: Determines sync bytes and addressing
2. **Payload**: Determines length encoding and checksum

## Header Types

### Basic Header (2 bytes)
```
[0x90] [0x70 + PayloadType]
```
Two-byte sync for reliable synchronization. Recommended for most applications.

### Tiny Header (1 byte)
```
[0x70 + PayloadType]
```
Single-byte sync for bandwidth-limited scenarios.

### None Header (0 bytes)
```
(no header)
```
For trusted links where synchronization isn't needed.

## Payload Types

### Minimal
```
[MSG_ID] [PAYLOAD...]
```
1 byte overhead. Requires message length lookup. No checksum or length field.

### Default
```
[LENGTH] [MSG_ID] [PAYLOAD...] [CRC_HI] [CRC_LO]
```
4 bytes overhead. Includes length (1 byte, max 255) and Fletcher-16 checksum.

### Extended
```
[LENGTH_HI] [LENGTH_LO] [MSG_ID] [PAYLOAD...] [CRC_HI] [CRC_LO]
```
5 bytes overhead. 16-bit length field (max 65535 bytes).

### ExtendedMultiSystemStream
```
[LENGTH_HI] [LENGTH_LO] [SRC] [DST] [SEQ] [MSG_ID] [PAYLOAD...] [CRC_HI] [CRC_LO]
```
8 bytes overhead. Adds source/destination addresses and sequence numbers for multi-node networks.

## Frame Profiles

Profiles combine header + payload types:

| Profile | Header | Payload | Total Overhead |
|---------|--------|---------|----------------|
| Standard | Basic | Default | 6 bytes |
| Sensor | Tiny | Minimal | 2 bytes |
| IPC | None | Minimal | 1 byte |
| Bulk | Basic | Extended | 8 bytes |
| Network | Basic | ExtendedMultiSystemStream | 11 bytes |

## Checksum (Fletcher-16)

The Default and Extended payload types use Fletcher-16 checksum.

**Magic Numbers:**
- Basic frame start: `0x90` followed by `0x70 + PayloadType`
- Tiny frame start: `0x70 + PayloadType`
- Payload type base value: `0x70`

The checksum algorithm:

```
For each byte in [LENGTH, MSG_ID, PAYLOAD]:
    sum1 = (sum1 + byte) mod 255
    sum2 = (sum2 + sum1) mod 255
checksum = (sum2 << 8) | sum1
```

## Parser State Machine

The parser implements a state machine:

```
IDLE → wait for start byte(s)
HEADER → read header bytes
PAYLOAD → read length, msg_id, data
CHECKSUM → verify CRC
COMPLETE → return message
```

For Minimal payloads, the parser requires a message length callback to determine payload size.

## Usage in C++

```cpp
#include "FrameProfiles.hpp"

using namespace FrameParsers;

// Using profiles
uint8_t buffer[1024];
ProfileStandardWriter writer(buffer, sizeof(buffer));
ProfileStandardAccumulatingReader reader;

// Encode
writer.write(msg);
send_data(writer.buffer(), writer.size());

// Decode (streaming)
while (receiving) {
    if (auto result = reader.push_byte(read_byte())) {
        handle_message(result.msg_id, result.msg_data, result.msg_len);
    }
}

// Decode (buffer)
reader.add_data(buffer, buffer_size);
while (auto result = reader.next()) {
    handle_message(result.msg_id, result.msg_data, result.msg_len);
}
```

## Usage in Python

```python
from struct_frame_parser import Parser, HeaderType, PayloadType

# Create parser with specific frame types
parser = Parser(
    enabled_headers=[HeaderType.BASIC, HeaderType.TINY],
    enabled_payloads=[PayloadType.DEFAULT, PayloadType.EXTENDED]
)

# Encode
frame = parser.encode(
    msg_id=42,
    msg=b"payload data",
    header_type=HeaderType.BASIC,
    payload_type=PayloadType.DEFAULT
)

# Decode (byte-by-byte)
for byte in incoming_data:
    result = parser.parse_byte(byte)
    if result.valid:
        handle_message(result)
```

## Custom Profiles

Create custom frame formats by combining header and payload types:

=== "C++"
    ```cpp
    // Custom: Tiny header with Extended payload
    using CustomConfig = FrameConfig<
        HeaderTiny,
        PayloadExtended
    >;
    
    FrameEncoderWithCrc<CustomConfig> encoder;
    BufferParserWithCrc<CustomConfig> parser;
    ```

=== "Python"
    ```python
    from struct_frame_parser import create_custom_profile, HeaderType, PayloadType
    
    custom = create_custom_profile(
        "TinyExtended",
        HeaderType.TINY,
        PayloadType.EXTENDED
    )
    ```

