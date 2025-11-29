# What is Struct Frame

Struct Frame is a code generation framework that converts Protocol Buffer (.proto) files into serialization code for C, C++, TypeScript, Python, and GraphQL. It provides message framing and parsing for structured communication over serial links, sockets, or any byte stream.

## Why Message Framing

When sending structured data over a communication channel:

1. Where does one message end and the next begin?
2. Is the received data complete and uncorrupted?
3. What kind of message is this?

These are problems that framing solves. Without framing, raw binary data is just a stream of bytes with no structure.

## Why Struct Frame

### No Encoding/Decoding Overhead in C/C++

C and C++ implementations use packed structs that map directly to memory. Messages can be cast to/from byte arrays without any encoding or decoding step. This reduces CPU usage and code complexity.

```c
// Direct memory access - no encode/decode
VehicleStatus* msg = (VehicleStatus*)buffer;
printf("Speed: %f\n", msg->speed);
```

### Cross-Platform Communication

Struct Frame generates code for multiple languages from a single .proto definition. A C program on an embedded device can communicate with a Python server or TypeScript frontend using the same message format.

### Small Frame Overhead

The basic frame format adds only 4 bytes of overhead:
- 1 byte start marker
- 1 byte message ID  
- 2 bytes checksum

Compare this to Mavlink (8-14 bytes header) or Cap'n Proto (8+ bytes header).

### Reduced Bandwidth Options

Different frame formats support different tradeoffs:
- No frame: Zero overhead, for point-to-point trusted links
- Basic frame: 4 bytes overhead, for most applications
- Custom formats: UBX, Mavlink v1/v2 support planned

### Simpler Than Protobuf and Cap'n Proto

Protobuf and Cap'n Proto are designed for general-purpose serialization with variable-length encoding, schema evolution, and RPC. This adds complexity and CPU overhead.

Struct Frame is simpler:
- Fixed-size messages with known layouts
- Direct memory mapping in C/C++
- No variable-length integer encoding
- No schema evolution complexity

### Memory Options

C/C++ parsers can:
- Return a pointer to the message in the receive buffer (zero-copy)
- Copy the message to a separate buffer

Framers can:
- Encode directly into a transmit buffer
- Create a message and copy it to a buffer

## Feature Compatibility

| Feature | C | C++ | TypeScript | Python | GraphQL |
|---------|---|-----|------------|--------|---------|
| Core Types | Yes | Yes | Yes | Yes | Yes |
| Strings | Yes | Yes | Yes | Yes | Yes |
| Enums | Yes | Yes | Yes | Yes | Yes |
| Enum Classes | N/A | Yes | N/A | N/A | N/A |
| Nested Messages | Yes | Yes | Yes | Yes | Yes |
| Message IDs | Yes | Yes | Yes | Yes | N/A |
| Serialization | Yes | Yes | Yes | Yes | N/A |
| Fixed Arrays | Yes | Yes | Yes | Yes | Yes |
| Bounded Arrays | Yes | Yes | Partial | Yes | Yes |
| Flatten | N/A | N/A | N/A | Yes | Yes |

## When to Use Struct Frame

Use Struct Frame when:
- You need low-overhead communication between embedded systems and higher-level languages
- You want direct memory access without encoding overhead
- You have bandwidth constraints
- You need a simple, predictable message format

Consider alternatives when:
- You need schema evolution (use Protobuf)
- You need RPC (use gRPC)
- You need maximum flexibility (use JSON)
