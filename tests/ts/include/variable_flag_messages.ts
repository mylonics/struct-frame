/**
 * Variable flag test message definitions (TypeScript).
 * Provides getMessage(index) function for variable flag truncation testing.
 *
 * This file matches the C++ variable_flag_messages.hpp structure.
 */

import {
  TruncationTestNonVariable,
  TruncationTestVariable,
  NestedPayload,
  NestedVariableMessage,
  VariableMultipleArrays,
  VariableMixedFields,
  VarEnvPayloadA,
  VarEnvPayloadB,
  VariableEnvelopeMessage,
  BasicTypesMessage,
  VariableEnvelopeMsgIdMessage,
} from '../../generated/ts/serialization-test.structframe';

import { FrameMsgInfo } from '../../generated/ts/frame-base';

// Type alias for message union (like C++ MessageVariant)
export type MessageType =
  | TruncationTestNonVariable
  | TruncationTestVariable
  | NestedVariableMessage
  | VariableMultipleArrays
  | VariableMixedFields
  | VariableEnvelopeMessage
  | VariableEnvelopeMsgIdMessage;

// Message count
export const MESSAGE_COUNT = 7;


// ============================================================================
// Helper functions to create messages (like C++ create_* functions)
// ============================================================================

function createNonVariable1_3Filled(): TruncationTestNonVariable {
  const dataArray = Array.from({ length: 67 }, (_, i) => i);
  return new TruncationTestNonVariable({
    sequenceId: 0xDEADBEEF,
    dataArrayCount: 67,
    dataArrayData: dataArray,
    footer: 0xCAFE,
  });
}

function createVariable1_3Filled(): TruncationTestVariable {
  const dataArray = Array.from({ length: 67 }, (_, i) => i);
  return new TruncationTestVariable({
    sequenceId: 0xDEADBEEF,
    dataArrayCount: 67,
    dataArrayData: dataArray,
    footer: 0xCAFE,
  });
}

function createNestedVariable(): NestedVariableMessage {
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

function createMultipleArrays(): VariableMultipleArrays {
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

function createMixedFields(): VariableMixedFields {
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

function createVariableEnvelopeFieldOrder(): VariableEnvelopeMessage {
  const payload = new VarEnvPayloadA({ code: 0x42, value: 0x1234 });
  return VariableEnvelopeMessage.wrap(payload, 7);
}

function createVariableEnvelopeMsgId(): VariableEnvelopeMsgIdMessage {
  const inner = new BasicTypesMessage({
    flag: true,
    smallUint: 0xAB,
    mediumUint: 0xCDEF,
    regularUint: 0x12345678,
  });
  return VariableEnvelopeMsgIdMessage.wrap(inner, 3);
}


// ============================================================================
// getMessage(index) - unified interface matching C++ MessageProvider pattern
// ============================================================================

export function getMessage(index: number): MessageType {
  if (index === 0) {
    return createNonVariable1_3Filled();
  } else if (index === 1) {
    return createVariable1_3Filled();
  } else if (index === 2) {
    return createNestedVariable();
  } else if (index === 3) {
    return createMultipleArrays();
  } else if (index === 4) {
    return createMixedFields();
  } else if (index === 5) {
    return createVariableEnvelopeFieldOrder();
  } else {
    return createVariableEnvelopeMsgId();
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
  if (info.msgId !== msgClass._msgid) return false;

  // Deserialize and compare
  const decoded = msgClass.deserialize(info);
  return decoded.equals(expected);
}
