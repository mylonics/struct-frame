/**
 * Frame format deserialization test for TypeScript.
 * 
 * This test reads binary files and deserializes using different frame formats.
 * Usage: test_frame_format_deserialization.ts <frame_format> <binary_file>
 */
import * as fs from 'fs';
import * as path from 'path';

function printFailureDetails(label: string): void {
  console.log('\n============================================================');
  console.log(`FAILURE DETAILS: ${label}`);
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

function validateFrameFormat(buffer: Buffer, frameFormat: string, expected: any): boolean {
  const config = FRAME_FORMATS[frameFormat];
  if (!config) {
    console.log(`  Unknown frame format: ${frameFormat}`);
    return false;
  }

  // Check minimum length
  if (buffer.length < config.headerSize + config.footerSize) {
    console.log(`  Data too short for ${frameFormat} format`);
    return false;
  }

  // Check start bytes
  for (let i = 0; i < config.start.length; i++) {
    if (buffer[i] !== config.start[i]) {
      console.log(`  Invalid start byte at position ${i} (expected 0x${config.start[i].toString(16)}, got 0x${buffer[i].toString(16)})`);
      return false;
    }
  }

  // Validate CRC if present
  if (config.footerSize > 0) {
    let byte1 = 0;
    let byte2 = 0;
    const checksumStart = config.start.length;
    const checksumEnd = buffer.length - config.footerSize;
    
    for (let i = checksumStart; i < checksumEnd; i++) {
      byte1 = (byte1 + buffer[i]) & 0xFF;
      byte2 = (byte2 + byte1) & 0xFF;
    }
    
    if (byte1 !== buffer[buffer.length - 2] || byte2 !== buffer[buffer.length - 1]) {
      console.log(`  Checksum mismatch`);
      return false;
    }
  }

  // Extract magic number from payload
  const payloadStart = config.headerSize;
  const magicNumber = buffer.readUInt32LE(payloadStart);
  if (magicNumber !== expected.magic_number) {
    console.log(`  Magic number mismatch (expected ${expected.magic_number}, got ${magicNumber})`);
    return false;
  }

  console.log(`  [OK] Data validated successfully with ${frameFormat} format`);
  return true;
}

function readAndValidateTestData(frameFormat: string, filename: string): boolean {
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

    if (!validateFrameFormat(binaryData, frameFormat, expected)) {
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
  console.log('\n[TEST START] TypeScript Frame Format Deserialization');

  const args = process.argv.slice(2);
  if (args.length !== 2) {
    console.log(`  Usage: ${process.argv[1]} <frame_format> <binary_file>`);
    console.log('  Supported formats:');
    for (const fmt of Object.keys(FRAME_FORMATS)) {
      console.log(`    ${fmt}`);
    }
    console.log('[TEST END] TypeScript Frame Format Deserialization: FAIL\n');
    return false;
  }

  try {
    const success = readAndValidateTestData(args[0], args[1]);

    console.log(`[TEST END] TypeScript Frame Format Deserialization: ${success ? 'PASS' : 'FAIL'}\n`);
    return success;
  } catch (error) {
    printFailureDetails(`Exception: ${error}`);
    console.log('[TEST END] TypeScript Frame Format Deserialization: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

export { main };
