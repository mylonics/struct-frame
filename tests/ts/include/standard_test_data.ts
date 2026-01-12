/**
 * Test message data definitions.
 * Hardcoded test messages for cross-platform compatibility testing.
 *
 * Structure:
 * - Separate arrays for each message type (SerializationTest, BasicTypes, UnionTest)
 * - Index variables track position within each typed array
 * - A msg_id order array (length 11) defines the encode/decode sequence
 * - Encoding uses msg_id array to select which typed array to pull from
 * - Decoding uses decoded msg_id to find the right array for comparison
 */

import { TestConfig } from './test_codec';
import {
  serialization_test_SerializationTestMessage,
  serialization_test_BasicTypesMessage,
  serialization_test_UnionTestMessage,
  serialization_test_ComprehensiveArrayMessage,
  get_message_length,
} from '../../generated/ts/serialization_test.sf';

/** Message count */
const MESSAGE_COUNT = 11;

/** Index tracking for encoding/validation */
let serialIdx = 0;
let basicIdx = 0;
let unionIdx = 0;

/** Message ID order array */
const MSG_ID_ORDER: number[] = [
  serialization_test_SerializationTestMessage._msgid!,  // 0: SerializationTest[0]
  serialization_test_SerializationTestMessage._msgid!,  // 1: SerializationTest[1]
  serialization_test_SerializationTestMessage._msgid!,  // 2: SerializationTest[2]
  serialization_test_SerializationTestMessage._msgid!,  // 3: SerializationTest[3]
  serialization_test_SerializationTestMessage._msgid!,  // 4: SerializationTest[4]
  serialization_test_BasicTypesMessage._msgid!,         // 5: BasicTypes[0]
  serialization_test_BasicTypesMessage._msgid!,         // 6: BasicTypes[1]
  serialization_test_BasicTypesMessage._msgid!,         // 7: BasicTypes[2]
  serialization_test_UnionTestMessage._msgid!,          // 8: UnionTest[0]
  serialization_test_UnionTestMessage._msgid!,          // 9: UnionTest[1]
  serialization_test_BasicTypesMessage._msgid!,         // 10: BasicTypes[3]
];

/** SerializationTestMessage array (5 messages) */
function getSerializationTestMessages(): serialization_test_SerializationTestMessage[] {
  return [
    new serialization_test_SerializationTestMessage({
      magic_number: 0xDEADBEEF,
      test_string_length: 'Cross-platform test!'.length,
      test_string_data: 'Cross-platform test!',
      test_float: 3.14159,
      test_bool: true,
      test_array_count: 3,
      test_array_data: [100, 200, 300],
    }),
    new serialization_test_SerializationTestMessage({
      magic_number: 0,
      test_string_length: 0,
      test_string_data: '',
      test_float: 0.0,
      test_bool: false,
      test_array_count: 0,
      test_array_data: [],
    }),
    new serialization_test_SerializationTestMessage({
      magic_number: 0xFFFFFFFF,
      test_string_length: 'Maximum length test string for coverage!'.length,
      test_string_data: 'Maximum length test string for coverage!',
      test_float: 999999.9,
      test_bool: true,
      test_array_count: 5,
      test_array_data: [2147483647, -2147483648, 0, 1, -1],
    }),
    new serialization_test_SerializationTestMessage({
      magic_number: 0xAAAAAAAA,
      test_string_length: 'Negative test'.length,
      test_string_data: 'Negative test',
      test_float: -273.15,
      test_bool: false,
      test_array_count: 4,
      test_array_data: [-100, -200, -300, -400],
    }),
    new serialization_test_SerializationTestMessage({
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
function getBasicTypesMessages(): serialization_test_BasicTypesMessage[] {
  return [
    new serialization_test_BasicTypesMessage({
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
    new serialization_test_BasicTypesMessage({
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
    new serialization_test_BasicTypesMessage({
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
    new serialization_test_BasicTypesMessage({
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
function createUnionWithArray(): serialization_test_UnionTestMessage {
  const msg = new serialization_test_UnionTestMessage();
  msg.payload_discriminator = serialization_test_ComprehensiveArrayMessage._msgid!;

  const innerMsg = new serialization_test_ComprehensiveArrayMessage({
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
  innerMsg._buffer.copy(msg._buffer, 2, 0, serialization_test_ComprehensiveArrayMessage._size);

  return msg;
}

/** Create UnionTestMessage with test payload */
function createUnionWithTest(): serialization_test_UnionTestMessage {
  const msg = new serialization_test_UnionTestMessage();
  msg.payload_discriminator = serialization_test_SerializationTestMessage._msgid!;

  const innerMsg = new serialization_test_SerializationTestMessage({
    magic_number: 0x12345678,
    test_string_length: 'Union test message'.length,
    test_string_data: 'Union test message',
    test_float: 99.99,
    test_bool: true,
    test_array_count: 5,
    test_array_data: [1, 2, 3, 4, 5],
  });

  // Copy inner buffer to payload area (offset 2 for discriminator)
  innerMsg._buffer.copy(msg._buffer, 2, 0, serialization_test_SerializationTestMessage._size);

  return msg;
}

/** UnionTestMessage array (2 messages) */
function getUnionTestMessages(): serialization_test_UnionTestMessage[] {
  return [
    createUnionWithArray(),
    createUnionWithTest(),
  ];
}

/** Reset state for new encode/decode run */
function resetState(): void {
  serialIdx = 0;
  basicIdx = 0;
  unionIdx = 0;
}

/** Encode message by index */
function encodeMessage(writer: any, index: number): number {
  const msgId = MSG_ID_ORDER[index];

  if (msgId === serialization_test_SerializationTestMessage._msgid) {
    const msg = getSerializationTestMessages()[serialIdx++];
    return writer.write(msg);
  } else if (msgId === serialization_test_BasicTypesMessage._msgid) {
    const msg = getBasicTypesMessages()[basicIdx++];
    return writer.write(msg);
  } else if (msgId === serialization_test_UnionTestMessage._msgid) {
    const msg = getUnionTestMessages()[unionIdx++];
    return writer.write(msg);
  }

  return 0;
}

/** Validate decoded message */
function validateMessage(msgId: number, data: Buffer, _index: number): boolean {
  if (msgId === serialization_test_SerializationTestMessage._msgid) {
    const expected = getSerializationTestMessages()[serialIdx++];
    if (data.length !== serialization_test_SerializationTestMessage._size) return false;
    return data.equals(expected._buffer);
  } else if (msgId === serialization_test_BasicTypesMessage._msgid) {
    const expected = getBasicTypesMessages()[basicIdx++];
    if (data.length !== serialization_test_BasicTypesMessage._size) return false;
    return data.equals(expected._buffer);
  } else if (msgId === serialization_test_UnionTestMessage._msgid) {
    const expected = getUnionTestMessages()[unionIdx++];
    if (data.length !== serialization_test_UnionTestMessage._size) return false;
    return data.equals(expected._buffer);
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
  getMessageLength: get_message_length,
  supportsFormat,
};
