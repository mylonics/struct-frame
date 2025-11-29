/**
 * Basic types test for JavaScript struct-frame.
 * Human-readable JavaScript version of the TypeScript test.
 */
"use strict";

function printFailureDetails(label, rawData) {
  console.log('\n============================================================');
  console.log('FAILURE DETAILS: ' + label);
  console.log('============================================================');
  
  if (rawData && rawData.length > 0) {
    console.log('\nRaw Data (' + rawData.length + ' bytes):');
    console.log('  Hex: ' + rawData.toString('hex').substring(0, 128) + (rawData.length > 64 ? '...' : ''));
  }
  
  console.log('============================================================\n');
}

let basic_types_BasicTypesMessage;
let msg_encode;
let struct_frame_buffer;
let basic_frame_config;

try {
  const basicTypesModule = require('./basic_types.sf');
  const structFrameModule = require('./struct_frame');
  const structFrameTypesModule = require('./struct_frame_types');

  basic_types_BasicTypesMessage = basicTypesModule.basic_types_BasicTypesMessage;
  msg_encode = structFrameModule.msg_encode;
  struct_frame_buffer = structFrameTypesModule.struct_frame_buffer;
  basic_frame_config = structFrameTypesModule.basic_frame_config;
} catch (error) {
  // Skip test if generated modules are not available (before code generation)
}

function testBasicTypes() {
  console.log('\n[TEST START] JavaScript Basic Types');
  
  try {
    const msg = new basic_types_BasicTypesMessage();
    msg.small_int = -42;
    msg.medium_int = -1000;
    msg.regular_int = -100000;
    msg.large_int = BigInt(-1000000000);
    msg.small_uint = 255;
    msg.medium_uint = 65535;
    msg.regular_uint = 4294967295;
    msg.large_uint = BigInt(1844674407370955);
    msg.single_precision = 3.14159;
    msg.double_precision = 2.718281828459045;
    msg.flag = true;
    msg.device_id = 'TEST_DEVICE_12345678901234567890';
    msg.description_length = 'Test description for basic types'.length;
    msg.description_data = 'Test description for basic types';

    const buffer = new struct_frame_buffer(1024);
    buffer.config = basic_frame_config;
    msg_encode(buffer, msg, 201);

    console.log('[TEST END] JavaScript Basic Types: PASS\n');
    return true;

  } catch (error) {
    printFailureDetails('Exception: ' + error);
    console.log('[TEST END] JavaScript Basic Types: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = testBasicTypes();
  process.exit(success ? 0 : 1);
}

module.exports.testBasicTypes = testBasicTypes;
