# Framing

Framing wraps messages with headers and checksums so receivers can identify message boundaries and verify integrity.

## Quick Start: Choose Your Profile

Instead of choosing individual frame features, **use these intent-based profiles** that bundle common features for your use case:

### Standard Profiles

| Profile | Maps To | Overhead | Max Payload | Multi-Node | Reliability (Seq) | Use Case |
|---------|---------|----------|-------------|------------|-------------------|----------|
| **Profile.Standard** | `BasicDefault` | 6 bytes | 255 bytes | No | No | General Serial / UART |
| **Profile.Sensor** | `TinyMinimal` | 2 bytes | N/A | No | No | Low-Bandwidth / Radio |
| **Profile.IPC** | `NoneMinimal` | 1 byte | N/A | No | No | Trusted / Board-to-Board |
| **Profile.Bulk** | `BasicExtended` | 8 bytes | 64 KB | No | No | Firmware / File Transfer |
| **Profile.Network** | `BasicExtendedMultiSystemStream` | 11 bytes | 64 KB | Yes | Yes | Multi-Node Mesh / Swarm |

!!! tip "Interactive Calculator"
    Use the [Frame Profile Calculator](framing-calculator.md) to select features and see which profile matches your needs!

!!! example "Using Profiles in Code"
    ```python
    from struct_frame.frame_formats import Profile, get_profile
    
    # Get a standard profile
    standard = get_profile(Profile.STANDARD)
    print(f"Overhead: {standard.total_overhead} bytes")  # 6 bytes
    
    # Or create a custom profile
    from struct_frame.frame_formats import create_custom_profile, HeaderType, PayloadType
    custom = create_custom_profile("TinyDefault", HeaderType.TINY, PayloadType.DEFAULT)
    ```
    
    See [examples/frame_format_profiles.py](https://github.com/mylonics/struct-frame/blob/main/examples/frame_format_profiles.py) for more examples.

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
│  └─ YES → Profile.Sensor (TinyMinimal)
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

#### Profile.Sensor (TinyMinimal) - 2 bytes overhead

```
┌────────┬────────┬─────────────────┐
│ START  │ MSG_ID │ YOUR PAYLOAD    │
│  0x70  │ 1 byte │   (variable)    │
└────────┴────────┴─────────────────┘
   ▲                  Actual data
   └─ Single sync byte (minimal overhead)
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

**Important**: Minimal frames (Profile.Sensor and Profile.IPC) don't include a length field. You must provide a callback function that returns the expected message length for each message ID. See the [Minimal Frames Guide](minimal-frames.md) for details.

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

---

## Using Profile Encode/Parse Functions

Each language provides ready-to-use encode and parse functions for all 5 standard profiles. These functions are thin wrappers around a generic implementation, maximizing code reuse.

### C Example

```c
#include "frame_profiles.h"

// Encode using Profile Standard
uint8_t buffer[256];
uint8_t payload[] = {0x01, 0x02, 0x03, 0x04};
size_t len = encode_profile_standard(buffer, sizeof(buffer), 
                                     42,           // msg_id
                                     payload, 4);  // payload, size

// Parse Profile Standard
frame_msg_info_t info = parse_profile_standard_buffer(buffer, len);
if (info.valid) {
    printf("Received msg_id=%d, len=%zu\n", info.msg_id, info.msg_len);
}

// Encode using Profile Bulk (with package ID)
len = encode_profile_bulk(buffer, sizeof(buffer),
                          1,             // pkg_id
                          42,            // msg_id
                          payload, 4);   // payload, size

// Encode using Profile Network (with routing)
len = encode_profile_network(buffer, sizeof(buffer),
                             0,           // sequence
                             1,           // system_id
                             2,           // component_id
                             3,           // pkg_id
                             42,          // msg_id
                             payload, 4); // payload, size
```

### C++ Example

```cpp
#include "FrameProfiles.hpp"
using namespace FrameParsers;

// Encode using Profile Standard
uint8_t buffer[256];
uint8_t payload[] = {0x01, 0x02, 0x03, 0x04};
size_t len = encode_profile_standard(buffer, sizeof(buffer), 42, payload, 4);

// Parse Profile Standard
FrameMsgInfo info = parse_profile_standard_buffer(buffer, len);
if (info.valid) {
    std::cout << "Received msg_id=" << (int)info.msg_id << std::endl;
}

// Using template-based API for custom configurations
using MyConfig = FrameFormatConfig<2, 0x90, 0x71, 4, 2, true, 1, true, false, false, false, false>;
size_t len2 = FrameEncoderWithCrc<MyConfig>::encode(buffer, sizeof(buffer), 
                                                     0, 0, 0, 0, 42, payload, 4);
```

### Python Example

```python
from struct_frame.boilerplate.py import (
    encode_profile_standard, parse_profile_standard_buffer,
    encode_profile_bulk, parse_profile_bulk_buffer,
    encode_profile_network, parse_profile_network_buffer,
    # For custom configurations
    FrameFormatConfig, encode_frame, parse_frame_buffer, create_custom_config
)

# Encode using Profile Standard
payload = bytes([0x01, 0x02, 0x03, 0x04])
frame = encode_profile_standard(msg_id=42, payload=payload)

# Parse Profile Standard
result = parse_profile_standard_buffer(frame)
if result.valid:
    print(f"Received msg_id={result.msg_id}, len={result.msg_len}")

# Encode using Profile Bulk (with package ID)
frame = encode_profile_bulk(msg_id=42, payload=payload, pkg_id=1)

# Encode using Profile Network (with routing)
frame = encode_profile_network(
    msg_id=42, payload=payload,
    seq=0, sys_id=1, comp_id=2, pkg_id=3
)

# Create a custom configuration
custom = create_custom_config(
    name="MyCustomFormat",
    header_type=HeaderType.BASIC,
    payload_type=PayloadType.DEFAULT,
    has_length=True, length_bytes=1,
    has_crc=True, has_pkg_id=False
)
frame = encode_frame(custom, msg_id=42, payload=payload)
```

### C# Example

```csharp
using StructFrame;

// Create parsers for each profile
var standardParser = FrameProfiles.CreateStandardParser();
var bulkParser = FrameProfiles.CreateBulkParser();
var networkParser = FrameProfiles.CreateNetworkParser();

// Encode using Profile Standard
byte[] payload = new byte[] { 0x01, 0x02, 0x03, 0x04 };
byte[] frame = standardParser.Encode(msgId: 42, payload: payload);

// Parse Profile Standard
var result = standardParser.ValidateBuffer(frame);
if (result.Valid)
{
    Console.WriteLine($"Received msg_id={result.MsgId}, len={result.MsgSize}");
}

// Encode using Profile Bulk (with package ID)
frame = bulkParser.Encode(msgId: 42, payload: payload, pkgId: 1);

// Encode using Profile Network (with routing)
frame = networkParser.Encode(
    msgId: 42, payload: payload,
    seq: 0, sysId: 1, compId: 2, pkgId: 3
);

// Create a custom configuration
var customConfig = FrameProfiles.CreateCustomConfig(
    name: "MyCustomFormat",
    numStartBytes: 2,
    startByte1: 0x90,
    startByte2: 0x71,
    hasLength: true, lengthBytes: 1,
    hasCrc: true, hasPkgId: false
);
var customParser = new FrameProfileParser(customConfig);
```

---

## Frame Format Definitions

All supported frame formats are provided as boilerplate code files that are copied to your project when generating code. The frame profiles define:

- Pre-configured encoder/decoder classes for each profile
- Header and payload type configurations
- Convenience type aliases for common use cases

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
| ExtendedMinimal | 9 | 0x79 | `[PKG_ID] [MSG_ID] [PACKET]` |

**Note**: ExtendedMinimal (added in v0.0.2) provides package ID support with minimal overhead. Like other Minimal types, it requires known message sizes and has no length field or CRC.

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
