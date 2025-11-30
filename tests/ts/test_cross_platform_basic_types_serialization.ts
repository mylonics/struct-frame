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

// BasicFrame constants
const BASIC_FRAME_START_BYTE1 = 0x90;
const BASIC_FRAME_START_BYTE2 = 0x91;
const BASIC_FRAME_HEADER_SIZE = 3;  // start1 + start2 + msg_id
const BASIC_FRAME_FOOTER_SIZE = 2;  // crc1 + crc2

function loadExpectedValues(): any {
  try {
    const jsonPath = path.join(__dirname, '../../../expected_values.json');
    const data = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));
    return data.basic_types;
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

    // Create a full BasicFrame message that matches C/Python format
    // Frame format: [START1=0x90] [START2=0x91] [MSG_ID] [payload] [checksum1] [checksum2]
    const msg_id = 201;  // BASIC_TYPES_BASIC_TYPES_MESSAGE_MSG_ID
    
    // Create full payload matching the BasicTypesMessage structure:
    // - small_int: int8 (1 byte)
    // - medium_int: int16 (2 bytes)
    // - regular_int: int32 (4 bytes)
    // - large_int: int64 (8 bytes)
    // - small_uint: uint8 (1 byte)
    // - medium_uint: uint16 (2 bytes)
    // - regular_uint: uint32 (4 bytes)
    // - large_uint: uint64 (8 bytes)
    // - single_precision: float (4 bytes)
    // - double_precision: double (8 bytes)
    // - flag: bool (1 byte)
    // - device_id: char[32] (32 bytes)
    // - description: length byte (1) + data (128 bytes) = 129 bytes
    // Total: 1+2+4+8+1+2+4+8+4+8+1+32+129 = 204 bytes
    const payloadSize = 204;
    const payload = Buffer.alloc(payloadSize);
    let offset = 0;
    
    // small_int (int8)
    payload.writeInt8(expected.small_int, offset);
    offset += 1;
    
    // medium_int (int16, little-endian)
    payload.writeInt16LE(expected.medium_int, offset);
    offset += 2;
    
    // regular_int (int32, little-endian)
    payload.writeInt32LE(expected.regular_int, offset);
    offset += 4;
    
    // large_int (int64, little-endian)
    payload.writeBigInt64LE(BigInt(expected.large_int), offset);
    offset += 8;
    
    // small_uint (uint8)
    payload.writeUInt8(expected.small_uint, offset);
    offset += 1;
    
    // medium_uint (uint16, little-endian)
    payload.writeUInt16LE(expected.medium_uint, offset);
    offset += 2;
    
    // regular_uint (uint32, little-endian)
    payload.writeUInt32LE(expected.regular_uint, offset);
    offset += 4;
    
    // large_uint (uint64, little-endian) - handle string representation
    const largeUint = typeof expected.large_uint === 'string' 
      ? BigInt(expected.large_uint) 
      : BigInt(expected.large_uint);
    payload.writeBigUInt64LE(largeUint, offset);
    offset += 8;
    
    // single_precision (float, little-endian)
    payload.writeFloatLE(expected.single_precision, offset);
    offset += 4;
    
    // double_precision (double, little-endian)
    payload.writeDoubleLE(expected.double_precision, offset);
    offset += 8;
    
    // flag (bool, 1 byte)
    payload.writeUInt8(expected.flag ? 1 : 0, offset);
    offset += 1;
    
    // device_id: fixed string of 32 bytes
    const deviceId = expected.device_id;
    Buffer.from(deviceId).copy(payload, offset, 0, Math.min(deviceId.length, 32));
    offset += 32;
    
    // description: length byte + 128 bytes of data
    const description = expected.description;
    payload.writeUInt8(description.length, offset);
    offset += 1;
    Buffer.from(description).copy(payload, offset, 0, Math.min(description.length, 128));
    offset += 128;
    
    // Calculate Fletcher checksum on msg_id + payload (consistent with C and Python BasicFrame)
    let byte1 = msg_id;  // Start with msg_id
    let byte2 = msg_id;
    for (let i = 0; i < payload.length; i++) {
      byte1 = (byte1 + payload[i]) & 0xFF;
      byte2 = (byte2 + byte1) & 0xFF;
    }
    
    // Build complete frame with BasicFrame format
    const frame = Buffer.alloc(BASIC_FRAME_HEADER_SIZE + payloadSize + BASIC_FRAME_FOOTER_SIZE);
    frame[0] = BASIC_FRAME_START_BYTE1;
    frame[1] = BASIC_FRAME_START_BYTE2;
    frame[2] = msg_id;
    payload.copy(frame, BASIC_FRAME_HEADER_SIZE);
    frame[frame.length - 2] = byte1;
    frame[frame.length - 1] = byte2;
    
    // Write to file - determine correct path based on where we're running from
    const outputPath = fs.existsSync('tests/generated/ts/js') 
      ? 'tests/generated/ts/js/typescript_basic_types_test_data.bin'
      : 'typescript_basic_types_test_data.bin';
    fs.writeFileSync(outputPath, frame);

    return true;
  } catch (error) {
    printFailureDetails(`Create test data exception: ${error}`);
    return false;
  }
}

function main(): boolean {
  console.log('\n[TEST START] TypeScript Cross-Platform Basic Types Serialization');
  
  try {
    // Create TypeScript test data
    if (!createTestData()) {
      console.log('[TEST END] TypeScript Cross-Platform Basic Types Serialization: FAIL\n');
      return false;
    }

    console.log('[TEST END] TypeScript Cross-Platform Basic Types Serialization: PASS\n');
    return true;
  } catch (error) {
    printFailureDetails(`Exception: ${error}`);
    console.log('[TEST END] TypeScript Cross-Platform Basic Types Serialization: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

export { main };
