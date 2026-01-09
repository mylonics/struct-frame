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
        const unionMsgs = data.UnionTestMessage || [];
        
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
          } else if (msgType === 'UnionTestMessage') {
            msgData = unionMsgs.find((m: any) => m.name === msgName);
            if (msgData) {
              messages.push({ type: 'UnionTestMessage', data: msgData });
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


// Import generated frame profile functions - include BufferReader/Writer factory functions
import {
  ProfileStandard,
  ProfileSensor,
  ProfileIPC,
  ProfileBulk,
  ProfileNetwork,
  ProfileParser,
  createProfileStandardReader,
  createProfileStandardWriter,
  createProfileSensorReader,
  createProfileSensorWriter,
  createProfileIPCReader,
  createProfileIPCWriter,
  createProfileBulkReader,
  createProfileBulkWriter,
  createProfileNetworkReader,
  createProfileNetworkWriter,
} from './frame_profiles';

const {
  serialization_test_SerializationTestMessage,
  serialization_test_SerializationTestMessage_msgid,
  serialization_test_SerializationTestMessage_max_size,
  serialization_test_BasicTypesMessage,
  serialization_test_BasicTypesMessage_msgid,
  serialization_test_BasicTypesMessage_max_size,
  serialization_test_UnionTestMessage,
  serialization_test_UnionTestMessage_msgid,
  serialization_test_UnionTestMessage_max_size,
  serialization_test_ComprehensiveArrayMessage,
  serialization_test_ComprehensiveArrayMessage_msgid,
  serialization_test_ComprehensiveArrayMessage_max_size,
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
 * Get message info for UnionTestMessage
 */
export function getUnionTestMessageInfo() {
  return {
    struct: serialization_test_UnionTestMessage,
    msgId: serialization_test_UnionTestMessage_msgid,
    maxSize: serialization_test_UnionTestMessage_max_size,
  };
}

/**
 * Create BasicTypesMessage from test data
 */
export function createBasicTypesMessageFromData(msgStruct: any, testData: any): { msg: any; buffer: Buffer } {
  const size = msgStruct._size || msgStruct.getSize();
  const buffer = Buffer.alloc(size);
  const msg = new msgStruct(buffer);

  // large_int and large_uint may be stored as strings in JSON to preserve precision
  const largeInt = typeof testData.large_int === 'string' ? BigInt(testData.large_int) : BigInt(testData.large_int);
  const largeUint = typeof testData.large_uint === 'string' ? BigInt(testData.large_uint) : BigInt(testData.large_uint);

  msg.small_int = testData.small_int;
  msg.medium_int = testData.medium_int;
  msg.regular_int = testData.regular_int;
  msg.large_int = largeInt;
  msg.small_uint = testData.small_uint;
  msg.medium_uint = testData.medium_uint;
  msg.regular_uint = testData.regular_uint;
  msg.large_uint = largeUint;
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

  // large_int and large_uint may be stored as strings in JSON to preserve precision
  const expectedLargeInt = typeof testData.large_int === 'string' ? BigInt(testData.large_int) : BigInt(testData.large_int);
  const expectedLargeUint = typeof testData.large_uint === 'string' ? BigInt(testData.large_uint) : BigInt(testData.large_uint);

  if (msg.small_int !== testData.small_int) {
    errors.push(`small_int: expected ${testData.small_int}, got ${msg.small_int}`);
  }
  if (msg.medium_int !== testData.medium_int) {
    errors.push(`medium_int: expected ${testData.medium_int}, got ${msg.medium_int}`);
  }
  if (msg.regular_int !== testData.regular_int) {
    errors.push(`regular_int: expected ${testData.regular_int}, got ${msg.regular_int}`);
  }
  if (BigInt(msg.large_int) !== expectedLargeInt) {
    errors.push(`large_int: expected ${expectedLargeInt}, got ${msg.large_int}`);
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
  if (BigInt(msg.large_uint) !== expectedLargeUint) {
    errors.push(`large_uint: expected ${expectedLargeUint}, got ${msg.large_uint}`);
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
 * Create UnionTestMessage from test data
 * UnionTestMessage has a discriminator (payload_discriminator) and payload_data (byte array).
 * The payload_data contains either ComprehensiveArrayMessage or SerializationTestMessage.
 * The discriminator is the message ID of the inner message type:
 * - payload_type 1 (array_payload) -> ComprehensiveArrayMessage msg_id (203)
 * - payload_type 2 (test_payload) -> SerializationTestMessage msg_id (204)
 */
export function createUnionTestMessageFromData(msgStruct: any, testData: any): { msg: any; buffer: Buffer } {
  const size = msgStruct._size || msgStruct.getSize();
  const buffer = Buffer.alloc(size);
  const msg = new msgStruct(buffer);

  // Create the inner payload based on the type and set discriminator to inner message's msg_id
  if (testData.payload_type === 1 && testData.array_payload) {
    // ComprehensiveArrayMessage - discriminator is its msg_id
    msg.payload_discriminator = serialization_test_ComprehensiveArrayMessage_msgid;
    
    const innerSize = serialization_test_ComprehensiveArrayMessage_max_size;
    const innerBuffer = Buffer.alloc(innerSize);
    const innerMsg = new serialization_test_ComprehensiveArrayMessage(innerBuffer);
    
    // Set array fields from test data
    const ap = testData.array_payload;
    innerMsg.fixed_ints = ap.fixed_ints || [];
    innerMsg.fixed_floats = ap.fixed_floats || [];
    innerMsg.fixed_bools = ap.fixed_bools || [];
    innerMsg.bounded_uints_count = (ap.bounded_uints || []).length;
    innerMsg.bounded_uints_data = ap.bounded_uints || [];
    innerMsg.bounded_doubles_count = (ap.bounded_doubles || []).length;
    innerMsg.bounded_doubles_data = ap.bounded_doubles || [];
    innerMsg.fixed_statuses = ap.fixed_statuses || [];
    innerMsg.bounded_statuses_count = (ap.bounded_statuses || []).length;
    innerMsg.bounded_statuses_data = ap.bounded_statuses || [];
    
    // Copy inner buffer to payload_data
    (innerMsg as any)._buffer.copy((msg as any)._buffer, 2, 0, innerSize);
  } else if (testData.payload_type === 2 && testData.test_payload) {
    // SerializationTestMessage - discriminator is its msg_id
    msg.payload_discriminator = serialization_test_SerializationTestMessage_msgid;
    
    const innerSize = serialization_test_SerializationTestMessage_max_size;
    const innerBuffer = Buffer.alloc(innerSize);
    const innerMsg = new serialization_test_SerializationTestMessage(innerBuffer);
    
    const tp = testData.test_payload;
    innerMsg.magic_number = tp.magic_number;
    innerMsg.test_string_length = tp.test_string.length;
    innerMsg.test_string_data = tp.test_string;
    innerMsg.test_float = tp.test_float;
    innerMsg.test_bool = tp.test_bool;
    innerMsg.test_array_count = tp.test_array.length;
    innerMsg.test_array_data = tp.test_array;
    
    // Copy inner buffer to payload_data
    (innerMsg as any)._buffer.copy((msg as any)._buffer, 2, 0, innerSize);
  }

  return { msg, buffer: (msg as any)._buffer };
}

/**
 * Validate UnionTestMessage against test data
 * The discriminator should be the message ID:
 * - payload_type 1 -> msg_id 203 (ComprehensiveArrayMessage)
 * - payload_type 2 -> msg_id 204 (SerializationTestMessage)
 */
export function validateUnionTestMessageAgainstData(msg: any, testData: any): boolean {
  const errors: string[] = [];

  // Map payload_type to expected discriminator (message ID)
  const expectedDiscriminator = testData.payload_type === 1 
    ? serialization_test_ComprehensiveArrayMessage_msgid 
    : serialization_test_SerializationTestMessage_msgid;

  if (msg.payload_discriminator !== expectedDiscriminator) {
    errors.push(`payload_discriminator: expected ${expectedDiscriminator}, got ${msg.payload_discriminator}`);
  }

  // Validate the inner payload based on type
  if (testData.payload_type === 1 && testData.array_payload) {
    // ComprehensiveArrayMessage - extract from payload_data
    const innerBuffer = Buffer.alloc(serialization_test_ComprehensiveArrayMessage_max_size);
    (msg as any)._buffer.copy(innerBuffer, 0, 2, 2 + serialization_test_ComprehensiveArrayMessage_max_size);
    const innerMsg = new serialization_test_ComprehensiveArrayMessage(innerBuffer);
    
    const ap = testData.array_payload;
    // Validate fixed arrays
    for (let i = 0; i < (ap.fixed_ints || []).length; i++) {
      if (innerMsg.fixed_ints[i] !== ap.fixed_ints[i]) {
        errors.push(`array_payload.fixed_ints[${i}]: expected ${ap.fixed_ints[i]}, got ${innerMsg.fixed_ints[i]}`);
      }
    }
    for (let i = 0; i < (ap.fixed_floats || []).length; i++) {
      if (Math.abs(innerMsg.fixed_floats[i] - ap.fixed_floats[i]) > 0.01) {
        errors.push(`array_payload.fixed_floats[${i}]: expected ${ap.fixed_floats[i]}, got ${innerMsg.fixed_floats[i]}`);
      }
    }
  } else if (testData.payload_type === 2 && testData.test_payload) {
    // SerializationTestMessage
    const innerBuffer = Buffer.alloc(serialization_test_SerializationTestMessage_max_size);
    (msg as any)._buffer.copy(innerBuffer, 0, 2, 2 + serialization_test_SerializationTestMessage_max_size);
    const innerMsg = new serialization_test_SerializationTestMessage(innerBuffer);
    
    const tp = testData.test_payload;
    if (innerMsg.magic_number !== tp.magic_number) {
      errors.push(`test_payload.magic_number: expected ${tp.magic_number}, got ${innerMsg.magic_number}`);
    }
    const testString = innerMsg.test_string_data.substring(0, innerMsg.test_string_length);
    if (testString !== tp.test_string) {
      errors.push(`test_payload.test_string: expected '${tp.test_string}', got '${testString}'`);
    }
    if (Math.abs(innerMsg.test_float - tp.test_float) > 0.1) {
      errors.push(`test_payload.test_float: expected ${tp.test_float}, got ${innerMsg.test_float}`);
    }
    if (innerMsg.test_bool !== tp.test_bool) {
      errors.push(`test_payload.test_bool: expected ${tp.test_bool}, got ${innerMsg.test_bool}`);
    }
    for (let i = 0; i < tp.test_array.length; i++) {
      if (innerMsg.test_array_data[i] !== tp.test_array[i]) {
        errors.push(`test_payload.test_array[${i}]: expected ${tp.test_array[i]}, got ${innerMsg.test_array_data[i]}`);
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
 * Uses BufferWriter for efficient multi-frame encoding.
 */
export function encodeTestMessage(formatName: string): Buffer {
  const serialMsgInfo = getMessageInfo();
  const basicMsgInfo = getBasicTypesMessageInfo();
  const unionMsgInfo = getUnionTestMessageInfo();

  const mixedMessages = loadMixedMessages();
  
  // Create the appropriate BufferWriter for this profile
  const capacity = 4096; // Should be enough for test messages
  const writerCreators: { [key: string]: () => any } = {
    'profile_standard': () => createProfileStandardWriter(capacity),
    'profile_sensor': () => createProfileSensorWriter(capacity),
    'profile_ipc': () => createProfileIPCWriter(capacity),
    'profile_bulk': () => createProfileBulkWriter(capacity),
    'profile_network': () => createProfileNetworkWriter(capacity),
  };
  
  const creator = writerCreators[formatName];
  if (!creator) {
    console.log(`  Unknown format: ${formatName}`);
    return Buffer.alloc(0);
  }
  
  const writer = creator();

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
    } else if (msgType === 'UnionTestMessage') {
      msgInfo = unionMsgInfo;
      createFunc = createUnionTestMessageFromData;
    } else {
      console.log(`  Unknown message type: ${msgType}`);
      return Buffer.alloc(0);
    }

    const { msg, buffer } = createFunc(msgInfo.struct, testData);
    // Use BufferWriter to encode and append frame - it tracks offset automatically
    const bytesWritten = writer.write(msgInfo.msgId, buffer);
    if (bytesWritten === 0) {
      console.log('  Encoding failed for message');
      return Buffer.alloc(0);
    }
  }

  // Return the encoded data from BufferWriter
  return Buffer.from(writer.data());
}

/**
 * Decode and validate multiple test messages using the specified frame format.
 * Uses BufferReader for efficient multi-frame parsing.
 * Returns the number of messages successfully decoded.
 */
export function decodeTestMessage(formatName: string, data: Buffer): number {
  const serialMsgInfo = getMessageInfo();
  const basicMsgInfo = getBasicTypesMessageInfo();
  const unionMsgInfo = getUnionTestMessageInfo();

  const mixedMessages = loadMixedMessages();
  
  // Create the appropriate BufferReader for this profile
  const readerCreators: { [key: string]: () => any } = {
    'profile_standard': () => createProfileStandardReader(data),
    'profile_sensor': () => createProfileSensorReader(data, getMsgLength),
    'profile_ipc': () => createProfileIPCReader(data, getMsgLength),
    'profile_bulk': () => createProfileBulkReader(data),
    'profile_network': () => createProfileNetworkReader(data),
  };
  
  const creator = readerCreators[formatName];
  if (!creator) {
    console.log(`  Unknown format: ${formatName}`);
    return 0;
  }
  
  const reader = creator();
  let messageCount = 0;

  // Use BufferReader to iterate through frames - it handles offset tracking automatically
  while (reader.hasMore() && messageCount < mixedMessages.length) {
    const result = reader.next();

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
    } else if (msgType === 'UnionTestMessage') {
      expectedMsgId = unionMsgInfo.msgId;
      msgStruct = unionMsgInfo.struct;
      validateFunc = validateUnionTestMessageAgainstData;
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

    messageCount++;
  }

  if (messageCount !== mixedMessages.length) {
    console.log(`  Expected ${mixedMessages.length} messages, but decoded ${messageCount}`);
    return messageCount;
  }

  // Ensure all data was consumed (BufferReader tracks remaining bytes)
  if (reader.remaining > 0) {
    console.log(`  Extra data after messages: ${reader.remaining} bytes remaining`);
    return messageCount;
  }

  return messageCount;
}
