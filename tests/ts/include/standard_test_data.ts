/**
 * Test message data definitions.
 * Hardcoded test messages for cross-platform compatibility testing.
 *
 * Structure:
 * - Separate arrays for each message type (SerializationTest, BasicTypes, UnionTest, VariableSingleArray)
 * - Index variables track position within each typed array
 * - A msg_id order array (length 16) defines the encode/decode sequence
 * - Encoding uses msg_id array to select which typed array to pull from
 * - Decoding uses decoded msg_id to find the right array for comparison
 */

import { FrameMsgInfo } from '../../generated/ts/frame-base';
import { TestConfig } from './test_codec';
import {
  SerializationTestSerializationTestMessage,
  SerializationTestBasicTypesMessage,
  SerializationTestUnionTestMessage,
  SerializationTestComprehensiveArrayMessage,
  SerializationTestVariableSingleArray,
  SerializationTestMessage,
  SerializationTestMsgSeverity,
  get_message_info,
} from '../../generated/ts/serialization_test.structframe';

/** Message count */
const MESSAGE_COUNT = 17;

/** Index tracking for encoding/validation */
let serialIdx = 0;
let basicIdx = 0;
let unionIdx = 0;
let varSingleIdx = 0;
let messageIdx = 0;

/** Message ID order array */
const MSG_ID_ORDER: number[] = [
  SerializationTestSerializationTestMessage._msgid!,  // 0: SerializationTest[0]
  SerializationTestSerializationTestMessage._msgid!,  // 1: SerializationTest[1]
  SerializationTestSerializationTestMessage._msgid!,  // 2: SerializationTest[2]
  SerializationTestSerializationTestMessage._msgid!,  // 3: SerializationTest[3]
  SerializationTestSerializationTestMessage._msgid!,  // 4: SerializationTest[4]
  SerializationTestBasicTypesMessage._msgid!,         // 5: BasicTypes[0]
  SerializationTestBasicTypesMessage._msgid!,         // 6: BasicTypes[1]
  SerializationTestBasicTypesMessage._msgid!,         // 7: BasicTypes[2]
  SerializationTestUnionTestMessage._msgid!,          // 8: UnionTest[0]
  SerializationTestUnionTestMessage._msgid!,          // 9: UnionTest[1]
  SerializationTestBasicTypesMessage._msgid!,         // 10: BasicTypes[3]
  SerializationTestVariableSingleArray._msgid!,       // 11: VariableSingleArray[0] - empty
  SerializationTestVariableSingleArray._msgid!,       // 12: VariableSingleArray[1] - single
  SerializationTestVariableSingleArray._msgid!,       // 13: VariableSingleArray[2] - 1/3 filled
  SerializationTestVariableSingleArray._msgid!,       // 14: VariableSingleArray[3] - one empty
  SerializationTestVariableSingleArray._msgid!,       // 15: VariableSingleArray[4] - full
  SerializationTestMessage._msgid!,                   // 16: Message[0]
];

/** SerializationTestMessage array (5 messages) */
function getSerializationTestMessages(): SerializationTestSerializationTestMessage[] {
  return [
    new SerializationTestSerializationTestMessage({
      magic_number: 0xDEADBEEF,
      test_string_length: 'Cross-platform test!'.length,
      test_string_data: 'Cross-platform test!',
      test_float: 3.14159,
      test_bool: true,
      test_array_count: 3,
      test_array_data: [100, 200, 300],
    }),
    new SerializationTestSerializationTestMessage({
      magic_number: 0,
      test_string_length: 0,
      test_string_data: '',
      test_float: 0.0,
      test_bool: false,
      test_array_count: 0,
      test_array_data: [],
    }),
    new SerializationTestSerializationTestMessage({
      magic_number: 0xFFFFFFFF,
      test_string_length: 'Maximum length test string for coverage!'.length,
      test_string_data: 'Maximum length test string for coverage!',
      test_float: 999999.9,
      test_bool: true,
      test_array_count: 5,
      test_array_data: [2147483647, -2147483648, 0, 1, -1],
    }),
    new SerializationTestSerializationTestMessage({
      magic_number: 0xAAAAAAAA,
      test_string_length: 'Negative test'.length,
      test_string_data: 'Negative test',
      test_float: -273.15,
      test_bool: false,
      test_array_count: 4,
      test_array_data: [-100, -200, -300, -400],
    }),
    new SerializationTestSerializationTestMessage({
      magic_number: 1234567890,
      test_string_length: 'Special: !@#$%^&*()'.length,
      test_string_data: 'Special: !@#$%^&*()',
      test_float: 2.71828,
      test_bool: true,
      test_array_count: 5,
      test_array_data: [0, 1, 1, 2, 3],
    }),
  ];
}

/** BasicTypesMessage array (4 messages) */
function getBasicTypesMessages(): SerializationTestBasicTypesMessage[] {
  return [
    new SerializationTestBasicTypesMessage({
      small_int: 42,
      medium_int: 1000,
      regular_int: 123456,
      large_int: 9876543210n,
      small_uint: 200,
      medium_uint: 50000,
      regular_uint: 4000000000,
      large_uint: 9223372036854775807n,
      single_precision: 3.14159,
      double_precision: 2.718281828459045,
      flag: true,
      device_id: 'DEVICE-001',
      description_length: 'Basic test values'.length,
      description_data: 'Basic test values',
    }),
    new SerializationTestBasicTypesMessage({
      small_int: 0,
      medium_int: 0,
      regular_int: 0,
      large_int: 0n,
      small_uint: 0,
      medium_uint: 0,
      regular_uint: 0,
      large_uint: 0n,
      single_precision: 0.0,
      double_precision: 0.0,
      flag: false,
      device_id: '',
      description_length: 0,
      description_data: '',
    }),
    new SerializationTestBasicTypesMessage({
      small_int: -128,
      medium_int: -32768,
      regular_int: -2147483648,
      large_int: -9223372036854775807n,
      small_uint: 255,
      medium_uint: 65535,
      regular_uint: 4294967295,
      large_uint: 9223372036854775807n,
      single_precision: -273.15,
      double_precision: -9999.999999,
      flag: false,
      device_id: 'NEG-TEST',
      description_length: 'Negative and max values'.length,
      description_data: 'Negative and max values',
    }),
    new SerializationTestBasicTypesMessage({
      small_int: -128,
      medium_int: -32768,
      regular_int: -2147483648,
      large_int: -9223372036854775807n,
      small_uint: 255,
      medium_uint: 65535,
      regular_uint: 4294967295,
      large_uint: 9223372036854775807n,
      single_precision: -273.15,
      double_precision: -9999.999999,
      flag: false,
      device_id: 'NEG-TEST',
      description_length: 'Negative and max values'.length,
      description_data: 'Negative and max values',
    }),
  ];
}

/** Create UnionTestMessage with array payload */
function createUnionWithArray(): SerializationTestUnionTestMessage {
  const msg = new SerializationTestUnionTestMessage();
  msg.payload_discriminator = SerializationTestComprehensiveArrayMessage._msgid!;

  const innerMsg = new SerializationTestComprehensiveArrayMessage({
    fixed_ints: [10, 20, 30],
    fixed_floats: [1.5, 2.5],
    fixed_bools: [1, 0, 1, 0],  // Use 1/0 for bool array
    bounded_uints_count: 2,
    bounded_uints_data: [100, 200],
    bounded_doubles_count: 1,
    bounded_doubles_data: [3.14159],
    fixed_strings: ['Hello', 'World'],
    bounded_strings_count: 1,
    bounded_strings_data: ['Test'],
    fixed_statuses: [1, 2],  // ACTIVE, ERROR
    bounded_statuses_count: 1,
    bounded_statuses_data: [0],  // INACTIVE
    fixed_sensors: [
      { id: 1, value: 25.5, status: 1, name: 'TempSensor' },
      { id: 0, value: 0, status: 0, name: '' },
    ],
    bounded_sensors_count: 0,
    bounded_sensors_data: [],
  });

  // Copy inner buffer to payload area (offset 2 for discriminator)
  innerMsg._buffer.copy(msg._buffer, 2, 0, SerializationTestComprehensiveArrayMessage._size);

  return msg;
}

/** Create UnionTestMessage with test payload */
function createUnionWithTest(): SerializationTestUnionTestMessage {
  const msg = new SerializationTestUnionTestMessage();
  msg.payload_discriminator = SerializationTestSerializationTestMessage._msgid!;

  const innerMsg = new SerializationTestSerializationTestMessage({
    magic_number: 0x12345678,
    test_string_length: 'Union test message'.length,
    test_string_data: 'Union test message',
    test_float: 99.99,
    test_bool: true,
    test_array_count: 5,
    test_array_data: [1, 2, 3, 4, 5],
  });

  // Copy inner buffer to payload area (offset 2 for discriminator)
  innerMsg._buffer.copy(msg._buffer, 2, 0, SerializationTestSerializationTestMessage._size);

  return msg;
}

/** UnionTestMessage array (2 messages) */
function getUnionTestMessages(): SerializationTestUnionTestMessage[] {
  return [
    createUnionWithArray(),
    createUnionWithTest(),
  ];
}

/** VariableSingleArray array (5 messages with different fill levels) */
function getVariableSingleArrayMessages(): SerializationTestVariableSingleArray[] {
  // Generate arrays for different fill levels
  const thirdFilled = Array.from({ length: 67 }, (_, i) => i);
  const almostFull = Array.from({ length: 199 }, (_, i) => i);
  const full = Array.from({ length: 200 }, (_, i) => i);

  return [
    // 0: Empty payload (0 elements)
    new SerializationTestVariableSingleArray({
      message_id: 0x00000001,
      payload_count: 0,
      payload_data: [],
      checksum: 0x0001,
    }),
    // 1: Single element
    new SerializationTestVariableSingleArray({
      message_id: 0x00000002,
      payload_count: 1,
      payload_data: [42],
      checksum: 0x0002,
    }),
    // 2: One-third filled (67 elements for max_size=200)
    new SerializationTestVariableSingleArray({
      message_id: 0x00000003,
      payload_count: 67,
      payload_data: thirdFilled,
      checksum: 0x0003,
    }),
    // 3: One position empty (199 elements)
    new SerializationTestVariableSingleArray({
      message_id: 0x00000004,
      payload_count: 199,
      payload_data: almostFull,
      checksum: 0x0004,
    }),
    // 4: Full (200 elements)
    new SerializationTestVariableSingleArray({
      message_id: 0x00000005,
      payload_count: 200,
      payload_data: full,
      checksum: 0x0005,
    }),
  ];
}

/** Message array (1 message) */
function getMessageMessages(): SerializationTestMessage[] {
  return [
    new SerializationTestMessage({
      severity: SerializationTestMsgSeverity.SEV_MSG,
      module_length: 4,
      module_data: 'test',
      msg_length: 13,
      msg_data: 'A really good',
    }),
  ];
}

/** Reset state for new encode/decode run */
function resetState(): void {
  serialIdx = 0;
  basicIdx = 0;
  unionIdx = 0;
  varSingleIdx = 0;
  messageIdx = 0;
}

/** Encode message by index */
function encodeMessage(writer: any, index: number): number {
  const msgId = MSG_ID_ORDER[index];

  if (msgId === SerializationTestSerializationTestMessage._msgid) {
    const msg = getSerializationTestMessages()[serialIdx++];
    return writer.write(msg);
  } else if (msgId === SerializationTestBasicTypesMessage._msgid) {
    const msg = getBasicTypesMessages()[basicIdx++];
    return writer.write(msg);
  } else if (msgId === SerializationTestUnionTestMessage._msgid) {
    const msg = getUnionTestMessages()[unionIdx++];
    return writer.write(msg);
  } else if (msgId === SerializationTestVariableSingleArray._msgid) {
    const msg = getVariableSingleArrayMessages()[varSingleIdx++];
    return writer.write(msg);
  } else if (msgId === SerializationTestMessage._msgid) {
    const msg = getMessageMessages()[messageIdx++];
    return writer.write(msg);
  }

  return 0;
}

/** Validate decoded message using equals() method. Accepts FrameMsgInfo. */
function validateMessage(data: FrameMsgInfo, _index: number): boolean {
  const msgId = data.msg_id;
  if (msgId === SerializationTestSerializationTestMessage._msgid) {
    const expected = getSerializationTestMessages()[serialIdx++];
    const decoded = SerializationTestSerializationTestMessage.deserialize(data);
    return decoded.equals(expected);
  } else if (msgId === SerializationTestBasicTypesMessage._msgid) {
    const expected = getBasicTypesMessages()[basicIdx++];
    const decoded = SerializationTestBasicTypesMessage.deserialize(data);
    return decoded.equals(expected);
  } else if (msgId === SerializationTestUnionTestMessage._msgid) {
    const expected = getUnionTestMessages()[unionIdx++];
    const decoded = SerializationTestUnionTestMessage.deserialize(data);
    return decoded.equals(expected);
  } else if (msgId === SerializationTestVariableSingleArray._msgid) {
    const expected = getVariableSingleArrayMessages()[varSingleIdx++];
    const decoded = SerializationTestVariableSingleArray.deserialize(data);
    return decoded.equals(expected);
  } else if (msgId === SerializationTestMessage._msgid) {
    const expected = getMessageMessages()[messageIdx++];
    const decoded = SerializationTestMessage.deserialize(data);
    return decoded.equals(expected);
  }

  return false;
}

/** Check if format is supported */
function supportsFormat(format: string): boolean {
  return format === 'profile_standard' ||
    format === 'profile_sensor' ||
    format === 'profile_ipc' ||
    format === 'profile_bulk' ||
    format === 'profile_network';
}

/** Standard test configuration */
export const stdTestConfig: TestConfig = {
  messageCount: MESSAGE_COUNT,
  bufferSize: 4096,
  formatsHelp: 'profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network',
  testName: 'TypeScript',
  getMsgIdOrder: () => MSG_ID_ORDER,
  encodeMessage,
  validateMessage,
  resetState,
  getMessageInfo: get_message_info,
  supportsFormat,
};
