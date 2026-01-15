# SDK Overview

The SDK provides high-level abstractions for message communication, including transport layers and message routing.

## What the SDK Provides

- Transport abstractions (UDP, TCP, Serial, WebSocket)
- Message routing and handlers
- Observer/subscriber patterns
- Asynchronous I/O (where supported)

## When to Use the SDK

**Use the SDK when:**
- Building applications that communicate over networks or serial
- Need transport abstraction (switch between UDP/TCP/Serial easily)
- Want message routing and handler registration

**Use code generation only when:**
- Implementing custom communication protocols
- Working in resource-constrained environments
- Need full control over message handling

## SDK Availability

| Language | SDK | Transports |
|----------|-----|------------|
| C++ | ✓ | Serial, UDP, TCP, WebSocket (via ASIO) |
| TypeScript/JavaScript | ✓ | UDP, TCP, WebSocket, Serial |
| Python | ✓ | Serial, sockets, WebSocket |
| C# | ✓ | UDP, TCP, Serial |
| C | - | N/A |

## Generating with SDK

```bash
# C++ with full SDK (includes ASIO)
python -m struct_frame messages.proto --build_cpp --sdk

# C++ embedded SDK (no external dependencies)
python -m struct_frame messages.proto --build_cpp --sdk_embedded

# TypeScript with SDK
python -m struct_frame messages.proto --build_ts --sdk

# Python with SDK
python -m struct_frame messages.proto --build_py --sdk
```

## Language-Specific Guides

- [C++ SDK](cpp-sdk.md)
- [TypeScript/JavaScript SDK](typescript-sdk.md)
- [Python SDK](python-sdk.md)
- [C# SDK](csharp-sdk.md)

