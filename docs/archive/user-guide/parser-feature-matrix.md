# Parser & Framer Feature Matrix

This document provides a comprehensive matrix of parser and framer features across all supported languages in struct-frame.

## Overview

struct-frame supports multiple parser types and framing strategies optimized for different use cases:

- **Profile-Specific Parsers**: Optimized parsers for individual frame profiles (STANDARD, SENSOR, IPC, BULK, NETWORK)
- **Polyglot Parsers**: Universal parsers that can handle multiple frame profiles in a single parser instance
- **Buffer Parsing**: Efficient in-place parsing of byte buffers without copying
- **Zero-Copy Framing**: Access message data directly from input buffer without copying to intermediate structures

## Feature Matrix

| Language   | Profile-Specific Parsers | Polyglot Parser | Buffer Parsing | Zero-Copy Support | Notes |
|------------|--------------------------|-----------------|----------------|-------------------|-------|
| **C**      | ✅ Yes                   | ❌ No           | ⚠️ Byte-by-byte | ✅ Yes           | Profile parsers via `profile_standard_t`, `profile_sensor_t`, etc. |
| **C++**    | ✅ Yes                   | ❌ No           | ✅ Yes          | ✅ Yes           | Buffer API: `parse_buffer()`, returns pointer into original buffer |
| **Python** | ✅ Yes                   | ✅ Yes          | ⚠️ Byte-by-byte | ⚠️ Partial      | Profile parsers available, polyglot parser is default |
| **TypeScript** | ✅ Yes               | ❌ No           | ⚠️ Byte-by-byte | ⚠️ Partial      | Profile parsers via generated classes |
| **JavaScript** | ✅ Yes               | ❌ No           | ⚠️ Byte-by-byte | ⚠️ Partial      | Profile parsers via generated classes |
| **C#**     | ✅ Yes                   | ❌ No           | ⚠️ Byte-by-byte | ⚠️ Partial      | Profile parsers via generated classes |
| **GraphQL**| N/A                      | N/A             | N/A            | N/A              | Schema generation only |

### Legend

- ✅ **Yes**: Full support with optimized implementation
- ⚠️ **Partial**: Basic support, may have limitations or performance implications
- ⚠️ **Byte-by-byte**: Parser processes one byte at a time (no buffer scanning API)
- ❌ **No**: Not supported
- **N/A**: Not applicable for this language

## Profile-Specific Parsers

Profile-specific parsers are optimized for a single frame format, eliminating runtime checks for profile detection and reducing overhead.

### Supported Profiles

All languages support parsers for these standard profiles:

1. **STANDARD** (`BasicDefault`): General serial/UART communication
2. **SENSOR** (`TinyMinimal`): Low-bandwidth sensor data
3. **IPC** (`NoneMinimal`): Trusted inter-process communication
4. **BULK** (`BasicExtended`): Large file transfers
5. **NETWORK** (`BasicExtendedMultiSystemStream`): Multi-node mesh networks

### Language-Specific Usage

#### C

```c
#include "frame_parsers.h"

// Profile-specific parser (using STANDARD profile)
profile_standard_t parser;
uint8_t buffer[256];
profile_standard_init(&parser, buffer, sizeof(buffer), NULL);

// Parse byte-by-byte
frame_msg_info_t result = profile_standard_parse_byte(&parser, byte);
if (result.valid) {
    // Process message: result.msg_id, result.msg_data, result.msg_len
}
```

#### C++

```cpp
#include "frame_parsers.hpp"

using namespace FrameParsers;

// Profile-specific parser (using STANDARD profile)
uint8_t buffer[256];
ProfileStandard parser(buffer, sizeof(buffer));

// Option 1: Byte-by-byte parsing
FrameMsgInfo result = parser.parse_byte(byte);

// Option 2: Buffer parsing (efficient, zero-copy)
size_t consumed = 0;
FrameMsgInfo result = parser.parse_buffer(data_buffer, data_len, &consumed);
if (result.valid) {
    // result.msg_data points into original data_buffer (zero-copy!)
    process_message(result.msg_id, result.msg_data, result.msg_len);
    data_buffer += consumed;  // Advance buffer
    data_len -= consumed;
}

// Profile aliases for convenience
using ProfileStandard = BasicDefaultParser;  // Profile.STANDARD
using ProfileSensor = TinyMinimalParser;     // Profile.SENSOR
using ProfileBulk = BasicExtendedParser;     // Profile.BULK
using ProfileNetwork = BasicExtendedMultiSystemStreamParser;  // Profile.NETWORK
```

#### Python

```python
from struct_frame_parser import BasicDefaultParser

# Profile-specific parser (STANDARD profile)
parser = BasicDefaultParser()

# Parse byte-by-byte
result = parser.parse_byte(byte_val)
if result['valid']:
    msg_id = result['msg_id']
    msg_data = result['msg_data']
    msg_len = result['msg_len']
```

#### TypeScript

```typescript
import { createProfileStandardAccumulatingReader } from './frame_profiles';

// Create an accumulating reader for ProfileStandard
const reader = createProfileStandardAccumulatingReader();

// Parse byte-by-byte (streaming mode)
const result = reader.pushByte(byte);
if (result && result.valid) {
    const msgId = result.msg_id;
    const msgData = result.msg_data;
    const msgLen = result.msg_len;
}
```

## Polyglot Parsers

Polyglot parsers can handle multiple frame profiles in a single parser instance, automatically detecting the profile from start bytes.

### Trade-offs

| Aspect | Profile-Specific | Polyglot |
|--------|------------------|----------|
| **Performance** | ⚡ Faster (no profile detection) | Slower (runtime profile checks) |
| **Code Size** | Larger (separate parser per profile) | Smaller (single unified parser) |
| **Flexibility** | Fixed to one profile | Handles multiple profiles |
| **Use Case** | Known fixed profile | Dynamic or mixed profiles |

### Language Support

#### Python (Default)

```python
from struct_frame_parser import Parser

# Polyglot parser supporting multiple profiles
parser = Parser(
    enabled_headers=[HeaderType.BASIC, HeaderType.TINY],
    enabled_payloads=[PayloadType.DEFAULT, PayloadType.MINIMAL]
)

result = parser.parse_byte(byte_val)
# Automatically detects profile from start bytes
```

#### C++

```cpp
// C++ polyglot parser implementation TBD
// Currently use profile-specific parsers
```

## Buffer Parsing

Buffer parsing allows scanning entire byte buffers for frames without byte-by-byte state machine overhead.

### C++ Buffer Parsing API

The C++ implementation provides the most advanced buffer parsing support:

```cpp
#include "frame_parsers.hpp"

using namespace FrameParsers;

BasicDefaultParser parser(internal_buffer, sizeof(internal_buffer));

// Efficient buffer scanning
const uint8_t* ring_buffer = get_uart_buffer();
size_t available = get_uart_available();
size_t consumed = 0;

// Scan for frames (no copying)
FrameMsgInfo result = parser.parse_buffer(ring_buffer, available, &consumed);

if (result.valid) {
    // result.msg_data points directly into ring_buffer (zero-copy!)
    // Process the message immediately or copy if needed for async processing
    handle_message(result.msg_id, result.msg_data, result.msg_len);
    
    // Advance ring buffer read pointer
    advance_ring_buffer(consumed);
}
```

### Benefits

- **Performance**: Scans memory directly, no byte-by-byte state machine overhead
- **Zero-Copy**: Message data pointer points into original buffer (when CRC valid)
- **Ring Buffer Support**: Works seamlessly with circular buffers
- **No std Library**: Pure pointer arithmetic, embedded-friendly
- **Error Recovery**: Automatically skips junk bytes before valid frame

### Use Cases

1. **High-Throughput Serial**: Parse multiple frames from DMA buffer
2. **Network Packets**: Scan UDP/TCP payload for embedded frames
3. **File Processing**: Parse frame log files efficiently
4. **Ring Buffers**: Direct parsing from UART/SPI circular buffers

## Zero-Copy Support

Zero-copy parsing avoids intermediate memory copies by returning pointers into the original input buffer.

### C++ (Full Support)

```cpp
// Buffer parsing returns pointer into original buffer
FrameMsgInfo result = parser.parse_buffer(uart_buffer, uart_len, &consumed);
// result.msg_data points into uart_buffer - no copy!
```

### Constraints

Zero-copy is only possible when:

1. **CRC is valid**: Message integrity verified before returning pointer
2. **Buffer remains valid**: Caller must not free/reuse buffer while using msg_data
3. **No framing modifications**: Buffer content is unmodified

### When to Copy

Copy the message data if:

- Asynchronous processing (buffer may be reused)
- Long-term storage (buffer is temporary)
- Buffer is ring/circular (wrapping may occur)

```cpp
// Copy for async processing
std::vector<uint8_t> message_copy(result.msg_data, result.msg_data + result.msg_len);
async_queue.push(MessageTask{result.msg_id, std::move(message_copy)});
```

## Best Practices

### Choosing a Parser Type

1. **Embedded C++ with High Throughput**: Use C++ buffer parsing with profile-specific parser
2. **Embedded C with Low Resources**: Use C byte-by-byte with profile-specific parser
3. **Python for Flexibility**: Use polyglot parser for dynamic environments
4. **Web/Desktop Apps**: Use TypeScript/C# profile-specific for type safety

### Optimizing Performance

1. **Use Profile-Specific Parsers**: When profile is known at compile time
2. **Use Buffer Parsing**: For batch processing or high-throughput scenarios
3. **Minimize CRC Checks**: Profile-specific parsers do CRC once per frame
4. **Zero-Copy When Possible**: Avoid unnecessary memory copies

### Error Handling

```cpp
// C++ with buffer parsing
size_t consumed = 0;
FrameMsgInfo result = parser.parse_buffer(buffer, len, &consumed);

if (result.valid) {
    process_message(result);
} else if (consumed > 0) {
    // Skipped some junk bytes, keep parsing
    buffer += consumed;
    len -= consumed;
} else {
    // Not enough data for complete frame, wait for more
    wait_for_more_data();
}
```

## Future Enhancements

Planned improvements to parser feature matrix:

- [ ] C buffer parsing API (similar to C++)
- [ ] Python buffer parsing API (with memoryview support)
- [ ] TypeScript/JavaScript buffer parsing (Uint8Array)
- [ ] C# buffer parsing (Span<byte>)
- [ ] Profile-specific polyglot parser (detect profile once, then switch to optimized path)

## See Also

- [Framing Guide](framing.md) - Choosing the right profile
- [Framing Architecture](framing-architecture.md) - How framing works
- [C++ SDK](cpp-sdk.md) - C++ API documentation
- [C SDK](c-sdk.md) - C API documentation (TBD)
- [Python SDK](python-sdk.md) - Python API documentation
