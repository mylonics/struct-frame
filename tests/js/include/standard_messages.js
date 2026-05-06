/**
 * Standard test message definitions (JavaScript).
 * Provides getMessage(index) function for test messages.
 *
 * This file matches the C++ standard_messages.hpp structure.
 */

const {
  SerializationTestMessage,
  BasicTypesMessage,
  UnionTestMessage,
  ComprehensiveArrayMessage,
  VariableSingleArray,
  Message,
  MsgSeverity,
  NestedEnumMessage,
  NestedEnumMessageOperationMode,
  CollisionEnumMessage,
  CollisionEnumMessageStatus,
} = require('../../generated/js/serialization-test.structframe');

// Message count
const MESSAGE_COUNT = 21;


// ============================================================================
// Helper functions to create messages (like C++ create_* functions)
// ============================================================================

function createSerializationTest(magic, str, flt, bl, arr) {
  return new SerializationTestMessage({
    magicNumber: magic,
    testStringLength: str.length,
    testStringData: str,
    testFloat: flt,
    testBool: bl,
    testArrayCount: arr.length,
    testArrayData: arr,
  });
}

function createBasicTypes(si, mi, ri, li, su, mu, ru, lu, sp, dp, fl, dev, desc) {
  return new BasicTypesMessage({
    smallInt: si,
    mediumInt: mi,
    regularInt: ri,
    largeInt: li,
    smallUint: su,
    mediumUint: mu,
    regularUint: ru,
    largeUint: lu,
    singlePrecision: sp,
    doublePrecision: dp,
    flag: fl,
    deviceId: dev,
    descriptionLength: desc.length,
    descriptionData: desc,
  });
}

function createUnionWithArray() {
  const msg = new UnionTestMessage();
  msg.payloadDiscriminator = ComprehensiveArrayMessage._msgid;

  const innerMsg = new ComprehensiveArrayMessage({
    fixedInts: [10, 20, 30],
    fixedFloats: [1.5, 2.5],
    fixedBools: [1, 0, 1, 0],
    boundedUintsCount: 2,
    boundedUintsData: [100, 200],
    boundedDoublesCount: 1,
    boundedDoublesData: [3.14159],
    fixedStrings: ['Hello', 'World'],
    boundedStringsCount: 1,
    boundedStringsData: ['Test'],
    fixedStatuses: [1, 2],
    boundedStatusesCount: 1,
    boundedStatusesData: [0],
    fixedSensors: [
      { id: 1, value: 25.5, status: 1, name: 'TempSensor' },
      { id: 0, value: 0, status: 0, name: '' },
    ],
    boundedSensorsCount: 0,
    boundedSensorsData: [],
  });

  innerMsg._buffer.copy(msg._buffer, 2, 0, ComprehensiveArrayMessage._size);
  return msg;
}

function createUnionWithTest() {
  const msg = new UnionTestMessage();
  msg.payloadDiscriminator = SerializationTestMessage._msgid;

  const innerMsg = new SerializationTestMessage({
    magicNumber: 0x12345678,
    testStringLength: 'Union test message'.length,
    testStringData: 'Union test message',
    testFloat: 99.99,
    testBool: true,
    testArrayCount: 5,
    testArrayData: [1, 2, 3, 4, 5],
  });

  innerMsg._buffer.copy(msg._buffer, 2, 0, SerializationTestMessage._size);
  return msg;
}

function createVariableSingleArrayEmpty() {
  return new VariableSingleArray({
    messageId: 0x00000001,
    payloadCount: 0,
    payloadData: [],
    checksum: 0x0001,
  });
}

function createVariableSingleArraySingle() {
  return new VariableSingleArray({
    messageId: 0x00000002,
    payloadCount: 1,
    payloadData: [42],
    checksum: 0x0002,
  });
}

function createVariableSingleArrayThird() {
  const thirdFilled = Array.from({ length: 67 }, (_, i) => i);
  return new VariableSingleArray({
    messageId: 0x00000003,
    payloadCount: 67,
    payloadData: thirdFilled,
    checksum: 0x0003,
  });
}

function createVariableSingleArrayAlmost() {
  const almostFull = Array.from({ length: 199 }, (_, i) => i);
  return new VariableSingleArray({
    messageId: 0x00000004,
    payloadCount: 199,
    payloadData: almostFull,
    checksum: 0x0004,
  });
}

function createVariableSingleArrayFull() {
  const full = Array.from({ length: 200 }, (_, i) => i);
  return new VariableSingleArray({
    messageId: 0x00000005,
    payloadCount: 200,
    payloadData: full,
    checksum: 0x0005,
  });
}

function createMessageTest() {
  return new Message({
    severity: MsgSeverity.SevMsg,
    moduleLength: 4,
    moduleData: 'test',
    msgLength: 13,
    msgData: 'A really good',
  });
}


// ============================================================================
// getMessage(index) - unified interface matching C++ MessageProvider pattern
// ============================================================================

function getMessage(index) {
  switch (index) {
    case 0: return createSerializationTest(0xDEADBEEF, 'Cross-platform test!', 3.14159, true, [100, 200, 300]);
    case 1: return createSerializationTest(0, '', 0.0, false, []);
    case 2: return createSerializationTest(0xFFFFFFFF, 'Maximum length test string for coverage!', 999999.9, true, [2147483647, -2147483648, 0, 1, -1]);
    case 3: return createSerializationTest(0xAAAAAAAA, 'Negative test', -273.15, false, [-100, -200, -300, -400]);
    case 4: return createSerializationTest(1234567890, 'Special: !@#$%^&*()', 2.71828, true, [0, 1, 1, 2, 3]);
    case 5: return createBasicTypes(42, 1000, 123456, 9876543210n, 200, 50000, 4000000000, 9223372036854775807n, 3.14159, 2.718281828459045, true, 'DEVICE-001', 'Basic test values');
    case 6: return createBasicTypes(0, 0, 0, 0n, 0, 0, 0, 0n, 0.0, 0.0, false, '', '');
    case 7: return createBasicTypes(-128, -32768, -2147483648, -9223372036854775807n, 255, 65535, 4294967295, 9223372036854775807n, -273.15, -9999.999999, false, 'NEG-TEST', 'Negative and max values');
    case 8: return createUnionWithArray();
    case 9: return createUnionWithTest();
    case 10: return createBasicTypes(-128, -32768, -2147483648, -9223372036854775807n, 255, 65535, 4294967295, 9223372036854775807n, -273.15, -9999.999999, false, 'NEG-TEST', 'Negative and max values');
    case 11: return createVariableSingleArrayEmpty();
    case 12: return createVariableSingleArraySingle();
    case 13: return createVariableSingleArrayThird();
    case 14: return createVariableSingleArrayAlmost();
    case 15: return createVariableSingleArrayFull();
    case 16: return createMessageTest();
    case 17: return new NestedEnumMessage({ mode: NestedEnumMessageOperationMode.Idle, value: 0, enabled: false });
    case 18: return new NestedEnumMessage({ mode: NestedEnumMessageOperationMode.Active, value: 42, enabled: true });
    case 19: return new CollisionEnumMessage({ status: CollisionEnumMessageStatus.Running, id: 7, time: 1.23 });
    default: return new CollisionEnumMessage({ status: CollisionEnumMessageStatus.Failed, id: 0, time: 0.0 });
  }
}


// ============================================================================
// checkMessage(index, info) - validates decoded message matches expected
// This is the callback passed to ProfileRunner.parse()
// ============================================================================

function checkMessage(index, info) {
  const expected = getMessage(index);
  const msgClass = expected.constructor;

  // Check msg_id matches
  if (info.msgId !== msgClass._msgid) return false;

  // Deserialize and compare
  const decoded = msgClass.deserialize(info);
  return decoded.equals(expected);
}

module.exports = {
  MESSAGE_COUNT,
  getMessage,
  checkMessage,
};
