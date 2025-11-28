import * as fs from 'fs';
import * as path from 'path';

function printFailureDetails(label: string): void {
  console.log('\n============================================================');
  console.log(`FAILURE DETAILS: ${label}`);
  console.log('============================================================\n');
}

function loadExpectedValues(): any {
  try {
    const jsonPath = path.join(__dirname, '../../expected_values.json');
    const data = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));
    return data.serialization_test;
  } catch (error) {
    console.log(`Error loading expected values: ${error}`);
    return null;
  }
}

function validateBasicFrame(buffer: Buffer, language: string, expected: any): boolean {
  // Very basic frame validation
  if (buffer.length < 4) {
    console.log(`  ${language} data too short`);
    return false;
  }

  // Check start byte
  if (buffer[0] !== 0x90) {
    console.log(`  ${language} invalid start byte`);
    return false;
  }

  // Check message ID
  if (buffer[1] !== 204) {
    console.log(`  ${language} invalid message ID`);
    return false;
  }

  // Extract magic number from payload (starts at byte 2)
  const magicNumber = buffer.readUInt32LE(2);
  if (magicNumber !== expected.magic_number) {
    console.log(`  ${language} magic number mismatch (expected ${expected.magic_number}, got ${magicNumber})`);
    return false;
  }

  console.log(`  [OK] ${language} data validated successfully`);
  return true;
}

function readAndValidateTestData(filename: string, language: string): boolean {
  try {
    if (!fs.existsSync(filename)) {
      console.log(`  Skipping ${language} - file not found: ${filename}`);
      return true;  // Skip if file not available
    }

    const binaryData = fs.readFileSync(filename);

    if (binaryData.length === 0) {
      printFailureDetails(`Empty data from ${language}`);
      return false;
    }

    const expected = loadExpectedValues();
    if (!expected) {
      return false;
    }

    if (!validateBasicFrame(binaryData, language, expected)) {
      console.log(`  Validation failed for ${language} data`);
      return false;
    }

    return true;
  } catch (error) {
    printFailureDetails(`Read ${language} data exception: ${error}`);
    return false;
  }
}

function main(): boolean {
  console.log('\n[TEST START] TypeScript Cross-Platform Deserialization');

  try {
    let success = true;
    success = success && readAndValidateTestData('python_test_data.bin', 'Python');
    success = success && readAndValidateTestData('c_test_data.bin', 'C');
    success = success && readAndValidateTestData('cpp_test_data.bin', 'C++');
    success = success && readAndValidateTestData('typescript_test_data.bin', 'TypeScript');

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
