/**
 * Frame format serialization test for TypeScript.
 * 
 * This test serializes data using different frame formats and saves to binary files.
 * Usage: test_frame_format_serialization.ts <frame_format>
 */
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

interface FrameFormatConfig {
  start: number[];
  headerSize: number;
  footerSize: number;
  hasLength: boolean;
  lengthBytes: number;
}

// Frame format configurations
const FRAME_FORMATS: { [key: string]: FrameFormatConfig } = {
  'basic_default': { start: [0x90, 0x71], headerSize: 4, footerSize: 2, hasLength: true, lengthBytes: 1 },
  'basic_minimal': { start: [0x90, 0x70], headerSize: 3, footerSize: 0, hasLength: false, lengthBytes: 0 },
  'basic_seq': { start: [0x90, 0x76], headerSize: 5, footerSize: 2, hasLength: true, lengthBytes: 1 },
  'basic_sys_comp': { start: [0x90, 0x75], headerSize: 6, footerSize: 2, hasLength: true, lengthBytes: 1 },
  'basic_extended_msg_ids': { start: [0x90, 0x72], headerSize: 5, footerSize: 2, hasLength: true, lengthBytes: 1 },
  'basic_extended_length': { start: [0x90, 0x73], headerSize: 5, footerSize: 2, hasLength: true, lengthBytes: 2 },
  'basic_extended': { start: [0x90, 0x74], headerSize: 6, footerSize: 2, hasLength: true, lengthBytes: 2 },
  'basic_multi_system_stream': { start: [0x90, 0x77], headerSize: 7, footerSize: 2, hasLength: true, lengthBytes: 1 },
  'basic_extended_multi_system_stream': { start: [0x90, 0x78], headerSize: 9, footerSize: 2, hasLength: true, lengthBytes: 2 },
  'tiny_default': { start: [0x71], headerSize: 3, footerSize: 2, hasLength: true, lengthBytes: 1 },
  'tiny_minimal': { start: [0x70], headerSize: 2, footerSize: 0, hasLength: false, lengthBytes: 0 },
  'tiny_seq': { start: [0x76], headerSize: 4, footerSize: 2, hasLength: true, lengthBytes: 1 },
  'tiny_sys_comp': { start: [0x75], headerSize: 5, footerSize: 2, hasLength: true, lengthBytes: 1 },
  'tiny_extended_msg_ids': { start: [0x72], headerSize: 4, footerSize: 2, hasLength: true, lengthBytes: 1 },
  'tiny_extended_length': { start: [0x73], headerSize: 4, footerSize: 2, hasLength: true, lengthBytes: 2 },
  'tiny_extended': { start: [0x74], headerSize: 5, footerSize: 2, hasLength: true, lengthBytes: 2 },
  'tiny_multi_system_stream': { start: [0x77], headerSize: 6, footerSize: 2, hasLength: true, lengthBytes: 1 },
  'tiny_extended_multi_system_stream': { start: [0x78], headerSize: 8, footerSize: 2, hasLength: true, lengthBytes: 2 },
};

function createTestData(frameFormat: string): boolean {
  try {
    const config = FRAME_FORMATS[frameFormat];
    if (!config) {
      console.log(`  Unknown frame format: ${frameFormat}`);
      return false;
    }

    // Load expected values from JSON
    const expected = loadExpectedValues();
    if (!expected) {
      return false;
    }

    const msg_id = 204;
    
    // Create payload matching the message structure
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
    
    // Build frame based on format
    const totalSize = config.headerSize + payloadSize + config.footerSize;
    const frame = Buffer.alloc(totalSize);
    let frameOffset = 0;
    
    // Start bytes
    for (const b of config.start) {
      frame[frameOffset++] = b;
    }
    
    // Length field (if present)
    if (config.hasLength) {
      if (config.lengthBytes === 2) {
        frame.writeUInt16LE(payloadSize, frameOffset);
        frameOffset += 2;
      } else {
        frame[frameOffset++] = payloadSize & 0xFF;
      }
    }
    
    // Msg ID
    frame[frameOffset++] = msg_id;
    
    // Payload
    payload.copy(frame, frameOffset);
    frameOffset += payloadSize;
    
    // CRC (if present)
    if (config.footerSize > 0) {
      // Calculate Fletcher checksum starting after start bytes
      let byte1 = 0;
      let byte2 = 0;
      for (let i = config.start.length; i < frameOffset; i++) {
        byte1 = (byte1 + frame[i]) & 0xFF;
        byte2 = (byte2 + byte1) & 0xFF;
      }
      frame[frameOffset++] = byte1;
      frame[frameOffset++] = byte2;
    }
    
    // Write to file
    const outputPath = fs.existsSync('tests/generated/ts/js') 
      ? `tests/generated/ts/js/typescript_${frameFormat}_test_data.bin`
      : `typescript_${frameFormat}_test_data.bin`;
    fs.writeFileSync(outputPath, frame);

    console.log(`  [OK] Encoded with ${frameFormat} format (${frame.length} bytes) -> ${outputPath}`);
    return true;
  } catch (error) {
    printFailureDetails(`Create test data exception: ${error}`);
    return false;
  }
}

function main(): boolean {
  console.log('\n[TEST START] TypeScript Frame Format Serialization');
  
  const args = process.argv.slice(2);
  if (args.length !== 1) {
    console.log(`  Usage: ${process.argv[1]} <frame_format>`);
    console.log('  Supported formats:');
    for (const fmt of Object.keys(FRAME_FORMATS)) {
      console.log(`    ${fmt}`);
    }
    console.log('[TEST END] TypeScript Frame Format Serialization: FAIL\n');
    return false;
  }
  
  try {
    if (!createTestData(args[0])) {
      console.log('[TEST END] TypeScript Frame Format Serialization: FAIL\n');
      return false;
    }

    console.log('[TEST END] TypeScript Frame Format Serialization: PASS\n');
    return true;
  } catch (error) {
    printFailureDetails(`Exception: ${error}`);
    console.log('[TEST END] TypeScript Frame Format Serialization: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

export { main };
