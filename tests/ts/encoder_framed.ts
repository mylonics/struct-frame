#!/usr/bin/env node
// Encoder for cross-platform testing with framing
// Encodes a SerializationTestMessage with framing and writes to stdout

const serializationTestModule = require('./serialization_test.sf');
const structFrameModule = require('./struct_frame');
const structFrameTypesModule = require('./struct_frame_types');

const serialization_test_SerializationTestMessage = serializationTestModule.serialization_test_SerializationTestMessage;
const msg_encode = structFrameModule.msg_encode;
const struct_frame_buffer = structFrameTypesModule.struct_frame_buffer;
const basic_frame_config = structFrameTypesModule.basic_frame_config;

try {
  // Create a message instance
  const msg = new serialization_test_SerializationTestMessage();

  // Set test data
  msg.magic_number = 0xDEADBEEF;
  // Skip string fields due to typed-struct library bug with String setters
  msg.test_string_length = 0;
  // msg.test_string_data would crash, so leave it empty
  msg.test_float = 3.14159;
  msg.test_bool = true;
  msg.test_array_count = 3;
  // Set array elements individually
  msg.test_array_data[0] = 100;
  msg.test_array_data[1] = 200;
  msg.test_array_data[2] = 300;

  // Create encoding buffer
  const buffer = new struct_frame_buffer(512);
  buffer.config = basic_frame_config;

  // Encode the message
  msg_encode(buffer, msg, 204);  // Message ID from proto

  // Write binary data to stdout
  const binaryData = buffer.data.slice(0, buffer.size);
  process.stdout.write(binaryData);
} catch (error) {
  process.stderr.write(`ERROR: Failed to encode: ${error}\n`);
  process.exit(1);
}
