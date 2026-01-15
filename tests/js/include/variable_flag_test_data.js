/**
 * Variable flag truncation test data definitions (JavaScript).
 * Tests that messages with variable=true properly truncate unused array space.
 */

const {
  SerializationTestTruncationTestNonVariable,
  SerializationTestTruncationTestVariable,
  get_message_info,
} = require('../../generated/js/serialization_test.structframe');

/** Message count */
const MESSAGE_COUNT = 2;

/** Index tracking for encoding/validation */
let nonVarIdx = 0;
let varIdx = 0;

/** Message ID order array */
const MSG_ID_ORDER = [
  SerializationTestTruncationTestNonVariable._msgid,  // 0: Non-variable message
  SerializationTestTruncationTestVariable._msgid,     // 1: Variable message
];

/** Non-variable message array (1 message) */
function getNonVariableMessages() {
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
function getVariableMessages() {
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
function encodeMessage(writer, index) {
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

/** Validator function */
function getExpected(msgId) {
  if (msgId === SerializationTestTruncationTestNonVariable._msgid) {
    const msg = getNonVariableMessages()[nonVarIdx++];
    const data = msg.serialize();
    return { data, size: data.length };
  } else if (msgId === SerializationTestTruncationTestVariable._msgid) {
    const msg = getVariableMessages()[varIdx++];
    const data = msg.serialize();
    return { data, size: data.length };
  }
  return null;
}

/** Equality validator function */
function validateWithEquals(msgId, decodedData, decodedSize) {
  if (msgId === SerializationTestTruncationTestNonVariable._msgid) {
    const expected = getNonVariableMessages()[nonVarIdx++];
    const expectedData = expected.serialize();
    if (decodedSize !== expectedData.length) return false;
    const decoded = SerializationTestTruncationTestNonVariable.deserialize(decodedData.slice(0, decodedSize));
    return decoded.equals(expected);
  } else if (msgId === SerializationTestTruncationTestVariable._msgid) {
    const expected = getVariableMessages()[varIdx++];
    const expectedData = expected.serialize();
    if (decodedSize !== expectedData.length) return false;
    const decoded = SerializationTestTruncationTestVariable.deserialize(decodedData.slice(0, decodedSize));
    return decoded.equals(expected);
  }
  return false;
}

/** Validate decoded message using equals() method. Accepts FrameMsgInfo. */
function validateMessage(data, _index) {
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
const variableFlagTestConfig = {
  messageCount: MESSAGE_COUNT,
  bufferSize: 4096,
  formatsHelp: 'profile_bulk',
  testName: 'Variable Flag JavaScript',
  getMsgIdOrder: () => MSG_ID_ORDER,
  encodeMessage,
  getExpected,
  validateWithEquals,
  validateMessage,
  getMessageInfo: (msgId) => get_message_info(msgId),
  supportsFormat: (format) => format === 'profile_bulk',
  resetState: () => {
    nonVarIdx = 0;
    varIdx = 0;
  },
  resetIndices: () => {
    nonVarIdx = 0;
    varIdx = 0;
  },
};

module.exports = { variableFlagTestConfig };
