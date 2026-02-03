/**
 * Variable flag test message definitions (TypeScript).
 * Provides getMessage(index) function for variable flag truncation testing.
 *
 * This file matches the C++ variable_flag_messages.hpp structure.
 */

import {
  SerializationTestTruncationTestNonVariable,
  SerializationTestTruncationTestVariable,
} from '../../generated/ts/serialization_test.structframe';

// Type alias for message union (like C++ MessageVariant)
export type MessageType =
  | SerializationTestTruncationTestNonVariable
  | SerializationTestTruncationTestVariable;

// Message count
export const MESSAGE_COUNT = 2;


// ============================================================================
// Helper functions to create messages (like C++ create_* functions)
// ============================================================================

function createNonVariable1_3Filled(): SerializationTestTruncationTestNonVariable {
  const dataArray = Array.from({ length: 67 }, (_, i) => i);
  return new SerializationTestTruncationTestNonVariable({
    sequence_id: 0xDEADBEEF,
    data_array_count: 67,
    data_array_data: dataArray,
    footer: 0xCAFE,
  });
}

function createVariable1_3Filled(): SerializationTestTruncationTestVariable {
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

export function getMessage(index: number): MessageType {
  if (index === 0) {
    return createNonVariable1_3Filled();
  } else {
    return createVariable1_3Filled();
  }
}
