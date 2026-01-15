# Framing

Framing wraps messages with headers and checksums for reliable communication over serial links, network sockets, or any byte stream.

## Why Framing

When sending data over a communication channel, you need to:

1. Identify message boundaries
2. Validate message integrity
3. Route messages by type

Framing solves these problems by adding structure around your message data.

## Standard Profiles

Use these pre-configured profiles for common scenarios:

| Profile | Overhead | Max Payload | Use Case |
|---------|----------|-------------|----------|
| **Standard** | 6 bytes | 255 bytes | General serial/UART |
| **Sensor** | 2 bytes | N/A | Low-bandwidth sensors |
| **IPC** | 1 byte | N/A | Trusted board-to-board |
| **Bulk** | 8 bytes | 64 KB | Firmware/file transfer |
| **Network** | 11 bytes | 64 KB | Multi-node networks |

## Quick Decision Guide

```
Do you need routing between nodes? → Network
Is it a trusted internal link (SPI)? → IPC
Are you bandwidth-limited (radio)? → Sensor
Sending large files (> 255 bytes)? → Bulk
Otherwise → Standard (recommended)
```

## Basic Frame Structure

The Standard profile (recommended for most uses):

```
┌────────┬────────┬────────┬────────┬─────────┬─────────┬─────────┐
│ START1 │ START2 │ LENGTH │ MSG_ID │ PAYLOAD │  CRC1   │  CRC2   │
│  0x90  │  0x71  │ 1 byte │ 1 byte │ N bytes │ 1 byte  │ 1 byte  │
└────────┴────────┴────────┴────────┴─────────┴─────────┴─────────┘
```

- **Start bytes**: Sync markers to find frame boundaries
- **Length**: Payload size (0-255)
- **MSG_ID**: Message type identifier
- **Payload**: Your message data
- **CRC**: Fletcher-16 checksum for error detection

## Usage Example

=== "Python"
    ```python
    from struct_frame_parser import Parser, HeaderType, PayloadType
    
    parser = Parser()
    
    # Encode
    frame = parser.encode_basic(msg_id=42, msg=b"data")
    
    # Decode
    for byte in frame:
        result = parser.parse_byte(byte)
        if result.valid:
            print(f"Message {result.msg_id}: {result.msg_data}")
    ```

=== "C++"
    ```cpp
    #include "FrameProfiles.hpp"
    
    using namespace StructFrame;
    
    // Encode
    uint8_t buffer[1024];
    ProfileStandardWriter writer(buffer, sizeof(buffer));
    writer.write(msg);
    
    // Decode
    ProfileStandardAccumulatingReader reader;
    reader.add_data(buffer, buffer_size);
    while (auto result = reader.next()) {
        // Process message - result is valid due to operator bool()
    }
    ```

For more details, see [Framing Details](framing-details.md).

