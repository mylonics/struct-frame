# Frame Formats Module

This module provides language-agnostic definitions for struct-frame frame formats.

## Overview

Frame formats define how messages are wrapped with headers, metadata fields, and error detection. The module uses a composable architecture where:

1. **Headers** define start byte patterns for synchronization
2. **Payloads** define metadata field structure (length, CRC, etc.)
3. **Profiles** combine headers and payloads for common use cases

## Quick Start

### Using Standard Profiles (Recommended)

```python
from struct_frame.frame_formats import Profile, get_profile

# Get a standard profile
standard = get_profile(Profile.STANDARD)
print(f"Name: {standard.name}")  # BasicDefault
print(f"Overhead: {standard.total_overhead} bytes")  # 6 bytes
```

Available profiles:
- `Profile.STANDARD` - General serial/UART (BasicDefault, 6 bytes)
- `Profile.SENSOR` - Low-bandwidth sensors (TinyMinimal, 2 bytes)
- `Profile.IPC` - Trusted inter-process (NoneMinimal, 1 byte)
- `Profile.BULK` - Large file transfers (BasicExtended, 8 bytes)
- `Profile.NETWORK` - Multi-node mesh (BasicExtendedMultiSystemStream, 11 bytes)

### Creating Custom Profiles

```python
from struct_frame.frame_formats import create_custom_profile, HeaderType, PayloadType

# Create a custom combination
custom = create_custom_profile(
    "TinyDefault",
    HeaderType.TINY,
    PayloadType.DEFAULT,
    "Tiny header with default payload for lower overhead"
)
print(f"Overhead: {custom.total_overhead} bytes")  # 5 bytes
```

### Listing All Profiles

```python
from struct_frame.frame_formats import list_profiles

for name, format_name, overhead, description in list_profiles():
    print(f"{name}: {format_name} ({overhead} bytes)")
```

## Architecture

### Headers

Headers define the start byte pattern:

```python
from struct_frame.frame_formats import HeaderType, get_header

header = get_header(HeaderType.BASIC)
print(f"Start bytes: {header.num_start_bytes}")  # 2
print(f"Encodes payload: {header.encodes_payload_type}")  # True
```

Available header types:
- `NONE` - No start bytes (0 bytes)
- `TINY` - 1 start byte encoding payload type
- `BASIC` - 2 start bytes (0x90 + payload-encoded byte)
- `UBX` - u-blox GPS protocol (0xB5, 0x62)
- `MAVLINK_V1` - Classic drone protocol (0xFE)
- `MAVLINK_V2` - Modern drone protocol (0xFD)

### Payloads

Payloads define metadata field structure:

```python
from struct_frame.frame_formats import PayloadType, get_payload

payload = get_payload(PayloadType.DEFAULT)
print(f"Has CRC: {payload.has_crc}")  # True
print(f"Has length: {payload.has_length}")  # True
print(f"Overhead: {payload.overhead} bytes")  # 4 bytes
```

Available payload types:
- `MINIMAL` - Just MSG_ID (1 byte)
- `DEFAULT` - Length + CRC (4 bytes)
- `EXTENDED_MSG_IDS` - Default + package ID (5 bytes)
- `EXTENDED_LENGTH` - 16-bit length + CRC (5 bytes)
- `EXTENDED` - Extended length + package ID (6 bytes)
- `SYS_COMP` - Routing (system/component IDs) (6 bytes)
- `SEQ` - Sequence number (5 bytes)
- `MULTI_SYSTEM_STREAM` - Routing + sequence (7 bytes)
- `EXTENDED_MULTI_SYSTEM_STREAM` - All features (9 bytes)

### CRC Utilities

```python
from struct_frame.frame_formats import calculate_crc16, crc_to_bytes, verify_crc

data = b"Hello, World!"
crc = calculate_crc16(data)
crc_byte1, crc_byte2 = crc_to_bytes(crc)

# Verify
is_valid = verify_crc(data, crc)
```

## File Organization

```
frame_formats/
├── __init__.py          # Public API
├── base.py              # Core data structures
├── headers.py           # Header definitions
├── payloads.py          # Payload definitions
├── profiles.py          # Standard profiles
└── crc.py               # CRC utilities
```

## API Reference

### Classes

- `FrameFormatDefinition` - Complete frame format (header + payload)
- `HeaderDefinition` - Header specification
- `PayloadDefinition` - Payload specification

### Enums

- `Profile` - Standard profile enumeration
- `HeaderType` - Header type enumeration
- `PayloadType` - Payload type enumeration

### Functions

- `get_profile(profile: Profile)` - Get a standard profile
- `get_profile_by_name(name: str)` - Get profile by name
- `create_custom_profile(...)` - Create custom profile
- `list_profiles()` - List all standard profiles
- `get_header(header_type: HeaderType)` - Get header definition
- `get_payload(payload_type: PayloadType)` - Get payload definition
- `calculate_crc16(data: bytes)` - Calculate CRC-16-CCITT
- `crc_to_bytes(crc: int)` - Convert CRC to bytes
- `bytes_to_crc(byte1: int, byte2: int)` - Convert bytes to CRC
- `verify_crc(data: bytes, expected: int)` - Verify CRC

## Examples

### Exploring Profile Details

```python
from struct_frame.frame_formats import Profile, get_profile

network = get_profile(Profile.NETWORK)

print(f"Name: {network.name}")
print(f"Header: {network.header.name} ({network.header.num_start_bytes} bytes)")
print(f"Payload: {network.payload.name} ({network.payload.overhead} bytes)")
print(f"Total overhead: {network.total_overhead} bytes")
print(f"Start byte: 0x{network.start_byte_value:02X}")
print(f"Has sequence: {network.payload.has_sequence}")
print(f"Has routing: {network.payload.has_system_id and network.payload.has_component_id}")
```

### Field Order in Payload

```python
from struct_frame.frame_formats import get_profile, Profile

standard = get_profile(Profile.STANDARD)
fields = standard.payload.get_field_order()
print(f"Field order: {fields}")  # ['length', 'msg_id']
```

### Converting to Dictionary

```python
from struct_frame.frame_formats import get_profile, Profile

bulk = get_profile(Profile.BULK)
data = bulk.to_dict()
print(data)
# {
#   'name': 'BasicExtended',
#   'header_type': 'BASIC',
#   'payload_type': 'EXTENDED',
#   'total_overhead': 8,
#   'max_payload_size': 65535,
#   'has_crc': True,
#   'has_sequence': False,
#   'has_routing': False,
#   'description': '...'
# }
```

## Testing

Run the test suite:

```bash
PYTHONPATH=src python3 tests/py/test_profiles.py
```

Or use the interactive test:

```bash
PYTHONPATH=src python3 test_frame_formats.py
```

## Contributing

To add a new header or payload type:

1. Add enum value to `HeaderType` or `PayloadType` in `base.py`
2. Add definition to `headers.py` or `payloads.py`
3. Update the corresponding registry (`HEADER_DEFINITIONS` or `PAYLOAD_DEFINITIONS`)
4. Submit a PR to the struct-frame repository

To add a new profile:

1. Add enum value to `Profile` in `profiles.py`
2. Add definition to `PROFILE_DEFINITIONS`
3. Update documentation

## See Also

- [Framing Guide](../../docs/user-guide/framing.md) - User guide
- [Framing Architecture](../../docs/user-guide/framing-architecture.md) - Architecture details
- [Frame Profile Calculator](../../docs/user-guide/framing-calculator.md) - Interactive tool
