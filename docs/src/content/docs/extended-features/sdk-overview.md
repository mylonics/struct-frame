---
title: SDK Overview
description: High-level SDK abstractions for message communication, including transport layers and message routing.
---

The SDK provides high-level abstractions for message communication, including transport layers and message routing.

## What the SDK Provides

- Transport abstractions (UDP, TCP, Serial, and WebSocket where listed below)
- Message routing and handlers
- Observer/subscriber patterns
- Request/response helpers (Python, TypeScript/JavaScript, C#)
- Error reporting hooks
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
| C++ | ✓ | Serial, UDP, TCP (via ASIO); no WebSocket |
| TypeScript/JavaScript | ✓ | UDP, TCP, WebSocket, Serial |
| Python | ✓ | Serial, sockets, WebSocket |
| C# | ✓ | Serial, UDP, TCP, WebSocket |
| Rust | ✓ (frame SDK) | N/A — frame encoding/parsing only; no transport layer |
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

# C# (SDK core is always generated; enable transports in the .csproj with
# -p:IncludeSerialTransport=true / -p:IncludeNetCoreServer=true)
python -m struct_frame messages.proto --build_csharp
```

`--sdk` applies to C++, Python, TypeScript and JavaScript. `--sdk_embedded` is only honoured for C++.

## Request/Response

Send a message and wait for the matching reply. The wait is bounded (default 5 seconds) and the temporary subscription is always removed, whether the request succeeds, times out or fails.

```python
# Python (blocking; the async SDK has an awaitable request())
reply = sdk.request(Ping(seq=1), Pong, match=lambda r: r.seq == 1, timeout=2.0)
```

```typescript
// TypeScript / JavaScript (returns a Promise)
const reply = await sdk.request<Pong>(ping, Pong._msgid, { match: r => r.seq === 1, timeout: 2 });
```

```csharp
// C#
var reply = await sdk.RequestAsync<Ping, Pong>(ping, match: r => r.Seq == 1, timeoutSeconds: 2f);
```

All three throw/reject with a timeout error when no matching response arrives. `match` is optional; without it the first message with the response ID wins. The C++ and Rust SDKs have no request helper: subscribe to the response ID and correlate it yourself.

## Error Reporting

Transport errors, exceptions thrown by handlers and deserialization failures are delivered to an error hook instead of being swallowed:

| SDK | Hook |
|-----|------|
| Python | `StructFrameSdkConfig(on_error=callable)` |
| TypeScript / JavaScript | `onError` in the SDK config |
| C# | `StructFrameSdk.ErrorOccurred` event |
| C++ | `sdk.SetErrorCallback(fn, ctx)` (transport errors only) |

Without a hook these errors are only visible when debug logging is enabled, so production code should always install one. The callback must not throw.

## Language-Specific Guides

- [C++ SDK](/extended-features/cpp-sdk/)
- [TypeScript/JavaScript SDK](/extended-features/typescript-sdk/)
- [Python SDK](/extended-features/python-sdk/)
- [C# SDK](/extended-features/csharp-sdk/)
- [Rust SDK](/extended-features/rust-sdk/)

