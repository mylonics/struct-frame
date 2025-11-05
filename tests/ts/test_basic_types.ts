import * as fs from 'fs';
import * as path from 'path';

// Import generated types - these will be generated when the test suite runs
// Note: These imports will work after code generation
let basic_types_BasicTypesMessage: any;
let msg_encode: any;
let struct_frame_buffer: any;
let basic_frame_config: any;

try {
  const basicTypesModule = require('./basic_types.sf');
  const structFrameModule = require('./struct_frame');
  const structFrameTypesModule = require('./struct_frame_types');

  basic_types_BasicTypesMessage = basicTypesModule.basic_types_BasicTypesMessage;
  msg_encode = structFrameModule.msg_encode;
  struct_frame_buffer = structFrameTypesModule.struct_frame_buffer;
  basic_frame_config = structFrameTypesModule.basic_frame_config;
} catch (error) {
  console.log('⚠️  Generated modules not found - this is expected before code generation');
}

function testBasicTypes(): boolean {
  console.log('Testing Basic Types TypeScript Implementation...');

  try {
    // Create a message instance
    const msg = new basic_types_BasicTypesMessage();

    // Set all fields with test data
    msg.small_int = -42;
    msg.medium_int = -1000;
    msg.regular_int = -100000;
    msg.large_int = -1000000000;  // Use regular number for now

    msg.small_uint = 255;
    msg.medium_uint = 65535;
    msg.regular_uint = 4294967295;
    msg.large_uint = 1844674407370955; // Use regular number for now

    msg.single_precision = 3.14159;
    msg.double_precision = 2.718281828459045;

    msg.flag = true;

    // Fixed string - exactly 32 chars
    msg.device_id = 'TEST_DEVICE_12345678901234567890';

    // Variable string 
    msg.description_length = 'Test description for basic types'.length;
    msg.description_data = 'Test description for basic types';

    console.log('✅ Message created and populated with test data');

    // Create encoding buffer
    const buffer = new struct_frame_buffer(1024);
    buffer.config = basic_frame_config;

    // Encode the message
    msg_encode(buffer, msg, 201);  // Message ID from proto

    console.log(`✅ Message encoded successfully, size: ${buffer.size} bytes`);

    // For now, just verify we can create and encode without errors
    // Full decode testing would require parser implementation
    console.log('✅ Basic types TypeScript test completed');

    return true;

  } catch (error) {
    console.log(`❌ Basic types test failed: ${error}`);
    return false;
  }
}

function main(): boolean {
  console.log('=== TypeScript Basic Types Test ===');

  if (!testBasicTypes()) {
    console.log('❌ Basic types tests failed');
    return false;
  }

  console.log('🎉 All TypeScript basic types tests completed successfully!');
  return true;
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

export { main };