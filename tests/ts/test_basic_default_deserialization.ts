/**
 * Basic Default frame format deserialization test for TypeScript.
 */
import * as fs from 'fs';
import * as path from 'path';

// BasicDefault constants
const BASIC_DEFAULT_START_BYTE1 = 0x90;
const BASIC_DEFAULT_START_BYTE2 = 0x71;
const BASIC_DEFAULT_HEADER_SIZE = 4;
const BASIC_DEFAULT_FOOTER_SIZE = 2;

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

function validateBasicDefault(buffer: Buffer, expected: any): boolean {
  if (buffer.length < BASIC_DEFAULT_HEADER_SIZE + BASIC_DEFAULT_FOOTER_SIZE) {
    console.log('  Data too short');
    return false;
  }

  if (buffer[0] !== BASIC_DEFAULT_START_BYTE1 || buffer[1] !== BASIC_DEFAULT_START_BYTE2) {
    console.log('  Invalid start bytes');
    return false;
  }

  if (buffer[3] !== 204) {
    console.log('  Invalid message ID');
    return false;
  }

  const msgLen = buffer.length - BASIC_DEFAULT_HEADER_SIZE - BASIC_DEFAULT_FOOTER_SIZE;
  let byte1 = buffer[2];
  let byte2 = buffer[2];
  byte1 = (byte1 + buffer[3]) % 256;
  byte2 = (byte2 + byte1) % 256;
  for (let i = 0; i < msgLen; i++) {
    byte1 = (byte1 + buffer[BASIC_DEFAULT_HEADER_SIZE + i]) & 0xFF;
    byte2 = (byte2 + byte1) & 0xFF;
  }
  
  if (byte1 !== buffer[buffer.length - 2] || byte2 !== buffer[buffer.length - 1]) {
    console.log('  Checksum mismatch');
    return false;
  }

  const magicNumber = buffer.readUInt32LE(BASIC_DEFAULT_HEADER_SIZE);
  if (magicNumber !== expected.magic_number) {
    console.log('  Magic number mismatch');
    return false;
  }

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

    if (!validateBasicDefault(binaryData, expected)) {
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
  console.log('\n[TEST START] TypeScript Basic Default Deserialization');

  const args = process.argv.slice(2);
  if (args.length !== 1) {
    console.log(`  Usage: ${process.argv[1]} <binary_file>`);
    console.log('[TEST END] TypeScript Basic Default Deserialization: FAIL\n');
    return false;
  }

  try {
    const success = readAndValidateTestData(args[0]);

    console.log(`[TEST END] TypeScript Basic Default Deserialization: ${success ? 'PASS' : 'FAIL'}\n`);
    return success;
  } catch (error) {
    printFailureDetails(`Exception: ${error}`);
    console.log('[TEST END] TypeScript Basic Default Deserialization: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

export { main };
