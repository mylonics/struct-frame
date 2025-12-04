/**
 * Basic Default frame format serialization test for JavaScript.
 */
"use strict";

const fs = require('fs');
const path = require('path');

// BasicDefault constants
const BASIC_DEFAULT_START_BYTE1 = 0x90;
const BASIC_DEFAULT_START_BYTE2 = 0x71;
const BASIC_DEFAULT_HEADER_SIZE = 4;  // start1 + start2 + length + msg_id
const BASIC_DEFAULT_FOOTER_SIZE = 2;  // crc1 + crc2

function printFailureDetails(label, expectedValues, actualValues, rawData) {
  console.log('\n============================================================');
  console.log('FAILURE DETAILS: ' + label);
  console.log('============================================================');
  
  if (expectedValues) {
    console.log('\nExpected Values:');
    for (const [key, val] of Object.entries(expectedValues)) {
      console.log('  ' + key + ': ' + val);
    }
  }
  
  if (actualValues) {
    console.log('\nActual Values:');
    for (const [key, val] of Object.entries(actualValues)) {
      console.log('  ' + key + ': ' + val);
    }
  }
  
  if (rawData && rawData.length > 0) {
    console.log('\nRaw Data (' + rawData.length + ' bytes):');
    console.log('  Hex: ' + rawData.toString('hex').substring(0, 128) + (rawData.length > 64 ? '...' : ''));
  }
  
  console.log('============================================================\n');
}

function loadExpectedValues() {
  try {
    const jsonPath = path.join(__dirname, '../../expected_values.json');
    const data = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));
    return data.serialization_test;
  } catch (error) {
    console.log('Error loading expected values: ' + error);
    return null;
  }
}

function createTestData() {
  try {
    const expected = loadExpectedValues();
    if (!expected) {
      return false;
    }

    const msg_id = 204;
    const payloadSize = 95;
    const payload = Buffer.alloc(payloadSize);
    let offset = 0;
    
    // magic_number (uint32, little-endian)
    payload.writeUInt32LE(expected.magic_number, offset);
    offset += 4;
    
    // test_string: length byte + 64 bytes of data
    const testString = expected.test_string;
    payload.writeUInt8(testString.length, offset);
    offset += 1;
    Buffer.from(testString).copy(payload, offset, 0, testString.length);
    offset += 64;
    
    // test_float (float, little-endian)
    payload.writeFloatLE(expected.test_float, offset);
    offset += 4;
    
    // test_bool (1 byte)
    payload.writeUInt8(expected.test_bool ? 1 : 0, offset);
    offset += 1;
    
    // test_array: count byte + int32 data (5 elements max)
    const testArray = expected.test_array;
    payload.writeUInt8(testArray.length, offset);
    offset += 1;
    for (let i = 0; i < 5; i++) {
      if (i < testArray.length) {
        payload.writeInt32LE(testArray[i], offset);
      } else {
        payload.writeInt32LE(0, offset);
      }
      offset += 4;
    }
    
    // Calculate Fletcher checksum on length + msg_id + payload
    let byte1 = payloadSize & 0xFF;
    let byte2 = payloadSize & 0xFF;
    byte1 = (byte1 + msg_id) & 0xFF;
    byte2 = (byte2 + byte1) & 0xFF;
    for (let i = 0; i < payload.length; i++) {
      byte1 = (byte1 + payload[i]) & 0xFF;
      byte2 = (byte2 + byte1) & 0xFF;
    }
    
    // Build complete frame
    const frame = Buffer.alloc(BASIC_DEFAULT_HEADER_SIZE + payloadSize + BASIC_DEFAULT_FOOTER_SIZE);
    frame[0] = BASIC_DEFAULT_START_BYTE1;
    frame[1] = BASIC_DEFAULT_START_BYTE2;
    frame[2] = payloadSize & 0xFF;
    frame[3] = msg_id;
    payload.copy(frame, BASIC_DEFAULT_HEADER_SIZE);
    frame[frame.length - 2] = byte1;
    frame[frame.length - 1] = byte2;
    
    // Write to file
    const outputPath = fs.existsSync('tests/generated/js') 
      ? 'tests/generated/js/javascript_basic_default_test_data.bin'
      : 'javascript_basic_default_test_data.bin';
    fs.writeFileSync(outputPath, frame);

    return true;
  } catch (error) {
    printFailureDetails('Create test data exception: ' + error);
    return false;
  }
}

function main() {
  console.log('\n[TEST START] JavaScript Basic Default Serialization');
  
  try {
    if (!createTestData()) {
      console.log('[TEST END] JavaScript Basic Default Serialization: FAIL\n');
      return false;
    }

    console.log('[TEST END] JavaScript Basic Default Serialization: PASS\n');
    return true;
  } catch (error) {
    printFailureDetails('Exception: ' + error);
    console.log('[TEST END] JavaScript Basic Default Serialization: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

module.exports.main = main;
