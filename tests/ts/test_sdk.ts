/**
 * Subscribe / dispatch tests for the TypeScript StructFrameSdk (section 6.3)
 *
 * Uses a MockTransport and a real frame-parser backed by ProfileStandard
 * encoding/decoding to verify that subscribed handlers are invoked with the
 * correct payload when framed data arrives over the transport.
 */

import { BasicTypesMessage, getMessageInfo } from '../generated/ts/serialization-test.structframe';
import {
  ProfileStandardWriter,
  ProfileStandardConfig,
  parseFrameWithCrc,
} from '../generated/ts/frame-profiles';
import { StructFrameSdk } from '../generated/ts/struct-frame-sdk/struct-frame-sdk';
import { ITransport } from '../generated/ts/struct-frame-sdk/transport';

// =============================================================================
// Mock transport
// =============================================================================

class MockTransport implements ITransport {
  private dataCallback?: (data: Uint8Array) => void;
  private errorCallback?: (error: Error) => void;
  private closeCallback?: () => void;

  public readonly sentData: Uint8Array[] = [];
  private _connected = false;

  async connect(): Promise<void> { this._connected = true; }
  async disconnect(): Promise<void> { this._connected = false; }
  async send(data: Uint8Array): Promise<number> { this.sentData.push(data); return data.length; }

  isConnected(): boolean { return this._connected; }

  onData(callback: (data: Uint8Array) => void): void { this.dataCallback = callback; }
  onError(callback: (error: Error) => void): void { this.errorCallback = callback; }
  onClose(callback: () => void): void { this.closeCallback = callback; }

  /** Simulate incoming data from the peer. */
  injectData(data: Uint8Array): void { this.dataCallback?.(data); }
}

// =============================================================================
// Helpers
// =============================================================================

function encodeBasicTypes(regularInt: number, flag: boolean): Uint8Array {
  const msg = new BasicTypesMessage({ regularInt, flag });
  const writer = new ProfileStandardWriter(512);
  writer.write(msg);
  return writer.data();
}

function makeSdk(transport: MockTransport): StructFrameSdk {
  return new StructFrameSdk({
    transport,
    profile: ProfileStandardConfig,
    getMessageInfo,
  });
}

// =============================================================================
// Test infrastructure
// =============================================================================

let passed = 0;
let failed = 0;

function assert(name: string, condition: boolean): void {
  const ok = condition;
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}`);
  if (ok) passed++; else failed++;
}

// =============================================================================
// Tests
// =============================================================================

function testSubscribeAndDispatch(): void {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  let receivedPayload: Uint8Array | null = null;
  let receivedMsgId: number | null = null;
  let decoded: any = null;

  sdk.subscribe<Uint8Array>(BasicTypesMessage._msgid, (payload, msgId) => {
    receivedPayload = payload;
    receivedMsgId = msgId;
    decoded = BasicTypesMessage.deserialize(Buffer.from(payload));
  });

  transport.injectData(encodeBasicTypes(777, true));

  assert('subscribe: handler invoked on DataReceived', receivedPayload !== null);
  assert('subscribe: msgId matches BasicTypesMessage._msgid',
    receivedMsgId === BasicTypesMessage._msgid);
  assert('subscribe: regularInt field preserved', decoded?.regularInt === 777);
  assert('subscribe: flag field preserved', decoded?.flag === true);
}

function testMultipleHandlers(): void {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  let countA = 0, countB = 0;
  let lastA: any = null;
  let lastB: any = null;
  sdk.subscribe(BasicTypesMessage._msgid, (payload: Uint8Array) => {
    countA++;
    lastA = BasicTypesMessage.deserialize(Buffer.from(payload));
  });
  sdk.subscribe(BasicTypesMessage._msgid, (payload: Uint8Array) => {
    countB++;
    lastB = BasicTypesMessage.deserialize(Buffer.from(payload));
  });

  transport.injectData(encodeBasicTypes(1, false));

  assert('multiple handlers: first handler fires', countA === 1);
  assert('multiple handlers: second handler fires', countB === 1);
  assert('multiple handlers: first handler payload correct', lastA?.regularInt === 1);
  assert('multiple handlers: second handler payload correct', lastB?.regularInt === 1);
}

function testUnsubscribe(): void {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  let count = 0;
  let lastRegularInt = -1;
  const unsubscribe = sdk.subscribe(BasicTypesMessage._msgid, (payload: Uint8Array) => {
    count++;
    lastRegularInt = BasicTypesMessage.deserialize(Buffer.from(payload)).regularInt;
  });

  transport.injectData(encodeBasicTypes(1, false));
  assert('unsubscribe: handler fires before unsubscribe', count === 1);
  assert('unsubscribe: payload captured before unsubscribe', lastRegularInt === 1);

  unsubscribe();

  transport.injectData(encodeBasicTypes(2, true));
  assert('unsubscribe: handler silent after unsubscribe', count === 1);
  assert('unsubscribe: payload remains unchanged after unsubscribe', lastRegularInt === 1);
}

function testNoHandlerForUnregisteredId(): void {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  // Subscribe but then unsubscribe so no handler is active
  const unsub = sdk.subscribe(BasicTypesMessage._msgid, () => {});
  unsub();

  let errorThrown = false;
  try {
    transport.injectData(encodeBasicTypes(1, false));
  } catch {
    errorThrown = true;
  }

  assert('no handler: injecting data with no subscriber does not throw', !errorThrown);
}

function testWithCodecDeserializesMessage(): void {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  // Register a codec so the handler receives a deserialized object
  sdk.registerCodec({
    getMsgId: () => BasicTypesMessage._msgid,
    deserialize: (data: Uint8Array) => BasicTypesMessage.deserialize(Buffer.from(data)),
  });

  let decoded: BasicTypesMessage | null = null;
  sdk.subscribe<BasicTypesMessage>(BasicTypesMessage._msgid, (msg) => {
    decoded = msg;
  });

  transport.injectData(encodeBasicTypes(999, true));

  assert('codec: handler receives deserialized message', decoded !== null);
  assert('codec: regularInt field correct', (decoded as any)?.regularInt === 999);
  assert('codec: flag field correct', (decoded as any)?.flag === true);
}

async function testSendRawFramesThroughTransport(): Promise<void> {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  const payloadMsg = new BasicTypesMessage({ regularInt: 42, flag: true });
  const payload = payloadMsg.serialize();

  const sendResult = await sdk.sendRaw(BasicTypesMessage._msgid, payload);

  assert('sendRaw: transport.send was invoked', transport.sentData.length === 1);
  assert('sendRaw: result.success is true', sendResult.success === true);
  assert('sendRaw: attemptedBytes equals bytesWritten', sendResult.attemptedBytes === sendResult.bytesWritten);
  const sentFrame = transport.sentData[0];
  const parsed = parseFrameWithCrc(ProfileStandardConfig, sentFrame, getMessageInfo);
  assert('sendRaw: emitted frame parses as valid', parsed.valid === true);
  assert('sendRaw: emitted frame msgId preserved', parsed.msgId === BasicTypesMessage._msgid);
  assert('sendRaw: emitted frame payload preserved',
    Buffer.from(parsed.msgData).equals(Buffer.from(payload)));
}

// =============================================================================
// Main
// =============================================================================

async function main(): Promise<void> {
  console.log();
  console.log('========================================');
  console.log('SDK SUBSCRIBE/DISPATCH TESTS - TypeScript');
  console.log('========================================');
  console.log();

  testSubscribeAndDispatch();
  testMultipleHandlers();
  testUnsubscribe();
  testNoHandlerForUnregisteredId();
  testWithCodecDeserializesMessage();
  await testSendRawFramesThroughTransport();

  console.log();
  console.log('========================================');
  console.log(`Summary: ${passed}/${passed + failed} tests passed`);
  console.log('========================================');
  console.log();

  process.exit(failed > 0 ? 1 : 0);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
