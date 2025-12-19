# Framing

Framing wraps messages with headers and checksums so receivers can identify message boundaries and verify integrity.

## Quick Start: Choose Your Profile

Instead of choosing individual frame features, **use these intent-based profiles** that bundle common features for your use case:

### Standard Profiles

| Profile | Maps To | Overhead | Max Payload | Multi-Node | Reliability (Seq) | Use Case |
|---------|---------|----------|-------------|------------|-------------------|----------|
| **Profile.Standard** | `BasicDefault` | 6 bytes | 255 bytes | No | No | General Serial / UART |
| **Profile.Sensor** | `TinyDefault` | 5 bytes | 255 bytes | No | No | Low-Bandwidth / Radio |
| **Profile.IPC** | `NoneMinimal` | 1 byte | N/A | No | No | Trusted / Board-to-Board |
| **Profile.Bulk** | `BasicExtended` | 8 bytes | 64 KB | No | No | Firmware / File Transfer |
| **Profile.Fleet** | `BasicExtendedMultiSystemStream` | 11 bytes | 64 KB | Yes | Yes | Multi-Node Mesh / Swarm |

!!! tip "Interactive Calculator"
    Use the [Frame Profile Calculator](framing-calculator.md) to select features and see which profile matches your needs!

### Choose Your Frame: Decision Tree

```
START: What kind of system do you have?
│
├─ Do you need routing? (multi-node mesh, swarm)
│  └─ YES → Profile.Fleet (BasicExtendedMultiSystemStream)
│
├─ Is it a trusted internal link? (SPI, Shared Memory, Board-to-Board)
│  └─ YES → Profile.IPC (NoneMinimal)
│
├─ Are you bandwidth-starved? (radio, low-power sensors)
│  └─ YES → Profile.Sensor (TinyDefault)
│
├─ Are you sending files > 255B? (firmware updates, logs, bulk transfers)
│  └─ YES → Profile.Bulk (BasicExtended)
│
└─ None of the above?
   └─ Use Profile.Standard (BasicDefault) ← **RECOMMENDED**
```

### Visual Byte-Map Reference

Understanding how framing works helps when debugging with logic analyzers. Here's how headers wrap your payload like "onion layers":

#### Profile.Standard (BasicDefault) - 6 bytes overhead

```
┌────────┬────────┬────────┬────────┬─────────────────┬─────────┬─────────┐
│ START1 │ START2 │ LENGTH │ MSG_ID │ YOUR PAYLOAD    │  CRC1   │  CRC2   │
│  0x90  │  0x71  │ 1 byte │ 1 byte │   (variable)    │ 1 byte  │ 1 byte  │
└────────┴────────┴────────┴────────┴─────────────────┴─────────┴─────────┘
   ▲        ▲                           Actual data         ▲
   └────────┴─ Sync markers (find boundaries)               └─ Error detection
```

**Example frame for a 4-byte payload:**
```
 Byte:   0     1     2     3     4     5     6     7     8     9
       ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
       │ 90  │ 71  │ 04  │ 2A  │ 01  │ 02  │ 03  │ 04  │ 7F  │ 8A  │
       └─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
         │     │     │     │     └──── Payload (4 bytes) ────┘   │    │
         │     │     │     └─ Message ID = 42 (0x2A)             │    │
         │     │     └─ Length = 4 bytes                         │    │
         │     └─ Start byte 2 (0x71 = Default type)             │    │
         └─ Start byte 1 (0x90 = Basic frame)                    └────┘
                                                             CRC checksum
```

#### Profile.Sensor (TinyDefault) - 5 bytes overhead

```
┌────────┬────────┬────────┬─────────────────┬─────────┬─────────┐
│ START  │ LENGTH │ MSG_ID │ YOUR PAYLOAD    │  CRC1   │  CRC2   │
│  0x71  │ 1 byte │ 1 byte │   (variable)    │ 1 byte  │ 1 byte  │
└────────┴────────┴────────┴─────────────────┴─────────┴─────────┘
   ▲                            Actual data         ▲
   └─ Single sync byte (lower overhead)             └─ Error detection
```

#### Profile.IPC (NoneMinimal) - 1 byte overhead

```
┌────────┬─────────────────┐
│ MSG_ID │ YOUR PAYLOAD    │
│ 1 byte │   (variable)    │
└────────┴─────────────────┘
           Actual data

No framing overhead - for trusted internal links (SPI, Shared Memory)
```

#### Profile.Bulk (BasicExtended) - 8 bytes overhead

```
┌────────┬────────┬──────────┬──────────┬────────┬────────┬──────────┬──────┬──────┐
│ START1 │ START2 │ LEN_LO   │ LEN_HI   │ PKG_ID │ MSG_ID │ PAYLOAD  │ CRC1 │ CRC2 │
│  0x90  │  0x74  │  1 byte  │  1 byte  │ 1 byte │ 1 byte │ (64KB)   │ 1 B  │ 1 B  │
└────────┴────────┴──────────┴──────────┴────────┴────────┴──────────┴──────┴──────┘
                   └─ 16-bit length ──┘           └─ Package namespace
```

#### Profile.Fleet (BasicExtendedMultiSystemStream) - 11 bytes overhead

```
┌────────┬────────┬─────┬────────┬──────┬────────┬────────┬────────┬────────┬─────────┬─────┬─────┐
│ START1 │ START2 │ SEQ │ SYS_ID │ COMP │ LEN_LO │ LEN_HI │ PKG_ID │ MSG_ID │ PAYLOAD │ CRC1│ CRC2│
│  0x90  │  0x78  │ 1B  │  1B    │  1B  │  1B    │  1B    │  1B    │  1B    │ (64KB)  │ 1B  │ 1B  │
└────────┴────────┴─────┴────────┴──────┴────────┴────────┴────────┴────────┴─────────┴─────┴─────┘
                    ▲     └───────┴────┘  └─ 16-bit length ┘         └─ Package namespace
                    └─ Sequence for loss detection + Multi-node routing
```

---

## Framing Architecture

The framing system uses a two-level architecture:

1. **Frame Type** (Framer): Determines the number of start bytes for synchronization
   - **Basic**: 2 start bytes `[0x90] [0x70+PayloadType]`
   - **Tiny**: 1 start byte `[0x70+PayloadType]`
   - **None**: 0 start bytes (relies on external synchronization)

2. **Payload Type**: Defines the header/footer structure after start bytes
   - The second start byte of Basic (or the single start byte of Tiny) encodes the payload type
   - Payload type value is added to 0x70 base to get the start byte

## Frame Format Definitions

All supported frame formats are defined in [`examples/frame_formats.proto`](https://github.com/mylonics/struct-frame/blob/main/examples/frame_formats.proto). This file provides:

- Protocol Buffer definitions for each frame format
- Enumeration of frame types and payload types
- Configuration message for runtime format selection

## Start Byte Scheme

| PayloadType | Offset | Basic START2 / Tiny START | Payload Structure |
|-------------|--------|---------------------------|-------------------|
| Minimal | 0 | 0x70 | `[MSG_ID] [PACKET]` |
| Default | 1 | 0x71 | `[LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| ExtendedMsgIds | 2 | 0x72 | `[LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| ExtendedLength | 3 | 0x73 | `[LEN_LO] [LEN_HI] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| Extended | 4 | 0x74 | `[LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| SysComp | 5 | 0x75 | `[SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| Seq | 6 | 0x76 | `[SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| MultiSystemStream | 7 | 0x77 | `[SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| ExtendedMultiSystemStream | 8 | 0x78 | `[SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]` |

## Recommended Frame Formats

| Format | Start Bytes | Overhead | Use Case |
|--------|-------------|----------|----------|
| BasicDefault | 2 (0x90, 0x71) | 6 | **Recommended** - Standard format with length and CRC |
| TinyDefault | 1 (0x71) | 5 | Constrained environments, lower overhead |
| BasicSysComp | 2 (0x90, 0x75) | 8 | Multi-system networks |
| BasicMultiSystemStream | 2 (0x90, 0x77) | 9 | Multi-system with packet loss detection |
| BasicExtendedLength | 2 (0x90, 0x73) | 7 | Large payloads up to 64KB |

## Payload Types

### Minimal
**Format**: `[MSG_ID] [PACKET]`
- No length field, no CRC
- Requires known message sizes on both ends
- Minimal overhead (1 byte)
- Use for: Fixed-size messages in trusted environments

### Default (Recommended)
**Format**: `[LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]`
- 1-byte length field (up to 255 bytes)
- 2-byte Fletcher checksum
- Overhead: 4 bytes
- Use for: Most applications with variable-length messages

### ExtendedMsgIds
**Format**: `[LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]`
- Adds package ID for message namespace separation
- Allows 256 packages × 256 message IDs = 65536 message types
- Overhead: 5 bytes
- Use for: Large systems with many message types

### ExtendedLength
**Format**: `[LEN_LO] [LEN_HI] [MSG_ID] [PACKET] [CRC1] [CRC2]`
- 2-byte length field (up to 65535 bytes)
- Overhead: 5 bytes
- Use for: Large payloads, firmware updates, bulk transfers

### Extended
**Format**: `[LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]`
- Combines ExtendedMsgIds + ExtendedLength
- Overhead: 6 bytes
- Use for: Large systems with large payloads

### SysComp
**Format**: `[SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]`
- System ID identifies the vehicle/ground station (0-255)
- Component ID identifies the component (autopilot, camera, etc.)
- Overhead: 6 bytes
- Use for: Multi-vehicle networks, MAVLink-style routing

### Seq
**Format**: `[SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]`
- 1-byte sequence number for packet loss detection
- Overhead: 5 bytes
- Use for: Unreliable links where packet loss matters

### MultiSystemStream
**Format**: `[SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]`
- Combines Seq + SysComp
- Overhead: 7 bytes
- Use for: Multi-vehicle streaming with loss detection

### ExtendedMultiSystemStream
**Format**: `[SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]`
- Full-featured format with all extensions
- Overhead: 9 bytes
- Use for: Complex multi-system networks with large payloads

## Frame Types

### None Frame (0 start bytes)
For trusted point-to-point links where you control both ends.

Use cases:
- Direct function calls between components
- Shared memory between processes
- When another protocol already handles framing

Limitations:
- No message boundary detection
- Must synchronize externally

### Tiny Frame (1 start byte)
Low overhead framing for constrained environments.

```
[START=0x70+PayloadType] [PAYLOAD...]
```

- 1 byte header overhead
- Suitable for: Battery-powered devices, high message rates

### Basic Frame (2 start bytes)
The recommended frame format for most applications:

```
[START1=0x90] [START2=0x70+PayloadType] [PAYLOAD...]
```

- 2 bytes header overhead
- Better synchronization recovery than Tiny
- Recommended for: Most serial and network communication

## Basic Default Frame Example

The most common frame format (BasicDefault):

```
[0x90] [0x71] [LEN] [MSG_ID] [Payload Data...] [CRC1] [CRC2]
  ^      ^      ^      ^           ^              ^      ^
  |      |      |      |           |              |      |
Start1  Start2 Length MsgID    Variable        Fletcher-16
```

### Example

Message: VehicleHeartbeat (ID=42) with 4-byte payload [0x01, 0x02, 0x03, 0x04]

```
Frame: [0x90] [0x71] [0x04] [0x2A] [0x01, 0x02, 0x03, 0x04] [0x7F] [0x8A]
        Start1 Start2  Len    ID         Payload              Checksum
```

Total bytes = 2 (start) + 1 (len) + 1 (id) + 4 (payload) + 2 (crc) = 10 bytes

## Parser State Machine

The parser implements a state machine for Basic/Tiny frames:

```
States:
  LOOKING_FOR_START -> GETTING_HEADER -> GETTING_PAYLOAD
                  ^                            |
                  |____________________________|
                        (on complete or error)
```

**LOOKING_FOR_START** (Basic/Tiny only)
- Scans incoming bytes for start byte(s)
- Basic: looks for 0x90 then 0x7X
- Tiny: looks for 0x7X
- Discards other bytes

**GETTING_HEADER**
- Reads header fields (length, msg_id, etc.)
- Validates values
- Transitions to GETTING_PAYLOAD if valid

**GETTING_PAYLOAD**
- Collects payload bytes
- Collects CRC bytes (if applicable)
- Validates checksum on completion
- Returns to LOOKING_FOR_START

## CRC Check

The Fletcher-16 checksum provides error detection:

```
sum1 = 0
sum2 = 0
for each byte in (header_after_start + payload):
    sum1 = (sum1 + byte) % 256
    sum2 = (sum2 + sum1) % 256
checksum = [sum1, sum2]
```

## Third Party Protocols

| Format | Start Bytes | Length | CRC | Total Overhead | Use Case |
|--------|-------------|--------|-----|----------------|----------|
| UBX | 2 (0xB5, 0x62) | 2 | 2 | 8 | u-blox GPS compatibility |
| MavlinkV1 | 1 (0xFE) | 1 | 2 | 8 | Legacy drone communication |
| MavlinkV2 | 1 (0xFD) | 1 | 2-15 | 12-25 | Modern drone communication |

### UBX Format

u-blox proprietary binary protocol for GPS/GNSS receivers:

```
[SYNC1 (0xB5)] [SYNC2 (0x62)] [CLASS (1)] [ID (1)] [LEN (2)] [PAYLOAD] [CK_A] [CK_B]
```

### MAVLink v1

Legacy drone communication protocol:

```
[STX (0xFE)] [LEN (1)] [SEQ (1)] [SYS (1)] [COMP (1)] [MSG (1)] [PAYLOAD] [CRC (2)]
```

### MAVLink v2

Modern drone communication with extended features:

```
[STX (0xFD)] [LEN (1)] [INCOMPAT (1)] [COMPAT (1)] [SEQ (1)] [SYS (1)] [COMP (1)] [MSG_ID (3)] [PAYLOAD] [CRC (2)] [SIGNATURE (13, optional)]
```

## Complete Frame Format Reference

### None Frames (0 start bytes)

| Format | Overhead | Structure |
|--------|----------|-----------|
| NoneMinimal | 1 | `[MSG_ID] [PACKET]` |
| NoneDefault | 4 | `[LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| NoneExtendedMsgIds | 5 | `[LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| NoneExtendedLength | 5 | `[LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| NoneExtended | 6 | `[LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| NoneSysComp | 6 | `[SYS] [COMP] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| NoneSeq | 5 | `[SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| NoneMultiSystemStream | 7 | `[SEQ] [SYS] [COMP] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| NoneExtendedMultiSystemStream | 9 | `[SEQ] [SYS] [COMP] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]` |

### Tiny Frames (1 start byte: 0x70+PayloadType)

| Format | Start | Overhead | Structure |
|--------|-------|----------|-----------|
| TinyMinimal | 0x70 | 2 | `[START] [MSG_ID] [PACKET]` |
| TinyDefault | 0x71 | 5 | `[START] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| TinyExtendedMsgIds | 0x72 | 6 | `[START] [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| TinyExtendedLength | 0x73 | 6 | `[START] [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| TinyExtended | 0x74 | 7 | `[START] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| TinySysComp | 0x75 | 7 | `[START] [SYS] [COMP] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| TinySeq | 0x76 | 6 | `[START] [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| TinyMultiSystemStream | 0x77 | 8 | `[START] [SEQ] [SYS] [COMP] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| TinyExtendedMultiSystemStream | 0x78 | 10 | `[START] [SEQ] [SYS] [COMP] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]` |

### Basic Frames (2 start bytes: 0x90, 0x70+PayloadType)

| Format | Start2 | Overhead | Structure |
|--------|--------|----------|-----------|
| BasicMinimal | 0x70 | 3 | `[0x90] [START2] [MSG_ID] [PACKET]` |
| BasicDefault | 0x71 | 6 | `[0x90] [START2] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| BasicExtendedMsgIds | 0x72 | 7 | `[0x90] [START2] [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| BasicExtendedLength | 0x73 | 7 | `[0x90] [START2] [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| BasicExtended | 0x74 | 8 | `[0x90] [START2] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| BasicSysComp | 0x75 | 8 | `[0x90] [START2] [SYS] [COMP] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| BasicSeq | 0x76 | 7 | `[0x90] [START2] [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| BasicMultiSystemStream | 0x77 | 9 | `[0x90] [START2] [SEQ] [SYS] [COMP] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]` |
| BasicExtendedMultiSystemStream | 0x78 | 11 | `[0x90] [START2] [SEQ] [SYS] [COMP] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]` |

## Framing Compatibility

| Frame Format | C | C++ | TypeScript | Python |
|--------------|---|-----|------------|--------|
| None Frames | Yes | Yes | Yes | Yes |
| Basic Frames | Yes | Yes | Yes | Yes |
| Tiny Frames | Yes | Yes | Yes | Yes |
| UBX | Defined | Defined | Defined | Defined |
| Mavlink v1 | Defined | Defined | Defined | Defined |
| Mavlink v2 | Defined | Defined | Defined | Defined |

**Legend:**
- **Yes**: Fully implemented runtime support
- **Defined**: Frame format defined in proto, implementation pending

All frame formats are binary compatible across languages. A frame created in Python can be parsed in C and vice versa.
