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

  console.log(`\nSummary: ${passed} passed, ${failed} failed`);
  return failed > 0 ? 1 : 0;
}

process.exit(main());
