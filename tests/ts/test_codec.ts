/**
 * Test codec - Encode/decode functions for all frame formats (TypeScript).
 */
import * as fs from 'fs';
import * as path from 'path';

// Expected test values (from expected_values.json)
export const EXPECTED_VALUES = {
  magic_number: 3735928559,  // 0xDEADBEEF
  test_string: 'Cross-platform test!',
  test_float: 3.14159,
  test_bool: true,
  test_array: [100, 200, 300] as number[],
};

// Import generated modules dynamically
const { BasicDefault } = require('./BasicDefault');
const { BasicMinimal } = require('./BasicMinimal');
const { TinyDefault } = require('./TinyDefault');
const { TinyMinimal } = require('./TinyMinimal');
const {
  serialization_test_SerializationTestMessage,
  serialization_test_SerializationTestMessage_msgid,
  serialization_test_SerializationTestMessage_max_size
} = require('./serialization_test.sf');

/**
 * Get the parser class for a frame format.
 */
export function getParserClass(formatName: string): any {
  const formatMap: { [key: string]: any } = {
    'basic_default': BasicDefault,
    'basic_minimal': BasicMinimal,
    'tiny_default': TinyDefault,
    'tiny_minimal': TinyMinimal,
  };

  const ParserClass = formatMap[formatName];
  if (!ParserClass) {
    throw new Error(`Unknown frame format: ${formatName}`);
  }

  return ParserClass;
}

/**
 * Get the message struct and metadata.
 */
export function getMessageInfo() {
  return {
    struct: serialization_test_SerializationTestMessage,
    msgId: serialization_test_SerializationTestMessage_msgid,
    maxSize: serialization_test_SerializationTestMessage_max_size,
  };
}

/**
 * Create a test message with expected values.
 */
export function createTestMessage(msgStruct: any): { msg: any; buffer: Buffer } {
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
export function validateTestMessage(msg: any): boolean {
  const errors: string[] = [];

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
export function encodeTestMessage(formatName: string): Buffer {
  const ParserClass = getParserClass(formatName);
  const msgInfo = getMessageInfo();

  const { msg, buffer } = createTestMessage(msgInfo.struct);

  // Use static encodeMsg method (TypeScript version uses camelCase)
  return Buffer.from(ParserClass.encodeMsg(msgInfo.msgId, buffer));
}

/**
 * Decode a test message using the specified frame format.
 */
export function decodeTestMessage(formatName: string, data: Buffer): any | null {
  const ParserClass = getParserClass(formatName);
  const msgInfo = getMessageInfo();

  // Use static validatePacket method (TypeScript version uses camelCase)
  const result = ParserClass.validatePacket(data);

  if (!result || !result.valid) {
    return null;
  }

  // Create message object from decoded data
  const msg = new msgInfo.struct(Buffer.from(result.msg_data));
  return msg;
}
