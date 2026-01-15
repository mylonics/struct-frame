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
import { FrameMsgInfo } from '../../generated/ts/frame-base';
import {
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
  ExtendedTestExtendedVariableSingleArray,
  get_message_info,
} from '../../generated/ts/extended_test.structframe';

/** Message count */
const MESSAGE_COUNT = 17;

/** Message ID order array */
const MSG_ID_ORDER: number[] = [
  ExtendedTestExtendedIdMessage1._msgid!,            // 0: 750
  ExtendedTestExtendedIdMessage2._msgid!,            // 1: 1000
  ExtendedTestExtendedIdMessage3._msgid!,            // 2: 500
  ExtendedTestExtendedIdMessage4._msgid!,            // 3: 2048
  ExtendedTestExtendedIdMessage5._msgid!,            // 4: 300
  ExtendedTestExtendedIdMessage6._msgid!,            // 5: 1500
  ExtendedTestExtendedIdMessage7._msgid!,            // 6: 999
  ExtendedTestExtendedIdMessage8._msgid!,            // 7: 1234
  ExtendedTestExtendedIdMessage9._msgid!,            // 8: 4000
  ExtendedTestExtendedIdMessage10._msgid!,           // 9: 256
  ExtendedTestLargePayloadMessage1._msgid!,          // 10: 800
  ExtendedTestLargePayloadMessage2._msgid!,          // 11: 801
  ExtendedTestExtendedVariableSingleArray._msgid!,   // 12: empty
  ExtendedTestExtendedVariableSingleArray._msgid!,   // 13: single
  ExtendedTestExtendedVariableSingleArray._msgid!,   // 14: 1/3 filled
  ExtendedTestExtendedVariableSingleArray._msgid!,   // 15: one empty
  ExtendedTestExtendedVariableSingleArray._msgid!,   // 16: full
];

/** Create message instances */
function getMessageExt1(): ExtendedTestExtendedIdMessage1 {
  return new ExtendedTestExtendedIdMessage1({
    sequence_number: 12345678,
    label: 'Test Label Extended 1',
    value: 3.14159,
    enabled: true,
  });
}

function getMessageExt2(): ExtendedTestExtendedIdMessage2 {
  return new ExtendedTestExtendedIdMessage2({
    sensor_id: -42,
    reading: 2.718281828,
    status_code: 50000,
    description_length: 'Extended ID test message 2'.length,
    description_data: 'Extended ID test message 2',
  });
}

function getMessageExt3(): ExtendedTestExtendedIdMessage3 {
  return new ExtendedTestExtendedIdMessage3({
    timestamp: 1704067200000000n,
    temperature: -40,
    humidity: 85,
    location: 'Sensor Room A',
  });
}

function getMessageExt4(): ExtendedTestExtendedIdMessage4 {
  return new ExtendedTestExtendedIdMessage4({
    event_id: 999999,
    event_type: 42,
    event_time: 1704067200000n,
    event_data_length: 'Event payload with extended message ID'.length,
    event_data_data: 'Event payload with extended message ID',
  });
}

function getMessageExt5(): ExtendedTestExtendedIdMessage5 {
  return new ExtendedTestExtendedIdMessage5({
    x_position: 100.5,
    y_position: -200.25,
    z_position: 50.125,
    frame_number: 1000000,
  });
}

function getMessageExt6(): ExtendedTestExtendedIdMessage6 {
  return new ExtendedTestExtendedIdMessage6({
    command_id: -12345,
    parameter1: 1000,
    parameter2: 2000,
    acknowledged: false,
    command_name: 'CALIBRATE_SENSOR',
  });
}

function getMessageExt7(): ExtendedTestExtendedIdMessage7 {
  return new ExtendedTestExtendedIdMessage7({
    counter: 4294967295,
    average: 123.456789,
    minimum: -999.99,
    maximum: 999.99,
  });
}

function getMessageExt8(): ExtendedTestExtendedIdMessage8 {
  return new ExtendedTestExtendedIdMessage8({
    level: 255,
    offset: -32768,
    duration: 86400000,
    tag: 'TEST123',
  });
}

function getMessageExt9(): ExtendedTestExtendedIdMessage9 {
  return new ExtendedTestExtendedIdMessage9({
    big_number: -9223372036854775807n,
    big_unsigned: 18446744073709551615n,
    precision_value: 1.7976931348623157e+308,
  });
}

function getMessageExt10(): ExtendedTestExtendedIdMessage10 {
  return new ExtendedTestExtendedIdMessage10({
    small_value: 256,
    short_text: 'Boundary Test',
    flag: true,
  });
}

function getMessageLarge1(): ExtendedTestLargePayloadMessage1 {
  const sensorReadings: number[] = [];
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

function getMessageLarge2(): ExtendedTestLargePayloadMessage2 {
  const largeData: number[] = [];
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

/** Get ExtendedVariableSingleArray messages (5 with different fill levels) */
function getExtVarSingleMessages(): ExtendedTestExtendedVariableSingleArray[] {
  return [
    // Empty payload (0 elements)
    new ExtendedTestExtendedVariableSingleArray({
      timestamp: 0x0000000000000001n,
      telemetry_data_count: 0,
      telemetry_data_data: [],
      crc: 0x00000001,
    }),
    // Single element
    new ExtendedTestExtendedVariableSingleArray({
      timestamp: 0x0000000000000002n,
      telemetry_data_count: 1,
      telemetry_data_data: [42],
      crc: 0x00000002,
    }),
    // One-third filled (83 elements for max_size=250)
    new ExtendedTestExtendedVariableSingleArray({
      timestamp: 0x0000000000000003n,
      telemetry_data_count: 83,
      telemetry_data_data: Array.from({ length: 83 }, (_, i) => i),
      crc: 0x00000003,
    }),
    // One position empty (249 elements)
    new ExtendedTestExtendedVariableSingleArray({
      timestamp: 0x0000000000000004n,
      telemetry_data_count: 249,
      telemetry_data_data: Array.from({ length: 249 }, (_, i) => i % 256),
      crc: 0x00000004,
    }),
    // Full (250 elements)
    new ExtendedTestExtendedVariableSingleArray({
      timestamp: 0x0000000000000005n,
      telemetry_data_count: 250,
      telemetry_data_data: Array.from({ length: 250 }, (_, i) => i % 256),
      crc: 0x00000005,
    }),
  ];
}

/** Variable message indices for encoding/validation */
let extVarSingleEncodeIdx = 0;
let extVarSingleValidateIdx = 0;
const extVarSingleMsgs = getExtVarSingleMessages();

/** Message getters by msg_id - for fixed messages */
function getMessage(msgId: number): any {
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
function getMessageClass(msgId: number): any {
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
    case ExtendedTestExtendedVariableSingleArray._msgid: return ExtendedTestExtendedVariableSingleArray;
    default: return null;
  }
}

/** Reset state - resets variable message indices */
function resetState(): void {
  extVarSingleEncodeIdx = 0;
  extVarSingleValidateIdx = 0;
}

/** Encode message by index */
function encodeMessage(writer: any, index: number): number {
  const msgId = MSG_ID_ORDER[index];

  // Handle variable messages with index tracking
  if (msgId === ExtendedTestExtendedVariableSingleArray._msgid) {
    const msg = extVarSingleMsgs[extVarSingleEncodeIdx++];
    return writer.write(msg);
  }

  const msg = getMessage(msgId);
  if (!msg) return 0;
  return writer.write(msg);
}

/** Validate decoded message using equals() method. Accepts FrameMsgInfo. */
function validateMessage(data: FrameMsgInfo, _index: number): boolean {
  const msgId = data.msg_id;
  const MsgClass = getMessageClass(msgId);
  if (!MsgClass) return false;

  // Handle variable messages with index tracking
  if (msgId === ExtendedTestExtendedVariableSingleArray._msgid) {
    const expected = extVarSingleMsgs[extVarSingleValidateIdx++];
    const decoded = MsgClass.deserialize(data);
    return decoded.equals(expected);
  }

  const expected = getMessage(msgId);
  if (!expected) return false;

  const decoded = MsgClass.deserialize(data);
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
  getMessageInfo: get_message_info,
  supportsFormat,
};
