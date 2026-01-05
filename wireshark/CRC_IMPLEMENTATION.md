# CRC Calculation in Struct Frame

This document explains how the Fletcher-16 checksum is calculated in the Struct Frame protocol.

## Fletcher-16 Algorithm

The Fletcher-16 checksum used by Struct Frame is a simple two-byte checksum algorithm:

```python
def fletcher16(data):
    """Calculate Fletcher-16 checksum."""
    sum1 = 0
    sum2 = 0
    for byte in data:
        sum1 = (sum1 + byte) % 256
        sum2 = (sum2 + sum1) % 256
    return sum1, sum2
```

## What Data Is Included in the CRC

The CRC is calculated over **all frame data after the start bytes, excluding the CRC itself**.

### BasicDefault (Profile.STANDARD)

Frame structure: `[0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD...] [CRC1] [CRC2]`

CRC is calculated over: `[LEN] [MSG_ID] [PAYLOAD...]`
- Start offset: 2 (after the two start bytes)
- End offset: frame_length - 2 (before the CRC bytes)

**Example:**
```
Frame: 90 71 04 2a 01 02 03 04 38 fe
       │   │   └───── CRC data ──────┘ └─┘
       │   │                            CRC
       └───┘ Start bytes (excluded from CRC)

CRC input: [0x04, 0x2A, 0x01, 0x02, 0x03, 0x04]
Fletcher-16: sum1=0x38, sum2=0xFE
```

### BasicExtended (Profile.BULK)

Frame structure: `[0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD...] [CRC1] [CRC2]`

CRC is calculated over: `[LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD...]`
- Start offset: 2 (after the two start bytes)
- End offset: frame_length - 2 (before the CRC bytes)

**Example:**
```
Frame: 90 74 04 00 01 2a 01 02 03 04 39 0c
       │   │   └──────── CRC data ────────┘ └─┘
       │   │                                  CRC
       └───┘ Start bytes (excluded from CRC)

CRC input: [0x04, 0x00, 0x01, 0x2A, 0x01, 0x02, 0x03, 0x04]
Fletcher-16: sum1=0x39, sum2=0x0C
```

### BasicExtendedMultiSystemStream (Profile.NETWORK)

Frame structure: `[0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD...] [CRC1] [CRC2]`

CRC is calculated over: `[SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD...]`
- Start offset: 2 (after the two start bytes)
- End offset: frame_length - 2 (before the CRC bytes)

**Example:**
```
Frame: 90 78 05 01 02 04 00 01 2a 01 02 03 04 41 5f
       │   │   └────────────── CRC data ──────────┘ └─┘
       │   │                                          CRC
       └───┘ Start bytes (excluded from CRC)

CRC input: [0x05, 0x01, 0x02, 0x04, 0x00, 0x01, 0x2A, 0x01, 0x02, 0x03, 0x04]
Fletcher-16: sum1=0x41, sum2=0x5F
```

### TinyMinimal (Profile.SENSOR)

Frame structure: `[0x70] [MSG_ID] [PAYLOAD...]`

This profile has **no CRC**. The minimal overhead is achieved by omitting error detection.

## Implementation Notes

### In the Wireshark Dissector

The dissector calculates the CRC over the same range:

```lua
-- For Basic frames
local crc_start_offset = 2  -- After start bytes
local crc_data_len = offset - crc_start_offset
local crc_data = buffer(crc_start_offset, crc_data_len)
local calc_crc1, calc_crc2 = fletcher16(crc_data)
```

### In the Test Generator

The test packet generator follows the same pattern:

```python
# For BasicDefault
frame = bytearray([0x90, 0x71])  # Start bytes
frame.append(len(payload))        # Length
frame.append(msg_id)              # Message ID
frame.extend(payload)             # Payload data

# Calculate CRC over everything after start bytes
crc_data = bytes([len(payload), msg_id]) + payload
crc1, crc2 = fletcher16(crc_data)

frame.extend([crc1, crc2])        # Add CRC
```

## Validation

The `validate_packets.py` script verifies that CRC calculations are correct by:

1. Reading the generated binary packet
2. Extracting the CRC data range (after start bytes, before CRC)
3. Calculating Fletcher-16 over that range
4. Comparing with the received CRC bytes

All tests pass, confirming the implementation is correct.

## Reference Implementation

The authoritative implementation is in the generated Python parser code (`parser.py`):

```python
# From generated code
crc_start = header_size  # 2 for Basic, 1 for Tiny
crc_end = len(self.buffer) - config.crc_bytes
calc_crc = fletcher_checksum(self.buffer, crc_start, crc_end)
recv_crc = (self.buffer[-2], self.buffer[-1])
if calc_crc != recv_crc:
    # CRC validation failed
    self.reset()
```

This confirms that:
- CRC starts after the header (start bytes)
- CRC ends before the CRC bytes themselves
- CRC includes: payload header fields + message ID + payload data
