# TypeScript/JavaScript SDK

The TypeScript/JavaScript SDK provides a high-level, Promise-based interface for structured message communication.

## Installation

Generate TypeScript code with SDK:

```bash
python -m struct_frame your_messages.proto --build_ts --ts_path generated/ts --sdk
```

**Note**: The SDK is not included by default. Use the `--sdk` flag to generate SDK files.

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

## Using the Parser

### Basic Parser Usage

```typescript
import { GenericFrameParser, FrameParserConfig } from './frame_base';
import { HEADER_BASIC_CONFIG } from './frame_headers/header_basic';
import { PAYLOAD_DEFAULT_CONFIG } from './payload_types/payload_default';

// Create a BasicDefault parser configuration
const config: FrameParserConfig = {
    name: 'BasicDefault',
    startBytes: [0x90, 0x71],  // Basic + Default
    headerSize: 4,              // start bytes (2) + length (1) + msg_id (1)
    footerSize: 2,              // CRC (2)
    hasLength: true,
    lengthBytes: 1,
    hasCrc: true,
};

const parser = new GenericFrameParser(config);

// Parse incoming bytes
for (const byte of incomingData) {
    const result = parser.parse_byte(byte);
    if (result.valid) {
        console.log(`Received msg_id=${result.msg_id}`);
        console.log(`Data: ${result.msg_data}`);
    }
}

// Encode a message
const frame = parser.encode(42, new Uint8Array([1, 2, 3, 4, 5]));
```

### Using Minimal Frames

For minimal payloads (no length field, no CRC), provide a callback to determine message length:

```typescript
import { GenericFrameParser, FrameParserConfig } from './frame_base';

// Define message size lookup
function getMsgLength(msgId: number): number | undefined {
    const messageSizes: {[key: number]: number} = {
        1: 10,  // Status message is 10 bytes
        2: 20,  // Command message is 20 bytes
        3: 5,   // Sensor reading is 5 bytes
    };
    return messageSizes[msgId];
}

// Configure for TinyMinimal
const config: FrameParserConfig = {
    name: 'TinyMinimal',
    startBytes: [0x70],  // Tiny+Minimal
    headerSize: 2,       // start byte + msg_id
    footerSize: 0,       // no CRC
    hasLength: false,    // no length field
    lengthBytes: 0,
    hasCrc: false,
};

// Create parser with callback
const parser = new GenericFrameParser(config, getMsgLength);

// Parse bytes
for (const byte of incomingData) {
    const result = parser.parse_byte(byte);
    if (result.valid) {
        console.log(`Minimal frame: msg_id=${result.msg_id}, len=${result.msg_len}`);
    }
}

// Encode minimal frame
const data = new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
const frame = parser.encode(1, data);
// Result: [0x70] [0x01] [0x01 0x02 ... 0x0A]
```

For more details on minimal frames, see the [Minimal Frames Guide](minimal-frames.md).

## Profile-Based Parsing API

The TypeScript/JavaScript SDK provides high-performance parsing classes that match the C++ gold standard implementation. These are optimized for specific frame profiles and provide convenient factory functions.

### Available Profiles

| Profile | Header | Payload | Use Case |
|---------|--------|---------|----------|
| `ProfileStandard` | Basic | Default | General serial/UART communication |
| `ProfileSensor` | Tiny | Minimal | Low-bandwidth sensors, radio links |
| `ProfileIPC` | None | Minimal | Trusted inter-process communication |
| `ProfileBulk` | Basic | Extended | Firmware/file transfers |
| `ProfileNetwork` | Basic | ExtendedMultiSystemStream | Multi-node mesh networks |

### BufferReader - Parse Multiple Frames from a Buffer

`BufferReader` iterates through a buffer containing one or more frames, automatically tracking the offset:

```typescript
import {
  createProfileStandardReader,
  createProfileSensorReader,
} from './frame_profiles';

// Parse a buffer containing multiple ProfileStandard frames
const reader = createProfileStandardReader(bufferData);
while (reader.hasMore()) {
    const result = reader.next();
    if (!result.valid) break;
    console.log(`Message ID: ${result.msg_id}, Length: ${result.msg_len}`);
    processMessage(result.msg_data);
}

console.log(`Processed ${reader.offset} bytes, ${reader.remaining} remaining`);
```

For minimal profiles (no length field), provide a message length callback:

```typescript
import { get_message_length } from './my_messages.sf';

// Parse ProfileSensor frames (minimal payload)
const reader = createProfileSensorReader(bufferData, get_message_length);
while (reader.hasMore()) {
    const result = reader.next();
    if (result.valid) {
        processMessage(result.msg_id, result.msg_data);
    }
}
```

### BufferWriter - Encode Multiple Frames

`BufferWriter` encodes multiple frames into a buffer with automatic offset tracking:

```typescript
import {
  createProfileStandardWriter,
  createProfileNetworkWriter,
} from './frame_profiles';

// Create writer with capacity
const writer = createProfileStandardWriter(4096);

// Write multiple messages
writer.write(1, msg1Data);
writer.write(2, msg2Data);
writer.write(3, msg3Data);

// Get the encoded data
const encodedBuffer = writer.data();
console.log(`Encoded ${writer.size()} bytes with ${writer.count()} messages`);
```

For network profiles with extra header fields:

```typescript
const writer = createProfileNetworkWriter(4096);
writer.write(1, data, { seq: 1, sysId: 10, compId: 1 });
```

### AccumulatingReader - Unified Buffer and Streaming Parser

`AccumulatingReader` handles both buffer mode and byte-by-byte streaming, with support for partial messages across buffer boundaries:

**Buffer Mode** - Processing chunks of data:

```typescript
import { createProfileStandardAccumulatingReader } from './frame_profiles';

const reader = createProfileStandardAccumulatingReader();

// Process incoming chunks (e.g., from network or file)
reader.addData(chunk1);
while (true) {
    const result = reader.next();
    if (!result.valid) break;
    processMessage(result.msg_id, result.msg_data);
}

// Add more data (handles partial messages automatically)
reader.addData(chunk2);
while (true) {
    const result = reader.next();
    if (!result.valid) break;
    processMessage(result.msg_id, result.msg_data);
}
```

**Stream Mode** - Byte-by-byte processing (UART/serial):

```typescript
import { createProfileSensorAccumulatingReader } from './frame_profiles';
import { get_message_length } from './my_messages.sf';

const reader = createProfileSensorAccumulatingReader(get_message_length);

// Process incoming bytes one at a time
serialPort.on('data', (data: Buffer) => {
    for (const byte of data) {
        const result = reader.pushByte(byte);
        if (result.valid) {
            // Complete message received
            processMessage(result.msg_id, result.msg_data);
        }
    }
});
```

### Factory Functions

All profiles have factory functions for creating readers and writers:

```typescript
import {
    // BufferReader factories
    createProfileStandardReader,
    createProfileSensorReader,
    createProfileIPCReader,
    createProfileBulkReader,
    createProfileNetworkReader,
    
    // BufferWriter factories
    createProfileStandardWriter,
    createProfileSensorWriter,
    createProfileIPCWriter,
    createProfileBulkWriter,
    createProfileNetworkWriter,
    
    // AccumulatingReader factories
    createProfileStandardAccumulatingReader,
    createProfileSensorAccumulatingReader,
    createProfileIPCAccumulatingReader,
    createProfileBulkAccumulatingReader,
    createProfileNetworkAccumulatingReader,
} from './frame_profiles';
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
