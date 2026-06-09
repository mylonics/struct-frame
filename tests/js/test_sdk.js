/**
 * Subscribe / dispatch tests for the JavaScript StructFrameSdk (section 6.3)
 *
 * Uses a MockTransport and a real frame-parser backed by ProfileStandard
 * encoding/decoding to verify that subscribed handlers are invoked with the
 * correct payload when framed data arrives over the transport.
 */

'use strict';

const { BasicTypesMessage, getMessageInfo } = require('../generated/js/serialization-test.structframe');
const { ProfileStandardConfig, ProfileStandardWriter, parseFrameWithCrc, encodeMessage } = require('../generated/js/frame-profiles');
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
  async send(data) { this.sentData.push(data); }
  isConnected() { return this._connected; }
  onData(cb) { this._dataCallback = cb; }
  onError(cb) { this._errorCallback = cb; }
  onClose(cb) { this._closeCallback = cb; }

  /** Simulate incoming data from the peer. */
  injectData(data) { if (this._dataCallback) this._dataCallback(data); }
}

// =============================================================================
// Frame parser backed by real ProfileStandard encode/decode
// =============================================================================

const standardFrameParser = {
  parse(data) {
    return parseFrameWithCrc(ProfileStandardConfig, data, getMessageInfo);
  },
  frame(msgId, data) {
    const info = getMessageInfo(msgId);
    const rawMsg = {
      _buffer: data,
      getMsgId: () => msgId,
      getMagic1: () => (info?.magic1 ?? 0),
      getMagic2: () => (info?.magic2 ?? 0),
      isVariable: () => false,
    };
    return encodeMessage(ProfileStandardConfig, rawMsg);
  },
};

// =============================================================================
// Helpers
// =============================================================================

function encodeBasicTypes(regularInt, flag) {
  const msg = new BasicTypesMessage({ regularInt, flag });
  const writer = new ProfileStandardWriter(512);
  writer.write(msg);
  return writer.data();
}

function makeSdk(transport) {
  return new StructFrameSdk({ transport, frameParser: standardFrameParser });
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

  sdk.subscribe(BasicTypesMessage._msgid, (payload, msgId) => {
    receivedPayload = payload;
    receivedMsgId = msgId;
  });

  transport.injectData(encodeBasicTypes(777, true));

  assert('subscribe: handler invoked on DataReceived', receivedPayload !== null);
  assert('subscribe: msgId matches BasicTypesMessage._msgid',
    receivedMsgId === BasicTypesMessage._msgid);
}

function testMultipleHandlers() {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  let countA = 0, countB = 0;
  sdk.subscribe(BasicTypesMessage._msgid, () => { countA++; });
  sdk.subscribe(BasicTypesMessage._msgid, () => { countB++; });

  transport.injectData(encodeBasicTypes(1, false));

  assert('multiple handlers: first handler fires', countA === 1);
  assert('multiple handlers: second handler fires', countB === 1);
}

function testUnsubscribe() {
  const transport = new MockTransport();
  const sdk = makeSdk(transport);

  let count = 0;
  const unsub = sdk.subscribe(BasicTypesMessage._msgid, () => { count++; });

  transport.injectData(encodeBasicTypes(1, false));
  assert('unsubscribe: handler fires before unsubscribe', count === 1);

  unsub();

  transport.injectData(encodeBasicTypes(2, true));
  assert('unsubscribe: handler silent after unsubscribe', count === 1);
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
  return sdk.sendRaw(BasicTypesMessage._msgid, payload).then(() => {
    assert('sendRaw: transport.send was invoked', transport.sentData.length === 1);
    const sentFrame = transport.sentData[0];
    const parsed = parseFrameWithCrc(ProfileStandardConfig, sentFrame, getMessageInfo);
    assert('sendRaw: emitted frame parses as valid', parsed.valid === true);
    assert('sendRaw: emitted frame msgId preserved', parsed.msgId === BasicTypesMessage._msgid);
    assert('sendRaw: emitted frame payload preserved',
      Buffer.from(parsed.msgData).equals(Buffer.from(payload)));
  });
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

// testSendRaw is async — run it last and exit when it resolves
testSendRaw().then(() => {
  console.log();
  console.log('========================================');
  console.log(`Summary: ${passed}/${passed + failed} tests passed`);
  console.log('========================================');
  console.log();
  process.exit(failed > 0 ? 1 : 0);
});
