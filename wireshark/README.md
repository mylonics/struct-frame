# Wireshark Dissector for Struct Frame

This directory contains a Wireshark Lua dissector for the Struct Frame protocol. The dissector can decode all standard frame format profiles used in struct-frame communication.

## Features

- **Automatic Protocol Detection**: Detects Basic and Tiny frame formats based on start bytes
- **All Standard Profiles Supported**:
  - Standard (BasicDefault) - General Serial/UART
  - Sensor (TinyMinimal) - Low-Bandwidth
  - IPC (NoneMinimal) - Trusted Inter-Process (requires configuration)
  - Bulk (BasicExtended) - Large Data Transfers
  - Network (BasicExtendedMultiSystemStream) - Multi-Node Mesh
- **Field-by-field Decoding**: Displays all frame fields including:
  - Start bytes (0x90 for Basic, 0x70-0x78 for Tiny)
  - Sequence numbers
  - System/Component IDs for routing
  - Length fields (8-bit or 16-bit)
  - Package IDs
  - Message IDs
  - Payload data
  - CRC checksums with validation
- **CRC Validation**: Calculates and validates Fletcher-16 checksums

## Installation

### Method 1: User Plugin Directory (Recommended)

1. Copy `struct_frame.lua` to your Wireshark plugins directory:
   - **Windows**: `%APPDATA%\Wireshark\plugins\`
   - **Linux**: `~/.local/lib/wireshark/plugins/`
   - **macOS**: `~/.wireshark/plugins/`

2. Create the directory if it doesn't exist:
   ```bash
   # Linux/macOS
   mkdir -p ~/.local/lib/wireshark/plugins/
   cp struct_frame.lua ~/.local/lib/wireshark/plugins/
   
   # Or for global installation (requires sudo)
   # sudo cp struct_frame.lua /usr/lib/wireshark/plugins/
   ```

3. Restart Wireshark

### Method 2: Load from Command Line

You can also load the dissector directly when starting Wireshark:

```bash
wireshark -X lua_script:struct_frame.lua
```

## Verification

To verify the dissector is loaded correctly:

1. Open Wireshark
2. Go to **Help → About Wireshark → Plugins**
3. Look for `struct_frame.lua` in the list
4. Check the console output for "Struct Frame dissector loaded successfully"

Alternatively, check the Wireshark console:
- Go to **View → Internals → Lua**
- Look for the success message

## Usage

### Automatic Detection

The dissector will automatically detect Struct Frame packets in:
- **UDP** traffic
- **TCP** traffic
- Packets with User DLT 147

It looks for the characteristic start bytes:
- `0x90` followed by `0x70-0x78` (Basic frames)
- `0x70-0x78` as the first byte (Tiny frames)

### Capture Filter

To capture only Struct Frame traffic, use:

```
udp port 14550
```

(Replace `14550` with your actual port number)

### Display Filter

Use these display filters to view specific Struct Frame traffic:

```
# All Struct Frame packets
struct_frame

# Specific profile
struct_frame.profile_name contains "Standard"

# Specific message ID
struct_frame.message_id == 42

# Invalid CRC
struct_frame.crc_status contains "Invalid"

# Specific system ID (for Network profile)
struct_frame.system_id == 1
```

### Decoding Existing Captures

If you have existing packet captures:

1. Open the PCAP file in Wireshark
2. Right-click on a packet
3. Select **Decode As...**
4. Choose **Struct Frame** as the protocol

## Frame Format Reference

### Basic Frame Profiles

| Profile | Start Bytes | Overhead | Structure |
|---------|-------------|----------|-----------|
| BasicDefault (Standard) | `0x90 0x71` | 6 bytes | `[0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]` |
| BasicExtended (Bulk) | `0x90 0x74` | 8 bytes | `[0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]` |
| BasicExtendedMultiSystemStream (Network) | `0x90 0x78` | 11 bytes | `[0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]` |

### Tiny Frame Profiles

| Profile | Start Byte | Overhead | Structure |
|---------|------------|----------|-----------|
| TinyMinimal (Sensor) | `0x70` | 2 bytes | `[0x70] [MSG_ID] [PAYLOAD]` |
| TinyDefault | `0x71` | 5 bytes | `[0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]` |

### Payload Type Encoding

The second start byte (for Basic) or the single start byte (for Tiny) encodes the payload type:

- `0x70` = Minimal
- `0x71` = Default
- `0x72` = ExtendedMsgIds
- `0x73` = ExtendedLength
- `0x74` = Extended
- `0x75` = SysComp
- `0x76` = Seq
- `0x77` = MultiSystemStream
- `0x78` = ExtendedMultiSystemStream

## Example Packet Dissection

### Standard Profile (BasicDefault)

```
Frame: [0x90] [0x71] [0x04] [0x2A] [0x01, 0x02, 0x03, 0x04] [0x7F] [0x8A]

Dissected as:
  Struct Frame Protocol
    Start Byte 1: 0x90
    Start Byte 2: 0x71
    Header Type: Basic
    Payload Type: Default
    Profile Name: Standard (General Serial/UART)
    Length: 4
    Message ID: 42
    Payload Data: 01:02:03:04
    CRC Byte 1: 0x7F
    CRC Byte 2: 0x8A
    CRC Status: Valid
```

### Network Profile (BasicExtendedMultiSystemStream)

```
Frame: [0x90] [0x78] [0x05] [0x01] [0x02] [0x04] [0x00] [0x01] [0x2A] [0x01, 0x02, 0x03, 0x04] [CRC1] [CRC2]

Dissected as:
  Struct Frame Protocol
    Start Byte 1: 0x90
    Start Byte 2: 0x78
    Header Type: Basic
    Payload Type: ExtendedMultiSystemStream
    Profile Name: Network (Multi-Node Mesh)
    Sequence Number: 5
    System ID: 1
    Component ID: 2
    Length Low: 4
    Length High: 0
    Length: 4 (generated)
    Package ID: 1
    Message ID: 42
    Payload Data: 01:02:03:04
    CRC Byte 1: ...
    CRC Byte 2: ...
    CRC Status: Valid
```

## Troubleshooting

### Dissector Not Loading

1. Check Wireshark console for errors: **View → Internals → Lua**
2. Verify the file is in the correct plugins directory
3. Make sure the file has `.lua` extension
4. Restart Wireshark completely

### Packets Not Being Decoded

1. Verify the packets have the correct start bytes
2. Check if another dissector is claiming the packets first
3. Use "Decode As..." to force Struct Frame dissection
4. Enable heuristic dissectors: **Analyze → Enabled Protocols** and check "struct_frame"

### CRC Always Shows Invalid

1. Verify you're using the correct profile (CRC is only present in certain payload types)
2. Check that the captured data is complete and not corrupted
3. Compare with known-good test data

## Creating Test Data

To create test PCAP files for validation:

1. Generate struct-frame packets using the Python/TypeScript SDK
2. Capture traffic with:
   ```bash
   tcpdump -i any -w struct_frame_test.pcap udp port 14550
   ```
3. Open in Wireshark to verify dissection

Example Python code to generate test packets:
```python
from struct_frame.frame_formats import Profile, get_profile

# Get the Standard profile
profile = get_profile(Profile.STANDARD)

# Create a test message
# [0x90] [0x71] [0x04] [0x2A] [0x01, 0x02, 0x03, 0x04] [CRC1] [CRC2]
```

## Limitations

- **None frames** (no start bytes) cannot be auto-detected and require manual configuration
- **Third-party protocols** (UBX, MAVLink) are not yet implemented in the dissector
- Large payloads (>64KB) may cause performance issues in Wireshark

## Contributing

To add support for additional frame formats or improve the dissector:

1. Edit `struct_frame.lua`
2. Add payload type definitions to `payload_types` and `payload_structures`
3. Update the field parsing logic in the main dissector function
4. Test with sample packets
5. Submit a pull request to the struct-frame repository

## References

- [Struct Frame Documentation](https://struct-frame.mylonics.com/)
- [Framing Guide](https://struct-frame.mylonics.com/user-guide/framing/)
- [Wireshark Lua API](https://www.wireshark.org/docs/wsdg_html_chunked/lua_module_Proto.html)

## License

This dissector is part of the struct-frame project and is licensed under the same terms as the main project.
