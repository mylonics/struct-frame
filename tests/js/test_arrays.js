/**
 * Array operations test for JavaScript struct-frame.
 * Human-readable JavaScript version of the TypeScript test.
 */
"use strict";

function printFailureDetails(label, expectedValues, actualValues, rawData) {
  console.log('\n============================================================');
  console.log('FAILURE DETAILS: ' + label);
  console.log('============================================================');
  
  if (expectedValues) {
    console.log('\nExpected Values:');
    for (const [key, val] of Object.entries(expectedValues)) {
      console.log('  ' + key + ': ' + val);
    }
  }
  
  if (actualValues) {
    console.log('\nActual Values:');
    for (const [key, val] of Object.entries(actualValues)) {
      console.log('  ' + key + ': ' + val);
    }
  }
  
  if (rawData && rawData.length > 0) {
    console.log('\nRaw Data (' + rawData.length + ' bytes):');
    console.log('  Hex: ' + rawData.toString('hex').substring(0, 128) + (rawData.length > 64 ? '...' : ''));
  }
  
  console.log('============================================================\n');
}

let comprehensive_arrays_ComprehensiveArrayMessage;
let comprehensive_arrays_Sensor;
let msg_encode;
let struct_frame_buffer;
let basic_frame_config;

try {
  const comprehensiveArraysModule = require('./comprehensive_arrays.sf');
  const structFrameModule = require('./struct_frame');
  const structFrameTypesModule = require('./struct_frame_types');

  comprehensive_arrays_ComprehensiveArrayMessage = comprehensiveArraysModule.comprehensive_arrays_ComprehensiveArrayMessage;
  comprehensive_arrays_Sensor = comprehensiveArraysModule.comprehensive_arrays_Sensor;
  msg_encode = structFrameModule.msg_encode;
  struct_frame_buffer = structFrameTypesModule.struct_frame_buffer;
  basic_frame_config = structFrameTypesModule.basic_frame_config;
} catch (error) {
  // Skip test if generated modules are not available (before code generation)
}

function main() {
  console.log('\n[TEST START] JavaScript Array Operations');
  
  // Check if required modules are loaded
  if (!comprehensive_arrays_ComprehensiveArrayMessage || !comprehensive_arrays_Sensor || 
      !msg_encode || !struct_frame_buffer || !basic_frame_config) {
    console.log('[TEST SKIP] JavaScript Array Operations: Generated code not available\n');
    return true; // Return success for skip case
  }
  
  try {
    // Create a message with array data
    const msg = new comprehensive_arrays_ComprehensiveArrayMessage();
    
    // Fixed arrays of primitives
    msg.fixed_ints = [1, 2, 3];
    msg.fixed_floats = [1.1, 2.2];
    msg.fixed_bools = [1, 0, 1, 0]; // booleans as uint8
    
    // Bounded arrays of primitives
    msg.bounded_uints_count = 3;
    msg.bounded_uints_data = [100, 200, 300];
    
    msg.bounded_doubles_count = 2;
    msg.bounded_doubles_data = [123.456, 789.012];
    
    // Fixed string arrays
    msg.fixed_strings = [
      { value: 'String1' },
      { value: 'String2' }
    ];
    
    // Bounded string arrays
    msg.bounded_strings_count = 2;
    msg.bounded_strings_data = [
      { value: 'BoundedStr1' },
      { value: 'BoundedStr2' }
    ];
    
    // Enum arrays
    msg.fixed_statuses = [1, 2]; // ACTIVE, ERROR
    msg.bounded_statuses_count = 2;
    msg.bounded_statuses_data = [1, 3]; // ACTIVE, MAINTENANCE
    
    // Nested message arrays
    const sensor1 = new comprehensive_arrays_Sensor();
    sensor1.id = 1;
    sensor1.value = 25.5;
    sensor1.status = 1; // ACTIVE
    sensor1.name = 'Temp1';
    msg.fixed_sensors = [sensor1];
    
    const sensor3 = new comprehensive_arrays_Sensor();
    sensor3.id = 3;
    sensor3.value = 15.5;
    sensor3.status = 2; // ERROR
    sensor3.name = 'Pressure';
    
    msg.bounded_sensors_count = 1;
    msg.bounded_sensors_data = [sensor3];
    
    // Try to encode the message
    const buffer = new struct_frame_buffer(1024);
    buffer.config = basic_frame_config;
    msg_encode(buffer, msg, 203);
    
    if (buffer.size === 0) {
      printFailureDetails('Empty encoded data',
        { encoded_size: '>0' },
        { encoded_size: buffer.size }
      );
      console.log('[TEST END] JavaScript Array Operations: FAIL\n');
      return false;
    }
    
    console.log('[TEST END] JavaScript Array Operations: PASS\n');
    return true;
  } catch (error) {
    printFailureDetails('Exception: ' + error);
    console.log('[TEST END] JavaScript Array Operations: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

module.exports.main = main;
