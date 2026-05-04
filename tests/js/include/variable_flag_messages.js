/**
 * Variable flag test message definitions (JavaScript).
 * Provides getMessage(index) function for variable flag truncation testing.
 *
 * This file matches the C++ variable_flag_messages.hpp structure.
 */

const {
  TruncationTestNonVariable,
  TruncationTestVariable,
  NestedPayload,
  NestedVariableMessage,
  VariableMultipleArrays,
  VariableMixedFields,
} = require('../../generated/js/serialization-test.structframe');

// Message count
const MESSAGE_COUNT = 5;


// ============================================================================
// Helper functions to create messages (like C++ create_* functions)
// ============================================================================

function createNonVariable1_3Filled() {
  const dataArray = Array.from({ length: 67 }, (_, i) => i);
  return new TruncationTestNonVariable({
    sequenceId: 0xDEADBEEF,
    dataArrayCount: 67,
    dataArrayData: dataArray,
    footer: 0xCAFE,
  });
}

function createVariable1_3Filled() {
  const dataArray = Array.from({ length: 67 }, (_, i) => i);
  return new TruncationTestVariable({
    sequenceId: 0xDEADBEEF,
    dataArrayCount: 67,
    dataArrayData: dataArray,
    footer: 0xCAFE,
  });
}

function createNestedVariable() {
  const nestedPayload = new NestedPayload({
    id: 7,
    labelLength: 5,
    labelData: 'Hello',
    samplesCount: 3,
    samplesData: [10, 20, 30],
  });
  return new NestedVariableMessage({
    sequence: 0x12345678,
    payload: [nestedPayload],
    descriptionLength: 20,
    descriptionData: 'nested variable test',
  });
}

function createMultipleArrays() {
  return new VariableMultipleArrays({
    type: 5,
    readingsCount: 3,
    readingsData: [100, 200, 300],
    valuesCount: 2,
    valuesData: [1.5, 2.5],
    labelLength: 17,
    labelData: 'multi arrays test',
  });
}

function createMixedFields() {
  return new VariableMixedFields({
    fixedId: 0xABCD1234,
    fixedValue: 3.14,
    fixedName: 'DeviceName',
    variableDataCount: 5,
    variableDataData: [1000, 2000, 3000, 4000, 5000],
    variableDescLength: 17,
    variableDescData: 'mixed fields test',
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
