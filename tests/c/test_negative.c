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
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, frame_size, get_message_info);
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
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, truncated, get_message_info);
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
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, frame_size, get_message_info);
  frame_msg_info_t result = buffer_reader_next(&reader);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser handles zero-length buffer
 */
bool test_zero_length_buffer(void) {
  uint8_t buffer[1024];
  
  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, 0, get_message_info);
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
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, frame_size, get_message_info);
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
  accumulating_reader_init(&reader, &PROFILE_STANDARD_CONFIG, internal_buffer, sizeof(internal_buffer), get_message_info);
  
  // Feed byte by byte
  for (size_t i = 0; i < frame_size; i++) {
    accumulating_reader_push_byte(&reader, buffer[i]);
  }
  
  frame_msg_info_t result = accumulating_reader_next(&reader);
  return !result.valid;  // Expect failure
}

/**
 * Test: Streaming parser handles garbage data
 */
bool test_streaming_garbage(void) {
  // Allocate internal buffer for accumulating reader
  uint8_t internal_buffer[1024];
  
  // Create accumulating reader
  accumulating_reader_t reader;
  accumulating_reader_init(&reader, &PROFILE_STANDARD_CONFIG, internal_buffer, sizeof(internal_buffer), get_message_info);
  
  // Feed garbage bytes
  uint8_t garbage[] = {0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56, 0x78, 0x9A};
  
  for (size_t i = 0; i < sizeof(garbage); i++) {
    accumulating_reader_push_byte(&reader, garbage[i]);
  }
  
  frame_msg_info_t result = accumulating_reader_next(&reader);
  return !result.valid;  // Expect no valid frame
}

/**
 * Test: Multiple frames with corrupted middle frame
 */
bool test_multiple_corrupted_frames(void) {
  uint8_t buffer[4096];
  SerializationTestBasicTypesMessage msg;
  
  // Create writer
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));
  
  // Write three frames
  create_test_message(&msg);
  msg.small_int = 1;
  
  uint8_t payload1[256];
  size_t payload_size1 = SerializationTestBasicTypesMessage_serialize(&msg, payload1);
  buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                     payload1, payload_size1, 0, 0, 0, 0,
                     SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                     SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  size_t first_frame_end = buffer_writer_size(&writer);
  
  msg.small_int = 2;
  uint8_t payload2[256];
  size_t payload_size2 = SerializationTestBasicTypesMessage_serialize(&msg, payload2);
  buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                     payload2, payload_size2, 0, 0, 0, 0,
                     SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                     SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  size_t second_frame_end = buffer_writer_size(&writer);
  
  msg.small_int = 3;
  uint8_t payload3[256];
  size_t payload_size3 = SerializationTestBasicTypesMessage_serialize(&msg, payload3);
  buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                     payload3, payload_size3, 0, 0, 0, 0,
                     SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                     SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  size_t total_size = buffer_writer_size(&writer);
  
  // Corrupt the second frame's CRC (last 2 bytes before third frame)
  buffer[second_frame_end - 1] ^= 0xFF;
  buffer[second_frame_end - 2] ^= 0xFF;
  
  // Parse all frames
  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, total_size, get_message_info);
  
  // First should be valid
  frame_msg_info_t result1 = buffer_reader_next(&reader);
  if (!result1.valid) return false;
  
  // Second should be invalid
  frame_msg_info_t result2 = buffer_reader_next(&reader);
  return !result2.valid;  // Expect failure on second frame
}

/**
 * Test: Bulk profile with corrupted CRC
 */
bool test_bulk_profile_corrupted_crc(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);
  
  // Create writer with bulk profile
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_BULK_CONFIG, buffer, sizeof(buffer));
  
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
  buffer_reader_init(&reader, &PROFILE_BULK_CONFIG, buffer, frame_size, get_message_info);
  frame_msg_info_t result = buffer_reader_next(&reader);
  
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
    {"Bulk profile: Corrupted CRC", test_bulk_profile_corrupted_crc},
    {"Corrupted CRC detection", test_corrupted_crc},
    {"Corrupted length field detection", test_corrupted_length},
    {"Invalid start bytes detection", test_invalid_start_bytes},
    {"Multiple frames: Corrupted middle frame", test_multiple_corrupted_frames},
    {"Streaming: Corrupted CRC detection", test_streaming_corrupted_crc},
    {"Streaming: Garbage data handling", test_streaming_garbage},
    {"Truncated frame detection", test_truncated_frame},
    {"Zero-length buffer handling", test_zero_length_buffer}
  };
  
  int num_tests = sizeof(tests) / sizeof(tests[0]);
  
  printf("Test Results Matrix:\n\n");
  printf("%-50s %6s\n", "Test Name", "Result");
  printf("%-50s %6s\n", "==================================================", "======");
  
  // Run all tests from the matrix
  for (int i = 0; i < num_tests; i++) {
    tests_run++;
    bool passed = tests[i].func();
    
    printf("%-50s %6s\n", tests[i].name, passed ? "PASS" : "FAIL");
    
    if (passed) {
      tests_passed++;
    } else {
      tests_failed++;
    }
  }
  
  printf("\n========================================\n");
  printf("Summary: %d/%d tests passed\n", tests_passed, tests_run);
  printf("========================================\n\n");
  
  return tests_failed > 0 ? 1 : 0;
}
