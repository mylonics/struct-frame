/**
 * Tiny Minimal frame format serialization test for JavaScript.
 */
"use strict";

const fs = require('fs');
const path = require('path');

// TinyMinimal constants
const TINY_MINIMAL_START_BYTE = 0x70;
const TINY_MINIMAL_HEADER_SIZE = 2;  // start + msg_id
const TINY_MINIMAL_FOOTER_SIZE = 0;  // no crc

function printFailureDetails(label) {
  console.log('\n============================================================');
  console.log('FAILURE DETAILS: ' + label);
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
    
    // Build complete frame (no CRC for minimal)
    const frame = Buffer.alloc(TINY_MINIMAL_HEADER_SIZE + payloadSize + TINY_MINIMAL_FOOTER_SIZE);
    frame[0] = TINY_MINIMAL_START_BYTE;
    frame[1] = msg_id;
    payload.copy(frame, TINY_MINIMAL_HEADER_SIZE);
    
    // Write to file
    const outputPath = fs.existsSync('tests/generated/js') 
      ? 'tests/generated/js/javascript_tiny_minimal_test_data.bin'
      : 'javascript_tiny_minimal_test_data.bin';
    fs.writeFileSync(outputPath, frame);

    return true;
  } catch (error) {
    printFailureDetails('Create test data exception: ' + error);
    return false;
  }
}

function main() {
  console.log('\n[TEST START] JavaScript Tiny Minimal Serialization');
  
  try {
    if (!createTestData()) {
      console.log('[TEST END] JavaScript Tiny Minimal Serialization: FAIL\n');
      return false;
    }

    console.log('[TEST END] JavaScript Tiny Minimal Serialization: PASS\n');
    return true;
  } catch (error) {
    printFailureDetails('Exception: ' + error);
    console.log('[TEST END] JavaScript Tiny Minimal Serialization: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

module.exports.main = main;
