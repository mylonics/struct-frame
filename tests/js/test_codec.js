/**
 * Test codec - Encode/decode functions for all frame formats (JavaScript).
 */
"use strict";

const path = require('path');

// Expected test values (from expected_values.json)
const EXPECTED_VALUES = {
  magic_number: 3735928559,  // 0xDEADBEEF
  test_string: 'Cross-platform test!',
  test_float: 3.14159,
  test_bool: true,
  test_array: [100, 200, 300],
};

/**
 * Get the parser class for a frame format or profile.
 */
function getParserClass(formatName) {
  const formatMap = {
    // Profile names (preferred)
    'profile_standard': 'BasicDefault',
    'profile_sensor': 'TinyMinimal',
    'profile_bulk': 'BasicExtended',
    'profile_network': 'BasicExtendedMultiSystemStream',
    // Legacy direct format names
    'basic_default': 'BasicDefault',
    'basic_minimal': 'BasicMinimal',
    'tiny_default': 'TinyDefault',
    'tiny_minimal': 'TinyMinimal',
    'basic_extended': 'BasicExtended',
    'basic_extended_multi_system_stream': 'BasicExtendedMultiSystemStream',
  };

  const className = formatMap[formatName];
  if (!className) {
    throw new Error(`Unknown frame format: ${formatName}`);
  }

  const module = require('./frame_compat');
  return module[className];
}

/**
 * Get the message struct and metadata.
 */
function getMessageInfo() {
  const module = require('./serialization_test.sf');
  return {
    struct: module.serialization_test_SerializationTestMessage,
    msgId: module.serialization_test_SerializationTestMessage_msgid,
    maxSize: module.serialization_test_SerializationTestMessage_max_size,
  };
}

/**
 * Create a test message with expected values.
 */
function createTestMessage(msgStruct) {
  const size = msgStruct._size || msgStruct.getSize();
  const buffer = Buffer.alloc(size);
  const msg = new msgStruct(buffer);

  msg.magic_number = EXPECTED_VALUES.magic_number;
  msg.test_string_length = EXPECTED_VALUES.test_string.length;
  msg.test_string_data = EXPECTED_VALUES.test_string;
  msg.test_float = EXPECTED_VALUES.test_float;
  msg.test_bool = EXPECTED_VALUES.test_bool;
  msg.test_array_count = EXPECTED_VALUES.test_array.length;

  for (let i = 0; i < EXPECTED_VALUES.test_array.length; i++) {
    msg.test_array_data[i] = EXPECTED_VALUES.test_array[i];
  }

  return { msg, buffer };
}

/**
 * Validate that a decoded message matches expected values.
 */
function validateTestMessage(msg) {
  const errors = [];

  if (msg.magic_number !== EXPECTED_VALUES.magic_number) {
    errors.push(`magic_number: expected ${EXPECTED_VALUES.magic_number}, got ${msg.magic_number}`);
  }

  const testString = msg.test_string_data.substring(0, msg.test_string_length);
  if (testString !== EXPECTED_VALUES.test_string) {
    errors.push(`test_string: expected '${EXPECTED_VALUES.test_string}', got '${testString}'`);
  }

  if (Math.abs(msg.test_float - EXPECTED_VALUES.test_float) > 0.0001) {
    errors.push(`test_float: expected ${EXPECTED_VALUES.test_float}, got ${msg.test_float}`);
  }

  if (msg.test_bool !== EXPECTED_VALUES.test_bool) {
    errors.push(`test_bool: expected ${EXPECTED_VALUES.test_bool}, got ${msg.test_bool}`);
  }

  const arrayCount = msg.test_array_count;
  if (arrayCount !== EXPECTED_VALUES.test_array.length) {
    errors.push(`test_array.count: expected ${EXPECTED_VALUES.test_array.length}, got ${arrayCount}`);
  } else {
    for (let i = 0; i < arrayCount; i++) {
      if (msg.test_array_data[i] !== EXPECTED_VALUES.test_array[i]) {
        errors.push(`test_array[${i}]: expected ${EXPECTED_VALUES.test_array[i]}, got ${msg.test_array_data[i]}`);
      }
    }
  }

  if (errors.length > 0) {
    for (const error of errors) {
      console.log(`  Value mismatch: ${error}`);
    }
    return false;
  }

  return true;
}

/**
 * Encode a test message using the specified frame format.
 */
function encodeTestMessage(formatName) {
  const ParserClass = getParserClass(formatName);
  const msgInfo = getMessageInfo();

  const { msg, buffer } = createTestMessage(msgInfo.struct);

  // Use static encode method
  return ParserClass.encode(msgInfo.msgId, buffer);
}

/**
 * Decode a test message using the specified frame format.
 */
function decodeTestMessage(formatName, data) {
  const ParserClass = getParserClass(formatName);
  const msgInfo = getMessageInfo();

  // Use static validate_packet method
  const result = ParserClass.validate_packet(data);

  if (!result || !result.valid) {
    return null;
  }

  // Create message object from decoded data
  const msg = new msgInfo.struct(Buffer.from(result.msg_data));
  return msg;
}

module.exports = {
  EXPECTED_VALUES,
  createTestMessage,
  validateTestMessage,
  encodeTestMessage,
  decodeTestMessage,
  getParserClass,
  getMessageInfo,
};
