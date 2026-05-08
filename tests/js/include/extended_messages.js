/**
 * Extended test message definitions (JavaScript).
 * Three representative extended IDs (boundary/mid/high) + two large-payload
 * messages + five variable-array fill levels = 10 total.
 */

const {
  ExtendedIdMessage2,
  ExtendedIdMessage9,
  ExtendedIdMessage10,
  LargePayloadMessage1,
  LargePayloadMessage2,
  ExtendedVariableSingleArray,
} = require('../../generated/js/extended-test.structframe');

const MESSAGE_COUNT = 10;

// ============================================================================
// Helper functions
// ============================================================================

function createExtId10() {
  return new ExtendedIdMessage10({ smallValue: 256, shortText: 'Boundary Test', flag: true });
}

function createExtId2() {
  return new ExtendedIdMessage2({
    sensorId: -42,
    reading: 2.718281828,
    statusCode: 50000,
    descriptionLength: 'Extended ID test message 2'.length,
    descriptionData: 'Extended ID test message 2',
  });
}

function createExtId9() {
  return new ExtendedIdMessage9({
    bigNumber: -9223372036854775807n,
    bigUnsigned: 18446744073709551615n,
    precisionValue: 1.7976931348623157e+308,
  });
}

function createLarge1() {
  return new LargePayloadMessage1({
    sensorReadings: Array.from({ length: 64 }, (_, i) => i + 1),
    readingCount: 64,
    timestamp: 1704067200000000n,
    deviceName: 'Large Sensor Array Device',
  });
}

function createLarge2() {
  const largeData = [];
  for (let i = 0; i < 256; i++) largeData.push(i);
  for (let i = 256; i < 280; i++) largeData.push(i - 256);
  return new LargePayloadMessage2({ largeData });
}

function extVar(ts, count, data, crc) {
  return new ExtendedVariableSingleArray({
    timestamp: ts,
    telemetryDataCount: count,
    telemetryDataData: data,
    crc,
  });
}

// ============================================================================
// getMessage(index) - order: ExtId10, ExtId2, ExtId9, Large1, Large2, Var×5
// ============================================================================

function getMessage(index) {
  switch (index) {
    case 0: return createExtId10();
    case 1: return createExtId2();
    case 2: return createExtId9();
    case 3: return createLarge1();
    case 4: return createLarge2();
    case 5: return extVar(0x0000000000000001n, 0,   [],                                            0x00000001);
    case 6: return extVar(0x0000000000000002n, 1,   [42],                                          0x00000002);
    case 7: return extVar(0x0000000000000003n, 83,  Array.from({ length: 83  }, (_, i) => i),      0x00000003);
    case 8: return extVar(0x0000000000000004n, 249, Array.from({ length: 249 }, (_, i) => i % 256), 0x00000004);
    default: return extVar(0x0000000000000005n, 250, Array.from({ length: 250 }, (_, i) => i % 256), 0x00000005);
  }
}

// ============================================================================
// checkMessage(index, info) - validates decoded message
// ============================================================================

function checkMessage(index, info) {
  const expected = getMessage(index);
  const msgClass = expected.constructor;
  if (info.msgId !== msgClass._msgid) return false;
  const decoded = msgClass.deserialize(info);
  return decoded.equals(expected);
}

module.exports = { MESSAGE_COUNT, getMessage, checkMessage };
