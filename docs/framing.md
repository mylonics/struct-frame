# Framing

Framing wraps messages with headers and checksums so receivers can identify message boundaries and verify integrity.

## Frame Format Definitions

All supported frame formats are defined in [`examples/frame_formats.proto`](../examples/frame_formats.proto). This file provides:

- Protocol Buffer definitions for each frame format
- Enumeration of all frame format types
- Configuration message for runtime format selection

## Recommended Frame Formats

| Format | Preamble | Header | CRC | Length | Total Overhead | Use Case |
|--------|----------|--------|-----|--------|----------------|----------|
| NoFormat | 0 | 0 | 0 | None | 0 | Trusted links, nested protocols |
| BasicFrame | 1 | 2 | 2 | None | 4 | Standard reliable communication |
| BasicFrameLen8 | 1 | 3 | 2 | 8-bit | 5 | Variable length messages |

## All Frame Formats

| Format | Preamble | Header | CRC | Length | Total Overhead | Use Case |
|--------|----------|--------|-----|--------|----------------|----------|
| NoFormat | 0 | 0 | 0 | None | 0 | Trusted links, nested protocols |
| MsgIdFrame | 0 | 1 | 2 | None | 3 | Minimal framing with CRC |
| MsgIdFrameNoCrc | 0 | 1 | 0 | None | 1 | Minimal framing, trusted link |
| MsgIdFrameLen8 | 0 | 2 | 2 | 8-bit | 4 | Variable length, minimal |
| MsgIdFrameLen8NoCrc | 0 | 2 | 0 | 8-bit | 2 | Variable length, no CRC |
| MsgIdFrameLen16 | 0 | 3 | 2 | 16-bit | 5 | Large payloads, minimal |
| MsgIdFrameLen16NoCrc | 0 | 3 | 0 | 16-bit | 3 | Large payloads, no CRC |
| BasicFrame | 1 | 2 | 2 | None | 4 | Standard reliable communication |
| BasicFrameNoCrc | 1 | 2 | 0 | None | 2 | Sync recovery, no CRC |
| BasicFrameLen8 | 1 | 3 | 2 | 8-bit | 5 | Variable length messages |
| BasicFrameLen8NoCrc | 1 | 3 | 0 | 8-bit | 3 | Variable length, no CRC |
| BasicFrameLen16 | 1 | 4 | 2 | 16-bit | 6 | Large payload messages |
| BasicFrameLen16NoCrc | 1 | 4 | 0 | 16-bit | 4 | Large payloads, no CRC |
| TinyFrame | 1 | 2 | 2 | None | 4 | Constrained environments |
| TinyFrameNoCrc | 1 | 2 | 0 | None | 2 | Minimal overhead |
| TinyFrameLen8 | 1 | 3 | 2 | 8-bit | 5 | Variable length, constrained |
| TinyFrameLen8NoCrc | 1 | 3 | 0 | 8-bit | 3 | Variable, minimal overhead |
| TinyFrameLen16 | 1 | 4 | 2 | 16-bit | 6 | Large payloads, constrained |
| TinyFrameLen16NoCrc | 1 | 4 | 0 | 16-bit | 4 | Large, minimal overhead |

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

## MSG ID Frame Variants

Minimal framing with just message ID and optional CRC:

**MsgIdFrame**: `[MSG_ID (1)] [PAYLOAD] [CRC (2)]`
- 3 bytes overhead
- For synchronized links with error detection

**MsgIdFrameNoCrc**: `[MSG_ID (1)] [PAYLOAD]`
- 1 byte overhead
- For trusted, synchronized links

## Tiny Frame Variants

Low overhead framing for constrained environments:

**TinyFrame**: `[START (1)] [MSG_ID (1)] [PAYLOAD] [CRC (2)]`
- 4 bytes overhead
- Battery-powered devices, high message rates

**TinyFrameNoCrc**: `[START (1)] [MSG_ID (1)] [PAYLOAD]`
- 2 bytes overhead
- Minimal overhead with sync recovery

## Length-Prefixed Variants

All frame formats have variants with explicit length fields:

**8-bit length (Len8)**: Supports payloads up to 255 bytes
- Adds 1 byte to header
- Use for variable-length messages

**16-bit length (Len16)**: Supports payloads up to 65,535 bytes
- Adds 2 bytes to header (little-endian)
- Use for large data transfers, firmware updates

Example: `BasicFrameLen16`
```
[START (1)] [MSG_ID (1)] [LEN_LO (1)] [LEN_HI (1)] [PAYLOAD] [CRC (2)]
```

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

## Third Party Protocols

| Format | Preamble | Header | CRC | Length | Total Overhead | Use Case |
|--------|----------|--------|-----|--------|----------------|----------|
| UBX | 2 | 6 | 2 | 16-bit | 8 | u-blox GPS compatibility |
| MavlinkV1 | 1 | 6 | 2 | 8-bit | 8 | Legacy drone communication |
| MavlinkV2 | 1 | 10 | 2-15 | 8-bit | 12-25 | Modern drone communication |

### UBX Format

u-blox proprietary binary protocol for GPS/GNSS receivers:

```
[SYNC1 (0xB5)] [SYNC2 (0x62)] [CLASS (1)] [ID (1)] [LEN (2)] [PAYLOAD] [CK_A] [CK_B]
```

- 8 bytes overhead
- Class + ID for message routing
- Fletcher-8 checksum
- Use for u-blox GPS integration

### MAVLink v1

Legacy drone communication protocol:

```
[STX (0xFE)] [LEN (1)] [SEQ (1)] [SYS (1)] [COMP (1)] [MSG (1)] [PAYLOAD] [CRC (2)]
```

- 8 bytes overhead
- Sequence counter for packet loss detection
- System ID and Component ID for multi-vehicle networks
- CRC-16/X.25 checksum
- Use for ArduPilot/PX4 compatibility

### MAVLink v2

Modern drone communication with extended features:

```
[STX (0xFD)] [LEN (1)] [INCOMPAT (1)] [COMPAT (1)] [SEQ (1)] [SYS (1)] [COMP (1)] [MSG_ID (3)] [PAYLOAD] [CRC (2)] [SIGNATURE (13, optional)]
```

- 12-25 bytes overhead
- 24-bit message ID (16.7M message types)
- Incompatibility/compatibility flags for version negotiation
- Optional 13-byte signature for authentication
- Use for secure drone communication

## Framing Compatibility

| Frame Format | C | C++ | TypeScript | Python |
|--------------|---|-----|------------|--------|
| No Header (No Framing) | Yes | Yes | Yes | Yes |
| Basic Frame Format | Yes | Yes | Yes | Yes |
| MSG ID Frames | Defined | Defined | Defined | Defined |
| Tiny Frames | Defined | Defined | Defined | Defined |
| Length-Prefixed | Defined | Defined | Defined | Defined |
| UBX | Defined | Defined | Defined | Defined |
| Mavlink v1 | Defined | Defined | Defined | Defined |
| Mavlink v2 | Defined | Defined | Defined | Defined |

**Legend:**
- **Yes**: Fully implemented runtime support
- **Defined**: Frame format defined in proto, implementation pending

All frame formats are binary compatible across languages. A frame created in Python can be parsed in C and vice versa.
