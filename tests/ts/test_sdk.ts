/**
 * Subscribe / dispatch tests for the TypeScript StructFrameSdk (section 6.3)
 *
 * Uses a MockTransport and a real frame-parser backed by ProfileStandard
 * encoding/decoding to verify that subscribed handlers are invoked with the
 * correct payload when framed data arrives over the transport.
 */

import { BasicTypesMessage, getMessageInfo } from '../generated/ts/serialization-test.structframe';
import {
  encodeMessage,
  ProfileStandardWriter,
  ProfileStandardConfig,
  parseFrameWithCrc,
} from '../generated/ts/frame-profiles';
import { FrameMsgInfo } from '../generated/ts/frame-base';
import { StructFrameSdk, FrameParser } from '../generated/ts/struct-frame-sdk/struct-frame-sdk';
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
  async send(data: Uint8Array): Promise<void> { this.sentData.push(data); }

  isConnected(): boolean { return this._connected; }

  onData(callback: (data: Uint8Array) => void): void { this.dataCallback = callback; }
  onError(callback: (error: Error) => void): void { this.errorCallback = callback; }
  onClose(callback: () => void): void { this.closeCallback = callback; }

  /** Simulate incoming data from the peer. */
  injectData(data: Uint8Array): void { this.dataCallback?.(data); }
}

// =============================================================================
// Frame parser backed by real ProfileStandard encode/decode
// =============================================================================

class StandardFrameParser implements FrameParser {
  parse(data: Uint8Array): FrameMsgInfo {
    return parseFrameWithCrc(ProfileStandardConfig, data, getMessageInfo);
  }

  frame(msgId: number, data: Uint8Array): Uint8Array {
    const info = getMessageInfo(msgId);
    const rawMsg: any = {
      _buffer: data,
      getMsgId: () => msgId,
      getMagic1: () => info?.magic1 ?? 0,
      getMagic2: () => info?.magic2 ?? 0,
      isVariable: () => false,
    };
    return encodeMessage(ProfileStandardConfig, rawMsg);
  }
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
    frameParser: new StandardFrameParser(),
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

  let receivedPayload: any = null;
  let receivedMsgId: number | null = null;

  sdk.subscribe<Uint8Array>(BasicTypesMessage._msgid, (payload, msgId) => {
    receivedPayload = payload;
    receivedMsgId = msgId;
  });

  transport.injectData(encodeBasicTypes(777, true));

  assert('subscribe: handler invoked on DataReceived', receivedPayload !== null);
  assert('subscribe: msgId matches BasicTypesMessage._msgid',
    receivedMsgId === BasicTypesMessage._msgid);
}

function testMultipleHandlers(): void {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  let countA = 0, countB = 0;
  sdk.subscribe(BasicTypesMessage._msgid, () => { countA++; });
  sdk.subscribe(BasicTypesMessage._msgid, () => { countB++; });

  transport.injectData(encodeBasicTypes(1, false));

  assert('multiple handlers: first handler fires', countA === 1);
  assert('multiple handlers: second handler fires', countB === 1);
}

function testUnsubscribe(): void {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  let count = 0;
  const unsubscribe = sdk.subscribe(BasicTypesMessage._msgid, () => { count++; });

  transport.injectData(encodeBasicTypes(1, false));
  assert('unsubscribe: handler fires before unsubscribe', count === 1);

  unsubscribe();

  transport.injectData(encodeBasicTypes(2, true));
  assert('unsubscribe: handler silent after unsubscribe', count === 1);
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

  await sdk.sendRaw(BasicTypesMessage._msgid, payload);

  assert('sendRaw: transport.send was invoked', transport.sentData.length === 1);
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
