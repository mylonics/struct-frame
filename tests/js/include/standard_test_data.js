/**
 * Test message data definitions (JavaScript).
 * Hardcoded test messages for cross-platform compatibility testing.
 *
 * This module follows the C++ test pattern with a unified getMessage(index) interface.
 * The getMessage() function returns a message based on index, matching the C++ approach.
 */

const {
  SerializationTestSerializationTestMessage,
  SerializationTestBasicTypesMessage,
  SerializationTestUnionTestMessage,
  SerializationTestComprehensiveArrayMessage,
  SerializationTestVariableSingleArray,
  SerializationTestMessage,
  SerializationTestMsgSeverity,
  get_message_info,
} = require('../../generated/js/serialization_test.structframe');

// ============================================================================
// Message count and supported profiles
// ============================================================================

const MESSAGE_COUNT = 17;
const PROFILES = 'standard, sensor, ipc, bulk, network';

// ============================================================================
// Helper functions to create messages (like C++ create_* functions)
// ============================================================================

function createSerializationTest(magic, str, flt, bl, arr) {
  return new SerializationTestSerializationTestMessage({
    magic_number: magic,
    test_string_length: str.length,
    test_string_data: str,
    test_float: flt,
    test_bool: bl,
    test_array_count: arr.length,
    test_array_data: arr,
  });
}

function createBasicTypes(si, mi, ri, li, su, mu, ru, lu, sp, dp, fl, dev, desc) {
  return new SerializationTestBasicTypesMessage({
    small_int: si,
    medium_int: mi,
    regular_int: ri,
    large_int: li,
    small_uint: su,
    medium_uint: mu,
    regular_uint: ru,
    large_uint: lu,
    single_precision: sp,
    double_precision: dp,
    flag: fl,
    device_id: dev,
    description_length: desc.length,
    description_data: desc,
  });
}

function createUnionWithArray() {
  const msg = new SerializationTestUnionTestMessage();
  msg.payload_discriminator = SerializationTestComprehensiveArrayMessage._msgid;

  const innerMsg = new SerializationTestComprehensiveArrayMessage({
    fixed_ints: [10, 20, 30],
    fixed_floats: [1.5, 2.5],
    fixed_bools: [1, 0, 1, 0],
    bounded_uints_count: 2,
    bounded_uints_data: [100, 200],
    bounded_doubles_count: 1,
    bounded_doubles_data: [3.14159],
    fixed_strings: ['Hello', 'World'],
    bounded_strings_count: 1,
    bounded_strings_data: ['Test'],
    fixed_statuses: [1, 2],
    bounded_statuses_count: 1,
    bounded_statuses_data: [0],
    fixed_sensors: [
      { id: 1, value: 25.5, status: 1, name: 'TempSensor' },
      { id: 0, value: 0, status: 0, name: '' },
    ],
    bounded_sensors_count: 0,
    bounded_sensors_data: [],
  });

  innerMsg._buffer.copy(msg._buffer, 2, 0, SerializationTestComprehensiveArrayMessage._size);
  return msg;
}

function createUnionWithTest() {
  const msg = new SerializationTestUnionTestMessage();
  msg.payload_discriminator = SerializationTestSerializationTestMessage._msgid;

  const innerMsg = new SerializationTestSerializationTestMessage({
    magic_number: 0x12345678,
    test_string_length: 'Union test message'.length,
    test_string_data: 'Union test message',
    test_float: 99.99,
    test_bool: true,
    test_array_count: 5,
    test_array_data: [1, 2, 3, 4, 5],
  });

  innerMsg._buffer.copy(msg._buffer, 2, 0, SerializationTestSerializationTestMessage._size);
  return msg;
}

function createVariableSingleArrayEmpty() {
  return new SerializationTestVariableSingleArray({
    message_id: 0x00000001,
    payload_count: 0,
    payload_data: [],
    checksum: 0x0001,
  });
}

function createVariableSingleArraySingle() {
  return new SerializationTestVariableSingleArray({
    message_id: 0x00000002,
    payload_count: 1,
    payload_data: [42],
    checksum: 0x0002,
  });
}

function createVariableSingleArrayThird() {
  const thirdFilled = Array.from({ length: 67 }, (_, i) => i);
  return new SerializationTestVariableSingleArray({
    message_id: 0x00000003,
    payload_count: 67,
    payload_data: thirdFilled,
    checksum: 0x0003,
  });
}

function createVariableSingleArrayAlmost() {
  const almostFull = Array.from({ length: 199 }, (_, i) => i);
  return new SerializationTestVariableSingleArray({
    message_id: 0x00000004,
    payload_count: 199,
    payload_data: almostFull,
    checksum: 0x0004,
  });
}

function createVariableSingleArrayFull() {
  const full = Array.from({ length: 200 }, (_, i) => i);
  return new SerializationTestVariableSingleArray({
    message_id: 0x00000005,
    payload_count: 200,
    payload_data: full,
    checksum: 0x0005,
  });
}

function createMessageTest() {
  return new SerializationTestMessage({
    severity: SerializationTestMsgSeverity.SEV_MSG,
    module_length: 4,
    module_data: 'test',
    msg_length: 13,
    msg_data: 'A really good',
  });
}

// ============================================================================
// Unified getMessage(index) function - matches C++ MessageProvider pattern
// ============================================================================

/**
 * Get message by index - unified interface matching C++ get_message().
 * Message order matches standard_test_data get_msg_id_order().
 */
function getMessage(index) {
  switch (index) {
    // SerializationTest messages (0-4)
    case 0: return createSerializationTest(0xDEADBEEF, 'Cross-platform test!', 3.14159, true, [100, 200, 300]);
    case 1: return createSerializationTest(0, '', 0.0, false, []);
    case 2: return createSerializationTest(0xFFFFFFFF, 'Maximum length test string for coverage!', 999999.9, true, [2147483647, -2147483648, 0, 1, -1]);
    case 3: return createSerializationTest(0xAAAAAAAA, 'Negative test', -273.15, false, [-100, -200, -300, -400]);
    case 4: return createSerializationTest(1234567890, 'Special: !@#$%^&*()', 2.71828, true, [0, 1, 1, 2, 3]);
    // BasicTypes messages (5-7)
    case 5: return createBasicTypes(42, 1000, 123456, 9876543210n, 200, 50000, 4000000000, 9223372036854775807n, 3.14159, 2.718281828459045, true, 'DEVICE-001', 'Basic test values');
    case 6: return createBasicTypes(0, 0, 0, 0n, 0, 0, 0, 0n, 0.0, 0.0, false, '', '');
    case 7: return createBasicTypes(-128, -32768, -2147483648, -9223372036854775807n, 255, 65535, 4294967295, 9223372036854775807n, -273.15, -9999.999999, false, 'NEG-TEST', 'Negative and max values');
    // UnionTest messages (8-9)
    case 8: return createUnionWithArray();
    case 9: return createUnionWithTest();
    // BasicTypes message (10)
    case 10: return createBasicTypes(-128, -32768, -2147483648, -9223372036854775807n, 255, 65535, 4294967295, 9223372036854775807n, -273.15, -9999.999999, false, 'NEG-TEST', 'Negative and max values');
    // VariableSingleArray messages (11-15)
    case 11: return createVariableSingleArrayEmpty();
    case 12: return createVariableSingleArraySingle();
    case 13: return createVariableSingleArrayThird();
    case 14: return createVariableSingleArrayAlmost();
    case 15: return createVariableSingleArrayFull();
    // Message (16)
    default: return createMessageTest();
  }
}

// ============================================================================
// Message class lookup - maps message type to class for deserialization
// ============================================================================

const MESSAGE_CLASSES = {
  [SerializationTestSerializationTestMessage._msgid]: SerializationTestSerializationTestMessage,
  [SerializationTestBasicTypesMessage._msgid]: SerializationTestBasicTypesMessage,
  [SerializationTestUnionTestMessage._msgid]: SerializationTestUnionTestMessage,
  [SerializationTestVariableSingleArray._msgid]: SerializationTestVariableSingleArray,
  [SerializationTestMessage._msgid]: SerializationTestMessage,
};

// ============================================================================
// Encoder/Validator state - simplified to use getMessage(index) directly
// ============================================================================

let currentIndex = 0;

function resetState() {
  currentIndex = 0;
}

function encodeMessage(writer, _index) {
  const msg = getMessage(currentIndex);
  currentIndex++;
  return writer.write(msg);
}

function validateMessage(data, _index) {
  const msgId = data.msg_id;
  const MsgClass = MESSAGE_CLASSES[msgId];
  if (!MsgClass) return false;

  const expected = getMessage(currentIndex);
  currentIndex++;
  const decoded = MsgClass.deserialize(data);
  return decoded.equals(expected);
}

function supportsFormat(format) {
  return format === 'standard' || format === 'sensor' || format === 'ipc' || format === 'bulk' || format === 'network';
}

// ============================================================================
// Message ID order array - derived from getMessage()
// ============================================================================

const MSG_ID_ORDER = [
  SerializationTestSerializationTestMessage._msgid,  // 0-4: SerializationTest
  SerializationTestSerializationTestMessage._msgid,
  SerializationTestSerializationTestMessage._msgid,
  SerializationTestSerializationTestMessage._msgid,
  SerializationTestSerializationTestMessage._msgid,
  SerializationTestBasicTypesMessage._msgid,         // 5-7: BasicTypes
  SerializationTestBasicTypesMessage._msgid,
  SerializationTestBasicTypesMessage._msgid,
  SerializationTestUnionTestMessage._msgid,          // 8-9: UnionTest
  SerializationTestUnionTestMessage._msgid,
  SerializationTestBasicTypesMessage._msgid,         // 10: BasicTypes
  SerializationTestVariableSingleArray._msgid,       // 11-15: VariableSingleArray
  SerializationTestVariableSingleArray._msgid,
  SerializationTestVariableSingleArray._msgid,
  SerializationTestVariableSingleArray._msgid,
  SerializationTestVariableSingleArray._msgid,
  SerializationTestMessage._msgid,                   // 16: Message
];

// ============================================================================
// Test configuration - matches C++ TestHarness pattern
// ============================================================================

const stdTestConfig = {
  messageCount: MESSAGE_COUNT,
  bufferSize: 4096,
  formatsHelp: PROFILES,
  testName: 'JavaScript',
  getMsgIdOrder: () => MSG_ID_ORDER,
  encodeMessage,
  validateMessage,
  resetState,
  getMessageInfo: (msgId) => get_message_info(msgId),
  supportsFormat,
};

module.exports = { stdTestConfig };
