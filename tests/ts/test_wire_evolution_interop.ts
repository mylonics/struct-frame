/**
 * Cross-version wire-evolution *interop* tests for the TypeScript SDK.
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
 * Scenarios (mirrors the project's wire-evolution interop plan, 1-7):
 *   1. Newer sender -> older receiver (v2 encodes extensions, v1 decodes base)
 *   2. Older sender -> newer receiver (v1 base-only, v2 zero-fills extensions)
 *   3. Same-version sanity (v2 -> v2 with extension variant)
 *   4. Newer ext oneof variant -> older receiver degrades gracefully
 *   5. Older base oneof variant -> newer receiver decodes correctly
 *   6. Multi-oneof: base oneof unaffected while ext oneof exercises 4/5
 *   7. Corrupted extension bytes invalidate the full CRC
 *
 * Run:
 *   cd tests/ts && npx ts-node test_wire_evolution_interop.ts
 */

import {
  BaseExtensionMessage as V1BaseExtensionMessage,
  OneOfExtensionMessage as V1OneOfExtensionMessage,
  OneOfExtensionMessageCommandField as V1CommandField,
  MultiOneOfExtensionMessage as V1MultiOneOfExtensionMessage,
  getMessageInfo as v1GetMessageInfo,
} from '../generated/ts/wire-evolution-v1.structframe';

import {
  BaseExtensionMessage as V2BaseExtensionMessage,
  OneOfExtensionMessage as V2OneOfExtensionMessage,
  OneOfExtensionMessageCommandField as V2CommandField,
  MultiOneOfExtensionMessage as V2MultiOneOfExtensionMessage,
  MultiOneOfExtensionMessageBaseUnionField as V2BaseUnionField,
  MultiOneOfExtensionMessageExtUnionField as V2ExtUnionField,
  getMessageInfo as v2GetMessageInfo,
} from '../generated/ts/wire-evolution-v2.structframe';

import {
  ProfileStandardConfig,
  ProfileBulkConfig,
  ProfileNetworkConfig,
  encodeMessage,
  parseFrameWithCrc,
} from '../generated/ts/frame-profiles';

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
// Scenario 1: newer sender -> older receiver over length-bearing profiles
// ---------------------------------------------------------------------------
function scenario1(): void {
  const profiles: Array<[any, string]> = [
    [ProfileStandardConfig, 'standard'],
    [ProfileBulkConfig, 'bulk'],
    [ProfileNetworkConfig, 'network'],
  ];
  for (const [config, name] of profiles) {
    const orig = new V2BaseExtensionMessage({ header: 0xBEEF, seq: 42, crcSeed: 0xDEADC0DE });
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
function scenario2(): void {
  const orig = new V1BaseExtensionMessage({ header: 0x1234, seq: 7 });
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
function scenario3(): void {
  const orig = new V2OneOfExtensionMessage({
    deviceId: 2,
    commandDiscriminator: V2CommandField.CmdC,
  });
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
    check(d.commandDiscriminator === V2CommandField.CmdC
      && Math.abs(view.readFloatLE(0) - 3.14) < 0.001,
      '[S3] v2 round-trips the extension variant');
  }
}

// ---------------------------------------------------------------------------
// Scenario 4: newer ext oneof variant -> older receiver degrades gracefully
// ---------------------------------------------------------------------------
function scenario4(): void {
  const orig = new V2OneOfExtensionMessage({
    deviceId: 9,
    commandDiscriminator: V2CommandField.CmdD,
  });
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
function scenario5(): void {
  const orig = new V1OneOfExtensionMessage({
    deviceId: 5,
    commandDiscriminator: V1CommandField.CmdB,
  });
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
    check(d.commandDiscriminator === V2CommandField.CmdB
      && view.readInt16LE(0) === -1234,
      '[S5] v2 decodes the older base oneof variant correctly');
  }
}

// ---------------------------------------------------------------------------
// Scenario 6: multi-oneof, ext only in the second union
// ---------------------------------------------------------------------------
function scenario6(): void {
  const orig = new V2MultiOneOfExtensionMessage({
    priority: 3,
    baseUnionDiscriminator: V2BaseUnionField.FirstA,
    extUnionDiscriminator: V2ExtUnionField.SecondExt,
  });
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
    check(d.priority === 3
      && Number(d.baseUnionDiscriminator) === 1
      && baseView.readUInt32LE(0) === 100,
      '[S6] v1 decodes the FIRST (base) oneof unaffected by ext in the second');
  }
}

// ---------------------------------------------------------------------------
// Scenario 7: corrupted extension bytes invalidate the full CRC
// ---------------------------------------------------------------------------
function scenario7(): void {
  const orig = new V2BaseExtensionMessage({ header: 0xBEEF, seq: 42, crcSeed: 0xDEADC0DE });
  const frame = encodeMessage(ProfileStandardConfig, orig);

  const corrupted = new Uint8Array(frame);
  const headerSize = 2 + 4; // start bytes(2) + length(2) + msgid(2)
  const extOffset = headerSize + V2BaseExtensionMessage._baseSize;
  corrupted[extOffset] ^= 0xFF;

  const info = parseFrameWithCrc(ProfileStandardConfig, corrupted, v1GetMessageInfo);
  check(!info.valid, '[S7] corrupted extension byte invalidates full CRC');
}

console.log('=== TypeScript Cross-Version Wire-Evolution Interop Tests ===\n');

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

console.log(`\nResults: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
