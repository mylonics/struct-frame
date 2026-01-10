/**
 * Test codec - Extended message ID and payload tests (JavaScript).
 */
"use strict";

const path = require('path');
const fs = require('fs');

// Import generated frame profile classes
const {
  ProfileBulkReader,
  ProfileBulkWriter,
  ProfileNetworkReader,
  ProfileNetworkWriter,
} = require('../generated/js/frame_profiles');

// Import generated extended message classes
const {
  extended_test_ExtendedIdMessage1,
  extended_test_ExtendedIdMessage2,
  extended_test_ExtendedIdMessage3,
  extended_test_ExtendedIdMessage4,
  extended_test_ExtendedIdMessage5,
  extended_test_ExtendedIdMessage6,
  extended_test_ExtendedIdMessage7,
  extended_test_ExtendedIdMessage8,
  extended_test_ExtendedIdMessage9,
  extended_test_ExtendedIdMessage10,
  extended_test_LargePayloadMessage1,
  extended_test_LargePayloadMessage2,
} = require('../generated/js/extended_test.sf');

// Load extended messages from JSON following MixedMessages sequence
function loadExtendedMessages() {
  const possiblePaths = [
    path.join(__dirname, '..', 'extended_messages.json'),
    path.join(__dirname, '..', '..', 'extended_messages.json'),
    'extended_messages.json',
    '../extended_messages.json',
  ];

  for (const filePath of possiblePaths) {
    try {
      if (fs.existsSync(filePath)) {
        const jsonData = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        const mixedArray = jsonData.MixedMessages || [];
        
        const messages = [];
        for (const item of mixedArray) {
          const msgType = item.type;
          const msgName = item.name;
          
          const msgArr = jsonData[msgType] || [];
          const msgData = msgArr.find(m => m.name === msgName);
          if (msgData) {
            messages.push({ type: msgType, data: msgData });
          }
        }
        
        return messages;
      }
    } catch (e) {
      // Continue to next path
    }
  }

  throw new Error('Could not find extended_messages.json');
}

// Map message types to classes
const msgClasses = {
  'ExtendedIdMessage1': extended_test_ExtendedIdMessage1,
  'ExtendedIdMessage2': extended_test_ExtendedIdMessage2,
  'ExtendedIdMessage3': extended_test_ExtendedIdMessage3,
  'ExtendedIdMessage4': extended_test_ExtendedIdMessage4,
  'ExtendedIdMessage5': extended_test_ExtendedIdMessage5,
  'ExtendedIdMessage6': extended_test_ExtendedIdMessage6,
  'ExtendedIdMessage7': extended_test_ExtendedIdMessage7,
  'ExtendedIdMessage8': extended_test_ExtendedIdMessage8,
  'ExtendedIdMessage9': extended_test_ExtendedIdMessage9,
  'ExtendedIdMessage10': extended_test_ExtendedIdMessage10,
  'LargePayloadMessage1': extended_test_LargePayloadMessage1,
  'LargePayloadMessage2': extended_test_LargePayloadMessage2,
};

/**
 * Create extended message from test data
 */
function createExtendedMessage(MsgClass, testData, msgType) {
  if (msgType === 'ExtendedIdMessage1') {
    return new MsgClass({
      sequence_number: testData.sequence_number,
      label: testData.label,
      value: testData.value,
      enabled: testData.enabled,
    });
  } else if (msgType === 'ExtendedIdMessage2') {
    return new MsgClass({
      sensor_id: testData.sensor_id,
      reading: testData.reading,
      status_code: testData.status_code,
      description_length: testData.description.length,
      description_data: testData.description,
    });
  } else if (msgType === 'ExtendedIdMessage3') {
    const timestamp = typeof testData.timestamp === 'string' ? BigInt(testData.timestamp) : BigInt(testData.timestamp);
    return new MsgClass({
      timestamp: timestamp,
      temperature: testData.temperature,
      humidity: testData.humidity,
      location: testData.location,
    });
  } else if (msgType === 'ExtendedIdMessage4') {
    const eventTime = typeof testData.event_time === 'string' ? BigInt(testData.event_time) : BigInt(testData.event_time);
    return new MsgClass({
      event_id: testData.event_id,
      event_type: testData.event_type,
      event_time: eventTime,
      event_data_length: testData.event_data.length,
      event_data_data: testData.event_data,
    });
  } else if (msgType === 'ExtendedIdMessage5') {
    return new MsgClass({
      x_position: testData.x_position,
      y_position: testData.y_position,
      z_position: testData.z_position,
      frame_number: testData.frame_number,
    });
  } else if (msgType === 'ExtendedIdMessage6') {
    return new MsgClass({
      command_id: testData.command_id,
      parameter1: testData.parameter1,
      parameter2: testData.parameter2,
      acknowledged: testData.acknowledged,
      command_name: testData.command_name,
    });
  } else if (msgType === 'ExtendedIdMessage7') {
    return new MsgClass({
      counter: testData.counter,
      average: testData.average,
      minimum: testData.minimum,
      maximum: testData.maximum,
    });
  } else if (msgType === 'ExtendedIdMessage8') {
    return new MsgClass({
      level: testData.level,
      offset: testData.offset,
      duration: testData.duration,
      tag: testData.tag,
    });
  } else if (msgType === 'ExtendedIdMessage9') {
    const bigNumber = typeof testData.big_number === 'string' ? BigInt(testData.big_number) : BigInt(testData.big_number);
    const bigUnsigned = typeof testData.big_unsigned === 'string' ? BigInt(testData.big_unsigned) : BigInt(testData.big_unsigned);
    return new MsgClass({
      big_number: bigNumber,
      big_unsigned: bigUnsigned,
      precision_value: testData.precision_value,
    });
  } else if (msgType === 'ExtendedIdMessage10') {
    return new MsgClass({
      small_value: testData.small_value,
      short_text: testData.short_text,
      flag: testData.flag,
    });
  } else if (msgType === 'LargePayloadMessage1') {
    const timestamp = typeof testData.timestamp === 'string' ? BigInt(testData.timestamp) : BigInt(testData.timestamp);
    return new MsgClass({
      sensor_readings: testData.sensor_readings,
      reading_count: testData.reading_count,
      timestamp: timestamp,
      device_name: testData.device_name,
    });
  } else if (msgType === 'LargePayloadMessage2') {
    return new MsgClass({
      large_data: testData.large_data,
    });
  }
  throw new Error(`Unknown message type: ${msgType}`);
}

/**
 * Encode multiple extended test messages using the specified frame format.
 */
function encodeExtendedMessages(formatName) {
  const messages = loadExtendedMessages();
  
  // Only extended profiles support msg_id > 255
  const capacity = 8192; // Larger for extended payloads
  const writerCreators = {
    'profile_bulk': () => new ProfileBulkWriter(capacity),
    'profile_network': () => new ProfileNetworkWriter(capacity),
  };

  const creator = writerCreators[formatName];
  if (!creator) {
    throw new Error(`Format not supported for extended messages: ${formatName}. Use profile_bulk or profile_network.`);
  }

  const writer = creator();

  for (const item of messages) {
    const msgType = item.type;
    const testData = item.data;

    const MsgClass = msgClasses[msgType];
    if (!MsgClass) {
      throw new Error(`Unknown message type: ${msgType}`);
    }

    const msg = createExtendedMessage(MsgClass, testData, msgType);
    
    // Use BufferWriter to encode and append frame
    const bytesWritten = writer.write(msg);
    if (bytesWritten === 0) {
      throw new Error('Failed to encode message: buffer full or encoding error');
    }
  }

  // Return the encoded data from BufferWriter
  return Buffer.from(writer.data());
}

/**
 * Decode and validate multiple extended test messages using the specified frame format.
 */
function decodeExtendedMessages(formatName, data) {
  const messages = loadExtendedMessages();
  
  // Only extended profiles support msg_id > 255
  const readerCreators = {
    'profile_bulk': () => new ProfileBulkReader(data),
    'profile_network': () => new ProfileNetworkReader(data),
  };

  const creator = readerCreators[formatName];
  if (!creator) {
    throw new Error(`Format not supported for extended messages: ${formatName}. Use profile_bulk or profile_network.`);
  }

  const reader = creator();
  let messageCount = 0;

  while (reader.hasMore() && messageCount < messages.length) {
    const result = reader.next();

    if (!result || !result.valid) {
      console.log(`  Decoding failed for message ${messageCount}`);
      return { success: false, messageCount };
    }

    const item = messages[messageCount];
    const msgType = item.type;

    const MsgClass = msgClasses[msgType];
    if (!MsgClass) {
      console.log(`  Unknown message type: ${msgType}`);
      return { success: false, messageCount };
    }

    const expectedMsgId = MsgClass._msgid;
    
    // The reader already combines pkg_id and msg_id into msg_id for extended profiles
    if (result.msg_id !== expectedMsgId) {
      console.log(`  Message ID mismatch for message ${messageCount}: expected ${expectedMsgId}, got ${result.msg_id}`);
      return { success: false, messageCount };
    }

    // Create message object from decoded data (just verify it decodes without error)
    new MsgClass(Buffer.from(result.msg_data));

    messageCount++;
  }

  if (messageCount !== messages.length) {
    console.log(`  Expected ${messages.length} messages, but decoded ${messageCount}`);
    return { success: false, messageCount };
  }

  // Ensure all data was consumed
  if (reader.remaining > 0) {
    console.log(`  Extra data after messages: ${reader.remaining} bytes remaining`);
    return { success: false, messageCount };
  }

  return { success: true, messageCount };
}

module.exports = {
  encodeExtendedMessages,
  decodeExtendedMessages,
};
