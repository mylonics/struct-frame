/**
 * Variable flag truncation test data definitions (TypeScript).
 * Tests that messages with variable=true properly truncate unused array space.
 *
 * Structure:
 * - Two identical messages (TruncationTestNonVariable and TruncationTestVariable)
 * - Only difference: TruncationTestVariable has option variable = true
 * - Both have data_array filled to 1/3 capacity (67 out of 200 bytes)
 * - Tests that variable message gets truncated and non-variable does not
 */

import { TestConfig } from './test_codec';
import { MessageInfo } from '../../generated/ts/frame-profiles';
import { FrameMsgInfo } from '../../generated/ts/frame-base';
import {
  SerializationTestTruncationTestNonVariable,
  SerializationTestTruncationTestVariable,
  get_message_info,
} from '../../generated/ts/serialization_test.structframe';

/** Message count */
const MESSAGE_COUNT = 2;

/** Index tracking for encoding/validation */
let nonVarIdx = 0;
let varIdx = 0;

/** Message ID order array */
const MSG_ID_ORDER: number[] = [
  SerializationTestTruncationTestNonVariable._msgid!,  // 0: Non-variable message
  SerializationTestTruncationTestVariable._msgid!,     // 1: Variable message
];

/** Non-variable message array (1 message) */
function getNonVariableMessages(): SerializationTestTruncationTestNonVariable[] {
  const dataArray = Array.from({ length: 67 }, (_, i) => i); // 1/3 filled
  return [
    new SerializationTestTruncationTestNonVariable({
      sequence_id: 0xDEADBEEF,
      data_array_count: 67,
      data_array_data: dataArray,
      footer: 0xCAFE,
    }),
  ];
}

/** Variable message array (1 message) */
function getVariableMessages(): SerializationTestTruncationTestVariable[] {
  const dataArray = Array.from({ length: 67 }, (_, i) => i); // 1/3 filled
  return [
    new SerializationTestTruncationTestVariable({
      sequence_id: 0xDEADBEEF,
      data_array_count: 67,
      data_array_data: dataArray,
      footer: 0xCAFE,
    }),
  ];
}

/** Encoder function */
function encodeMessage(writer: any, index: number): number {
  const msgId = MSG_ID_ORDER[index];
  if (msgId === SerializationTestTruncationTestNonVariable._msgid) {
    const msg = getNonVariableMessages()[nonVarIdx++];
    const written = writer.write(msg);
    const payloadSize = msg._buffer.length;
    console.log(`MSG1: ${written} bytes (payload=${payloadSize}, no truncation)`);
    return written;
  } else if (msgId === SerializationTestTruncationTestVariable._msgid) {
    const msg = getVariableMessages()[varIdx++];
    const written = writer.write(msg);
    const payloadSize = msg._buffer.length;
    console.log(`MSG2: ${written} bytes (payload=${payloadSize}, TRUNCATED)`);
    return written;
  }
  return 0;
}

/** Validate decoded message using equals() method. Accepts FrameMsgInfo. */
function validateMessage(data: FrameMsgInfo, _index: number): boolean {
  const msgId = data.msg_id;
  if (msgId === SerializationTestTruncationTestNonVariable._msgid) {
    const expected = getNonVariableMessages()[nonVarIdx++];
    const decoded = SerializationTestTruncationTestNonVariable.deserialize(data);
    return decoded.equals(expected);
  } else if (msgId === SerializationTestTruncationTestVariable._msgid) {
    const expected = getVariableMessages()[varIdx++];
    const decoded = SerializationTestTruncationTestVariable.deserialize(data);
    return decoded.equals(expected);
  }
  return false;
}

/** Test configuration */
export const variableFlagTestConfig: TestConfig = {
  messageCount: MESSAGE_COUNT,
  bufferSize: 4096,
  formatsHelp: 'profile_bulk',
  testName: 'Variable Flag TypeScript',
  getMsgIdOrder: () => MSG_ID_ORDER,
  encodeMessage,
  validateMessage,
  getMessageInfo: (msgId: number): MessageInfo | undefined => get_message_info(msgId),
  supportsFormat: (format: string): boolean => format === 'profile_bulk',
  resetState: () => {
    nonVarIdx = 0;
    varIdx = 0;
  },
};
