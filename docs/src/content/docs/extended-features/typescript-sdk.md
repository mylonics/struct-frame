---
title: TypeScript/JavaScript SDK
description: Promise-based TypeScript and JavaScript SDK with transport layers for Node.js and browser environments.
---

The TypeScript/JavaScript SDK provides promise-based transport layers for Node.js and browser environments.

## Installation

Generate with SDK:

```bash
python -m struct_frame messages.proto --build_ts --ts_path src/generated/ --sdk
```

## Basic Usage

```typescript
import { StructFrameSdk, StructFrameSdkConfig } from './generated/ts/struct-frame-sdk';
import { TcpTransport } from './generated/ts/struct-frame-sdk';
import { Status } from './generated/ts/status.structframe';

const sdk = new StructFrameSdk({
    transport: new TcpTransport({ host: '192.168.1.100', port: 8080 }),
    frameParser: ...,  // frame parser instance
});

// Subscribe to messages by ID
sdk.subscribe<Status>(Status.MSG_ID, (msg) => {
    console.log(`Status: ${msg.value}`);
});

sdk.connect();
```

## Transports

### UDP

```typescript
import { UdpTransport } from './generated/ts/struct-frame-sdk';

const transport = new UdpTransport({ remoteHost: '192.168.1.100', remotePort: 8080 });
await transport.connect();
```

### TCP

```typescript
import { TcpTransport } from './generated/ts/struct-frame-sdk';

const transport = new TcpTransport({ host: '192.168.1.100', port: 8080 });
await transport.connect();
```

### WebSocket

```typescript
import { WebSocketTransport } from './generated/ts/struct-frame-sdk';

const transport = new WebSocketTransport({ url: 'ws://localhost:8080' });
await transport.connect();
```

### Serial (Node.js only)

```typescript
import { SerialTransport } from './generated/ts/struct-frame-sdk';

const transport = new SerialTransport({ path: '/dev/ttyUSB0', baudRate: 115200 });
await transport.connect();
```

## Browser vs Node.js

The SDK works in both environments:

- **Node.js**: Full support including Serial transport
- **Browser**: WebSocket and (with polyfills) UDP/TCP

```typescript
// Detect environment
if (typeof window === 'undefined') {
    // Node.js
    const { SerialTransport } = await import('./struct-frame-sdk');
} else {
    // Browser
    const { WebSocketTransport } = await import('./struct-frame-sdk');
}
```

