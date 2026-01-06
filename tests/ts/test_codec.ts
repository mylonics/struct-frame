/**
 * Test codec - Encode/decode functions for all frame formats (TypeScript).
 */
import * as fs from 'fs';
import * as path from 'path';

// Test message interface
export interface TestMessage {
  name: string;
  magic_number: number;
  test_string: string;
  test_float: number;
  test_bool: boolean;
  test_array: number[];
}

// Load test messages from JSON
export function loadTestMessages(): TestMessage[] {
  const possiblePaths = [
    path.join(__dirname, '..', '..', '..', 'test_messages.json'),
    path.join(__dirname, '..', '..', 'test_messages.json'),
    path.join(__dirname, '..', 'test_messages.json'),
    'test_messages.json',
    '../test_messages.json',
  ];

  for (const filePath of possiblePaths) {
    try {
      if (fs.existsSync(filePath)) {
        const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        // Return SerializationTestMessage data for backwards compatibility
        return (data.SerializationTestMessage || data.messages || []) as TestMessage[];
      }
    } catch (e) {
      // Continue to next path
    }
  }

  throw new Error('Could not find test_messages.json');
}

// Load mixed messages from JSON following MixedMessages sequence
export function loadMixedMessages(): any[] {
  const possiblePaths = [
    path.join(__dirname, '..', '..', '..', 'test_messages.json'),
    path.join(__dirname, '..', '..', 'test_messages.json'),
    path.join(__dirname, '..', 'test_messages.json'),
    'test_messages.json',
    '../test_messages.json',
  ];

  for (const filePath of possiblePaths) {
    try {
      if (fs.existsSync(filePath)) {
        const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        const mixedArray = data.MixedMessages || [];
        const serialMsgs = data.SerializationTestMessage || [];
        const basicMsgs = data.BasicTypesMessage || [];
        
        const messages = [];
        for (const item of mixedArray) {
          const msgType = item.type;
          const msgName = item.name;
          
          let msgData = null;
          if (msgType === 'SerializationTestMessage') {
            msgData = serialMsgs.find((m: any) => m.name === msgName);
            if (msgData) {
              messages.push({ type: 'SerializationTestMessage', data: msgData });
            }
          } else if (msgType === 'BasicTypesMessage') {
            msgData = basicMsgs.find((m: any) => m.name === msgName);
            if (msgData) {
              messages.push({ type: 'BasicTypesMessage', data: msgData });
            }
          }
        }
        
        return messages;
      }
    } catch (e) {
      // Continue to next path
    }
  }

  throw new Error('Could not find test_messages.json');
}


// Load test messages at module initialization
const TEST_MESSAGES: TestMessage[] = loadTestMessages();

// Expected test values (from test_messages.json) - first message for backwards compatibility
export const EXPECTED_VALUES = TEST_MESSAGES.length > 0 ? {
  magic_number: TEST_MESSAGES[0].magic_number,
  test_string: TEST_MESSAGES[0].test_string,
  test_float: TEST_MESSAGES[0].test_float,
  test_bool: TEST_MESSAGES[0].test_bool,
  test_array: TEST_MESSAGES[0].test_array as number[],
} : {
  magic_number: 0,
  test_string: '',
  test_float: 0.0,
  test_bool: false,
  test_array: [] as number[],
};


// Import generated frame profile functions
import {
  ProfileStandard,
  ProfileSensor,
  ProfileIPC,
  ProfileBulk,
  ProfileNetwork,
  ProfileParser,
} from './frame_profiles';

const {
  serialization_test_SerializationTestMessage,
  serialization_test_SerializationTestMessage_msgid,
  serialization_test_SerializationTestMessage_max_size,
  serialization_test_BasicTypesMessage,
  serialization_test_BasicTypesMessage_msgid,
  serialization_test_BasicTypesMessage_max_size,
  get_message_length
} = require('./serialization_test.sf');

// Helper to get message length for minimal payloads
function getMsgLength(msgId: number): number | undefined {
  return get_message_length(msgId);
}

// Wrap ProfileSensor and ProfileIPC to include getMsgLength callback
const ProfileSensorWithLength: ProfileParser = {
  config: ProfileSensor.config,
  encodeMsg: ProfileSensor.encodeMsg.bind(ProfileSensor),
  validatePacket: function(buffer: Uint8Array) {
    return ProfileSensor.validatePacket(buffer, getMsgLength);
  }
};

const ProfileIPCWithLength: ProfileParser = {
  config: ProfileIPC.config,
  encodeMsg: ProfileIPC.encodeMsg.bind(ProfileIPC),
  validatePacket: function(buffer: Uint8Array) {
    return ProfileIPC.validatePacket(buffer, getMsgLength);
  }
};

/**
 * Get the parser class for a frame format or profile.
 */
export function getParserClass(formatName: string): any {
  const formatMap: { [key: string]: any } = {
    // Profile names (preferred) - using generated profile functions
    'profile_standard': ProfileStandard,
    'profile_sensor': ProfileSensorWithLength,
    'profile_ipc': ProfileIPCWithLength,
    'profile_bulk': ProfileBulk,
    'profile_network': ProfileNetwork,
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
 * Get message info for BasicTypesMessage
 */
export function getBasicTypesMessageInfo() {
  return {
    struct: serialization_test_BasicTypesMessage,
    msgId: serialization_test_BasicTypesMessage_msgid,
    maxSize: serialization_test_BasicTypesMessage_max_size,
  };
}

/**
 * Create BasicTypesMessage from test data
 */
export function createBasicTypesMessageFromData(msgStruct: any, testData: any): { msg: any; buffer: Buffer } {
  const size = msgStruct._size || msgStruct.getSize();
  const buffer = Buffer.alloc(size);
  const msg = new msgStruct(buffer);

  msg.small_int = testData.small_int;
  msg.medium_int = testData.medium_int;
  msg.regular_int = testData.regular_int;
  msg.large_int = testData.large_int;
  msg.small_uint = testData.small_uint;
  msg.medium_uint = testData.medium_uint;
  msg.regular_uint = testData.regular_uint;
  msg.large_uint = testData.large_uint;
  msg.single_precision = testData.single_precision;
  msg.double_precision = testData.double_precision;
  msg.flag = testData.flag;
  msg.device_id = testData.device_id;
  msg.description_length = testData.description.length;
  msg.description_data = testData.description;

  return { msg, buffer: (msg as any)._buffer };
}

/**
 * Validate BasicTypesMessage against test data
 */
export function validateBasicTypesMessageAgainstData(msg: any, testData: any): boolean {
  const errors: string[] = [];

  if (msg.small_int !== testData.small_int) {
    errors.push(`small_int: expected ${testData.small_int}, got ${msg.small_int}`);
  }
  if (msg.medium_int !== testData.medium_int) {
    errors.push(`medium_int: expected ${testData.medium_int}, got ${msg.medium_int}`);
  }
  if (msg.regular_int !== testData.regular_int) {
    errors.push(`regular_int: expected ${testData.regular_int}, got ${msg.regular_int}`);
  }
  // Skip large_int validation for very large values due to JSON precision
  if (Math.abs(testData.large_int) < 9e18 && msg.large_int != testData.large_int) {
    errors.push(`large_int: expected ${testData.large_int}, got ${msg.large_int}`);
  }
  if (msg.small_uint !== testData.small_uint) {
    errors.push(`small_uint: expected ${testData.small_uint}, got ${msg.small_uint}`);
  }
  if (msg.medium_uint !== testData.medium_uint) {
    errors.push(`medium_uint: expected ${testData.medium_uint}, got ${msg.medium_uint}`);
  }
  if (msg.regular_uint !== testData.regular_uint) {
    errors.push(`regular_uint: expected ${testData.regular_uint}, got ${msg.regular_uint}`);
  }
  // Skip large_uint validation for very large values due to JSON precision
  if (testData.large_uint < 9e18 && msg.large_uint != testData.large_uint) {
    errors.push(`large_uint: expected ${testData.large_uint}, got ${msg.large_uint}`);
  }

  if (Math.abs(msg.single_precision - testData.single_precision) > 0.01) {
    errors.push(`single_precision: expected ${testData.single_precision}, got ${msg.single_precision}`);
  }
  if (Math.abs(msg.double_precision - testData.double_precision) > 0.000001) {
    errors.push(`double_precision: expected ${testData.double_precision}, got ${msg.double_precision}`);
  }

  if (msg.flag !== testData.flag) {
    errors.push(`flag: expected ${testData.flag}, got ${msg.flag}`);
  }

  if (msg.device_id !== testData.device_id) {
    errors.push(`device_id: expected ${testData.device_id}, got ${msg.device_id}`);
  }

  const description = msg.description_data.substring(0, msg.description_length);
  if (description !== testData.description) {
    errors.push(`description: expected '${testData.description}', got '${description}'`);
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
 * Create message from test data
 */
export function createMessageFromData(msgStruct: any, testData: TestMessage): { msg: any; buffer: Buffer } {
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
  return { msg, buffer: (msg as any)._buffer };
}

/**
 * Validate message against test data
 */
export function validateMessageAgainstData(msg: any, testData: TestMessage): boolean {
  const errors: string[] = [];

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
 * Encode multiple test messages using the specified frame format.
 */
export function encodeTestMessage(formatName: string): Buffer {
  const ParserClass = getParserClass(formatName);
  const serialMsgInfo = getMessageInfo();
  const basicMsgInfo = getBasicTypesMessageInfo();

  const mixedMessages = loadMixedMessages();
  const encodedBuffers: Buffer[] = [];

  for (const item of mixedMessages) {
    const msgType = item.type;
    const testData = item.data;

    let msgInfo: any, createFunc: any;
    if (msgType === 'SerializationTestMessage') {
      msgInfo = serialMsgInfo;
      createFunc = createMessageFromData;
    } else if (msgType === 'BasicTypesMessage') {
      msgInfo = basicMsgInfo;
      createFunc = createBasicTypesMessageFromData;
    } else {
      console.log(`  Unknown message type: ${msgType}`);
      return Buffer.alloc(0);
    }

    const { msg, buffer } = createFunc(msgInfo.struct, testData);
    const encoded = Buffer.from(ParserClass.encodeMsg(msgInfo.msgId, buffer));
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
export function decodeTestMessage(formatName: string, data: Buffer): number {
  const ParserClass = getParserClass(formatName);
  const serialMsgInfo = getMessageInfo();
  const basicMsgInfo = getBasicTypesMessageInfo();

  const mixedMessages = loadMixedMessages();
  let offset = 0;
  let messageCount = 0;

  while (offset < data.length && messageCount < mixedMessages.length) {
    // Extract remaining data
    const remainingData = data.slice(offset);

    // Use static validatePacket method
    const result = ParserClass.validatePacket(remainingData);

    if (!result || !result.valid) {
      console.log(`  Decoding failed for message ${messageCount}`);
      return messageCount;
    }

    // Get expected message type
    const item = mixedMessages[messageCount];
    const msgType = item.type;
    const testData = item.data;

    // Validate msg_id matches expected type
    let expectedMsgId: number, msgStruct: any, validateFunc: any;
    if (msgType === 'SerializationTestMessage') {
      expectedMsgId = serialMsgInfo.msgId;
      msgStruct = serialMsgInfo.struct;
      validateFunc = validateMessageAgainstData;
    } else if (msgType === 'BasicTypesMessage') {
      expectedMsgId = basicMsgInfo.msgId;
      msgStruct = basicMsgInfo.struct;
      validateFunc = validateBasicTypesMessageAgainstData;
    } else {
      console.log(`  Unknown message type: ${msgType}`);
      return messageCount;
    }

    if (result.msg_id !== expectedMsgId) {
      console.log(`  Message ID mismatch for message ${messageCount}: expected ${expectedMsgId}, got ${result.msg_id}`);
      return messageCount;
    }

    // Create message object from decoded data
    const msg = new msgStruct(Buffer.from(result.msg_data));

    // Validate the message against test data
    if (!validateFunc(msg, testData)) {
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

  if (messageCount !== mixedMessages.length) {
    console.log(`  Expected ${mixedMessages.length} messages, but decoded ${messageCount}`);
    return messageCount;
  }

  if (offset !== data.length) {
    console.log(`  Extra data after messages: processed ${offset} bytes, got ${data.length} bytes`);
    return messageCount;
  }

  return messageCount;
}
