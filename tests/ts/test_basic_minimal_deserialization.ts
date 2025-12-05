/**
 * Basic Minimal frame format deserialization test for TypeScript.
 */
import * as fs from 'fs';
import * as path from 'path';

// BasicMinimal constants
const BASIC_MINIMAL_START_BYTE1 = 0x90;
const BASIC_MINIMAL_START_BYTE2 = 0x70;
const BASIC_MINIMAL_HEADER_SIZE = 3;
const BASIC_MINIMAL_FOOTER_SIZE = 0;

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

function validateBasicMinimal(buffer: Buffer, expected: any): boolean {
  if (buffer.length < BASIC_MINIMAL_HEADER_SIZE + BASIC_MINIMAL_FOOTER_SIZE) {
    console.log('  Data too short');
    return false;
  }

  if (buffer[0] !== BASIC_MINIMAL_START_BYTE1 || buffer[1] !== BASIC_MINIMAL_START_BYTE2) {
    console.log('  Invalid start bytes');
    return false;
  }

  if (buffer[2] !== 204) {
    console.log('  Invalid message ID');
    return false;
  }

  const magicNumber = buffer.readUInt32LE(BASIC_MINIMAL_HEADER_SIZE);
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

    if (!validateBasicMinimal(binaryData, expected)) {
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
  console.log('\n[TEST START] TypeScript Basic Minimal Deserialization');

  const args = process.argv.slice(2);
  if (args.length !== 1) {
    console.log(`  Usage: ${process.argv[1]} <binary_file>`);
    console.log('[TEST END] TypeScript Basic Minimal Deserialization: FAIL\n');
    return false;
  }

  try {
    const success = readAndValidateTestData(args[0]);

    console.log(`[TEST END] TypeScript Basic Minimal Deserialization: ${success ? 'PASS' : 'FAIL'}\n`);
    return success;
  } catch (error) {
    printFailureDetails(`Exception: ${error}`);
    console.log('[TEST END] TypeScript Basic Minimal Deserialization: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

export { main };
