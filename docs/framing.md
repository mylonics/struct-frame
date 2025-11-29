# Framing

Framing wraps messages with headers and checksums so receivers can identify message boundaries and verify integrity.

## No Frame Format

For trusted point-to-point links where you control both ends, you can skip framing entirely. Messages are sent as raw bytes with no header or checksum.

Use cases:
- Direct function calls between components
- Shared memory between processes
- When another protocol already handles framing and packeting

Limitations:
- No message boundary detection
- No error detection
- Must know message type externally

## Basic Frame Format

The default frame format used by Struct Frame:

```
[Start Byte] [Message ID] [Payload Data...] [Checksum 1] [Checksum 2]
     0x90        1 byte     Variable Length     1 byte      1 byte
```

### Components

**Start Byte (0x90)**
- Fixed marker to identify frame boundaries
- Parser scans for this byte to synchronize
- Allows recovery after corruption

**Message ID (1 byte)**
- Maps to specific message type defined in proto
- Range 0-255
- Must match `option msgid = X` in proto definition

**Payload**
- Raw serialized message data
- Variable length depending on message type
- Little-endian byte order

**Fletcher Checksum (2 bytes)**
- Fletcher-16 algorithm
- Calculated over Message ID + Payload
- Detects single-bit errors and most multi-bit errors

### Example

Message: VehicleHeartbeat (ID=42) with payload [0x01, 0x02, 0x03, 0x04]

```
Frame: [0x90] [0x2A] [0x01, 0x02, 0x03, 0x04] [0x7F] [0x8A]
        Start   ID         Payload              Checksum
```

### Frame Size

Total bytes = 2 (header) + payload size + 2 (checksum)

For a message with 5 bytes of data: 2 + 5 + 2 = 9 bytes total

## Parser State Machine

The parser implements a state machine to handle partial data and recover from corruption:

```
States:
  LOOKING_FOR_START_BYTE -> GETTING_HEADER -> GETTING_PAYLOAD
                  ^                                  |
                  |__________________________________|
                        (on complete or error)
```

**LOOKING_FOR_START_BYTE**
- Scans incoming bytes for 0x90
- Discards all other bytes
- Transitions to GETTING_HEADER on match

**GETTING_HEADER**
- Reads message ID
- Looks up expected message size
- Transitions to GETTING_PAYLOAD if valid
- Returns to LOOKING_FOR_START_BYTE if invalid

**GETTING_PAYLOAD**
- Collects payload bytes
- Collects checksum bytes
- Validates checksum on completion
- Returns to LOOKING_FOR_START_BYTE

This handles:
- Partial frame reception (data arrives in chunks)
- Frame corruption (invalid start bytes, bad checksums)
- Synchronization loss (automatic recovery)

## CRC Check

The Fletcher-16 checksum provides error detection:

```
sum1 = 0
sum2 = 0
for each byte in (message_id + payload):
    sum1 = (sum1 + byte) % 256
    sum2 = (sum2 + sum1) % 256
checksum = [sum1, sum2]
```

## Custom Frame Formats

The architecture supports alternative frame formats. Planned implementations:

**UBX Format**
- Used by u-blox GPS receivers
- 2-byte sync sequence (0xB5, 0x62)
- Class + ID message identification
- Little-endian 2-byte length field
- Fletcher-8 checksum

**Mavlink v1**
- Used by ArduPilot and PX4
- 0xFE start byte
- Sequence counter
- System ID and Component ID
- CRC-16 checksum

**Mavlink v2**
- 0xFD start byte
- Incompatibility flags
- Compatibility flags
- Optional signature for authentication

## Framing Compatibility

| Frame Format | C | C++ | TypeScript | Python |
|--------------|---|-----|------------|--------|
| No Header (No Framing) | Yes | Yes | Yes | Yes |
| Basic Frame Format | Yes | Yes | Yes | Yes |
| UBX | Planned | Planned | Planned | Planned |
| Mavlink v1 | Planned | Planned | Planned | Planned |
| Mavlink v2 | Planned | Planned | Planned | Planned |

All frame formats are binary compatible across languages. A frame created in Python can be parsed in C and vice versa.
