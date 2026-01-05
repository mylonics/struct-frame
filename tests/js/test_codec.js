/**
 * Test codec - Encode/decode functions for all frame formats (JavaScript).
 */
"use strict";

const path = require('path');

// Expected test values (from expected_values.json) - first message for backwards compatibility
const EXPECTED_VALUES = {
  magic_number: 3735928559,  // 0xDEADBEEF
  test_string: 'Cross-platform test!',
  test_float: 3.14159,
  test_bool: true,
  test_array: [100, 200, 300],
};

// Hardcoded test messages matching test_messages.json
const TEST_MESSAGES = [
  // basic_values
  {
    magic_number: 3735928559,  // 0xDEADBEEF
    test_string: 'Cross-platform test!',
    test_float: 3.14159,
    test_bool: true,
    test_array: [100, 200, 300],
  },
  // zero_values
  {
    magic_number: 0,
    test_string: '',
    test_float: 0.0,
    test_bool: false,
    test_array: [],
  },
  // max_values
  {
    magic_number: 4294967295,  // 0xFFFFFFFF
    test_string: 'Maximum length test string for coverage!',
    test_float: 999999.9,
    test_bool: true,
    test_array: [2147483647, -2147483648, 0, 1, -1],
  },
  // negative_values
  {
    magic_number: 2863311530,  // 0xAAAAAAAA
    test_string: 'Negative test',
    test_float: -273.15,
    test_bool: false,
    test_array: [-100, -200, -300, -400],
  },
  // special_chars
  {
    magic_number: 1234567890,  // 0x499602D2
    test_string: 'Special: !@#$%^&*()',
    test_float: 2.71828,
    test_bool: true,
    test_array: [0, 1, 1, 2, 3],
  },
];

// Import frame base functions
const { BASIC_START_BYTE } = require('./frame_headers/base');
const {
  getTinyStartByte,
  isTinyStartByte,
} = require('./frame_headers/header_tiny');
const {
  getBasicSecondStartByte,
  isBasicSecondStartByte,
} = require('./frame_headers/header_basic');
const { fletcher_checksum } = require('./frame_base');

/* Minimal frame format helper classes (replacing frame_compat) */

const BasicDefault = {
  encodeMsg: function (msgId, msg) {
    const headerSize = 4;
    const footerSize = 2;
    const totalSize = headerSize + msg.length + footerSize;
    if (msg.length > 255) return new Uint8Array(0);

    const buffer = new Uint8Array(totalSize);
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = getBasicSecondStartByte(1);
    buffer[2] = msg.length;
    buffer[3] = msgId;
    buffer.set(msg, headerSize);

    const ck = fletcher_checksum(buffer, 2, headerSize + msg.length);
    buffer[totalSize - 2] = ck[0];
    buffer[totalSize - 1] = ck[1];
    return buffer;
  },

  validatePacket: function (buffer) {
    if (buffer.length < 6 || buffer[0] !== BASIC_START_BYTE || !isBasicSecondStartByte(buffer[1])) {
      return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
    }
    const msgLen = buffer[2];
    const msgId = buffer[3];
    const totalSize = 4 + msgLen + 2;
    if (buffer.length < totalSize) {
      return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
    }
    const ck = fletcher_checksum(buffer, 2, 4 + msgLen);
    if (ck[0] === buffer[totalSize - 2] && ck[1] === buffer[totalSize - 1]) {
      return {
        valid: true,
        msg_id: msgId,
        msg_len: msgLen,
        msg_data: buffer.slice(4, 4 + msgLen),
      };
    }
    return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
  }
};

const TinyMinimal = {
  encodeMsg: function (msgId, msg) {
    const headerSize = 2;
    const buffer = new Uint8Array(headerSize + msg.length);
    buffer[0] = getTinyStartByte(0);
    buffer[1] = msgId;
    buffer.set(msg, headerSize);
    return buffer;
  },

  validatePacket: function (buffer) {
    if (buffer.length < 2 || !isTinyStartByte(buffer[0])) {
      return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
    }
    const msgId = buffer[1];
    // For minimal payloads, we need to know the message size (use known max size)
    const msgInfo = getMessageInfo();
    const msgLen = msgInfo.maxSize;
    const totalSize = 2 + msgLen;
    if (buffer.length < totalSize) {
      return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
    }
    return {
      valid: true,
      msg_id: msgId,
      msg_len: msgLen,
      msg_data: buffer.slice(2, 2 + msgLen),
    };
  }
};

const NoneMinimal = {
  encodeMsg: function (msgId, msg) {
    const headerSize = 1;
    const buffer = new Uint8Array(headerSize + msg.length);
    buffer[0] = msgId;
    buffer.set(msg, headerSize);
    return buffer;
  },

  validatePacket: function (buffer) {
    if (buffer.length < 1) {
      return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
    }
    const msgId = buffer[0];
    // For minimal payloads, we need to know the message size (use known max size)
    const msgInfo = getMessageInfo();
    const msgLen = msgInfo.maxSize;
    const totalSize = 1 + msgLen;
    if (buffer.length < totalSize) {
      return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
    }
    return {
      valid: true,
      msg_id: msgId,
      msg_len: msgLen,
      msg_data: buffer.slice(1, 1 + msgLen),
    };
  }
};

const BasicExtended = {
  encodeMsg: function (msgId, msg) {
    const headerSize = 6;
    const footerSize = 2;
    const totalSize = headerSize + msg.length + footerSize;
    if (msg.length > 65535) return new Uint8Array(0);

    const buffer = new Uint8Array(totalSize);
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = getBasicSecondStartByte(4);
    buffer[2] = msg.length & 0xff;
    buffer[3] = (msg.length >> 8) & 0xff;
    buffer[4] = 0;
    buffer[5] = msgId;
    buffer.set(msg, headerSize);

    const ck = fletcher_checksum(buffer, 2, headerSize + msg.length);
    buffer[totalSize - 2] = ck[0];
    buffer[totalSize - 1] = ck[1];
    return buffer;
  },

  validatePacket: function (buffer) {
    if (buffer.length < 8 || buffer[0] !== BASIC_START_BYTE || !isBasicSecondStartByte(buffer[1])) {
      return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
    }
    const msgLen = buffer[2] | (buffer[3] << 8);
    const msgId = buffer[5];
    const totalSize = 6 + msgLen + 2;
    if (buffer.length < totalSize) {
      return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
    }
    const ck = fletcher_checksum(buffer, 2, 6 + msgLen);
    if (ck[0] === buffer[totalSize - 2] && ck[1] === buffer[totalSize - 1]) {
      return {
        valid: true,
        msg_id: msgId,
        msg_len: msgLen,
        msg_data: buffer.slice(6, 6 + msgLen),
      };
    }
    return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
  }
};

const BasicExtendedMultiSystemStream = {
  encodeMsg: function (msgId, msg) {
    const headerSize = 9;
    const footerSize = 2;
    const totalSize = headerSize + msg.length + footerSize;
    if (msg.length > 65535) return new Uint8Array(0);

    const buffer = new Uint8Array(totalSize);
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = getBasicSecondStartByte(8);
    buffer[2] = 0;
    buffer[3] = 0;
    buffer[4] = 0;
    buffer[5] = msg.length & 0xff;
    buffer[6] = (msg.length >> 8) & 0xff;
    buffer[7] = 0;
    buffer[8] = msgId;
    buffer.set(msg, headerSize);

    const ck = fletcher_checksum(buffer, 2, headerSize + msg.length);
    buffer[totalSize - 2] = ck[0];
    buffer[totalSize - 1] = ck[1];
    return buffer;
  },

  validatePacket: function (buffer) {
    if (buffer.length < 11 || buffer[0] !== BASIC_START_BYTE || !isBasicSecondStartByte(buffer[1])) {
      return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
    }
    const msgLen = buffer[5] | (buffer[6] << 8);
    const msgId = buffer[8];
    const totalSize = 9 + msgLen + 2;
    if (buffer.length < totalSize) {
      return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
    }
    const ck = fletcher_checksum(buffer, 2, 9 + msgLen);
    if (ck[0] === buffer[totalSize - 2] && ck[1] === buffer[totalSize - 1]) {
      return {
        valid: true,
        msg_id: msgId,
        msg_len: msgLen,
        msg_data: buffer.slice(9, 9 + msgLen),
      };
    }
    return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
  }
};

const BasicMinimal = {
  encodeMsg: function (msgId, msg) {
    const headerSize = 3;
    const buffer = new Uint8Array(headerSize + msg.length);
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = getBasicSecondStartByte(0);
    buffer[2] = msgId;
    buffer.set(msg, headerSize);
    return buffer;
  },

  validatePacket: function (buffer) {
    if (buffer.length < 3 || buffer[0] !== BASIC_START_BYTE || !isBasicSecondStartByte(buffer[1])) {
      return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
    }
    const msgId = buffer[2];
    const msgLen = buffer.length - 3;
    return {
      valid: true,
      msg_id: msgId,
      msg_len: msgLen,
      msg_data: buffer.slice(3),
    };
  }
};

const TinyDefault = {
  encodeMsg: function (msgId, msg) {
    const headerSize = 3;
    const footerSize = 2;
    const totalSize = headerSize + msg.length + footerSize;
    if (msg.length > 255) return new Uint8Array(0);

    const buffer = new Uint8Array(totalSize);
    buffer[0] = getTinyStartByte(1);
    buffer[1] = msg.length;
    buffer[2] = msgId;
    buffer.set(msg, headerSize);

    const ck = fletcher_checksum(buffer, 1, headerSize + msg.length);
    buffer[totalSize - 2] = ck[0];
    buffer[totalSize - 1] = ck[1];
    return buffer;
  },

  validatePacket: function (buffer) {
    if (buffer.length < 5 || !isTinyStartByte(buffer[0])) {
      return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
    }
    const msgLen = buffer[1];
    const msgId = buffer[2];
    const totalSize = 3 + msgLen + 2;
    if (buffer.length < totalSize) {
      return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
    }
    const ck = fletcher_checksum(buffer, 1, 3 + msgLen);
    if (ck[0] === buffer[totalSize - 2] && ck[1] === buffer[totalSize - 1]) {
      return {
        valid: true,
        msg_id: msgId,
        msg_len: msgLen,
        msg_data: buffer.slice(3, 3 + msgLen),
      };
    }
    return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
  }
};

/**
 * Get the parser class for a frame format or profile.
 */
function getParserClass(formatName) {
  const formatMap = {
    // Profile names (preferred)
    'profile_standard': BasicDefault,
    'profile_sensor': TinyMinimal,
    'profile_ipc': NoneMinimal,
    'profile_bulk': BasicExtended,
    'profile_network': BasicExtendedMultiSystemStream,
  };

  const parserClass = formatMap[formatName];
  if (!parserClass) {
    throw new Error(`Unknown frame format: ${formatName}`);
  }

  return parserClass;
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
 * Create message from test data
 */
function createMessageFromData(msgStruct, testData) {
  const size = msgStruct._size || msgStruct.getSize();
  const buffer = Buffer.alloc(size);
  const msg = new msgStruct(buffer);

  msg.magic_number = testData.magic_number;
  msg.test_string_length = testData.test_string.length;
  msg.test_string_data = testData.test_string;
  msg.test_float = testData.test_float;
  msg.test_bool = testData.test_bool;
  msg.test_array_count = testData.test_array.length;
  msg.test_array_data = testData.test_array; // Set the whole array at once

  // Return the message's internal buffer which has been updated
  return { msg, buffer: msg._buffer };
}

/**
 * Validate message against test data
 */
function validateMessageAgainstData(msg, testData) {
  const errors = [];

  if (msg.magic_number !== testData.magic_number) {
    errors.push(`magic_number: expected ${testData.magic_number}, got ${msg.magic_number}`);
  }

  const testString = msg.test_string_data.substring(0, msg.test_string_length);
  if (testString !== testData.test_string) {
    errors.push(`test_string: expected '${testData.test_string}', got '${testString}'`);
  }

  if (Math.abs(msg.test_float - testData.test_float) > 0.1) {
    errors.push(`test_float: expected ${testData.test_float}, got ${msg.test_float}`);
  }

  if (msg.test_bool !== testData.test_bool) {
    errors.push(`test_bool: expected ${testData.test_bool}, got ${msg.test_bool}`);
  }

  const arrayCount = msg.test_array_count;
  if (arrayCount !== testData.test_array.length) {
    errors.push(`test_array.count: expected ${testData.test_array.length}, got ${arrayCount}`);
  } else {
    for (let i = 0; i < arrayCount; i++) {
      if (msg.test_array_data[i] !== testData.test_array[i]) {
        errors.push(`test_array[${i}]: expected ${testData.test_array[i]}, got ${msg.test_array_data[i]}`);
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
 * Encode multiple test messages using the specified frame format.
 */
function encodeTestMessage(formatName) {
  const ParserClass = getParserClass(formatName);
  const msgInfo = getMessageInfo();

  const encodedBuffers = [];

  for (const testData of TEST_MESSAGES) {
    const { msg, buffer } = createMessageFromData(msgInfo.struct, testData);
    const encoded = ParserClass.encodeMsg(msgInfo.msgId, buffer);
    if (!encoded || encoded.length === 0) {
      console.log('  Encoding failed for message');
      return Buffer.alloc(0);
    }
    encodedBuffers.push(encoded);
  }

  // Concatenate all encoded messages
  return Buffer.concat(encodedBuffers);
}

/**
 * Decode and validate multiple test messages using the specified frame format.
 * Returns the number of messages successfully decoded.
 */
function decodeTestMessage(formatName, data) {
  const ParserClass = getParserClass(formatName);
  const msgInfo = getMessageInfo();

  let offset = 0;
  let messageCount = 0;

  while (offset < data.length && messageCount < TEST_MESSAGES.length) {
    // Extract remaining data
    const remainingData = data.slice(offset);

    // Use static validatePacket method
    const result = ParserClass.validatePacket(remainingData);

    if (!result || !result.valid) {
      console.log(`  Decoding failed for message ${messageCount}`);
      return messageCount;
    }

    // Create message object from decoded data
    const msg = new msgInfo.struct(Buffer.from(result.msg_data));

    // Validate the message against test data
    if (!validateMessageAgainstData(msg, TEST_MESSAGES[messageCount])) {
      console.log(`  Validation failed for message ${messageCount}`);
      return messageCount;
    }

    // Calculate message size based on format
    let msgSize = 0;
    if (formatName === 'profile_standard') {
      msgSize = 4 + result.msg_len + 2; // header + payload + crc
    } else if (formatName === 'profile_sensor') {
      msgSize = 2 + result.msg_len; // header + payload
    } else if (formatName === 'profile_ipc') {
      msgSize = 1 + result.msg_len; // header + payload
    } else if (formatName === 'profile_bulk') {
      msgSize = 6 + result.msg_len + 2; // header + payload + crc
    } else if (formatName === 'profile_network') {
      msgSize = 9 + result.msg_len + 2; // header + payload + crc
    }

    offset += msgSize;
    messageCount++;
  }

  if (messageCount !== TEST_MESSAGES.length) {
    console.log(`  Expected ${TEST_MESSAGES.length} messages, but decoded ${messageCount}`);
    return messageCount;
  }

  if (offset !== data.length) {
    console.log(`  Extra data after messages: processed ${offset} bytes, got ${data.length} bytes`);
    return messageCount;
  }

  return messageCount;
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
