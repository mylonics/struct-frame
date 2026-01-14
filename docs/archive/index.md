# What is Struct Frame

Struct Frame is a cross-platform packeting, framing, and parsing framework. It uses .proto files to define message structures and generates code for C, C++, TypeScript, Python, and GraphQL.

## Why Message Framing

When sending structured data over a communication channel:

1. Where does one message end and the next begin?
2. Is the received data complete and uncorrupted?
3. What kind of message is this?

These are problems that framing solves. Without framing, raw binary data is just a stream of bytes with no structure.

## Why Struct Frame

### No Encoding/Decoding Overhead in C/C++

C and C++ implementations use packed structs that map directly to memory. Messages can be cast to/from byte arrays without any encoding or decoding step. This reduces CPU and memory usage.

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

### More Memory and CPU Efficient Than Protobuf and Cap'n Proto

Protobuf and Cap'n Proto are designed for general-purpose serialization with variable-length encoding, schema evolution, and RPC.

Struct Frame is simpler:
- Fixed-size messages with known layouts
- Direct memory mapping in C/C++
- No variable-length integer encoding
- No schema evolution complexity

### No Runtime Dependencies

Everything needed to use struct-frame is generated or included with the boilerplate code. There are no external libraries to link against at runtime. The C/C++ implementation is header-only.

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
