# TypeScript/JavaScript SDK

The TypeScript/JavaScript SDK provides a high-level, Promise-based interface for structured message communication.

## Installation

The SDK is automatically included when you generate TypeScript code:

```bash
python -m struct_frame your_messages.proto --build_ts --ts_path generated/ts
```

## Available Transports

### UDP Transport

Uses Node.js `dgram` module for UDP communication.

```typescript
import { UdpTransport, UdpTransportConfig } from './struct_frame_sdk';

const transport = new UdpTransport({
  remoteHost: '192.168.1.100',
  remotePort: 5000,
  localPort: 5001,
  localAddress: '0.0.0.0',
  socketType: 'udp4', // or 'udp6'
  broadcast: false,
  autoReconnect: true,
  reconnectDelay: 1000,
  maxReconnectAttempts: 5,
});
```

### TCP Transport

Uses Node.js `net` module for TCP communication.

```typescript
import { TcpTransport, TcpTransportConfig } from './struct_frame_sdk';

const transport = new TcpTransport({
  host: '192.168.1.100',
  port: 5000,
  timeout: 5000,
  autoReconnect: true,
});
```

### WebSocket Transport

Uses the WebSocket API (works in both browser and Node.js with `ws` package).

```typescript
import { WebSocketTransport, WebSocketTransportConfig } from './struct_frame_sdk';

const transport = new WebSocketTransport({
  url: 'ws://localhost:8080',
  protocols: [], // Optional WebSocket protocols
  autoReconnect: true,
});
```

### Serial Transport

Uses the `serialport` package for serial communication.

```typescript
import { SerialTransport, SerialTransportConfig } from './struct_frame_sdk';

const transport = new SerialTransport({
  path: '/dev/ttyUSB0', // or 'COM3' on Windows
  baudRate: 115200,
  dataBits: 8,
  stopBits: 1,
  parity: 'none',
});
```

## SDK Usage

### Creating the SDK

```typescript
import { StructFrameSdk, StructFrameSdkConfig } from './struct_frame_sdk';
import { BasicDefault } from './BasicDefault'; // Frame parser

const sdk = new StructFrameSdk({
  transport: transport,
  frameParser: new BasicDefault(),
  debug: true, // Enable debug logging
});
```

### Connecting and Disconnecting

```typescript
// Connect
await sdk.connect();

// Check connection status
if (sdk.isConnected()) {
  console.log('Connected!');
}

// Disconnect
await sdk.disconnect();
```

### Subscribing to Messages

```typescript
import { StatusMessage } from './my_messages';

// Subscribe with typed handler
const unsubscribe = sdk.subscribe<StatusMessage>(
  StatusMessage.msg_id,
  (message, msgId) => {
    console.log(`Temperature: ${message.temperature}`);
    console.log(`Status: ${message.status}`);
  }
);

// Unsubscribe when done
unsubscribe();
```

### Sending Messages

```typescript
import { CommandMessage } from './my_messages';

// Create and send message
const cmd = new CommandMessage();
cmd.command = 'START';
cmd.value = 100;

await sdk.send(cmd);

// Or send raw bytes
const rawData = new Uint8Array([1, 2, 3, 4]);
await sdk.sendRaw(CommandMessage.msg_id, rawData);
```

### Automatic Message Deserialization

Register codecs for automatic deserialization:

```typescript
import { StatusMessage } from './my_messages';

// Create a codec wrapper
const statusCodec = {
  getMsgId: () => StatusMessage.msg_id,
  deserialize: (data: Uint8Array) => StatusMessage.create_unpack(data),
};

sdk.registerCodec(statusCodec);

// Now messages are automatically deserialized
sdk.subscribe<StatusMessage>(StatusMessage.msg_id, (message, msgId) => {
  // message is already a StatusMessage instance
  console.log(message);
});
```

## Complete Example

```typescript
import {
  StructFrameSdk,
  TcpTransport,
} from './struct_frame_sdk';
import { BasicDefault } from './BasicDefault';
import { StatusMessage, CommandMessage } from './robot_messages';

async function main() {
  // Create transport
  const transport = new TcpTransport({
    host: 'localhost',
    port: 8080,
    autoReconnect: true,
    reconnectDelay: 2000,
    maxReconnectAttempts: 10,
  });

  // Create SDK
  const sdk = new StructFrameSdk({
    transport,
    frameParser: new BasicDefault(),
    debug: true,
  });

  // Subscribe to status messages
  sdk.subscribe<StatusMessage>(StatusMessage.msg_id, (msg, id) => {
    console.log(`[Status] Temp: ${msg.temperature}°C, Battery: ${msg.battery}%`);
  });

  // Connect
  await sdk.connect();
  console.log('Connected to robot');

  // Send command
  const cmd = new CommandMessage();
  cmd.command = 'MOVE_FORWARD';
  cmd.speed = 50;
  await sdk.send(cmd);

  // Handle errors
  transport.onError((error) => {
    console.error('Transport error:', error);
  });

  // Handle close
  transport.onClose(() => {
    console.log('Connection closed');
  });

  // Keep alive
  process.on('SIGINT', async () => {
    await sdk.disconnect();
    process.exit(0);
  });
}

main().catch(console.error);
```

## Error Handling

```typescript
try {
  await sdk.connect();
} catch (error) {
  console.error('Failed to connect:', error);
}

// Transport-level error handling
transport.onError((error) => {
  console.error('Transport error:', error);
});

transport.onClose(() => {
  console.log('Connection closed');
});
```

## Dependencies

- **UDP/TCP**: Built-in Node.js modules (`dgram`, `net`)
- **WebSocket**: Global `WebSocket` API (browser) or `ws` package (Node.js)
- **Serial**: `serialport` package (`npm install serialport`)

Install dependencies:

```bash
npm install ws serialport @types/ws @types/serialport
```

## TypeScript Types

All SDK components are fully typed:

```typescript
interface ITransport {
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  send(data: Uint8Array): Promise<void>;
  onData(callback: (data: Uint8Array) => void): void;
  onError(callback: (error: Error) => void): void;
  onClose(callback: () => void): void;
  isConnected(): boolean;
}

interface IFrameParser {
  parse(data: Uint8Array): FrameMsgInfo;
  frame(msgId: number, data: Uint8Array): Uint8Array;
}

interface IMessageCodec<T = any> {
  getMsgId(): number;
  deserialize(data: Uint8Array): T;
}
```
