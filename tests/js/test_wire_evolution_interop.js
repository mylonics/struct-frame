/**
 * Cross-version wire-evolution *interop* tests for the JavaScript SDK.
 *
 * Unlike the single-schema round-trip test, this runner uses two SEPARATELY
 * generated schema versions of the same messages:
 *
 *   - wire-evolution-v1  -- base fields only (older, extension-unaware)
 *   - wire-evolution-v2  -- base fields + `extensions_start` extension fields
 *
 * Each side has its own message classes, magic constants and `getMessageInfo`
 * lookup, exactly as two independently-built code-bases would.  The tests
 * exercise genuine newer<->older interop over the length-bearing
 * Standard/Bulk/Network profiles plus negative coverage.
 *
 * Scenarios (mirrors the project's wire-evolution interop plan, 1-10):
 *   1. Newer sender -> older receiver (v2 encodes extensions, v1 decodes base)
 *   2. Older sender -> newer receiver (v1 base-only, v2 zero-fills extensions)
 *   3. Same-version sanity (v2 -> v2 with extension variant)
 *   4. Newer ext oneof variant -> older receiver degrades gracefully
 *   5. Older base oneof variant -> newer receiver decodes correctly
 *   6. Multi-oneof: base oneof unaffected while ext oneof exercises 4/5
 *   7. Corrupted extension bytes invalidate the full CRC
 *   8. Truncated payload (fewer bytes than length field claims) is rejected
 *   9. Length-less profile guard (IPC): both sides must agree on full size
 *  10. Variable base array + trailing extension field, both interop directions
 *
 * Run:
 *   node tests/js/test_wire_evolution_interop.js
 */

'use strict';

const {
  BaseExtensionMessage: V1BaseExtensionMessage,
  OneOfExtensionMessage: V1OneOfExtensionMessage,
  MultiOneOfExtensionMessage: V1MultiOneOfExtensionMessage,
  VariableExtensionMessage: V1VariableExtensionMessage,
  getMessageInfo: v1GetMessageInfo,
} = require('../generated/js/wire-evolution-v1.structframe');

const {
  BaseExtensionMessage: V2BaseExtensionMessage,
  OneOfExtensionMessage: V2OneOfExtensionMessage,
  MultiOneOfExtensionMessage: V2MultiOneOfExtensionMessage,
  VariableExtensionMessage: V2VariableExtensionMessage,
  getMessageInfo: v2GetMessageInfo,
} = require('../generated/js/wire-evolution-v2.structframe');

const {
  ProfileStandardConfig,
  ProfileBulkConfig,
  ProfileNetworkConfig,
  ProfileIPCConfig,
  encodeMessage,
  parseFrameWithCrc,
  parseFrameMinimal,
} = require('../generated/js/frame-profiles');

// Discriminator values (matching the generated enum values)
const CMD_B = 2; // OneOfExtensionMessageCommandField.CmdB
const CMD_C = 3; // OneOfExtensionMessageCommandField.CmdC
const CMD_D = 4; // OneOfExtensionMessageCommandField.CmdD
const FIRST_A = 1; // MultiOneOfExtensionMessageBaseUnionField.FirstA
const SECOND_EXT = 2; // MultiOneOfExtensionMessageExtUnionField.SecondExt

let passCount = 0;
let failCount = 0;

function check(cond, msg) {
  if (cond) {
    console.log(`  [PASS] ${msg}`);
    passCount++;
  } else {
    console.error(`  [FAIL] ${msg}`);
    failCount++;
  }
}

// ---------------------------------------------------------------------------
// Scenario 1: newer sender -> older receiver over length-bearing profiles
// ---------------------------------------------------------------------------
function scenario1() {
  const profiles = [
    [ProfileStandardConfig, 'standard'],
    [ProfileBulkConfig, 'bulk'],
    [ProfileNetworkConfig, 'network'],
  ];
  for (const [config, name] of profiles) {
    const orig = new V2BaseExtensionMessage();
    orig.header = 0xBEEF;
    orig.seq = 42;
    orig.crcSeed = 0xDEADC0DE;
    const frame = encodeMessage(config, orig);
    const info = parseFrameWithCrc(config, frame, v1GetMessageInfo);
    check(info.valid, `[S1/${name}] v2->v1 frame validates CRC (magic from base)`);
    if (info.valid && info.msgData) {
      const d = V1BaseExtensionMessage.deserialize(info);
      check(d.header === 0xBEEF && d.seq === 42,
        `[S1/${name}] v1 decodes base; trailing ext bytes ignored`);
    }
  }
}

// ---------------------------------------------------------------------------
// Scenario 2: older sender -> newer receiver (zero-fill extensions)
// ---------------------------------------------------------------------------
function scenario2() {
  const orig = new V1BaseExtensionMessage();
  orig.header = 0x1234;
  orig.seq = 7;
  const frame = encodeMessage(ProfileStandardConfig, orig);
  const info = parseFrameWithCrc(ProfileStandardConfig, frame, v2GetMessageInfo);
  check(info.valid, '[S2] v1->v2 base-only frame validates CRC');
  if (info.valid && info.msgData) {
    // V2 deserialize copies the short payload into a _size buffer, leaving the
    // extension bytes zero-filled to their defaults.
    const d = V2BaseExtensionMessage.deserialize(info);
    check(d.header === 0x1234 && d.seq === 7, '[S2] v2 decodes base fields correctly');
    check(d.crcSeed === 0, '[S2] v2 extension field zero-filled to default');
  }
}

// ---------------------------------------------------------------------------
// Scenario 3: same-version sanity (v2 -> v2 with extension variant)
// ---------------------------------------------------------------------------
function scenario3() {
  const orig = new V2OneOfExtensionMessage();
  orig.deviceId = 2;
  orig.commandDiscriminator = CMD_C;
  const cmdC = Buffer.alloc(5);
  cmdC.writeFloatLE(3.14, 0);
  cmdC.writeUInt8(2, 4);
  orig.commandData = Array.from(cmdC);

  const frame = encodeMessage(ProfileStandardConfig, orig);
  const info = parseFrameWithCrc(ProfileStandardConfig, frame, v2GetMessageInfo);
  check(info.valid, '[S3] v2->v2 (ext variant) frame validates CRC');
  if (info.valid && info.msgData) {
    const d = V2OneOfExtensionMessage.deserialize(info);
    const view = Buffer.from(d.commandData);
    check(d.commandDiscriminator === CMD_C && Math.abs(view.readFloatLE(0) - 3.14) < 0.001,
      '[S3] v2 round-trips the extension variant');
  }
}

// ---------------------------------------------------------------------------
// Scenario 4: newer ext oneof variant -> older receiver degrades gracefully
// ---------------------------------------------------------------------------
function scenario4() {
  const orig = new V2OneOfExtensionMessage();
  orig.deviceId = 9;
  orig.commandDiscriminator = CMD_D;
  const cmdD = Buffer.alloc(8);
  cmdD.writeDoubleLE(2.718281828, 0);
  orig.commandData = Array.from(cmdD);

  const frame = encodeMessage(ProfileStandardConfig, orig);
  const info = parseFrameWithCrc(ProfileStandardConfig, frame, v1GetMessageInfo);
  check(info.valid, '[S4] v2 ext-variant -> v1 frame validates CRC');
  if (info.valid && info.msgData) {
    const d = V1OneOfExtensionMessage.deserialize(info);
    check(d.deviceId === 9, '[S4] v1 still decodes the base header field');
    // v1 knows nothing about discriminator 4; it must preserve the raw value
    // without corrupting the base field.
    check(Number(d.commandDiscriminator) === 4,
      '[S4] v1 preserves unknown ext discriminator without corruption');
  }
}

// ---------------------------------------------------------------------------
// Scenario 5: older base oneof variant -> newer receiver decodes correctly
// ---------------------------------------------------------------------------
function scenario5() {
  const orig = new V1OneOfExtensionMessage();
  orig.deviceId = 5;
  orig.commandDiscriminator = CMD_B;
  // BaseCommandB: value_b (int16 LE) + active_b (bool)
  const cmdB = Buffer.alloc(3);
  cmdB.writeInt16LE(-1234, 0);
  cmdB.writeUInt8(1, 2);
  orig.commandData = Array.from(cmdB);

  const frame = encodeMessage(ProfileStandardConfig, orig);
  const info = parseFrameWithCrc(ProfileStandardConfig, frame, v2GetMessageInfo);
  check(info.valid, '[S5] v1 base-variant -> v2 frame validates CRC');
  if (info.valid && info.msgData) {
    const d = V2OneOfExtensionMessage.deserialize(info);
    const view = Buffer.from(d.commandData);
    check(d.commandDiscriminator === CMD_B && view.readInt16LE(0) === -1234,
      '[S5] v2 decodes the older base oneof variant correctly');
  }
}

// ---------------------------------------------------------------------------
// Scenario 6: multi-oneof, ext only in the second union
// ---------------------------------------------------------------------------
function scenario6() {
  const orig = new V2MultiOneOfExtensionMessage();
  orig.priority = 3;
  orig.baseUnionDiscriminator = FIRST_A;
  orig.extUnionDiscriminator = SECOND_EXT;
  // base_union first_a (BaseCommandA: value_a uint32 + flags_a uint16)
  const baseBuf = Buffer.alloc(6);
  baseBuf.writeUInt32LE(100, 0);
  baseBuf.writeUInt16LE(5, 4);
  orig.baseUnionData = Array.from(baseBuf);
  // ext_union second_ext (ExtCommandC: value_c float + mode_c uint8)
  const extBuf = Buffer.alloc(6);
  extBuf.writeFloatLE(2.71, 0);
  extBuf.writeUInt8(1, 4);
  orig.extUnionData = Array.from(extBuf);

  const frame = encodeMessage(ProfileStandardConfig, orig);
  const info = parseFrameWithCrc(ProfileStandardConfig, frame, v1GetMessageInfo);
  check(info.valid, '[S6] v2 multi-oneof (ext in 2nd union) -> v1 validates CRC');
  if (info.valid && info.msgData) {
    const d = V1MultiOneOfExtensionMessage.deserialize(info);
    const baseView = Buffer.from(d.baseUnionData);
    check(d.priority === 3 && Number(d.baseUnionDiscriminator) === 1
      && baseView.readUInt32LE(0) === 100,
      '[S6] v1 decodes the FIRST (base) oneof unaffected by ext in the second');
  }
}

// ---------------------------------------------------------------------------
// Scenario 7: corrupted extension bytes invalidate the full CRC
// ---------------------------------------------------------------------------
function scenario7() {
  const orig = new V2BaseExtensionMessage();
  orig.header = 0xBEEF;
  orig.seq = 42;
  orig.crcSeed = 0xDEADC0DE;
  const frame = encodeMessage(ProfileStandardConfig, orig);

  const corrupted = Buffer.from(frame);
  const headerSize = 2 + 4; // start bytes(2) + length(2) + msgid(2)
  const extOffset = headerSize + V2BaseExtensionMessage._baseSize;
  corrupted[extOffset] ^= 0xFF;

  const info = parseFrameWithCrc(ProfileStandardConfig, corrupted, v1GetMessageInfo);
  check(!info.valid, '[S7] corrupted extension byte invalidates full CRC');
}

// ---------------------------------------------------------------------------
// Scenario 8: truncated payload is rejected
// ---------------------------------------------------------------------------
function scenario8() {
  const orig = new V1BaseExtensionMessage();
  orig.header = 1;
  orig.seq = 2;
  const frame = encodeMessage(ProfileStandardConfig, orig);
  // Drop the last byte — fewer bytes than the length field claims.
  const truncated = frame.slice(0, frame.length - 1);
  const info = parseFrameWithCrc(ProfileStandardConfig, truncated, v1GetMessageInfo);
  check(!info.valid, '[S8] truncated payload (fewer bytes than length claims) is rejected');
}

// ---------------------------------------------------------------------------
// Scenario 9: length-less profile guard (IPC)
//
// On a length-less (IPC) profile both sides must agree on the full fixed size.
// An older (base-only, shorter) frame is NOT silently accepted by a newer
// receiver because the frame size does not match the expected MAX_SIZE.
// ---------------------------------------------------------------------------
function scenario9() {
  // Positive: same-version v2 over IPC validates.
  const same = new V2BaseExtensionMessage();
  same.header = 0xAA;
  same.seq = 5;
  same.crcSeed = 0x99;
  const frame = encodeMessage(ProfileIPCConfig, same);
  const info = parseFrameMinimal(ProfileIPCConfig, frame, v2GetMessageInfo);
  check(info.valid, '[S9] IPC same-version v2 frame validates');

  // Negative: base-only v1 frame (shorter) rejected by newer v2 receiver.
  const older = new V1BaseExtensionMessage();
  older.header = 0xAA;
  older.seq = 5;
  const frame2 = encodeMessage(ProfileIPCConfig, older);
  const info2 = parseFrameMinimal(ProfileIPCConfig, frame2, v2GetMessageInfo);
  check(!info2.valid,
    '[S9] IPC base-only older frame is rejected by newer receiver '
    + '(both sides must agree on size)');
}

// ---------------------------------------------------------------------------
// Scenario 10: variable base array + trailing extension, both directions
// ---------------------------------------------------------------------------
function scenario10() {
  // Newer -> older: v1 locates variable base, ignores trailing ext bytes.
  const orig = new V2VariableExtensionMessage();
  orig.nodeId = 7;
  orig.readingsCount = 3;
  orig.readingsData = [10, 20, 30];
  orig.extTimestamp = 0x12345678;

  const frame = encodeMessage(ProfileStandardConfig, orig);
  const info = parseFrameWithCrc(ProfileStandardConfig, frame, v1GetMessageInfo);
  check(info.valid, '[S10] v2 variable+ext -> v1 validates CRC');
  if (info.valid && info.msgData) {
    const d = V1VariableExtensionMessage.deserialize(info);
    check(d.nodeId === 7
      && d.readingsCount === 3
      && d.readingsData[0] === 10
      && d.readingsData[1] === 20
      && d.readingsData[2] === 30,
      '[S10] v1 locates/decodes variable base; trailing ext bytes ignored');
  }

  // Older -> newer: v2 zero-fills the trailing extension field.
  const orig2 = new V1VariableExtensionMessage();
  orig2.nodeId = 9;
  orig2.readingsCount = 2;
  orig2.readingsData = [1, 2];

  const frame2 = encodeMessage(ProfileStandardConfig, orig2);
  const info2 = parseFrameWithCrc(ProfileStandardConfig, frame2, v2GetMessageInfo);
  check(info2.valid, '[S10] v1 variable (base-only) -> v2 validates CRC');
  if (info2.valid && info2.msgData) {
    const d2 = V2VariableExtensionMessage.deserialize(info2);
    check(d2.nodeId === 9
      && d2.readingsCount === 2
      && d2.readingsData[0] === 1
      && d2.readingsData[1] === 2,
      '[S10] v2 locates variable base after cross-version decode');
    check(d2.extTimestamp === 0, '[S10] v2 zero-fills the trailing extension field');
  }
}

console.log('=== JavaScript Cross-Version Wire-Evolution Interop Tests ===\n');

console.log('Scenario 1: newer sender -> older receiver (length-bearing)');
scenario1();
console.log('\nScenario 2: older sender -> newer receiver (zero-fill)');
scenario2();
console.log('\nScenario 3: same-version sanity (v2 -> v2)');
scenario3();
console.log('\nScenario 4: newer ext oneof variant -> older receiver');
scenario4();
console.log('\nScenario 5: older base oneof variant -> newer receiver');
scenario5();
console.log('\nScenario 6: multi-oneof (ext only in 2nd union)');
scenario6();
console.log('\nScenario 7: corrupted extension bytes invalidate CRC');
scenario7();
console.log('\nScenario 8: truncated payload rejected');
scenario8();
console.log('\nScenario 9: length-less profile guard (IPC)');
scenario9();
console.log('\nScenario 10: variable base + trailing extension (both directions)');
scenario10();

console.log(`\nResults: ${passCount} passed, ${failCount} failed`);
process.exit(failCount === 0 ? 0 : 1);
