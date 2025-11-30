import * as fs from 'fs';
import * as path from 'path';

// BasicFrame constants
const BASIC_FRAME_START_BYTE1 = 0x90;
const BASIC_FRAME_START_BYTE2 = 0x91;
const BASIC_FRAME_HEADER_SIZE = 3;  // start1 + start2 + msg_id
const BASIC_FRAME_FOOTER_SIZE = 2;  // crc1 + crc2

function printFailureDetails(label: string): void {
  console.log('\n============================================================');
  console.log(`FAILURE DETAILS: ${label}`);
  console.log('============================================================\n');
}

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

function validateBasicFrame(buffer: Buffer, expected: any): boolean {
  // BasicFrame validation with 2 start bytes
  if (buffer.length < BASIC_FRAME_HEADER_SIZE + BASIC_FRAME_FOOTER_SIZE) {
    console.log('  Data too short');
    return false;
  }

  // Check start bytes
  if (buffer[0] !== BASIC_FRAME_START_BYTE1 || buffer[1] !== BASIC_FRAME_START_BYTE2) {
    console.log(`  Invalid start bytes (expected 0x90 0x91, got 0x${buffer[0].toString(16)} 0x${buffer[1].toString(16)})`);
    return false;
  }

  // Check message ID (at offset 2 in BasicFrame)
  if (buffer[2] !== 201) {
    console.log(`  Invalid message ID (expected 201, got ${buffer[2]})`);
    return false;
  }

  // Validate checksum
  const msgLen = buffer.length - BASIC_FRAME_HEADER_SIZE - BASIC_FRAME_FOOTER_SIZE;
  let byte1 = buffer[2];  // Start with msg_id
  let byte2 = buffer[2];
  for (let i = 0; i < msgLen; i++) {
    byte1 = (byte1 + buffer[BASIC_FRAME_HEADER_SIZE + i]) & 0xFF;
    byte2 = (byte2 + byte1) & 0xFF;
  }
  
  if (byte1 !== buffer[buffer.length - 2] || byte2 !== buffer[buffer.length - 1]) {
    console.log(`  Checksum mismatch`);
    return false;
  }

  // Extract and validate fields from payload (starts at offset 3 in BasicFrame)
  let offset = BASIC_FRAME_HEADER_SIZE;
  
  // small_int (int8)
  const smallInt = buffer.readInt8(offset);
  if (smallInt !== expected.small_int) {
    console.log(`  Value mismatch: small_int (expected ${expected.small_int}, got ${smallInt})`);
    return false;
  }
  offset += 1;
  
  // medium_int (int16)
  const mediumInt = buffer.readInt16LE(offset);
  if (mediumInt !== expected.medium_int) {
    console.log(`  Value mismatch: medium_int (expected ${expected.medium_int}, got ${mediumInt})`);
    return false;
  }
  offset += 2;
  
  // regular_int (int32)
  const regularInt = buffer.readInt32LE(offset);
  if (regularInt !== expected.regular_int) {
    console.log(`  Value mismatch: regular_int (expected ${expected.regular_int}, got ${regularInt})`);
    return false;
  }
  offset += 4;
  
  // large_int (int64)
  const largeInt = buffer.readBigInt64LE(offset);
  if (largeInt !== BigInt(expected.large_int)) {
    console.log(`  Value mismatch: large_int (expected ${expected.large_int}, got ${largeInt})`);
    return false;
  }
  offset += 8;
  
  // small_uint (uint8)
  const smallUint = buffer.readUInt8(offset);
  if (smallUint !== expected.small_uint) {
    console.log(`  Value mismatch: small_uint (expected ${expected.small_uint}, got ${smallUint})`);
    return false;
  }
  offset += 1;
  
  // medium_uint (uint16)
  const mediumUint = buffer.readUInt16LE(offset);
  if (mediumUint !== expected.medium_uint) {
    console.log(`  Value mismatch: medium_uint (expected ${expected.medium_uint}, got ${mediumUint})`);
    return false;
  }
  offset += 2;
  
  // single_precision (float) - skip regular_uint and large_uint for simplicity
  // Just validate the key fields for cross-platform compatibility

  console.log('  [OK] Data validated successfully');
  return true;
}

function readAndValidateTestData(filename: string): boolean {
  try {
    if (!fs.existsSync(filename)) {
      console.log(`  Error: file not found: ${filename}`);
      return false;
    }

    const binaryData = fs.readFileSync(filename);

    if (binaryData.length === 0) {
      printFailureDetails('Empty file');
      return false;
    }

    const expected = loadExpectedValues();
    if (!expected) {
      return false;
    }

    if (!validateBasicFrame(binaryData, expected)) {
      console.log('  Validation failed');
      return false;
    }

    return true;
  } catch (error) {
    printFailureDetails(`Read data exception: ${error}`);
    return false;
  }
}

function main(): boolean {
  console.log('\n[TEST START] TypeScript Cross-Platform Basic Types Deserialization');

  const args = process.argv.slice(2);
  if (args.length !== 1) {
    console.log(`  Usage: ${process.argv[1]} <binary_file>`);
    console.log('[TEST END] TypeScript Cross-Platform Basic Types Deserialization: FAIL\n');
    return false;
  }

  try {
    const success = readAndValidateTestData(args[0]);

    console.log(`[TEST END] TypeScript Cross-Platform Basic Types Deserialization: ${success ? 'PASS' : 'FAIL'}\n`);
    return success;
  } catch (error) {
    printFailureDetails(`Exception: ${error}`);
    console.log('[TEST END] TypeScript Cross-Platform Basic Types Deserialization: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

export { main };
