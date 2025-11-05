#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Include the header files that will be generated
// Note: These will be generated when the test suite runs
#include "basic_types.sf.h"
#include "struct_frame_default_frame.h"

// Debug printing function for BasicTypesMessage
void print_basic_types_message(const char* label, const BasicTypesBasicTypesMessage* msg) {
  printf("=== %s ===\n", label);
  printf("  small_int: %d\n", msg->small_int);
  printf("  medium_int: %d\n", msg->medium_int);
  printf("  regular_int: %d\n", msg->regular_int);
  printf("  large_int: %lld\n", msg->large_int);
  printf("  small_uint: %u\n", msg->small_uint);
  printf("  medium_uint: %u\n", msg->medium_uint);
  printf("  regular_uint: %u\n", msg->regular_uint);
  printf("  large_uint: %llu\n", msg->large_uint);
  printf("  single_precision: %.6f\n", msg->single_precision);
  printf("  double_precision: %.15f\n", msg->double_precision);
  printf("  flag: %s\n", msg->flag ? "true" : "false");
  printf("  device_id: '%s'\n", msg->device_id);
  printf("  description: '%s'\n", msg->description);
  printf("\n");
}

#define ASSERT_WITH_DEBUG(condition, msg1, msg2)           \
  do {                                                     \
    if (!(condition)) {                                    \
      printf("❌ ASSERTION FAILED: %s\n", #condition);     \
      print_basic_types_message("ORIGINAL MESSAGE", msg1); \
      print_basic_types_message("DECODED MESSAGE", msg2);  \
      assert(condition);                                   \
    }                                                      \
  } while (0)

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
  ASSERT_WITH_DEBUG(decoded_msg.small_int == -42, &msg, &decoded_msg);
  ASSERT_WITH_DEBUG(decoded_msg.medium_int == -1000, &msg, &decoded_msg);
  ASSERT_WITH_DEBUG(decoded_msg.regular_int == -100000, &msg, &decoded_msg);
  ASSERT_WITH_DEBUG(decoded_msg.large_int == -1000000000LL, &msg, &decoded_msg);

  ASSERT_WITH_DEBUG(decoded_msg.small_uint == 255, &msg, &decoded_msg);
  ASSERT_WITH_DEBUG(decoded_msg.medium_uint == 65535, &msg, &decoded_msg);
  ASSERT_WITH_DEBUG(decoded_msg.regular_uint == 4294967295U, &msg, &decoded_msg);
  ASSERT_WITH_DEBUG(decoded_msg.large_uint == 18446744073709551615ULL, &msg, &decoded_msg);

  ASSERT_WITH_DEBUG(decoded_msg.single_precision == 3.14159f, &msg, &decoded_msg);
  ASSERT_WITH_DEBUG(decoded_msg.double_precision == 2.718281828459045, &msg, &decoded_msg);

  ASSERT_WITH_DEBUG(decoded_msg.flag == true, &msg, &decoded_msg);

  ASSERT_WITH_DEBUG(strncmp(decoded_msg.device_id, "TEST_DEVICE_12345678901234567890", 32) == 0, &msg, &decoded_msg);
  ASSERT_WITH_DEBUG(decoded_msg.description.length == strlen("Test description for basic types"), &msg, &decoded_msg);
  ASSERT_WITH_DEBUG(
      strncmp(decoded_msg.description.data, "Test description for basic types", decoded_msg.description.length) == 0,
      &msg, &decoded_msg);

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