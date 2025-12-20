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

// Import generated modules
const {
  BASIC_START_BYTE,
  getTinyStartByte,
  isTinyStartByte,
  getBasicSecondStartByte,
  isBasicSecondStartByte,
  fletcher_checksum,
} = require('./frame_base');

const {
  serialization_test_SerializationTestMessage,
  serialization_test_SerializationTestMessage_msgid,
  serialization_test_SerializationTestMessage_max_size
} = require('./serialization_test.sf');

/* Minimal frame format helper classes (replacing frame_compat) */

class BasicDefault {
  static encodeMsg(msgId: number, msg: Uint8Array): Uint8Array {
    const headerSize = 4;
    const footerSize = 2;
    const totalSize = headerSize + msg.length + footerSize;
    if (msg.length > 255) return new Uint8Array(0);
    
    const buffer = new Uint8Array(totalSize);
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = getBasicSecondStartByte(1); // DEFAULT = 1
    buffer[2] = msg.length;
    buffer[3] = msgId;
    buffer.set(msg, headerSize);
    
    const ck = fletcher_checksum(buffer, 2, headerSize + msg.length);
    buffer[totalSize - 2] = ck[0];
    buffer[totalSize - 1] = ck[1];
    return buffer;
  }
  
  static validatePacket(buffer: Uint8Array): any {
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
}

class TinyMinimal {
  static encodeMsg(msgId: number, msg: Uint8Array): Uint8Array {
    const headerSize = 2;
    const buffer = new Uint8Array(headerSize + msg.length);
    buffer[0] = getTinyStartByte(0); // MINIMAL = 0
    buffer[1] = msgId;
    buffer.set(msg, headerSize);
    return buffer;
  }
  
  static validatePacket(buffer: Uint8Array): any {
    if (buffer.length < 2 || !isTinyStartByte(buffer[0])) {
      return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
    }
    const msgId = buffer[1];
    const msgLen = buffer.length - 2;
    return {
      valid: true,
      msg_id: msgId,
      msg_len: msgLen,
      msg_data: buffer.slice(2),
    };
  }
}

class BasicExtended {
  static encodeMsg(msgId: number, msg: Uint8Array): Uint8Array {
    const headerSize = 6;
    const footerSize = 2;
    const totalSize = headerSize + msg.length + footerSize;
    if (msg.length > 65535) return new Uint8Array(0);
    
    const buffer = new Uint8Array(totalSize);
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = getBasicSecondStartByte(4); // EXTENDED = 4
    buffer[2] = msg.length & 0xff;
    buffer[3] = (msg.length >> 8) & 0xff;
    buffer[4] = 0; // PKG_ID
    buffer[5] = msgId;
    buffer.set(msg, headerSize);
    
    const ck = fletcher_checksum(buffer, 2, headerSize + msg.length);
    buffer[totalSize - 2] = ck[0];
    buffer[totalSize - 1] = ck[1];
    return buffer;
  }
  
  static validatePacket(buffer: Uint8Array): any {
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
}

class BasicExtendedMultiSystemStream {
  static encodeMsg(msgId: number, msg: Uint8Array): Uint8Array {
    const headerSize = 9;
    const footerSize = 2;
    const totalSize = headerSize + msg.length + footerSize;
    if (msg.length > 65535) return new Uint8Array(0);
    
    const buffer = new Uint8Array(totalSize);
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = getBasicSecondStartByte(8); // EXTENDED_MULTI_SYSTEM_STREAM = 8
    buffer[2] = 0; // SEQ
    buffer[3] = 0; // SYS_ID
    buffer[4] = 0; // COMP_ID
    buffer[5] = msg.length & 0xff;
    buffer[6] = (msg.length >> 8) & 0xff;
    buffer[7] = 0; // PKG_ID
    buffer[8] = msgId;
    buffer.set(msg, headerSize);
    
    const ck = fletcher_checksum(buffer, 2, headerSize + msg.length);
    buffer[totalSize - 2] = ck[0];
    buffer[totalSize - 1] = ck[1];
    return buffer;
  }
  
  static validatePacket(buffer: Uint8Array): any {
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
}

class BasicMinimal {
  static encodeMsg(msgId: number, msg: Uint8Array): Uint8Array {
    const headerSize = 3;
    const buffer = new Uint8Array(headerSize + msg.length);
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = getBasicSecondStartByte(0); // MINIMAL = 0
    buffer[2] = msgId;
    buffer.set(msg, headerSize);
    return buffer;
  }
  
  static validatePacket(buffer: Uint8Array): any {
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
}

class TinyDefault {
  static encodeMsg(msgId: number, msg: Uint8Array): Uint8Array {
    const headerSize = 3;
    const footerSize = 2;
    const totalSize = headerSize + msg.length + footerSize;
    if (msg.length > 255) return new Uint8Array(0);
    
    const buffer = new Uint8Array(totalSize);
    buffer[0] = getTinyStartByte(1); // DEFAULT = 1
    buffer[1] = msg.length;
    buffer[2] = msgId;
    buffer.set(msg, headerSize);
    
    const ck = fletcher_checksum(buffer, 1, headerSize + msg.length);
    buffer[totalSize - 2] = ck[0];
    buffer[totalSize - 1] = ck[1];
    return buffer;
  }
  
  static validatePacket(buffer: Uint8Array): any {
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
}

/**
 * Get the parser class for a frame format or profile.
 */
export function getParserClass(formatName: string): any {
  const formatMap: { [key: string]: any } = {
    // Profile names (preferred)
    'profile_standard': BasicDefault,
    'profile_sensor': TinyMinimal,
    'profile_bulk': BasicExtended,
    'profile_network': BasicExtendedMultiSystemStream,
    // Legacy direct format names (for backward compatibility)
    'basic_default': BasicDefault,
    'basic_minimal': BasicMinimal,
    'tiny_default': TinyDefault,
    'tiny_minimal': TinyMinimal,
    'basic_extended': BasicExtended,
    'basic_extended_multi_system_stream': BasicExtendedMultiSystemStream,
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
