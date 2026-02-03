/**
 * Variable flag test message definitions (JavaScript).
 * Provides getMessage(index) function for variable flag truncation testing.
 *
 * This file matches the C++ variable_flag_messages.hpp structure.
 */

const {
  SerializationTestTruncationTestNonVariable,
  SerializationTestTruncationTestVariable,
} = require('../../generated/js/serialization_test.structframe');

// Message count
const MESSAGE_COUNT = 2;


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


// ============================================================================
// getMessage(index) - unified interface matching C++ MessageProvider pattern
// ============================================================================

function getMessage(index) {
  if (index === 0) {
    return createNonVariable1_3Filled();
  } else {
    return createVariable1_3Filled();
  }
}

module.exports = {
  MESSAGE_COUNT,
  getMessage,
};
