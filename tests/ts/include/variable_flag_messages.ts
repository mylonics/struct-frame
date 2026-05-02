/**
 * Variable flag test message definitions (TypeScript).
 * Provides getMessage(index) function for variable flag truncation testing.
 *
 * This file matches the C++ variable_flag_messages.hpp structure.
 */

import {
  SerializationTestTruncationTestNonVariable,
  SerializationTestTruncationTestVariable,
  SerializationTestNestedPayload,
  SerializationTestNestedVariableMessage,
} from '../../generated/ts/serialization_test.structframe';

import { FrameMsgInfo } from '../../generated/ts/frame-base';

// Type alias for message union (like C++ MessageVariant)
export type MessageType =
  | SerializationTestTruncationTestNonVariable
  | SerializationTestTruncationTestVariable
  | SerializationTestNestedVariableMessage;

// Message count
export const MESSAGE_COUNT = 3;


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

function createNestedVariable(): SerializationTestNestedVariableMessage {
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

export function getMessage(index: number): MessageType {
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

export function checkMessage(index: number, info: FrameMsgInfo): boolean {
  const expected = getMessage(index);
  const msgClass = expected.constructor as any;

  // Check msg_id matches
  if (info.msg_id !== msgClass._msgid) return false;

  // Deserialize and compare
  const decoded = msgClass.deserialize(info);
  return decoded.equals(expected);
}
