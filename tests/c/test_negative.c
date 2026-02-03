/**
 * Negative tests for struct-frame C parser
 * 
 * Tests error handling for:
 * - Corrupted CRC/checksum
 * - Truncated frames
 * - Invalid start bytes
 * - Invalid message IDs
 * - Malformed data
 */

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "../generated/c/frame_profiles.h"
#include "../generated/c/serialization_test.h"

// Test result tracking
static int tests_run = 0;
static int tests_passed = 0;
static int tests_failed = 0;

#define TEST(name) \
  printf("  [TEST] %s... ", name); \
  tests_run++; \
  if (

#define EXPECT_FAIL() \
  ) { \
    printf("PASS\n"); \
    tests_passed++; \
  } else { \
    printf("FAIL\n"); \
    tests_failed++; \
  }

/**
 * Test: Parser rejects frame with corrupted CRC
 */
bool test_corrupted_crc(void) {
  uint8_t buffer[1024];
  
  // Create a valid BasicTypesMessage
  BasicTypesMessage msg = {
    .small_int = 42,
    .medium_int = 1000,
    .regular_int = 100000,
    .large_int = 1000000000LL,
    .small_uint = 200,
    .medium_uint = 50000,
    .regular_uint = 3000000000U,
    .large_uint = 9000000000000000000ULL,
    .single_precision = 3.14159f,
    .double_precision = 2.71828,
    .flag = true
  };
  strcpy(msg.device_id, "DEVICE123");
  strcpy(msg.description, "Test device");
  msg.description_length = strlen(msg.description);
  
  // Encode message
  FrameEncoderStandard encoder;
  frame_encoder_standard_init(&encoder, buffer, sizeof(buffer));
  size_t bytes = basic_types_message_encode(&encoder, &msg);
  
  if (bytes < 4) return false;
  
  // Corrupt the CRC (last 2 bytes)
  buffer[bytes - 1] ^= 0xFF;
  buffer[bytes - 2] ^= 0xFF;
  
  // Try to parse - should fail
  FrameParserStandard parser;
  frame_parser_standard_init(&parser, buffer, bytes);
  FrameMsgInfo result = frame_parser_standard_next(&parser);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser rejects truncated frame
 */
bool test_truncated_frame(void) {
  uint8_t buffer[1024];
  
  // Create a valid message
  BasicTypesMessage msg = {
    .small_int = 42,
    .medium_int = 1000,
    .regular_int = 100000,
    .large_int = 1000000000LL,
    .small_uint = 200,
    .medium_uint = 50000,
    .regular_uint = 3000000000U,
    .large_uint = 9000000000000000000ULL,
    .single_precision = 3.14159f,
    .double_precision = 2.71828,
    .flag = true
  };
  strcpy(msg.device_id, "DEVICE123");
  strcpy(msg.description, "Test device");
  msg.description_length = strlen(msg.description);
  
  // Encode message
  FrameEncoderStandard encoder;
  frame_encoder_standard_init(&encoder, buffer, sizeof(buffer));
  size_t bytes = basic_types_message_encode(&encoder, &msg);
  
  if (bytes < 10) return false;
  
  // Truncate the frame
  size_t truncated = bytes - 5;
  
  // Try to parse - should fail
  FrameParserStandard parser;
  frame_parser_standard_init(&parser, buffer, truncated);
  FrameMsgInfo result = frame_parser_standard_next(&parser);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser rejects frame with invalid start bytes
 */
bool test_invalid_start_bytes(void) {
  uint8_t buffer[1024];
  
  // Create a valid message
  BasicTypesMessage msg = {
    .small_int = 42,
    .medium_int = 1000,
    .regular_int = 100000,
    .large_int = 1000000000LL,
    .small_uint = 200,
    .medium_uint = 50000,
    .regular_uint = 3000000000U,
    .large_uint = 9000000000000000000ULL,
    .single_precision = 3.14159f,
    .double_precision = 2.71828,
    .flag = true
  };
  strcpy(msg.device_id, "DEVICE123");
  strcpy(msg.description, "Test device");
  msg.description_length = strlen(msg.description);
  
  // Encode message
  FrameEncoderStandard encoder;
  frame_encoder_standard_init(&encoder, buffer, sizeof(buffer));
  size_t bytes = basic_types_message_encode(&encoder, &msg);
  
  if (bytes < 2) return false;
  
  // Corrupt start bytes
  buffer[0] = 0xDE;
  buffer[1] = 0xAD;
  
  // Try to parse - should fail
  FrameParserStandard parser;
  frame_parser_standard_init(&parser, buffer, bytes);
  FrameMsgInfo result = frame_parser_standard_next(&parser);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser handles zero-length buffer
 */
bool test_zero_length_buffer(void) {
  uint8_t buffer[1024];
  
  FrameParserStandard parser;
  frame_parser_standard_init(&parser, buffer, 0);
  FrameMsgInfo result = frame_parser_standard_next(&parser);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser handles corrupted length field
 */
bool test_corrupted_length(void) {
  uint8_t buffer[1024];
  
  // Create a valid message
  BasicTypesMessage msg = {
    .small_int = 42,
    .medium_int = 1000,
    .regular_int = 100000,
    .large_int = 1000000000LL,
    .small_uint = 200,
    .medium_uint = 50000,
    .regular_uint = 3000000000U,
    .large_uint = 9000000000000000000ULL,
    .single_precision = 3.14159f,
    .double_precision = 2.71828,
    .flag = true
  };
  strcpy(msg.device_id, "DEVICE123");
  strcpy(msg.description, "Test device");
  msg.description_length = strlen(msg.description);
  
  // Encode message
  FrameEncoderStandard encoder;
  frame_encoder_standard_init(&encoder, buffer, sizeof(buffer));
  size_t bytes = basic_types_message_encode(&encoder, &msg);
  
  if (bytes < 4) return false;
  
  // Corrupt length field (byte 2)
  buffer[2] = 0xFF;
  
  // Try to parse - should fail
  FrameParserStandard parser;
  frame_parser_standard_init(&parser, buffer, bytes);
  FrameMsgInfo result = frame_parser_standard_next(&parser);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Streaming parser rejects corrupted CRC
 */
bool test_streaming_corrupted_crc(void) {
  uint8_t buffer[1024];
  
  // Create a valid message
  BasicTypesMessage msg = {
    .small_int = 42,
    .medium_int = 1000,
    .regular_int = 100000,
    .large_int = 1000000000LL,
    .small_uint = 200,
    .medium_uint = 50000,
    .regular_uint = 3000000000U,
    .large_uint = 9000000000000000000ULL,
    .single_precision = 3.14159f,
    .double_precision = 2.71828,
    .flag = true
  };
  strcpy(msg.device_id, "DEVICE123");
  strcpy(msg.description, "Test device");
  msg.description_length = strlen(msg.description);
  
  // Encode message
  FrameEncoderStandard encoder;
  frame_encoder_standard_init(&encoder, buffer, sizeof(buffer));
  size_t bytes = basic_types_message_encode(&encoder, &msg);
  
  if (bytes < 4) return false;
  
  // Corrupt CRC
  buffer[bytes - 1] ^= 0xFF;
  
  // Try streaming parse
  AccumulatingReaderStandard reader;
  accumulating_reader_standard_init(&reader);
  
  // Feed byte by byte
  for (size_t i = 0; i < bytes; i++) {
    accumulating_reader_standard_push_byte(&reader, buffer[i]);
  }
  
  FrameMsgInfo result = accumulating_reader_standard_next(&reader);
  return !result.valid;  // Expect failure
}

/**
 * Test: Streaming parser handles garbage data
 */
bool test_streaming_garbage(void) {
  AccumulatingReaderStandard reader;
  accumulating_reader_standard_init(&reader);
  
  // Feed garbage bytes
  uint8_t garbage[] = {0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56, 0x78, 0x9A};
  
  for (size_t i = 0; i < sizeof(garbage); i++) {
    accumulating_reader_standard_push_byte(&reader, garbage[i]);
  }
  
  FrameMsgInfo result = accumulating_reader_standard_next(&reader);
  return !result.valid;  // Expect no valid frame
}

int main(void) {
  printf("\n========================================\n");
  printf("NEGATIVE TESTS - C Parser\n");
  printf("========================================\n\n");
  
  printf("Testing error handling for invalid frames:\n\n");
  
  TEST("Corrupted CRC detection")
    test_corrupted_crc()
  EXPECT_FAIL()
  
  TEST("Truncated frame detection")
    test_truncated_frame()
  EXPECT_FAIL()
  
  TEST("Invalid start bytes detection")
    test_invalid_start_bytes()
  EXPECT_FAIL()
  
  TEST("Zero-length buffer handling")
    test_zero_length_buffer()
  EXPECT_FAIL()
  
  TEST("Corrupted length field detection")
    test_corrupted_length()
  EXPECT_FAIL()
  
  TEST("Streaming: Corrupted CRC detection")
    test_streaming_corrupted_crc()
  EXPECT_FAIL()
  
  TEST("Streaming: Garbage data handling")
    test_streaming_garbage()
  EXPECT_FAIL()
  
  printf("\n========================================\n");
  printf("RESULTS\n");
  printf("========================================\n");
  printf("Tests run:    %d\n", tests_run);
  printf("Tests passed: %d\n", tests_passed);
  printf("Tests failed: %d\n", tests_failed);
  printf("========================================\n\n");
  
  return tests_failed > 0 ? 1 : 0;
}
