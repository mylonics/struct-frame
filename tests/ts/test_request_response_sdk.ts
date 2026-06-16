/**
 * Request / response tests for the TypeScript StructFrameSdk.
 *
 * Uses MockTransport + real frame encoding.  Responses are injected via
 * setTimeout so they arrive after request() has registered its subscription
 * and the returned Promise is awaiting.
 *
 * Test matrix
 * -----------
 * - Basic request/response: request() resolves with the first matching response.
 * - Timeout: request() rejects when no response arrives.
 * - match predicate: responses are filtered by a correlation field.
 * - Concurrent requests: two in-flight requests resolve independently.
 * - Subscription cleanup: handler removed after success and after timeout.
 */

import { BasicTypesMessage, getMessageInfo } from '../generated/ts/serialization-test.structframe';
import {
  BufferWriter,
  ProfileStandardConfig,
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

  injectData(data: Uint8Array): void { this.dataCallback?.(data); }
}

// =============================================================================
// Helpers
// =============================================================================

function encodeMsg(regularInt: number, flag: boolean, mediumInt = 0): Uint8Array {
  const msg = new BasicTypesMessage({ regularInt, flag, mediumInt });
  const writer = new BufferWriter(ProfileStandardConfig, 512);
  writer.write(msg);
  return writer.data();
}

function makeSdk(transport: MockTransport): StructFrameSdk {
  return new StructFrameSdk({ transport, profile: ProfileStandardConfig, getMessageInfo });
}

function injectAfter(transport: MockTransport, data: Uint8Array, delayMs = 30): void {
  setTimeout(() => transport.injectData(data), delayMs);
}

// =============================================================================
// Test infrastructure
// =============================================================================

let passed = 0;
let failed = 0;

function assert(name: string, condition: boolean): void {
  console.log(`  ${condition ? 'PASS' : 'FAIL'}  ${name}`);
  if (condition) passed++; else failed++;
}

// =============================================================================
// Tests
// =============================================================================

async function testBasicRequestResponse(): Promise<void> {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  // Register codec so handler receives deserialized objects.
  sdk.registerCodec({
    getMsgId: () => BasicTypesMessage._msgid,
    deserialize: (data) => BasicTypesMessage.deserialize(Buffer.from(data)),
  });

  injectAfter(transport, encodeMsg(10, true));

  const result = await sdk.request<BasicTypesMessage>(
    new BasicTypesMessage({ regularInt: 10 }),
    BasicTypesMessage._msgid,
    { timeout: 2 },
  );

  assert('basic: request() resolves', result !== null && result !== undefined);
  assert('basic: result is BasicTypesMessage', result instanceof BasicTypesMessage);
  assert('basic: flag field correct', (result as any).flag === true);
  assert('basic: request was sent', transport.sentData.length === 1);
}

async function testTimeout(): Promise<void> {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  let rejected = false;
  try {
    await sdk.request<BasicTypesMessage>(
      new BasicTypesMessage({ regularInt: 99 }),
      BasicTypesMessage._msgid,
      { timeout: 0.1 },
    );
  } catch (err) {
    rejected = true;
    assert('timeout: error message mentions msgId',
      err instanceof Error && err.message.includes(String(BasicTypesMessage._msgid)));
  }
  assert('timeout: Promise rejects', rejected);
  assert('timeout: request was still sent', transport.sentData.length === 1);
}

async function testMatchPredicateFiltersResponses(): Promise<void> {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  sdk.registerCodec({
    getMsgId: () => BasicTypesMessage._msgid,
    deserialize: (data) => BasicTypesMessage.deserialize(Buffer.from(data)),
  });

  // Inject a wrong response first, then the correct one.
  setTimeout(() => {
    transport.injectData(encodeMsg(99, false));   // wrong
    setTimeout(() => transport.injectData(encodeMsg(7, true)), 30);  // correct
  }, 20);

  const result = await sdk.request<BasicTypesMessage>(
    new BasicTypesMessage({ regularInt: 7 }),
    BasicTypesMessage._msgid,
    {
      match: (r) => (r as any).regularInt === 7,
      timeout: 2,
    },
  );

  assert('match: non-matching response ignored', result !== null);
  assert('match: correct response returned', (result as any).regularInt === 7);
  assert('match: flag field from matching response', (result as any).flag === true);
}

async function testConcurrentRequestsWithMatch(): Promise<void> {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  sdk.registerCodec({
    getMsgId: () => BasicTypesMessage._msgid,
    deserialize: (data) => BasicTypesMessage.deserialize(Buffer.from(data)),
  });

  // Inject responses in reverse order after both requests are parked.
  setTimeout(() => {
    transport.injectData(encodeMsg(2, false));  // for request B first
    transport.injectData(encodeMsg(1, true));   // for request A
  }, 40);

  const [resultA, resultB] = await Promise.all([
    sdk.request<BasicTypesMessage>(
      new BasicTypesMessage({ regularInt: 1 }),
      BasicTypesMessage._msgid,
      { match: (r) => (r as any).regularInt === 1, timeout: 2 },
    ),
    sdk.request<BasicTypesMessage>(
      new BasicTypesMessage({ regularInt: 2 }),
      BasicTypesMessage._msgid,
      { match: (r) => (r as any).regularInt === 2, timeout: 2 },
    ),
  ]);

  assert('concurrent: request A resolved correctly', (resultA as any).regularInt === 1);
  assert('concurrent: request B resolved correctly', (resultB as any).regularInt === 2);
  assert('concurrent: A flag correct', (resultA as any).flag === true);
  assert('concurrent: B flag correct', (resultB as any).flag === false);
}

async function testSubscriptionRemovedAfterSuccess(): Promise<void> {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  sdk.registerCodec({
    getMsgId: () => BasicTypesMessage._msgid,
    deserialize: (data) => BasicTypesMessage.deserialize(Buffer.from(data)),
  });

  injectAfter(transport, encodeMsg(3, false));
  await sdk.request<BasicTypesMessage>(
    new BasicTypesMessage({ regularInt: 3 }),
    BasicTypesMessage._msgid,
    { timeout: 2 },
  );

  const handlers = (sdk as any).messageHandlers.get(BasicTypesMessage._msgid) ?? [];
  assert('cleanup: subscription removed after success', handlers.length === 0);
}

async function testSubscriptionRemovedAfterTimeout(): Promise<void> {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  try {
    await sdk.request<BasicTypesMessage>(
      new BasicTypesMessage({ regularInt: 0 }),
      BasicTypesMessage._msgid,
      { timeout: 0.05 },
    );
  } catch {
    // expected
  }

  const handlers = (sdk as any).messageHandlers.get(BasicTypesMessage._msgid) ?? [];
  assert('cleanup: subscription removed after timeout', handlers.length === 0);
}

// =============================================================================
// Main
// =============================================================================

async function main(): Promise<void> {
  console.log();
  console.log('========================================');
  console.log('REQUEST/RESPONSE TESTS - TypeScript');
  console.log('========================================');
  console.log();

  await testBasicRequestResponse();
  await testTimeout();
  await testMatchPredicateFiltersResponses();
  await testConcurrentRequestsWithMatch();
  await testSubscriptionRemovedAfterSuccess();
  await testSubscriptionRemovedAfterTimeout();

  console.log();
  console.log('========================================');
  console.log(`Summary: ${passed}/${passed + failed} tests passed`);
  console.log('========================================');
  console.log();

  process.exit(failed > 0 ? 1 : 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
