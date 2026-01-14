# TypeScript/JavaScript SDK

The TypeScript/JavaScript SDK provides promise-based transport layers for Node.js and browser environments.

## Installation

Generate with SDK:

```bash
python -m struct_frame messages.proto --build_ts --ts_path src/generated/ --sdk
```

## Basic Usage

```typescript
import { MessageRouter } from './generated/ts/struct_frame_sdk';
import { Status } from './generated/ts/messages.sf';

const router = new MessageRouter();

// Subscribe to messages
router.subscribe(Status, (msg: Status) => {
    console.log(`Status: ${msg.value}`);
});

// Process incoming data
router.processByte(byte);
```

## Transports

### UDP

```typescript
import { UDPTransport } from './generated/ts/struct_frame_sdk/transports';

const transport = new UDPTransport('192.168.1.100', 8080);
await transport.connect();
await transport.send(msgId, data);
```

### TCP

```typescript
import { TCPTransport } from './generated/ts/struct_frame_sdk/transports';

const transport = new TCPTransport('192.168.1.100', 8080);
await transport.connect();
await transport.send(msgId, data);
```

### WebSocket

```typescript
import { WebSocketTransport } from './generated/ts/struct_frame_sdk/transports';

const transport = new WebSocketTransport('ws://localhost:8080');
await transport.connect();
await transport.send(msgId, data);
```

### Serial (Node.js only)

```typescript
import { SerialTransport } from './generated/ts/struct_frame_sdk/transports';

const transport = new SerialTransport('/dev/ttyUSB0', 115200);
await transport.connect();
await transport.send(msgId, data);
```

## Browser vs Node.js

The SDK works in both environments:

- **Node.js**: Full support including Serial transport
- **Browser**: WebSocket and (with polyfills) UDP/TCP

```typescript
// Detect environment
if (typeof window === 'undefined') {
    // Node.js
    import { SerialTransport } from './struct_frame_sdk/transports';
} else {
    // Browser
    import { WebSocketTransport } from './struct_frame_sdk/transports';
}
```

