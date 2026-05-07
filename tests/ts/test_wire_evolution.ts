/**
 * Wire-evolution extension field tests for the TypeScript SDK.
 *
 * Verifies that `option extensions_start` and the extension-aware CRC algorithm
 * work correctly end-to-end using the generated TypeScript bindings.
 *
 * Tests:
 *   1. _baseSize < _size for extension messages
 *   2. Encode → decode round-trip for BaseExtensionMessage (Standard profile)
 *   3. Encode → decode round-trip for OneOfExtensionMessage (extension variant)
 *   4. Encode → decode round-trip for MultiOneOfExtensionMessage
 *   5. Legacy-frame compatibility: zero-extension frame still validates CRC
 *   6. Corrupted extension bytes invalidate CRC
 *
 * Run:
 *   cd tests/ts && npx ts-node test_wire_evolution.ts
 */

import {
  BaseExtensionMessage,
  BaseCommandA,
  BaseCommandB,
  ExtCommandC,
  OneOfExtensionMessage,
  OneOfExtensionMessageCommandField,
  MultiOneOfExtensionMessage,
  MultiOneOfExtensionMessageExtUnionField,
  getMessageInfo,
} from '../generated/ts/wire-evolution.structframe';

import {
  ProfileStandardConfig,
  encodeMessage,
  parseFrameWithCrc,
} from '../generated/ts/frame-profiles';

// ---------------------------------------------------------------------------
// Simple test harness
// ---------------------------------------------------------------------------

let pass = 0;
let fail = 0;

function check(cond: boolean, msg: string): void {
  if (cond) {
    console.log(`  [PASS] ${msg}`);
    pass++;
  } else {
    console.error(`  [FAIL] ${msg}`);
    fail++;
  }
}

// ---------------------------------------------------------------------------
// Test 1: compile-time _baseSize < _size
// ---------------------------------------------------------------------------

function testBaseSizeConstants(): void {
  check(BaseExtensionMessage._baseSize < BaseExtensionMessage._size,
    'BaseExtensionMessage _baseSize < _size');
  check(BaseExtensionMessage._baseSize === 3,
    'BaseExtensionMessage _baseSize === 3 (header+seq)');
  check(BaseExtensionMessage._size === 7,
    'BaseExtensionMessage _size === 7 (header+seq+crc_seed)');

  check(OneOfExtensionMessage._baseSize < OneOfExtensionMessage._size,
    'OneOfExtensionMessage _baseSize < _size');

  // MultiOneOfExtensionMessage: no extensions → _baseSize == _size
  check(MultiOneOfExtensionMessage._baseSize === MultiOneOfExtensionMessage._size,
    'MultiOneOfExtensionMessage _baseSize === _size (no extensions)');
}

// ---------------------------------------------------------------------------
// Test 2: BaseExtensionMessage encode → decode round-trip (Standard profile)
// ---------------------------------------------------------------------------

function testBaseExtensionRoundtrip(): void {
  const orig = new BaseExtensionMessage({ header: 0xBEEF, seq: 42, crcSeed: 0xDEADC0DE });

  const frameBytes = encodeMessage(ProfileStandardConfig, orig);
  check(frameBytes.length > 0, 'BaseExtensionMessage encode succeeded');

  const info = parseFrameWithCrc(ProfileStandardConfig, frameBytes, getMessageInfo);
  check(info.valid, 'BaseExtensionMessage frame validates CRC');
  check(info.msgId === BaseExtensionMessage._msgid,
    'BaseExtensionMessage msg_id matches');
  check(info.msgLen === BaseExtensionMessage._size,
    'BaseExtensionMessage msg_len matches _size');

  if (info.valid && info.msgData) {
    const decoded = BaseExtensionMessage.deserialize(info);
    check(decoded.header === 0xBEEF, 'decoded header matches');
    check(decoded.seq === 42, 'decoded seq matches');
    check(decoded.crcSeed === 0xDEADC0DE, 'decoded crcSeed matches');
  }
}

// ---------------------------------------------------------------------------
// Test 3: OneOfExtensionMessage with extension variant (CMD_C)
// ---------------------------------------------------------------------------

function testOneOfExtensionVariantRoundtrip(): void {
  const orig = new OneOfExtensionMessage({
    deviceId: 7,
    commandDiscriminator: OneOfExtensionMessageCommandField.CmdC,
  });
  // Manually write cmd_c payload bytes (valueC=3.14f, modeC=2)
  const cmdCBuf = Buffer.alloc(5);
  cmdCBuf.writeFloatLE(3.14, 0);
  cmdCBuf.writeUInt8(2, 4);
  orig.commandData = Array.from(cmdCBuf);

  const frameBytes = encodeMessage(ProfileStandardConfig, orig);
  check(frameBytes.length > 0, 'OneOfExtensionMessage (ext variant) encode succeeded');

  const info = parseFrameWithCrc(ProfileStandardConfig, frameBytes, getMessageInfo);
  check(info.valid, 'OneOfExtensionMessage (ext variant) frame validates CRC');

  if (info.valid && info.msgData) {
    const decoded = OneOfExtensionMessage.deserialize(info);
    check(decoded.deviceId === 7, 'decoded deviceId matches');
    check(decoded.commandDiscriminator === OneOfExtensionMessageCommandField.CmdC,
      'decoded command discriminator == CmdC');
    const cmdCView = Buffer.from(decoded.commandData);
    const decodedValueC = cmdCView.readFloatLE(0);
    check(Math.abs(decodedValueC - 3.14) < 0.001, 'decoded cmd_c.valueC matches');
    check(cmdCView.readUInt8(4) === 2, 'decoded cmd_c.modeC matches');
  }
}

// ---------------------------------------------------------------------------
// Test 4: MultiOneOfExtensionMessage with extension variant in second oneof
// ---------------------------------------------------------------------------

function testMultiOneOfExtensionRoundtrip(): void {
  const orig = new MultiOneOfExtensionMessage({
    priority: 3,
    baseUnionDiscriminator: 1, // FIRST_A
    extUnionDiscriminator: MultiOneOfExtensionMessageExtUnionField.SecondExt,
  });
  // Write ext_union second_ext (ExtCommandC: valueC=2.71f, modeC=1)
  const extBuf = Buffer.alloc(6);
  extBuf.writeFloatLE(2.71, 0);
  extBuf.writeUInt8(1, 4);
  orig.extUnionData = Array.from(extBuf);

  const frameBytes = encodeMessage(ProfileStandardConfig, orig);
  check(frameBytes.length > 0, 'MultiOneOfExtensionMessage encode succeeded');

  const info = parseFrameWithCrc(ProfileStandardConfig, frameBytes, getMessageInfo);
  check(info.valid, 'MultiOneOfExtensionMessage frame validates CRC');

  if (info.valid && info.msgData) {
    const decoded = MultiOneOfExtensionMessage.deserialize(info);
    check(decoded.priority === 3, 'decoded priority matches');
    check(decoded.extUnionDiscriminator === MultiOneOfExtensionMessageExtUnionField.SecondExt,
      'decoded ext_union discriminator == SecondExt');
    const extView = Buffer.from(decoded.extUnionData);
    const decodedValueC = extView.readFloatLE(0);
    check(Math.abs(decodedValueC - 2.71) < 0.001, 'decoded second_ext.valueC matches');
  }
}

// ---------------------------------------------------------------------------
// Test 5: Legacy-frame compatibility (zero extension bytes)
// ---------------------------------------------------------------------------

function testLegacyFrameCompatibility(): void {
  // Encode with extension field == 0 (simulates legacy sender)
  const orig = new BaseExtensionMessage({ header: 0x1234, seq: 7, crcSeed: 0 });
  const frameBytes = encodeMessage(ProfileStandardConfig, orig);
  check(frameBytes.length > 0, 'legacy (zero extension) frame encodes');

  const info = parseFrameWithCrc(ProfileStandardConfig, frameBytes, getMessageInfo);
  check(info.valid, 'legacy (zero extension) frame validates CRC');

  if (info.valid && info.msgData) {
    const decoded = BaseExtensionMessage.deserialize(info);
    check(decoded.header === 0x1234, 'legacy decoded header matches');
    check(decoded.seq === 7, 'legacy decoded seq matches');
    check(decoded.crcSeed === 0, 'legacy decoded crcSeed is 0');
  }

  // Verify that corrupting the extension bytes invalidates CRC
  // Frame structure: start1, start2, [crcStart] length_lo, length_hi, msgid_lo, msgid_hi, payload..., crc_lo, crc_hi
  // For Standard profile: header_size = 2 (start bytes) + 4 (length + msgid) = 6
  const corruptedFrame = new Uint8Array(frameBytes);
  const headerSize = 2 + 4; // start bytes + length(2) + msgid(2)
  const extOffset = headerSize + BaseExtensionMessage._baseSize;
  corruptedFrame[extOffset] ^= 0xFF;
  const badInfo = parseFrameWithCrc(ProfileStandardConfig, corruptedFrame, getMessageInfo);
  check(!badInfo.valid, 'corrupted extension bytes invalidate CRC');
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

console.log('=== TypeScript Wire-Evolution Extension Field Tests ===\n');

console.log('Test group 1: _baseSize constants');
testBaseSizeConstants();
console.log();

console.log('Test group 2: BaseExtensionMessage encode/decode round-trip');
testBaseExtensionRoundtrip();
console.log();

console.log('Test group 3: OneOfExtensionMessage (extension variant) round-trip');
testOneOfExtensionVariantRoundtrip();
console.log();

console.log('Test group 4: MultiOneOfExtensionMessage round-trip');
testMultiOneOfExtensionRoundtrip();
console.log();

console.log('Test group 5: Legacy-frame compatibility');
testLegacyFrameCompatibility();
console.log();

console.log(`Results: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
