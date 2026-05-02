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
  SerializationTestVariableMultipleArrays,
  SerializationTestVariableMixedFields,
} = require('../../generated/js/serialization_test.structframe');

// Message count
const MESSAGE_COUNT = 5;


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

function createMultipleArrays() {
  return new SerializationTestVariableMultipleArrays({
    type: 5,
    readings_count: 3,
    readings_data: [100, 200, 300],
    values_count: 2,
    values_data: [1.5, 2.5],
    label_length: 17,
    label_data: 'multi arrays test',
  });
}

function createMixedFields() {
  return new SerializationTestVariableMixedFields({
    fixed_id: 0xABCD1234,
    fixed_value: 3.14,
    fixed_name: 'DeviceName',
    variable_data_count: 5,
    variable_data_data: [1000, 2000, 3000, 4000, 5000],
    variable_desc_length: 17,
    variable_desc_data: 'mixed fields test',
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
  } else if (index === 2) {
    return createNestedVariable();
  } else if (index === 3) {
    return createMultipleArrays();
  } else {
    return createMixedFields();
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
