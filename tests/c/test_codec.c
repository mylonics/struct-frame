/**
 * Test codec - Encode/decode functions for all frame formats.
 */

#include "test_codec.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "frame_parsers.h"
#include "frame_compat.h"
#include "serialization_test.sf.h"

/* Expected test values (from expected_values.json) */
static const uint32_t EXPECTED_MAGIC_NUMBER = 3735928559; /* 0xDEADBEEF */
static const char* EXPECTED_TEST_STRING = "Cross-platform test!";
static const float EXPECTED_TEST_FLOAT = 3.14159f;
static const bool EXPECTED_TEST_BOOL = true;
static const int32_t EXPECTED_TEST_ARRAY[] = {100, 200, 300};
static const size_t EXPECTED_TEST_ARRAY_COUNT = 3;

void create_test_message(SerializationTestSerializationTestMessage* msg) {
  memset(msg, 0, sizeof(*msg));

  msg->magic_number = EXPECTED_MAGIC_NUMBER;
  msg->test_string.length = strlen(EXPECTED_TEST_STRING);
  strncpy(msg->test_string.data, EXPECTED_TEST_STRING, msg->test_string.length);
  msg->test_float = EXPECTED_TEST_FLOAT;
  msg->test_bool = EXPECTED_TEST_BOOL;
  msg->test_array.count = EXPECTED_TEST_ARRAY_COUNT;
  for (size_t i = 0; i < EXPECTED_TEST_ARRAY_COUNT; i++) {
    msg->test_array.data[i] = EXPECTED_TEST_ARRAY[i];
  }
}

bool validate_test_message(const SerializationTestSerializationTestMessage* msg) {
  if (msg->magic_number != EXPECTED_MAGIC_NUMBER) {
    printf("  Value mismatch: magic_number (expected %u, got %u)\n", EXPECTED_MAGIC_NUMBER, msg->magic_number);
    return false;
  }

  if (strncmp(msg->test_string.data, EXPECTED_TEST_STRING, msg->test_string.length) != 0) {
    printf("  Value mismatch: test_string (expected '%s', got '%.*s')\n", EXPECTED_TEST_STRING,
           (int)msg->test_string.length, msg->test_string.data);
    return false;
  }

  if (fabs(msg->test_float - EXPECTED_TEST_FLOAT) > 0.0001f) {
    printf("  Value mismatch: test_float (expected %f, got %f)\n", EXPECTED_TEST_FLOAT, msg->test_float);
    return false;
  }

  if (msg->test_bool != EXPECTED_TEST_BOOL) {
    printf("  Value mismatch: test_bool (expected %d, got %d)\n", EXPECTED_TEST_BOOL, msg->test_bool);
    return false;
  }

  if (msg->test_array.count != EXPECTED_TEST_ARRAY_COUNT) {
    printf("  Value mismatch: test_array.count (expected %zu, got %u)\n", EXPECTED_TEST_ARRAY_COUNT,
           msg->test_array.count);
    return false;
  }

  for (size_t i = 0; i < EXPECTED_TEST_ARRAY_COUNT; i++) {
    if (msg->test_array.data[i] != EXPECTED_TEST_ARRAY[i]) {
      printf("  Value mismatch: test_array[%zu] (expected %d, got %d)\n", i, EXPECTED_TEST_ARRAY[i],
             msg->test_array.data[i]);
      return false;
    }
  }

  return true;
}

bool encode_test_message(const char* format, uint8_t* buffer, size_t buffer_size, size_t* encoded_size) {
  SerializationTestSerializationTestMessage msg;
  create_test_message(&msg);

  *encoded_size = 0;

  // Support profile names (preferred) and legacy direct format names
  if (strcmp(format, "profile_standard") == 0 || strcmp(format, "basic_default") == 0) {
    *encoded_size = basic_default_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                         (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (strcmp(format, "profile_sensor") == 0 || strcmp(format, "tiny_minimal") == 0) {
    *encoded_size = tiny_minimal_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                        (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (strcmp(format, "profile_bulk") == 0 || strcmp(format, "basic_extended") == 0) {
    *encoded_size = basic_extended_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                          (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (strcmp(format, "profile_network") == 0 || strcmp(format, "basic_extended_multi_system_stream") == 0) {
    *encoded_size = basic_extended_multi_system_stream_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                                               (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (strcmp(format, "basic_minimal") == 0) {
    *encoded_size = basic_minimal_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                         (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else if (strcmp(format, "tiny_default") == 0) {
    *encoded_size = tiny_default_encode(buffer, buffer_size, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                        (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);
  } else {
    printf("  Unknown frame format: %s\n", format);
    return false;
  }

  return *encoded_size > 0;
}

bool decode_test_message(const char* format, const uint8_t* buffer, size_t buffer_size,
                         SerializationTestSerializationTestMessage* msg) {
  frame_msg_info_t decode_result;

  // Support profile names (preferred) and legacy direct format names
  if (strcmp(format, "profile_standard") == 0 || strcmp(format, "basic_default") == 0) {
    decode_result = basic_default_validate_packet(buffer, buffer_size);
  } else if (strcmp(format, "profile_sensor") == 0 || strcmp(format, "tiny_minimal") == 0) {
    decode_result = tiny_minimal_validate_packet(buffer, buffer_size);
  } else if (strcmp(format, "profile_bulk") == 0 || strcmp(format, "basic_extended") == 0) {
    decode_result = basic_extended_validate_packet(buffer, buffer_size);
  } else if (strcmp(format, "profile_network") == 0 || strcmp(format, "basic_extended_multi_system_stream") == 0) {
    decode_result = basic_extended_multi_system_stream_validate_packet(buffer, buffer_size);
  } else if (strcmp(format, "basic_minimal") == 0) {
    decode_result = basic_minimal_validate_packet(buffer, buffer_size);
  } else if (strcmp(format, "tiny_default") == 0) {
    decode_result = tiny_default_validate_packet(buffer, buffer_size);
  } else {
    printf("  Unknown frame format: %s\n", format);
    return false;
  }

  if (!decode_result.valid) {
    return false;
  }

  memcpy(msg, decode_result.msg_data, sizeof(*msg));
  return true;
}
