/**
 * Test codec - Encode/decode functions for all frame formats (JavaScript).
 */
"use strict";

const path = require('path');
const fs = require('fs');

// Load test messages from JSON
function loadTestMessages() {
  const possiblePaths = [
    path.join(__dirname, '..', 'test_messages.json'),
    path.join(__dirname, '..', '..', 'test_messages.json'),
    'test_messages.json',
    '../test_messages.json',
  ];

  for (const filePath of possiblePaths) {
    try {
      if (fs.existsSync(filePath)) {
        const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        // Return SerializationTestMessage data for backwards compatibility
        return data.SerializationTestMessage || data.messages || [];
      }
    } catch (e) {
      // Continue to next path
    }
  }

  throw new Error('Could not find test_messages.json');
}

// Load mixed messages from JSON following MixedMessages sequence
function loadMixedMessages() {
  const possiblePaths = [
    path.join(__dirname, '..', 'test_messages.json'),
    path.join(__dirname, '..', '..', 'test_messages.json'),
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
            msgData = serialMsgs.find(m => m.name === msgName);
            if (msgData) {
              messages.push({ type: 'SerializationTestMessage', data: msgData });
            }
          } else if (msgType === 'BasicTypesMessage') {
            msgData = basicMsgs.find(m => m.name === msgName);
            if (msgData) {
              messages.push({ type: 'BasicTypesMessage', data: msgData });
            }
          } else if (msgType === 'UnionTestMessage') {
            msgData = unionMsgs.find(m => m.name === msgName);
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

// Import generated frame profile subclasses
const {
  ProfileStandardReader,
  ProfileStandardWriter,
  ProfileSensorReader,
  ProfileSensorWriter,
  ProfileIPCReader,
  ProfileIPCWriter,
  ProfileBulkReader,
  ProfileBulkWriter,
  ProfileNetworkReader,
  ProfileNetworkWriter,
} = require('./frame_profiles');

// Helper to get message length for minimal payloads
function getMsgLength(msgId) {
  const module = require('../generated/js/serialization_test.sf');
  return module.get_message_length(msgId);
}

/**
 * Get the message struct and metadata.
 */
function getMessageInfo() {
  const module = require('../generated/js/serialization_test.sf');
  return {
    struct: module.serialization_test_SerializationTestMessage,
    msgId: module.serialization_test_SerializationTestMessage._msgid,
    maxSize: module.serialization_test_SerializationTestMessage._size,
  };
}

/**
 * Get message info for BasicTypesMessage
 */
function getBasicTypesMessageInfo() {
  const module = require('../generated/js/serialization_test.sf');
  return {
    struct: module.serialization_test_BasicTypesMessage,
    msgId: module.serialization_test_BasicTypesMessage._msgid,
    maxSize: module.serialization_test_BasicTypesMessage._size,
  };
}

/**
 * Get message info for UnionTestMessage
 */
function getUnionTestMessageInfo() {
  const module = require('../generated/js/serialization_test.sf');
  return {
    struct: module.serialization_test_UnionTestMessage,
    msgId: module.serialization_test_UnionTestMessage._msgid,
    maxSize: module.serialization_test_UnionTestMessage._size,
    // For inner messages
    comprehensiveArrayStruct: module.serialization_test_ComprehensiveArrayMessage,
    comprehensiveArrayMsgId: module.serialization_test_ComprehensiveArrayMessage._msgid,
    comprehensiveArrayMaxSize: module.serialization_test_ComprehensiveArrayMessage._size,
    serializationTestStruct: module.serialization_test_SerializationTestMessage,
    serializationTestMsgId: module.serialization_test_SerializationTestMessage._msgid,
    serializationTestMaxSize: module.serialization_test_SerializationTestMessage._size,
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
 * Create BasicTypesMessage from test data
 */
function createBasicTypesMessageFromData(msgStruct, testData) {
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
 * Validate BasicTypesMessage against test data
 */
function validateBasicTypesMessageAgainstData(msg, testData) {
  const errors = [];

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

  const deviceId = msg.device_id.replace(/\0/g, '');
  if (deviceId !== testData.device_id) {
    errors.push(`device_id: expected '${testData.device_id}', got '${deviceId}'`);
  }

  const description = msg.description_data.substring(0, msg.description_length).replace(/\0/g, '');
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
 * The discriminator is the message ID of the inner message type:
 * - payload_type 1 (array_payload) -> ComprehensiveArrayMessage msg_id (203)
 * - payload_type 2 (test_payload) -> SerializationTestMessage msg_id (204)
 */
function createUnionTestMessageFromData(msgStruct, testData) {
  const unionInfo = getUnionTestMessageInfo();
  const size = msgStruct._size || msgStruct.getSize();
  const buffer = Buffer.alloc(size);
  const msg = new msgStruct(buffer);

  // Create the inner payload based on the type and set discriminator to inner message's msg_id
  if (testData.payload_type === 1 && testData.array_payload) {
    // ComprehensiveArrayMessage - discriminator is its msg_id
    msg.payload_discriminator = unionInfo.comprehensiveArrayMsgId;
    
    const innerSize = unionInfo.comprehensiveArrayMaxSize;
    const innerBuffer = Buffer.alloc(innerSize);
    const innerMsg = new unionInfo.comprehensiveArrayStruct(innerBuffer);
    
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
    
    // Copy inner buffer to payload_data (after 2-byte discriminator)
    innerMsg._buffer.copy(msg._buffer, 2, 0, innerSize);
  } else if (testData.payload_type === 2 && testData.test_payload) {
    // SerializationTestMessage - discriminator is its msg_id
    msg.payload_discriminator = unionInfo.serializationTestMsgId;
    
    const innerSize = unionInfo.serializationTestMaxSize;
    const innerBuffer = Buffer.alloc(innerSize);
    const innerMsg = new unionInfo.serializationTestStruct(innerBuffer);
    
    const tp = testData.test_payload;
    innerMsg.magic_number = tp.magic_number;
    innerMsg.test_string_length = tp.test_string.length;
    innerMsg.test_string_data = tp.test_string;
    innerMsg.test_float = tp.test_float;
    innerMsg.test_bool = tp.test_bool;
    innerMsg.test_array_count = tp.test_array.length;
    innerMsg.test_array_data = tp.test_array;
    
    // Copy inner buffer to payload_data
    innerMsg._buffer.copy(msg._buffer, 2, 0, innerSize);
  }

  return { msg, buffer: msg._buffer };
}

/**
 * Validate UnionTestMessage against test data
 * The discriminator should be the message ID:
 * - payload_type 1 -> msg_id 203 (ComprehensiveArrayMessage)
 * - payload_type 2 -> msg_id 204 (SerializationTestMessage)
 */
function validateUnionTestMessageAgainstData(msg, testData) {
  const unionInfo = getUnionTestMessageInfo();
  const errors = [];

  // Map payload_type to expected discriminator (message ID)
  const expectedDiscriminator = testData.payload_type === 1 
    ? unionInfo.comprehensiveArrayMsgId 
    : unionInfo.serializationTestMsgId;

  if (msg.payload_discriminator !== expectedDiscriminator) {
    errors.push(`payload_discriminator: expected ${expectedDiscriminator}, got ${msg.payload_discriminator}`);
  }

  // Validate the inner payload based on type
  if (testData.payload_type === 1 && testData.array_payload) {
    // ComprehensiveArrayMessage
    const innerSize = unionInfo.comprehensiveArrayMaxSize;
    const innerBuffer = Buffer.alloc(innerSize);
    msg._buffer.copy(innerBuffer, 0, 2, 2 + innerSize);
    const innerMsg = new unionInfo.comprehensiveArrayStruct(innerBuffer);
    
    const ap = testData.array_payload;
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
    const innerSize = unionInfo.serializationTestMaxSize;
    const innerBuffer = Buffer.alloc(innerSize);
    msg._buffer.copy(innerBuffer, 0, 2, 2 + innerSize);
    const innerMsg = new unionInfo.serializationTestStruct(innerBuffer);
    
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
 * Encode multiple test messages using the specified frame format.
 * Uses BufferWriter for efficient multi-frame encoding.
 */
function encodeTestMessage(formatName) {
  const serialMsgInfo = getMessageInfo();
  const basicMsgInfo = getBasicTypesMessageInfo();
  const unionMsgInfo = getUnionTestMessageInfo();

  const mixedMessages = loadMixedMessages();
  
  // Create the appropriate BufferWriter for this profile
  const capacity = 4096; // Should be enough for test messages
  const writerCreators = {
    'profile_standard': () => new ProfileStandardWriter(capacity),
    'profile_sensor': () => new ProfileSensorWriter(capacity),
    'profile_ipc': () => new ProfileIPCWriter(capacity),
    'profile_bulk': () => new ProfileBulkWriter(capacity),
    'profile_network': () => new ProfileNetworkWriter(capacity),
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

    let msgInfo, createFunc;
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

    const { msg } = createFunc(msgInfo.struct, testData);
    // Use BufferWriter to encode and append frame - it tracks offset automatically
    const bytesWritten = writer.write(msg);
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
function decodeTestMessage(formatName, data) {
  const serialMsgInfo = getMessageInfo();
  const basicMsgInfo = getBasicTypesMessageInfo();
  const unionMsgInfo = getUnionTestMessageInfo();

  const mixedMessages = loadMixedMessages();
  
  // Create the appropriate BufferReader for this profile
  const readerCreators = {
    'profile_standard': () => new ProfileStandardReader(data),
    'profile_sensor': () => new ProfileSensorReader(data, getMsgLength),
    'profile_ipc': () => new ProfileIPCReader(data, getMsgLength),
    'profile_bulk': () => new ProfileBulkReader(data),
    'profile_network': () => new ProfileNetworkReader(data),
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
    let expectedMsgId, msgStruct, validateFunc;
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

module.exports = {
  encodeTestMessage,
  decodeTestMessage,
  getMessageInfo,
};
