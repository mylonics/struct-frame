/**
 * Variable flag test message definitions (JavaScript).
 * Provides getMessage(index) function for variable flag truncation testing.
 *
 * This file matches the C++ variable_flag_messages.hpp structure.
 */

const {
  SerializationTestTruncationTestNonVariable,
  SerializationTestTruncationTestVariable,
  SerializationTestNestedPayload,
  SerializationTestNestedVariableMessage,
} = require('../../generated/js/serialization_test.structframe');

// Message count
const MESSAGE_COUNT = 3;


// ============================================================================
// Helper functions to create messages (like C++ create_* functions)
// ============================================================================

function createNonVariable1_3Filled() {
  const dataArray = Array.from({ length: 67 }, (_, i) => i);
  return new SerializationTestTruncationTestNonVariable({
    sequence_id: 0xDEADBEEF,
    data_array_count: 67,
    data_array_data: dataArray,
    footer: 0xCAFE,
  });
}

function createVariable1_3Filled() {
  const dataArray = Array.from({ length: 67 }, (_, i) => i);
  return new SerializationTestTruncationTestVariable({
    sequence_id: 0xDEADBEEF,
    data_array_count: 67,
    data_array_data: dataArray,
    footer: 0xCAFE,
  });
}

function createNestedVariable() {
  const nestedPayload = new SerializationTestNestedPayload({
    id: 7,
    label_length: 5,
    label_data: 'Hello',
    samples_count: 3,
    samples_data: [10, 20, 30],
  });
  return new SerializationTestNestedVariableMessage({
    sequence: 0x12345678,
    payload: [nestedPayload],
    description_length: 20,
    description_data: 'nested variable test',
  });
}


// ============================================================================
// getMessage(index) - unified interface matching C++ MessageProvider pattern
// ============================================================================

function getMessage(index) {
  if (index === 0) {
    return createNonVariable1_3Filled();
  } else if (index === 1) {
    return createVariable1_3Filled();
  } else {
    return createNestedVariable();
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
  if (info.msg_id !== msgClass._msgid) return false;

  // Deserialize and compare
  const decoded = msgClass.deserialize(info);
  return decoded.equals(expected);
}

module.exports = {
  MESSAGE_COUNT,
  getMessage,
  checkMessage,
};
