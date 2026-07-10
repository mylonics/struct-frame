/**
 * Test for envelope SDK interface: msgid-discriminator (CommandEnvelope) and
 * field_order-discriminator (RawDataEnvelope) round-trips.
 *
 * Mirrors tests/rust/src/main.rs::run_envelope_sdk_tests().
 */

const {
  BufferWriter,
  AccumulatingReader,
  ProfileStandardConfig,
  ProfileBulkConfig,
} = require('../generated/js/frame-profiles');

const {
  CommandEnvelope,
  ADCCommand,
  RawDataEnvelope,
  RawSamplePayload,
  RawDataEnvelopePayloadField,
  getMessageInfo,
} = require('../generated/js/envelope-test.structframe');

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
  console.log('=== JavaScript EnvelopeSdk tests ===');

  // --- CommandEnvelope with msgid discriminator ---
  const adc = new ADCCommand({ channel: 2, sampleRate: 1000, enable: true });
  const env = CommandEnvelope.wrap(adc, 42, 5, true);

  expect(env.commandDiscriminator === ADCCommand._msgid,
    'CommandEnvelope: discriminator == ADCCommand._msgid');

  const writer = new BufferWriter(ProfileStandardConfig, 2048);
  const written = writer.write(env);
  expect(written > 0, 'CommandEnvelope: write returned > 0');

  const reader = new AccumulatingReader(ProfileStandardConfig, getMessageInfo, 4096);
  reader.addData(writer.data().subarray(0, written));
  const frame = reader.next();
  expect(frame.valid, 'CommandEnvelope: frame valid');
  if (frame.valid) {
    expect(frame.msgId === CommandEnvelope._msgid, 'CommandEnvelope: msgId matches');
    const decoded = CommandEnvelope.deserialize(frame, 'fixed');
    expect(decoded !== null, 'CommandEnvelope: deserialize succeeded');
    expect(decoded.sequenceNumber === 42, 'CommandEnvelope: sequenceNumber round-trips');
    expect(decoded.priority === 5, 'CommandEnvelope: priority round-trips');
    expect(decoded.runImmediately, 'CommandEnvelope: runImmediately round-trips');
    expect(decoded.commandDiscriminator === ADCCommand._msgid,
      'CommandEnvelope: discriminator round-trips');
    const adc2 = ADCCommand.deserialize(decoded.commandData);
    expect(adc2.channel === 2, 'CommandEnvelope: adc.channel round-trips');
    expect(adc2.sampleRate === 1000, 'CommandEnvelope: adc.sampleRate round-trips');
    expect(adc2.enable, 'CommandEnvelope: adc.enable round-trips');
  }

  // --- RawDataEnvelope with field_order discriminator ---
  const sample = new RawSamplePayload({ channel: 7, value: 2.718, flags: 0xBE });
  const rawEnv = RawDataEnvelope.wrap(sample, 3, 999000);

  // field_order discriminator: sample is 1st field -> discriminator == 1
  expect(rawEnv.payloadDiscriminator === RawDataEnvelopePayloadField.Sample,
    'RawDataEnvelope: field_order discriminator == Sample (1) for first variant');

  const rawWriter = new BufferWriter(ProfileBulkConfig, 2048);
  const rawWritten = rawWriter.write(rawEnv);
  expect(rawWritten > 0, 'RawDataEnvelope: write returned > 0');

  const rawReader = new AccumulatingReader(ProfileBulkConfig, getMessageInfo, 4096);
  rawReader.addData(rawWriter.data().subarray(0, rawWritten));
  const rawFrame = rawReader.next();
  expect(rawFrame.valid, 'RawDataEnvelope: frame valid');
  if (rawFrame.valid) {
    const rawDecoded = RawDataEnvelope.deserialize(rawFrame, 'fixed');
    expect(rawDecoded !== null, 'RawDataEnvelope: deserialize succeeded');
    expect(rawDecoded.priority === 3, 'RawDataEnvelope: priority round-trips');
    expect(rawDecoded.timestampUs === 999000, 'RawDataEnvelope: timestampUs round-trips');
    expect(rawDecoded.payloadDiscriminator === RawDataEnvelopePayloadField.Sample,
      'RawDataEnvelope: discriminator round-trips == Sample');
    const s2 = new RawSamplePayload(rawDecoded.payloadData);
    expect(s2.channel === 7, 'RawDataEnvelope: sample.channel round-trips');
    expect(Math.abs(s2.value - 2.718) < 1e-4, 'RawDataEnvelope: sample.value round-trips');
    expect(s2.flags === 0xBE, 'RawDataEnvelope: sample.flags round-trips');
  }

  console.log(`\nSummary: ${passed} passed, ${failed} failed`);
  return failed > 0 ? 1 : 0;
}

process.exit(main());
