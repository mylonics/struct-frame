#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "serialization_test.sf.h"
#include "struct_frame_default_frame.h"

// Debug printing function for SerializationTestMessage
void print_serialization_message(const char* label, const SerializationTestSerializationTestMessage* msg) {
  printf("=== %s ===\n", label);
  printf("  magic_number: 0x%X\n", msg->magic_number);
  printf("  test_string: length=%d, data='%.*s'\n", msg->test_string.length, msg->test_string.length,
         msg->test_string.data);
  printf("  test_float: %.6f\n", msg->test_float);
  printf("  test_bool: %s\n", msg->test_bool ? "true" : "false");
  printf("\n");
}

#define ASSERT_SERIALIZATION_WITH_DEBUG(condition, msg1, msg2) \
  do {                                                         \
    if (!(condition)) {                                        \
      printf("❌ ASSERTION FAILED: %s\n", #condition);         \
      print_serialization_message("ORIGINAL MESSAGE", msg1);   \
      print_serialization_message("DECODED MESSAGE", msg2);    \
      assert(condition);                                       \
    }                                                          \
  } while (0)

// This program creates a test message and serializes it to a binary file
// that can be used for cross-language compatibility testing
int create_test_data() {
  printf("Creating test data for cross-language compatibility...\n");

  SerializationTestSerializationTestMessage msg = {0};

  // Set predictable test data
  msg.magic_number = 0xDEADBEEF;
  msg.test_string.length = strlen("Hello from C!");
  strncpy(msg.test_string.data, "Hello from C!", msg.test_string.length);
  msg.test_float = 3.14159f;
  msg.test_bool = true;

  msg.test_array.count = 3;
  msg.test_array.data[0] = 100;
  msg.test_array.data[1] = 200;
  msg.test_array.data[2] = 300;

  // Create encoding buffer
  uint8_t encode_buffer[512];
  msg_encode_buffer buffer = {0};
  buffer.data = encode_buffer;

  // Encode the message
  packet_format_t* format = &default_frame_format;
  bool encoded = serialization_test_serialization_test_message_encode(&buffer, format, &msg);

  if (!encoded) {
    printf("❌ Failed to encode serialization test message\n");
    return 0;
  }

  printf("✅ Serialization test message encoded, size: %d bytes\n", buffer.size);

  // Write binary data to file for cross-language testing
  FILE* file = fopen("c_test_data.bin", "wb");
  if (!file) {
    printf("❌ Failed to create test data file\n");
    return 0;
  }

  fwrite(encode_buffer, 1, buffer.size, file);
  fclose(file);

  printf("✅ Test data written to c_test_data.bin\n");

  // Verify we can decode our own data
  msg_info_t decode_result = format->validate_packet(encode_buffer, buffer.size);

  if (!decode_result.valid) {
    printf("❌ Failed to validate our own packet\n");
    return 0;
  }

  SerializationTestSerializationTestMessage decoded_msg =
      serialization_test_serialization_test_message_get(decode_result);

  // Verify the decoded data matches
  ASSERT_SERIALIZATION_WITH_DEBUG(decoded_msg.magic_number == 0xDEADBEEF, &msg, &decoded_msg);
  ASSERT_SERIALIZATION_WITH_DEBUG(decoded_msg.test_string.length == strlen("Hello from C!"), &msg, &decoded_msg);
  ASSERT_SERIALIZATION_WITH_DEBUG(
      strncmp(decoded_msg.test_string.data, "Hello from C!", decoded_msg.test_string.length) == 0, &msg, &decoded_msg);
  ASSERT_SERIALIZATION_WITH_DEBUG(decoded_msg.test_float == 3.14159f, &msg, &decoded_msg);
  ASSERT_SERIALIZATION_WITH_DEBUG(decoded_msg.test_bool == true, &msg, &decoded_msg);
  ASSERT_SERIALIZATION_WITH_DEBUG(decoded_msg.test_array.count == 3, &msg, &decoded_msg);
  ASSERT_SERIALIZATION_WITH_DEBUG(decoded_msg.test_array.data[0] == 100, &msg, &decoded_msg);
  ASSERT_SERIALIZATION_WITH_DEBUG(decoded_msg.test_array.data[1] == 200, &msg, &decoded_msg);
  ASSERT_SERIALIZATION_WITH_DEBUG(decoded_msg.test_array.data[2] == 300, &msg, &decoded_msg);

  printf("✅ Self-verification passed!\n");
  return 1;
}

// This function tries to read and decode test data created by other languages
int read_test_data(const char* filename, const char* language) {
  printf("Reading test data from %s (created by %s)...\n", filename, language);

  FILE* file = fopen(filename, "rb");
  if (!file) {
    printf("⚠️  Test data file %s not found - skipping %s compatibility test\n", filename, language);
    return 1;  // Not a failure, just skip
  }

  // Read the binary data
  uint8_t buffer[512];
  size_t size = fread(buffer, 1, sizeof(buffer), file);
  fclose(file);

  if (size == 0) {
    printf("❌ Failed to read data from %s\n", filename);
    return 0;
  }

  // Decode the message
  packet_format_t* format = &default_frame_format;
  msg_info_t decode_result = format->validate_packet(buffer, size);

  if (!decode_result.valid) {
    printf("❌ Failed to decode %s data\n", language);
    return 0;
  }

  SerializationTestSerializationTestMessage decoded_msg =
      serialization_test_serialization_test_message_get(decode_result);

  // Print the decoded data
  printf("✅ Successfully decoded %s data:\n", language);
  printf("  magic_number: 0x%X\n", decoded_msg.magic_number);
  printf("  test_string: '%.*s'\n", decoded_msg.test_string.length, decoded_msg.test_string.data);
  printf("  test_float: %f\n", decoded_msg.test_float);
  printf("  test_bool: %s\n", decoded_msg.test_bool ? "true" : "false");
  printf("  test_array: [");
  for (int i = 0; i < decoded_msg.test_array.count; i++) {
    printf("%d", decoded_msg.test_array.data[i]);
    if (i < decoded_msg.test_array.count - 1) printf(", ");
  }
  printf("]\n");

  return 1;
}

int main() {
  printf("=== C Cross-Language Serialization Test ===\n");

  if (!create_test_data()) {
    printf("❌ Failed to create test data\n");
    return 1;
  }

  // Try to read test data from other languages
  if (!read_test_data("python_test_data.bin", "Python")) {
    printf("❌ Python compatibility test failed\n");
    return 1;
  }

  if (!read_test_data("typescript_test_data.bin", "TypeScript")) {
    printf("❌ TypeScript compatibility test failed\n");
    return 1;
  }

  printf("🎉 All C cross-language tests completed successfully!\n");
  return 0;
}