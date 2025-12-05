/**
 * Basic Minimal frame format serialization test for TypeScript.
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

function createTestData(): boolean {
  try {
    const expected = loadExpectedValues();
    if (!expected) {
      return false;
    }

    const msg_id = 204;
    const payloadSize = 95;
    const payload = Buffer.alloc(payloadSize);
    let offset = 0;
    
    payload.writeUInt32LE(expected.magic_number, offset);
    offset += 4;
    
    const testString = expected.test_string;
    payload.writeUInt8(testString.length, offset);
    offset += 1;
    Buffer.from(testString).copy(payload, offset, 0, testString.length);
    offset += 64;
    
    payload.writeFloatLE(expected.test_float, offset);
    offset += 4;
    
    payload.writeUInt8(expected.test_bool ? 1 : 0, offset);
    offset += 1;
    
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
    
    const frame = Buffer.alloc(BASIC_MINIMAL_HEADER_SIZE + payloadSize + BASIC_MINIMAL_FOOTER_SIZE);
    frame[0] = BASIC_MINIMAL_START_BYTE1;
    frame[1] = BASIC_MINIMAL_START_BYTE2;
    frame[2] = msg_id;
    payload.copy(frame, BASIC_MINIMAL_HEADER_SIZE);
    
    const outputPath = fs.existsSync('tests/generated/ts/js') 
      ? 'tests/generated/ts/js/typescript_basic_minimal_test_data.bin'
      : 'typescript_basic_minimal_test_data.bin';
    fs.writeFileSync(outputPath, frame);

    return true;
  } catch (error) {
    printFailureDetails(`Create test data exception: ${error}`);
    return false;
  }
}

function main(): boolean {
  console.log('\n[TEST START] TypeScript Basic Minimal Serialization');
  
  try {
    if (!createTestData()) {
      console.log('[TEST END] TypeScript Basic Minimal Serialization: FAIL\n');
      return false;
    }

    console.log('[TEST END] TypeScript Basic Minimal Serialization: PASS\n');
    return true;
  } catch (error) {
    printFailureDetails(`Exception: ${error}`);
    console.log('[TEST END] TypeScript Basic Minimal Serialization: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

export { main };
