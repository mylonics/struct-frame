/**
 * Extended test message data definitions.
 * Hardcoded test messages for extended message ID and payload testing.
 *
 * Structure:
 * - One instance per message type (ExtendedId1-10, LargePayload1-2)
 * - A msg_id order array (length 12) defines the encode/decode sequence
 * - Encoding uses msg_id array to select which message to write
 * - Decoding uses decoded msg_id to find the right message for comparison
 */

import { TestConfig } from './test_codec';
import {
  extended_test_ExtendedIdMessage1,
  extended_test_ExtendedIdMessage2,
  extended_test_ExtendedIdMessage3,
  extended_test_ExtendedIdMessage4,
  extended_test_ExtendedIdMessage5,
  extended_test_ExtendedIdMessage6,
  extended_test_ExtendedIdMessage7,
  extended_test_ExtendedIdMessage8,
  extended_test_ExtendedIdMessage9,
  extended_test_ExtendedIdMessage10,
  extended_test_LargePayloadMessage1,
  extended_test_LargePayloadMessage2,
} from '../../generated/ts/extended_test.sf';

/** Message count */
const MESSAGE_COUNT = 12;

/** Message ID order array */
const MSG_ID_ORDER: number[] = [
  extended_test_ExtendedIdMessage1._msgid!,    // 0: 750
  extended_test_ExtendedIdMessage2._msgid!,    // 1: 1000
  extended_test_ExtendedIdMessage3._msgid!,    // 2: 500
  extended_test_ExtendedIdMessage4._msgid!,    // 3: 2048
  extended_test_ExtendedIdMessage5._msgid!,    // 4: 300
  extended_test_ExtendedIdMessage6._msgid!,    // 5: 1500
  extended_test_ExtendedIdMessage7._msgid!,    // 6: 999
  extended_test_ExtendedIdMessage8._msgid!,    // 7: 1234
  extended_test_ExtendedIdMessage9._msgid!,    // 8: 4000
  extended_test_ExtendedIdMessage10._msgid!,   // 9: 256
  extended_test_LargePayloadMessage1._msgid!,  // 10: 800
  extended_test_LargePayloadMessage2._msgid!,  // 11: 801
];

/** Create message instances */
function getMessageExt1(): extended_test_ExtendedIdMessage1 {
  return new extended_test_ExtendedIdMessage1({
    sequence_number: 12345678,
    label: 'Test Label Extended 1',
    value: 3.14159,
    enabled: true,
  });
}

function getMessageExt2(): extended_test_ExtendedIdMessage2 {
  return new extended_test_ExtendedIdMessage2({
    sensor_id: -42,
    reading: 2.718281828,
    status_code: 50000,
    description_length: 'Extended ID test message 2'.length,
    description_data: 'Extended ID test message 2',
  });
}

function getMessageExt3(): extended_test_ExtendedIdMessage3 {
  return new extended_test_ExtendedIdMessage3({
    timestamp: 1704067200000000n,
    temperature: -40,
    humidity: 85,
    location: 'Sensor Room A',
  });
}

function getMessageExt4(): extended_test_ExtendedIdMessage4 {
  return new extended_test_ExtendedIdMessage4({
    event_id: 999999,
    event_type: 42,
    event_time: 1704067200000n,
    event_data_length: 'Event payload with extended message ID'.length,
    event_data_data: 'Event payload with extended message ID',
  });
}

function getMessageExt5(): extended_test_ExtendedIdMessage5 {
  return new extended_test_ExtendedIdMessage5({
    x_position: 100.5,
    y_position: -200.25,
    z_position: 50.125,
    frame_number: 1000000,
  });
}

function getMessageExt6(): extended_test_ExtendedIdMessage6 {
  return new extended_test_ExtendedIdMessage6({
    command_id: -12345,
    parameter1: 1000,
    parameter2: 2000,
    acknowledged: false,
    command_name: 'CALIBRATE_SENSOR',
  });
}

function getMessageExt7(): extended_test_ExtendedIdMessage7 {
  return new extended_test_ExtendedIdMessage7({
    counter: 4294967295,
    average: 123.456789,
    minimum: -999.99,
    maximum: 999.99,
  });
}

function getMessageExt8(): extended_test_ExtendedIdMessage8 {
  return new extended_test_ExtendedIdMessage8({
    level: 255,
    offset: -32768,
    duration: 86400000,
    tag: 'TEST123',
  });
}

function getMessageExt9(): extended_test_ExtendedIdMessage9 {
  return new extended_test_ExtendedIdMessage9({
    big_number: -9223372036854775807n,
    big_unsigned: 18446744073709551615n,
    precision_value: 1.7976931348623157e+308,
  });
}

function getMessageExt10(): extended_test_ExtendedIdMessage10 {
  return new extended_test_ExtendedIdMessage10({
    small_value: 256,
    short_text: 'Boundary Test',
    flag: true,
  });
}

function getMessageLarge1(): extended_test_LargePayloadMessage1 {
  const sensorReadings: number[] = [];
  for (let i = 0; i < 64; i++) {
    sensorReadings.push(i + 1);
  }
  return new extended_test_LargePayloadMessage1({
    sensor_readings: sensorReadings,
    reading_count: 64,
    timestamp: 1704067200000000n,
    device_name: 'Large Sensor Array Device',
  });
}

function getMessageLarge2(): extended_test_LargePayloadMessage2 {
  const largeData: number[] = [];
  for (let i = 0; i < 256; i++) {
    largeData.push(i);
  }
  for (let i = 256; i < 280; i++) {
    largeData.push(i - 256);
  }
  return new extended_test_LargePayloadMessage2({
    large_data: largeData,
  });
}

/** Message getters by msg_id */
function getMessage(msgId: number): any {
  switch (msgId) {
    case extended_test_ExtendedIdMessage1._msgid: return getMessageExt1();
    case extended_test_ExtendedIdMessage2._msgid: return getMessageExt2();
    case extended_test_ExtendedIdMessage3._msgid: return getMessageExt3();
    case extended_test_ExtendedIdMessage4._msgid: return getMessageExt4();
    case extended_test_ExtendedIdMessage5._msgid: return getMessageExt5();
    case extended_test_ExtendedIdMessage6._msgid: return getMessageExt6();
    case extended_test_ExtendedIdMessage7._msgid: return getMessageExt7();
    case extended_test_ExtendedIdMessage8._msgid: return getMessageExt8();
    case extended_test_ExtendedIdMessage9._msgid: return getMessageExt9();
    case extended_test_ExtendedIdMessage10._msgid: return getMessageExt10();
    case extended_test_LargePayloadMessage1._msgid: return getMessageLarge1();
    case extended_test_LargePayloadMessage2._msgid: return getMessageLarge2();
    default: return null;
  }
}

/** Message class lookup by msg_id */
function getMessageClass(msgId: number): any {
  switch (msgId) {
    case extended_test_ExtendedIdMessage1._msgid: return extended_test_ExtendedIdMessage1;
    case extended_test_ExtendedIdMessage2._msgid: return extended_test_ExtendedIdMessage2;
    case extended_test_ExtendedIdMessage3._msgid: return extended_test_ExtendedIdMessage3;
    case extended_test_ExtendedIdMessage4._msgid: return extended_test_ExtendedIdMessage4;
    case extended_test_ExtendedIdMessage5._msgid: return extended_test_ExtendedIdMessage5;
    case extended_test_ExtendedIdMessage6._msgid: return extended_test_ExtendedIdMessage6;
    case extended_test_ExtendedIdMessage7._msgid: return extended_test_ExtendedIdMessage7;
    case extended_test_ExtendedIdMessage8._msgid: return extended_test_ExtendedIdMessage8;
    case extended_test_ExtendedIdMessage9._msgid: return extended_test_ExtendedIdMessage9;
    case extended_test_ExtendedIdMessage10._msgid: return extended_test_ExtendedIdMessage10;
    case extended_test_LargePayloadMessage1._msgid: return extended_test_LargePayloadMessage1;
    case extended_test_LargePayloadMessage2._msgid: return extended_test_LargePayloadMessage2;
    default: return null;
  }
}

/** Reset state - not needed for extended tests (stateless) */
function resetState(): void {
  // No state to reset - each message type has exactly one instance
}

/** Encode message by index */
function encodeMessage(writer: any, index: number): number {
  const msgId = MSG_ID_ORDER[index];
  const msg = getMessage(msgId);
  if (!msg) return 0;
  return writer.write(msg);
}

/** Validate decoded message using equals() method */
function validateMessage(msgId: number, data: Buffer, _index: number): boolean {
  const expected = getMessage(msgId);
  const MsgClass = getMessageClass(msgId);
  if (!expected || !MsgClass) return false;

  if (data.length !== MsgClass._size) return false;

  const decoded = new MsgClass();
  data.copy(decoded._buffer);
  return decoded.equals(expected);
}

/** Check if format is supported - extended tests only use bulk and network */
function supportsFormat(format: string): boolean {
  return format === 'profile_bulk' || format === 'profile_network';
}

/** Extended test configuration */
export const extTestConfig: TestConfig = {
  messageCount: MESSAGE_COUNT,
  bufferSize: 8192,  // Larger for extended payloads
  formatsHelp: 'profile_bulk, profile_network',
  testName: 'TypeScript Extended',
  getMsgIdOrder: () => MSG_ID_ORDER,
  encodeMessage,
  validateMessage,
  resetState,
  getMessageLength: (_msgId: number) => undefined,
  supportsFormat,
};
