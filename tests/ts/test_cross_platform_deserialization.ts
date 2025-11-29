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

function validateBasicFrame(buffer: Buffer, expected: any): boolean {
  // Very basic frame validation
  if (buffer.length < 4) {
    console.log('  Data too short');
    return false;
  }

  // Check start byte
  if (buffer[0] !== 0x90) {
    console.log('  Invalid start byte');
    return false;
  }

  // Check message ID
  if (buffer[1] !== 204) {
    console.log('  Invalid message ID');
    return false;
  }

  // Extract magic number from payload (starts at byte 2)
  const magicNumber = buffer.readUInt32LE(2);
  if (magicNumber !== expected.magic_number) {
    console.log(`  Magic number mismatch (expected ${expected.magic_number}, got ${magicNumber})`);
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
  console.log('\n[TEST START] TypeScript Cross-Platform Deserialization');

  const args = process.argv.slice(2);
  if (args.length !== 1) {
    console.log(`  Usage: ${process.argv[1]} <binary_file>`);
    console.log('[TEST END] TypeScript Cross-Platform Deserialization: FAIL\n');
    return false;
  }

  try {
    const success = readAndValidateTestData(args[0]);

    console.log(`[TEST END] TypeScript Cross-Platform Deserialization: ${success ? 'PASS' : 'FAIL'}\n`);
    return success;
  } catch (error) {
    printFailureDetails(`Exception: ${error}`);
    console.log('[TEST END] TypeScript Cross-Platform Deserialization: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

export { main };
