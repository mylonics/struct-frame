# Framing

Framing wraps messages with headers and checksums so receivers can identify message boundaries and verify integrity.

## Quick Start: Choose Your Profile

Instead of choosing individual frame features, **use these intent-based profiles** that bundle common features for your use case:

### Standard Profiles

| Profile | Maps To | Overhead | Max Payload | Multi-Node | Reliability (Seq) | Use Case |
|---------|---------|----------|-------------|------------|-------------------|----------|
| **Profile.Standard** | `BasicDefault` | 6 bytes | 255 bytes | No | No | General Serial / UART |
| **Profile.Sensor** | `TinyDefault` | 4 bytes | 255 bytes | No | No | Low-Bandwidth / Radio |
| **Profile.IPC** | `NoneMinimal` | 1 byte | N/A | No | No | Trusted / Board-to-Board |
| **Profile.Bulk** | `BasicExtended` | 8 bytes | 64 KB | No | No | Firmware / File Transfer |
| **Profile.Network** | `BasicExtendedMultiSystemStream` | 11 bytes | 64 KB | Yes | Yes | Multi-Node Mesh / Swarm |

!!! tip "Interactive Calculator"
    Use the [Frame Profile Calculator](framing-calculator.md) to select features and see which profile matches your needs!

### Choose Your Frame: Decision Tree

```
START: What kind of system do you have?
│
├─ Do you need routing? (multi-node mesh, swarm)
│  └─ YES → Profile.Network (BasicExtendedMultiSystemStream)
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

#### Profile.Sensor (TinyDefault) - 4 bytes overhead

```
┌────────┬────────┬─────────────────┬─────────┬─────────┐
│ START  │ LENGTH │ YOUR PAYLOAD    │  CRC1   │  CRC2   │
│  0x71  │ 1 byte │   (variable)    │ 1 byte  │ 1 byte  │
└────────┴────────┴─────────────────┴─────────┴─────────┘
   ▲                  Actual data         ▲
   └─ Single sync byte (lower overhead)   └─ Error detection
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
┌────────┬────────┬──────────┬──────────┬────────┬────────┬──────────┬──────────┬──────────┐
│ START1 │ START2 │ LEN_LO   │ LEN_HI   │ PKG_ID │ MSG_ID │ PAYLOAD  │   CRC1   │   CRC2   │
│  0x90  │  0x74  │  1 byte  │  1 byte  │ 1 byte │ 1 byte │ (64KB)   │  1 byte  │  1 byte  │
└────────┴────────┴──────────┴──────────┴────────┴────────┴──────────┴──────────┴──────────┘
                   └─ 16-bit length ──┘           └─ Package namespace
```

#### Profile.Network (BasicExtendedMultiSystemStream) - 11 bytes overhead

```
┌────────┬────────┬──────────┬────────┬──────────┬────────┬────────┬────────┬────────┬─────────┬──────────┬──────────┐
│ START1 │ START2 │   SEQ    │ SYS_ID │   COMP   │ LEN_LO │ LEN_HI │ PKG_ID │ MSG_ID │ PAYLOAD │   CRC1   │   CRC2   │
│  0x90  │  0x78  │  1 byte  │ 1 byte │  1 byte  │ 1 byte │ 1 byte │ 1 byte │ 1 byte │ (64KB)  │  1 byte  │  1 byte  │
└────────┴────────┴──────────┴────────┴──────────┴────────┴────────┴────────┴────────┴─────────┴──────────┴──────────┘
                      ▲        └────────┴────────┘ └─ 16-bit length ┘         └─ Package namespace
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

For more detailed information about the framing system architecture, payload types, frame types, and complete format reference, see the [Framing Architecture](framing-architecture.md) guide.

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
