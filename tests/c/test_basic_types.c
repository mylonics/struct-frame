#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Include the header files that will be generated
// Note: These will be generated when the test suite runs
#include "basic_types.sf.h"
#include "struct_frame_default_frame.h"

int test_basic_types() {
  printf("Testing Basic Types C Implementation...\n");

  // Create a message instance
  BasicTypesBasicTypesMessage msg = {0};

  // Set all fields with test data
  msg.small_int = -42;
  msg.medium_int = -1000;
  msg.regular_int = -100000;
  msg.large_int = -1000000000LL;

  msg.small_uint = 255;
  msg.medium_uint = 65535;
  msg.regular_uint = 4294967295U;
  msg.large_uint = 18446744073709551615ULL;

  msg.single_precision = 3.14159f;
  msg.double_precision = 2.718281828459045;

  msg.flag = true;

  // Fixed string - exactly 32 chars
  strncpy(msg.device_id, "TEST_DEVICE_12345678901234567890", 32);

  // Variable string
  msg.description.length = strlen("Test description for basic types");
  strncpy(msg.description.data, "Test description for basic types", msg.description.length);

  // Create encoding buffer
  uint8_t encode_buffer[1024];
  msg_encode_buffer buffer = {0};
  buffer.data = encode_buffer;

  // Encode the message
  packet_format_t* format = &default_frame_format;
  bool encoded = basic_types_basic_types_message_encode(&buffer, format, &msg);

  if (!encoded) {
    printf("❌ Failed to encode message\n");
    return 0;
  }

  printf("✅ Message encoded successfully, size: %d bytes\n", buffer.size);

  // Decode the message
  msg_info_t decode_result = format->validate_packet(encode_buffer, buffer.size);

  if (!decode_result.valid) {
    printf("❌ Failed to validate packet\n");
    return 0;
  }

  // Get decoded message
  BasicTypesBasicTypesMessage decoded_msg = basic_types_basic_types_message_get(decode_result);

  // Verify the data
  assert(decoded_msg.small_int == -42);
  assert(decoded_msg.medium_int == -1000);
  assert(decoded_msg.regular_int == -100000);
  assert(decoded_msg.large_int == -1000000000LL);

  assert(decoded_msg.small_uint == 255);
  assert(decoded_msg.medium_uint == 65535);
  assert(decoded_msg.regular_uint == 4294967295U);
  assert(decoded_msg.large_uint == 18446744073709551615ULL);

  assert(decoded_msg.single_precision == 3.14159f);
  assert(decoded_msg.double_precision == 2.718281828459045);

  assert(decoded_msg.flag == true);

  assert(strncmp(decoded_msg.device_id, "TEST_DEVICE_12345678901234567890", 32) == 0);
  assert(decoded_msg.description.length == strlen("Test description for basic types"));
  assert(strncmp(decoded_msg.description.data, "Test description for basic types", decoded_msg.description.length) ==
         0);

  printf("✅ All basic types serialization/deserialization tests passed!\n");
  return 1;
}

int main() {
  printf("=== C Basic Types Test ===\n");

  if (!test_basic_types()) {
    printf("❌ Basic types tests failed\n");
    return 1;
  }

  printf("🎉 All C basic types tests completed successfully!\n");
  return 0;
}