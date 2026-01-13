/**
 * Extended test message data definitions.
 * Hardcoded test messages for extended message ID and payload testing.
 */

const {
  ExtendedTestExtendedIdMessage1,
  ExtendedTestExtendedIdMessage2,
  ExtendedTestExtendedIdMessage3,
  ExtendedTestExtendedIdMessage4,
  ExtendedTestExtendedIdMessage5,
  ExtendedTestExtendedIdMessage6,
  ExtendedTestExtendedIdMessage7,
  ExtendedTestExtendedIdMessage8,
  ExtendedTestExtendedIdMessage9,
  ExtendedTestExtendedIdMessage10,
  ExtendedTestLargePayloadMessage1,
  ExtendedTestLargePayloadMessage2,
} = require('../../generated/js/extended_test.structframe');

/** Message count */
const MESSAGE_COUNT = 12;

/** Message ID order array */
const MSG_ID_ORDER = [
  ExtendedTestExtendedIdMessage1._msgid,    // 0: 750
  ExtendedTestExtendedIdMessage2._msgid,    // 1: 1000
  ExtendedTestExtendedIdMessage3._msgid,    // 2: 500
  ExtendedTestExtendedIdMessage4._msgid,    // 3: 2048
  ExtendedTestExtendedIdMessage5._msgid,    // 4: 300
  ExtendedTestExtendedIdMessage6._msgid,    // 5: 1500
  ExtendedTestExtendedIdMessage7._msgid,    // 6: 999
  ExtendedTestExtendedIdMessage8._msgid,    // 7: 1234
  ExtendedTestExtendedIdMessage9._msgid,    // 8: 4000
  ExtendedTestExtendedIdMessage10._msgid,   // 9: 256
  ExtendedTestLargePayloadMessage1._msgid,  // 10: 800
  ExtendedTestLargePayloadMessage2._msgid,  // 11: 801
];

/** Create message instances */
function getMessageExt1() {
  return new ExtendedTestExtendedIdMessage1({
    sequence_number: 12345678,
    label: 'Test Label Extended 1',
    value: 3.14159,
    enabled: true,
  });
}

function getMessageExt2() {
  return new ExtendedTestExtendedIdMessage2({
    sensor_id: -42,
    reading: 2.718281828,
    status_code: 50000,
    description_length: 'Extended ID test message 2'.length,
    description_data: 'Extended ID test message 2',
  });
}

function getMessageExt3() {
  return new ExtendedTestExtendedIdMessage3({
    timestamp: 1704067200000000n,
    temperature: -40,
    humidity: 85,
    location: 'Sensor Room A',
  });
}

function getMessageExt4() {
  return new ExtendedTestExtendedIdMessage4({
    event_id: 999999,
    event_type: 42,
    event_time: 1704067200000n,
    event_data_length: 'Event payload with extended message ID'.length,
    event_data_data: 'Event payload with extended message ID',
  });
}

function getMessageExt5() {
  return new ExtendedTestExtendedIdMessage5({
    x_position: 100.5,
    y_position: -200.25,
    z_position: 50.125,
    frame_number: 1000000,
  });
}

function getMessageExt6() {
  return new ExtendedTestExtendedIdMessage6({
    command_id: -12345,
    parameter1: 1000,
    parameter2: 2000,
    acknowledged: false,
    command_name: 'CALIBRATE_SENSOR',
  });
}

function getMessageExt7() {
  return new ExtendedTestExtendedIdMessage7({
    counter: 4294967295,
    average: 123.456789,
    minimum: -999.99,
    maximum: 999.99,
  });
}

function getMessageExt8() {
  return new ExtendedTestExtendedIdMessage8({
    level: 255,
    offset: -32768,
    duration: 86400000,
    tag: 'TEST123',
  });
}

function getMessageExt9() {
  return new ExtendedTestExtendedIdMessage9({
    big_number: -9223372036854775807n,
    big_unsigned: 18446744073709551615n,
    precision_value: 1.7976931348623157e+308,
  });
}

function getMessageExt10() {
  return new ExtendedTestExtendedIdMessage10({
    small_value: 256,
    short_text: 'Boundary Test',
    flag: true,
  });
}

function getMessageLarge1() {
  const sensorReadings = [];
  for (let i = 0; i < 64; i++) {
    sensorReadings.push(i + 1);
  }
  return new ExtendedTestLargePayloadMessage1({
    sensor_readings: sensorReadings,
    reading_count: 64,
    timestamp: 1704067200000000n,
    device_name: 'Large Sensor Array Device',
  });
}

function getMessageLarge2() {
  const largeData = [];
  for (let i = 0; i < 256; i++) {
    largeData.push(i);
  }
  for (let i = 256; i < 280; i++) {
    largeData.push(i - 256);
  }
  return new ExtendedTestLargePayloadMessage2({
    large_data: largeData,
  });
}

/** Message getters by msg_id */
function getMessage(msgId) {
  switch (msgId) {
    case ExtendedTestExtendedIdMessage1._msgid: return getMessageExt1();
    case ExtendedTestExtendedIdMessage2._msgid: return getMessageExt2();
    case ExtendedTestExtendedIdMessage3._msgid: return getMessageExt3();
    case ExtendedTestExtendedIdMessage4._msgid: return getMessageExt4();
    case ExtendedTestExtendedIdMessage5._msgid: return getMessageExt5();
    case ExtendedTestExtendedIdMessage6._msgid: return getMessageExt6();
    case ExtendedTestExtendedIdMessage7._msgid: return getMessageExt7();
    case ExtendedTestExtendedIdMessage8._msgid: return getMessageExt8();
    case ExtendedTestExtendedIdMessage9._msgid: return getMessageExt9();
    case ExtendedTestExtendedIdMessage10._msgid: return getMessageExt10();
    case ExtendedTestLargePayloadMessage1._msgid: return getMessageLarge1();
    case ExtendedTestLargePayloadMessage2._msgid: return getMessageLarge2();
    default: return null;
  }
}

/** Message class lookup by msg_id */
function getMessageClass(msgId) {
  switch (msgId) {
    case ExtendedTestExtendedIdMessage1._msgid: return ExtendedTestExtendedIdMessage1;
    case ExtendedTestExtendedIdMessage2._msgid: return ExtendedTestExtendedIdMessage2;
    case ExtendedTestExtendedIdMessage3._msgid: return ExtendedTestExtendedIdMessage3;
    case ExtendedTestExtendedIdMessage4._msgid: return ExtendedTestExtendedIdMessage4;
    case ExtendedTestExtendedIdMessage5._msgid: return ExtendedTestExtendedIdMessage5;
    case ExtendedTestExtendedIdMessage6._msgid: return ExtendedTestExtendedIdMessage6;
    case ExtendedTestExtendedIdMessage7._msgid: return ExtendedTestExtendedIdMessage7;
    case ExtendedTestExtendedIdMessage8._msgid: return ExtendedTestExtendedIdMessage8;
    case ExtendedTestExtendedIdMessage9._msgid: return ExtendedTestExtendedIdMessage9;
    case ExtendedTestExtendedIdMessage10._msgid: return ExtendedTestExtendedIdMessage10;
    case ExtendedTestLargePayloadMessage1._msgid: return ExtendedTestLargePayloadMessage1;
    case ExtendedTestLargePayloadMessage2._msgid: return ExtendedTestLargePayloadMessage2;
    default: return null;
  }
}

/** Reset state - not needed for extended tests (stateless) */
function resetState() {
  // No state to reset - each message type has exactly one instance
}

/** Encode message by index */
function encodeMessage(writer, index) {
  const msgId = MSG_ID_ORDER[index];
  const msg = getMessage(msgId);
  if (!msg) return 0;
  return writer.write(msg);
}

/** Validate decoded message using equals() method */
function validateMessage(msgId, data, _index) {
  const expected = getMessage(msgId);
  const MsgClass = getMessageClass(msgId);
  if (!expected || !MsgClass) return false;

  if (data.length !== MsgClass._size) return false;

  const decoded = new MsgClass();
  data.copy(decoded._buffer);
  return decoded.equals(expected);
}

/** Check if format is supported - extended tests only use bulk and network */
function supportsFormat(format) {
  return format === 'profile_bulk' || format === 'profile_network';
}

/** Extended test configuration */
const extTestConfig = {
  messageCount: MESSAGE_COUNT,
  bufferSize: 8192,  // Larger for extended payloads
  formatsHelp: 'profile_bulk, profile_network',
  testName: 'JavaScript Extended',
  getMsgIdOrder: () => MSG_ID_ORDER,
  encodeMessage,
  validateMessage,
  resetState,
  getMessageLength: (_msgId) => undefined,
  supportsFormat,
};

module.exports = { extTestConfig };
