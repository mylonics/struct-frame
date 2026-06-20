/**
 * Subscribe / dispatch tests for the JavaScript StructFrameSdk (section 6.3)
 *
 * Uses a MockTransport and a real frame-parser backed by ProfileStandard
 * encoding/decoding to verify that subscribed handlers are invoked with the
 * correct payload when framed data arrives over the transport.
 */

'use strict';

const { BasicTypesMessage, getMessageInfo } = require('../generated/js/serialization-test.structframe');
const { ProfileStandardConfig, BufferWriter, parseFrameWithCrc } = require('../generated/js/frame-profiles');
const { StructFrameSdk } = require('../generated/js/struct-frame-sdk/struct-frame-sdk');

// =============================================================================
// Mock transport
// =============================================================================

class MockTransport {
  constructor() {
    this._dataCallback = null;
    this._errorCallback = null;
    this._closeCallback = null;
    this.sentData = [];
    this._connected = false;
  }

  async connect() { this._connected = true; }
  async disconnect() { this._connected = false; }
  async send(data) { this.sentData.push(data); return data.length; }
  isConnected() { return this._connected; }
  onData(cb) { this._dataCallback = cb; }
  onError(cb) { this._errorCallback = cb; }
  onClose(cb) { this._closeCallback = cb; }

  /** Simulate incoming data from the peer. */
  injectData(data) { if (this._dataCallback) this._dataCallback(data); }
}

// =============================================================================
// Helpers
// =============================================================================

function encodeBasicTypes(regularInt, flag) {
  const msg = new BasicTypesMessage({ regularInt, flag });
  const writer = new BufferWriter(ProfileStandardConfig, 512);
  writer.write(msg);
  return writer.data();
}

function makeSdk(transport) {
  return new StructFrameSdk({ transport, profile: ProfileStandardConfig, getMessageInfo });
}

// =============================================================================
// Test infrastructure
// =============================================================================

let passed = 0;
let failed = 0;

function assert(name, condition) {
  console.log(`  ${condition ? 'PASS' : 'FAIL'}  ${name}`);
  if (condition) passed++; else failed++;
}

// =============================================================================
// Tests
// =============================================================================

function testSubscribeAndDispatch() {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  let receivedPayload = null;
  let receivedMsgId = null;
  let decoded = null;

  sdk.subscribe(BasicTypesMessage._msgid, (payload, msgId) => {
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

function testMultipleHandlers() {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  let countA = 0, countB = 0;
  let lastA = null;
  let lastB = null;
  sdk.subscribe(BasicTypesMessage._msgid, (payload) => {
    countA++;
    lastA = BasicTypesMessage.deserialize(Buffer.from(payload));
  });
  sdk.subscribe(BasicTypesMessage._msgid, (payload) => {
    countB++;
    lastB = BasicTypesMessage.deserialize(Buffer.from(payload));
  });

  transport.injectData(encodeBasicTypes(1, false));

  assert('multiple handlers: first handler fires', countA === 1);
  assert('multiple handlers: second handler fires', countB === 1);
  assert('multiple handlers: first handler payload correct', lastA?.regularInt === 1);
  assert('multiple handlers: second handler payload correct', lastB?.regularInt === 1);
}

function testUnsubscribe() {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  let count = 0;
  let lastRegularInt = -1;
  const unsub = sdk.subscribe(BasicTypesMessage._msgid, (payload) => {
    count++;
    lastRegularInt = BasicTypesMessage.deserialize(Buffer.from(payload)).regularInt;
  });

  transport.injectData(encodeBasicTypes(1, false));
  assert('unsubscribe: handler fires before unsubscribe', count === 1);
  assert('unsubscribe: payload captured before unsubscribe', lastRegularInt === 1);

  unsub();

  transport.injectData(encodeBasicTypes(2, true));
  assert('unsubscribe: handler silent after unsubscribe', count === 1);
  assert('unsubscribe: payload remains unchanged after unsubscribe', lastRegularInt === 1);
}

function testNoHandlerForUnregisteredId() {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  // Subscribe then immediately unsubscribe
  const unsub = sdk.subscribe(BasicTypesMessage._msgid, () => {});
  unsub();

  let errorThrown = false;
  try {
    transport.injectData(encodeBasicTypes(1, false));
  } catch (_) {
    errorThrown = true;
  }

  assert('no handler: injecting data with no subscriber does not throw', !errorThrown);
}

function testWithCodecDeserializesMessage() {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  sdk.registerCodec({
    getMsgId: () => BasicTypesMessage._msgid,
    deserialize: (data) => BasicTypesMessage.deserialize(Buffer.from(data)),
  });

  let decoded = null;
  sdk.subscribe(BasicTypesMessage._msgid, (msg) => { decoded = msg; });

  transport.injectData(encodeBasicTypes(999, true));

  assert('codec: handler receives deserialized message', decoded !== null);
  assert('codec: regularInt field correct', decoded?.regularInt === 999);
  assert('codec: flag field correct', decoded?.flag === true);
}

function testSendRaw() {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  const msg = new BasicTypesMessage({ regularInt: 42 });
  const payload = msg.serialize();

  // sendRaw is async; drive it to completion before asserting
  return sdk.sendRaw(BasicTypesMessage._msgid, payload).then((result) => {
    assert('sendRaw: transport.send was invoked', transport.sentData.length === 1);
    assert('sendRaw: result.success is true', result.success === true);
    assert('sendRaw: attemptedBytes equals bytesWritten', result.attemptedBytes === result.bytesWritten);
    const sentFrame = transport.sentData[0];
    const parsed = parseFrameWithCrc(ProfileStandardConfig, sentFrame, getMessageInfo);
    assert('sendRaw: emitted frame parses as valid', parsed.valid === true);
    assert('sendRaw: emitted frame msgId preserved', parsed.msgId === BasicTypesMessage._msgid);
    assert('sendRaw: emitted frame payload preserved',
      Buffer.from(parsed.msgData).equals(Buffer.from(payload)));
  });
}

/**
 * Lifecycle parity with the C# `TestThrowingHandlerDoesNotStopSiblings` test:
 * a handler that throws must not prevent sibling handlers from running, nor
 * escape into the transport callback.
 */
function testThrowingHandlerDoesNotStopSiblings() {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  let siblingFired = false;
  sdk.subscribe(BasicTypesMessage._msgid, () => { throw new Error('boom'); });
  sdk.subscribe(BasicTypesMessage._msgid, () => { siblingFired = true; });

  let errorThrown = false;
  try {
    transport.injectData(encodeBasicTypes(1, false));
  } catch {
    errorThrown = true;
  }

  assert('handler isolation: throwing handler does not propagate', !errorThrown);
  assert('handler isolation: sibling handler still fires', siblingFired);
}

// =============================================================================
// Main
// =============================================================================

console.log();
console.log('========================================');
console.log('SDK SUBSCRIBE/DISPATCH TESTS - JavaScript');
console.log('========================================');
console.log();

testSubscribeAndDispatch();
testMultipleHandlers();
testUnsubscribe();
testNoHandlerForUnregisteredId();
testWithCodecDeserializesMessage();
testThrowingHandlerDoesNotStopSiblings();

// testSendRaw is async — run it last and exit when it resolves
testSendRaw().then(() => {
  console.log();
  console.log('========================================');
  console.log(`Summary: ${passed}/${passed + failed} tests passed`);
  console.log('========================================');
  console.log();
  process.exit(failed > 0 ? 1 : 0);
});
