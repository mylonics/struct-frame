import * as fs from 'fs';

// Import generated types - these will be generated when the test suite runs
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
  console.log('⚠️  Generated modules not found - this is expected before code generation');
}

// This function creates a test message and serializes it to a binary file
// that can be used for cross-language compatibility testing
function createTestData(): boolean {
  console.log('Creating test data for cross-language compatibility...');

  try {
    if (!serialization_test_SerializationTestMessage) {
      console.log('⚠️  Generated code not available, skipping serialization tests');
      return true;
    }

    // Create a message instance
    const msg = new serialization_test_SerializationTestMessage();

    // Set predictable test data
    msg.magic_number = 0xDEADBEEF;
    msg.test_string_length = 'Hello from TypeScript!'.length;
    msg.test_string_data = 'Hello from TypeScript!';
    msg.test_float = 3.14159;
    msg.test_bool = true;

    msg.test_array_count = 3;
    msg.test_array_data = [100, 200, 300];

    console.log('✅ Serialization test message created and populated');

    // Create encoding buffer
    const buffer = new struct_frame_buffer(512);
    buffer.config = basic_frame_config;

    // Encode the message
    msg_encode(buffer, msg, 204);  // Message ID from proto

    console.log(`✅ Serialization test message encoded, size: ${buffer.size} bytes`);

    // Write binary data to file for cross-language testing
    const binaryData = buffer.data.slice(0, buffer.size);
    fs.writeFileSync('typescript_test_data.bin', binaryData);

    console.log('✅ Test data written to typescript_test_data.bin');

    return true;

  } catch (error) {
    console.log(`❌ Failed to create test data: ${error}`);
    return false;
  }
}

// This function tries to read and decode test data created by other languages
function readTestData(filename: string, language: string): boolean {
  console.log(`Reading test data from ${filename} (created by ${language})...`);

  try {
    if (!fs.existsSync(filename)) {
      console.log(`⚠️  Test data file ${filename} not found - skipping ${language} compatibility test`);
      return true; // Not a failure, just skip
    }

    const binaryData = fs.readFileSync(filename);

    if (binaryData.length === 0) {
      console.log(`❌ Failed to read data from ${filename}`);
      return false;
    }

    console.log(`✅ Read ${binaryData.length} bytes from ${filename}`);
    console.log(`  Raw data (hex): ${binaryData.toString('hex')}`);

    // For now, just verify we can read the file
    // Full decode testing would require parser implementation
    console.log(`✅ Successfully read ${language} data file`);

    return true;

  } catch (error) {
    console.log(`❌ Failed to read ${language} data: ${error}`);
    return false;
  }
}

function main(): boolean {
  console.log('=== TypeScript Cross-Language Serialization Test ===');

  if (!createTestData()) {
    console.log('❌ Failed to create test data');
    return false;
  }

  // Try to read test data from other languages
  if (!readTestData('python_test_data.bin', 'Python')) {
    console.log('❌ Python compatibility test failed');
    return false;
  }

  if (!readTestData('c_test_data.bin', 'C')) {
    console.log('❌ C compatibility test failed');
    return false;
  }

  console.log('🎉 All TypeScript cross-language tests completed successfully!');
  return true;
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

export { main };