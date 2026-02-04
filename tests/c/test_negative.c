/**
 * Negative tests for struct-frame C parser
 * 
 * Tests error handling for:
 * - Corrupted CRC/checksum
 * - Truncated frames
 * - Invalid start bytes
 * - Malformed data
 * 
 * Note: C API uses buffer_writer_t/buffer_reader_t which differs from C++/Python.
 * These tests use a simplified approach focusing on the buffer reader API.
 */

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "frame_profiles.h"
#include "serialization_test.structframe.h"

// Test result tracking
static int tests_run = 0;
static int tests_passed = 0;
static int tests_failed = 0;

/**
 * Helper to create a test message
 */
static void create_test_message(SerializationTestBasicTypesMessage* msg) {
  memset(msg, 0, sizeof(*msg));
  msg->small_int = 42;
  msg->medium_int = 1000;
  msg->regular_int = 100000;
  msg->large_int = 1000000000LL;
  msg->small_uint = 200;
  msg->medium_uint = 50000;
  msg->regular_uint = 3000000000U;
  msg->large_uint = 9000000000000000000ULL;
  msg->single_precision = 3.14159f;
  msg->double_precision = 2.71828;
  msg->flag = true;
  strncpy(msg->device_id, "DEVICE123", sizeof(msg->device_id) - 1);
  msg->description.length = 11;
  strncpy(msg->description.data, "Test device", 63);
}

/**
 * Test: Parser rejects frame with corrupted CRC
 */
bool test_corrupted_crc(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);
  
  // Create writer and encode
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));
  
  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);
  
  size_t frame_size = buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload, payload_size, 0, 0, 0, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  if (frame_size < 4) return false;
  
  // Corrupt the CRC (last 2 bytes)
  buffer[frame_size - 1] ^= 0xFF;
  buffer[frame_size - 2] ^= 0xFF;
  
  // Try to parse - should fail
  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, frame_size, NULL);
  frame_msg_info_t result = buffer_reader_next(&reader);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser rejects truncated frame
 */
bool test_truncated_frame(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);
  
  // Create writer and encode
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));
  
  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);
  
  size_t frame_size = buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload, payload_size, 0, 0, 0, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  if (frame_size < 10) return false;
  
  // Truncate the frame
  size_t truncated = frame_size - 5;
  
  // Try to parse - should fail
  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, truncated, NULL);
  frame_msg_info_t result = buffer_reader_next(&reader);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser rejects frame with invalid start bytes
 */
bool test_invalid_start_bytes(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);
  
  // Create writer and encode
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));
  
  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);
  
  size_t frame_size = buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload, payload_size, 0, 0, 0, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  if (frame_size < 2) return false;
  
  // Corrupt start bytes
  buffer[0] = 0xDE;
  buffer[1] = 0xAD;
  
  // Try to parse - should fail
  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, frame_size, NULL);
  frame_msg_info_t result = buffer_reader_next(&reader);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser handles zero-length buffer
 */
bool test_zero_length_buffer(void) {
  uint8_t buffer[1024];
  
  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, 0, NULL);
  frame_msg_info_t result = buffer_reader_next(&reader);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser handles corrupted length field
 */
bool test_corrupted_length(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);
  
  // Create writer and encode
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));
  
  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);
  
  size_t frame_size = buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload, payload_size, 0, 0, 0, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  if (frame_size < 4) return false;
  
  // Corrupt length field (byte 2 for ProfileStandard)
  buffer[2] = 0xFF;
  
  // Try to parse - should fail
  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, frame_size, NULL);
  frame_msg_info_t result = buffer_reader_next(&reader);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Streaming parser rejects corrupted CRC
 */
bool test_streaming_corrupted_crc(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);
  
  // Create writer and encode
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));
  
  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);
  
  size_t frame_size = buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload, payload_size, 0, 0, 0, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  if (frame_size < 4) return false;
  
  // Corrupt CRC
  buffer[frame_size - 1] ^= 0xFF;
  
  // Allocate internal buffer for accumulating reader
  uint8_t internal_buffer[1024];
  
  // Try streaming parse
  accumulating_reader_t reader;
  accumulating_reader_init(&reader, &PROFILE_STANDARD_CONFIG, internal_buffer, sizeof(internal_buffer), NULL);
  
  // Feed byte by byte
  for (size_t i = 0; i < frame_size; i++) {
    accumulating_reader_push_byte(&reader, buffer[i]);
  }
  
  frame_msg_info_t result = accumulating_reader_next(&reader);
  return !result.valid;  // Expect failure
}

// Test function pointer type
typedef bool (*TestFunc)(void);

// Test case structure
typedef struct {
  const char* name;
  TestFunc func;
} TestCase;

int main(void) {
  printf("\n========================================\n");
  printf("NEGATIVE TESTS - C Parser\n");
  printf("========================================\n\n");
  
  // Define test matrix
  TestCase tests[] = {
    {"Corrupted CRC detection", test_corrupted_crc},
    {"Truncated frame detection", test_truncated_frame},
    {"Invalid start bytes detection", test_invalid_start_bytes},
    {"Zero-length buffer handling", test_zero_length_buffer},
    {"Corrupted length field detection", test_corrupted_length},
    {"Streaming: Corrupted CRC detection", test_streaming_corrupted_crc}
  };
  
  int num_tests = sizeof(tests) / sizeof(tests[0]);
  
  printf("Testing error handling for invalid frames:\n\n");
  
  // Run all tests from the matrix
  for (int i = 0; i < num_tests; i++) {
    printf("  [TEST] %s... ", tests[i].name);
    tests_run++;
    
    if (tests[i].func()) {
      printf("PASS\n");
      tests_passed++;
    } else {
      printf("FAIL\n");
      tests_failed++;
    }
  }
  
  printf("\n========================================\n");
  printf("RESULTS\n");
  printf("========================================\n");
  printf("Tests run:    %d\n", tests_run);
  printf("Tests passed: %d\n", tests_passed);
  printf("Tests failed: %d\n", tests_failed);
  printf("========================================\n\n");
  
  return tests_failed > 0 ? 1 : 0;
}
