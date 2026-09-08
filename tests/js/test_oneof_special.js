/**
 * Test for oneof special cases: discriminator=none and multi-oneof messages.
 *
 * Mirrors tests/rust/src/main.rs::run_oneof_special_tests(). JavaScript's
 * buffer-backed messages expose the raw union byte range via a `<field>Data`
 * getter/setter regardless of discriminator, so discriminator=none payloads
 * are recovered by deserializing that byte range directly (the app must
 * already know which variant is active -- there is no auto-decode without a
 * discriminator).
 */

const {
  NoneDiscriminatorMessage,
  MultiOneofMessage,
  BasicTypesMessage,
  VariableOneofMessage,
  VarEnvPayloadA,
  VarEnvPayloadB,
} = require('../generated/js/serialization-test.structframe');

let passed = 0;
let failed = 0;

function expect(condition, name) {
  if (condition) {
    console.log(`  PASS  ${name}`);
    passed++;
  } else {
    console.log(`  FAIL  ${name}`);
    failed++;
  }
}

function main() {
  console.log('=== JavaScript oneof special tests ===');

  // --- NoneDiscriminatorMessage: no discriminator field, data bytes preserved ---
  const basic = new BasicTypesMessage({ smallInt: -42, mediumUint: 5000 });
  const msg1 = new NoneDiscriminatorMessage({ header: 0xAB, dataData: basic.serialize() });

  const raw1 = msg1.serialize();
  const dec1 = NoneDiscriminatorMessage.deserialize(raw1, 'fixed');
  expect(dec1.header === 0xAB, 'NoneDiscriminator: header round-trips');
  // Without a discriminator the receiver must know which variant to use.
  const basic1 = BasicTypesMessage.deserialize(dec1.dataData);
  expect(basic1.smallInt === -42, 'NoneDiscriminator: basic.smallInt round-trips');
  expect(basic1.mediumUint === 5000, 'NoneDiscriminator: basic.mediumUint round-trips');

  // --- MultiOneofMessage: msgid-discriminated first_payload round-trips normally ---
  const basic2 = new BasicTypesMessage({ smallInt: 99 });
  const msg2 = new MultiOneofMessage({
    selector: 7,
    firstPayloadDiscriminator: BasicTypesMessage._msgid,
    firstPayloadData: basic2.serialize(),
  });

  const raw2 = msg2.serialize();
  const dec2 = MultiOneofMessage.deserialize(raw2, 'fixed');
  expect(dec2.selector === 7, 'MultiOneof: selector round-trips');
  expect(dec2.firstPayloadDiscriminator === BasicTypesMessage._msgid,
    'MultiOneof: firstPayload discriminator is BasicTypesMessage msgid');
  const b2 = BasicTypesMessage.deserialize(dec2.firstPayloadData);
  expect(b2.smallInt === 99, 'MultiOneof: basic.smallInt round-trips');

  // --- VariableOneofMessage: wire vs fixed layout at the same length ---
  // A variable oneof writes a uint16 length prefix ahead of the union payload
  // that the fixed layout does not have, so the largest variant produces a wire
  // frame exactly _size bytes long -- the same length as the fixed layout that
  // a minimal profile sends from msg._buffer. The two layouts are only
  // distinguishable by the framing profile, so mode="auto" resolves the
  // ambiguous length as the fixed (minimal profile) layout and a max-length
  // wire frame must be decoded explicitly with mode="wire".
  const large = new VarEnvPayloadB({ flags: 0x0A0B0C0D, ratio: 1.5 });
  const largeBytes = large.serialize();
  const msg3 = new VariableOneofMessage({
    header: 0x42,
    dataDiscriminator: 2,  // large_payload
    dataData: largeBytes,
  });

  const raw3 = msg3.serialize();
  expect(raw3.length === VariableOneofMessage._size,
    'VariableOneof: large variant frame is exactly _size bytes');
  const dec3 = VariableOneofMessage.deserialize(raw3, "wire");
  expect(dec3.header === 0x42, 'VariableOneof: header round-trips (explicit wire decode)');
  expect(dec3.dataDiscriminator === 2, 'VariableOneof: discriminator round-trips');
  expect(Buffer.from(dec3.dataData).equals(largeBytes),
    'VariableOneof: largePayload bytes round-trip at the ambiguous length');

  // A shorter wire frame is unambiguous and decodes through the auto path.
  const small = new VarEnvPayloadA({ code: 0x12, value: 0x3456 });
  const msg4 = new VariableOneofMessage({
    header: 0x43,
    dataDiscriminator: 1,  // small_payload
    dataData: small.serialize(),
  });
  const raw4 = msg4.serialize();
  expect(raw4.length < VariableOneofMessage._size,
    'VariableOneof: small variant frame is shorter than _size');
  const dec4 = VariableOneofMessage.deserialize(raw4);
  expect(dec4.header === 0x43, 'VariableOneof: header round-trips (auto)');
  expect(dec4.dataDiscriminator === 1, 'VariableOneof: discriminator round-trips (auto)');
  expect(Buffer.from(dec4.dataData.subarray(0, 3)).equals(small.serialize()),
    'VariableOneof: smallPayload bytes round-trip (auto)');

  // The fixed layout that a minimal profile (ProfileSensor/ProfileIPC) sends
  // must round-trip through the auto path at exactly _size bytes.
  const dec5 = VariableOneofMessage.deserialize(msg3._buffer);
  expect(dec5.header === 0x42, 'VariableOneof: header round-trips (fixed layout)');
  expect(Buffer.from(dec5.dataData).equals(largeBytes),
    'VariableOneof: largePayload bytes round-trip from the fixed layout');

  console.log(`\nSummary: ${passed} passed, ${failed} failed`);
  return failed > 0 ? 1 : 0;
}

process.exit(main());
