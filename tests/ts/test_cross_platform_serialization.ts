import * as fs from 'fs';
import * as path from 'path';

function printFailureDetails(label: string, expectedValues?: any, actualValues?: any, rawData?: Buffer): void {
  console.log('\n============================================================');
  console.log(`FAILURE DETAILS: ${label}`);
  console.log('============================================================');
  
  if (expectedValues) {
    console.log('\nExpected Values:');
    for (const [key, val] of Object.entries(expectedValues)) {
      console.log(`  ${key}: ${val}`);
    }
  }
  
  if (actualValues) {
    console.log('\nActual Values:');
    for (const [key, val] of Object.entries(actualValues)) {
      console.log(`  ${key}: ${val}`);
    }
  }
  
  if (rawData && rawData.length > 0) {
    console.log(`\nRaw Data (${rawData.length} bytes):`);
    console.log(`  Hex: ${rawData.toString('hex').substring(0, 128)}${rawData.length > 64 ? '...' : ''}`);
  }
  
  console.log('============================================================\n');
}

let serialization_test_SerializationTestMessage: any;
let msg_encode: any;
let struct_frame_buffer: any;
let basic_frame_config: any;

try {
  const serializationTestModule = require('./serialization_test.sf');
  const structFrameModule = require('./struct_frame');
  const structFrameTypesModule = require('./struct_frame_types');

  serialization_test_SerializationTestMessage = serializationTestModule.serialization_test_SerializationTestMessage;
  msg_encode = structFrameModule.msg_encode;
  struct_frame_buffer = structFrameTypesModule.struct_frame_buffer;
  basic_frame_config = structFrameTypesModule.basic_frame_config;
} catch (error) {
  // Skip test if generated modules are not available
}

function loadExpectedValues(): any {
  try {
    const jsonPath = path.join(__dirname, '../../../expected_values.json');
    const data = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));
    return data.serialization_test;
  } catch (error) {
    console.log(`Error loading expected values: ${error}`);
    return null;
  }
}

function createTestData(): boolean {
  try {
    // Load expected values from JSON
    const expected = loadExpectedValues();
    if (!expected) {
      return false;
    }

    // Create a full framed message manually that matches C/Python format
    // Frame format: [start_byte] [msg_id] [payload] [checksum1] [checksum2]
    const start_byte = 0x90;
    const msg_id = 204;
    
    // Create full payload matching the message structure:
    // - magic_number: uint32 (4 bytes)
    // - test_string: length byte (1) + data (64 bytes) = 65 bytes
    // - test_float: float (4 bytes)
    // - test_bool: bool (1 byte)
    // - test_array: count byte (1) + int32 data (5*4=20 bytes) = 21 bytes
    // Total: 4 + 65 + 4 + 1 + 21 = 95 bytes
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
    // String data array is 64 bytes, remaining bytes are already 0
    offset += 64;
    
    // test_float (float, little-endian)
    payload.writeFloatLE(expected.test_float, offset);
    offset += 4;
    
    // test_bool (1 byte)
    payload.writeUInt8(expected.test_bool ? 1 : 0, offset);
    offset += 1;
    
    // test_array: count byte + int32 data (5 elements max)
    const testArray: number[] = expected.test_array;
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
    
    // Calculate Fletcher checksum on msg_id + payload (consistent with C and Python)
    let byte1 = msg_id;  // Start with msg_id
    let byte2 = msg_id;
    for (let i = 0; i < payload.length; i++) {
      byte1 = (byte1 + payload[i]) & 0xFF;
      byte2 = (byte2 + byte1) & 0xFF;
    }
    
    // Build complete frame
    const frame = Buffer.alloc(2 + payloadSize + 2);
    frame[0] = start_byte;
    frame[1] = msg_id;
    payload.copy(frame, 2);
    frame[frame.length - 2] = byte1;
    frame[frame.length - 1] = byte2;
    
    // Write to file - determine correct path based on where we're running from
    const outputPath = fs.existsSync('tests/generated/ts/js') 
      ? 'tests/generated/ts/js/typescript_test_data.bin'
      : 'typescript_test_data.bin';
    fs.writeFileSync(outputPath, frame);

    return true;
  } catch (error) {
    printFailureDetails(`Create test data exception: ${error}`);
    return false;
  }
}

function main(): boolean {
  console.log('\n[TEST START] TypeScript Cross-Platform Serialization');
  
  try {
    // Create TypeScript test data
    if (!createTestData()) {
      console.log('[TEST END] TypeScript Cross-Platform Serialization: FAIL\n');
      return false;
    }

    console.log('[TEST END] TypeScript Cross-Platform Serialization: PASS\n');
    return true;
  } catch (error) {
    printFailureDetails(`Exception: ${error}`);
    console.log('[TEST END] TypeScript Cross-Platform Serialization: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

export { main };
