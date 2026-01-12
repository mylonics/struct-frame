#include "test_codec.h"

#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "frame_parsers.h"
#include "serialization_test.sf.h"
#include "test_messages_data.h"

/*
 * Frame format helper functions - Use generated profile functions from frame_profiles.h
 * The manual implementations have been replaced with calls to the generated functions.
 */

/* Basic + Default -> Profile Standard */
static inline size_t basic_default_encode(uint8_t* buffer, size_t buffer_size, uint16_t msg_id, const uint8_t* msg,
                                          size_t msg_size) {
  return encode_profile_standard(buffer, buffer_size, (uint8_t)msg_id, msg, msg_size);
}

static inline frame_msg_info_t basic_default_validate_packet(const uint8_t* buffer, size_t length) {
  return parse_profile_standard_buffer(buffer, length);
}

/* Tiny + Minimal -> Profile Sensor */
static inline size_t tiny_minimal_encode(uint8_t* buffer, size_t buffer_size, uint16_t msg_id, const uint8_t* msg,
                                         size_t msg_size) {
  return encode_profile_sensor(buffer, buffer_size, (uint8_t)msg_id, msg, msg_size);
}

static inline frame_msg_info_t tiny_minimal_validate_packet(const uint8_t* buffer, size_t length) {
  return parse_profile_sensor_buffer(buffer, length, get_message_length);
}

/* None + Minimal -> Profile IPC */
static inline size_t none_minimal_encode(uint8_t* buffer, size_t buffer_size, uint16_t msg_id, const uint8_t* msg,
                                         size_t msg_size) {
  return encode_profile_ipc(buffer, buffer_size, (uint8_t)msg_id, msg, msg_size);
}

static inline frame_msg_info_t none_minimal_validate_packet(const uint8_t* buffer, size_t length) {
  return parse_profile_ipc_buffer(buffer, length, get_message_length);
}

/* Basic + Extended -> Profile Bulk */
static inline size_t basic_extended_encode(uint8_t* buffer, size_t buffer_size, uint16_t msg_id, const uint8_t* msg,
                                           size_t msg_size) {
  return encode_profile_bulk(buffer, buffer_size, msg_id, msg, msg_size);
}

static inline frame_msg_info_t basic_extended_validate_packet(const uint8_t* buffer, size_t length) {
  return parse_profile_bulk_buffer(buffer, length);
}

/* Basic + Extended Multi System Stream -> Profile Network */
static inline size_t basic_extended_multi_system_stream_encode(uint8_t* buffer, size_t buffer_size, uint16_t msg_id,
                                                               const uint8_t* msg, size_t msg_size) {
  return encode_profile_network(buffer, buffer_size, 0, 0, 0, msg_id, msg, msg_size); /* seq=0, sys=0, comp=0 */
}

static inline frame_msg_info_t basic_extended_multi_system_stream_validate_packet(const uint8_t* buffer,
                                                                                  size_t length) {
  return parse_profile_network_buffer(buffer, length);
}

/* Basic + Minimal - This combination is not a standard profile but is used in tests */
static inline size_t basic_minimal_encode(uint8_t* buffer, size_t buffer_size, uint16_t msg_id, const uint8_t* msg,
                                          size_t msg_size) {
  const size_t header_size = 3; /* [0x90] [0x70] [MSG_ID] */
  const size_t total_size = header_size + msg_size;

  if (buffer_size < total_size) {
    return 0;
  }

  buffer[0] = BASIC_START_BYTE;
  buffer[1] = get_basic_second_start_byte(PAYLOAD_MINIMAL_CONFIG.payload_type);
  buffer[2] = msg_id;
  memcpy(buffer + header_size, msg, msg_size);

  return total_size;
}

static inline frame_msg_info_t basic_minimal_validate_packet(const uint8_t* buffer, size_t length) {
  frame_msg_info_t result = {false, 0, 0, NULL};

  if (length < 3 || buffer[0] != BASIC_START_BYTE || !is_basic_second_start_byte(buffer[1])) {
    return result;
  }

  /* For minimal payloads, we need to know the message size */
  const uint8_t msg_id = buffer[2];
  size_t msg_len = 0;
  if (!get_message_length(msg_id, &msg_len)) {
    return result; /* Unknown message ID */
  }

  const size_t total_size = 3 + msg_len; /* header + payload */
  if (length < total_size) {
    return result;
  }

  result.valid = true;
  result.msg_id = msg_id;
  result.msg_len = msg_len;
  result.msg_data = (uint8_t*)(buffer + 3);

  return result;
}

/* Tiny + Default - This combination is not a standard profile but is used in tests */
static inline size_t tiny_default_encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* msg,
                                         size_t msg_size) {
  const size_t header_size = 3; /* [0x71] [LEN] [MSG_ID] */
  const size_t footer_size = 2; /* [CRC1] [CRC2] */
  const size_t total_size = header_size + msg_size + footer_size;

  if (buffer_size < total_size || msg_size > 255) {
    return 0;
  }

  buffer[0] = get_tiny_start_byte(PAYLOAD_DEFAULT_CONFIG.payload_type);
  buffer[1] = (uint8_t)msg_size;
  buffer[2] = msg_id;
  memcpy(buffer + header_size, msg, msg_size);

  frame_checksum_t ck = frame_fletcher_checksum(buffer + 1, msg_size + 2);
  buffer[total_size - 2] = ck.byte1;
  buffer[total_size - 1] = ck.byte2;

  return total_size;
}

static inline frame_msg_info_t tiny_default_validate_packet(const uint8_t* buffer, size_t length) {
  frame_msg_info_t result = {false, 0, 0, NULL};

  if (length < 5 || !is_tiny_start_byte(buffer[0])) {
    return result;
  }

  /* Extract length from the frame */
  const size_t msg_len = buffer[1];
  const size_t total_size = 3 + msg_len + 2; /* header + payload + crc */

  if (length < total_size) {
    return result;
  }

  /* Verify CRC: covers [LEN] [MSG_ID] [PAYLOAD] */
  frame_checksum_t ck = frame_fletcher_checksum(buffer + 1, msg_len + 2);
  if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
    return result;
  }

  result.valid = true;
  result.msg_id = buffer[2]; /* MSG_ID at position 2 */
  result.msg_len = msg_len;
  result.msg_data = (uint8_t*)(buffer + 3); /* Payload starts after header */

  return result;
}

/* Load test messages - now uses hardcoded data instead of JSON */
size_t load_test_messages(test_message_t* messages, size_t max_count) {
  /* This function is deprecated but kept for backwards compatibility.
   * It returns only SerializationTestMessage entries from the test data.
   */
  size_t count = 0;
  size_t total_count = get_test_message_count();

  for (size_t i = 0; i < total_count && count < max_count; i++) {
    mixed_message_t msg;
    if (!get_test_message(i, &msg)) {
      continue;
    }

    /* Only include SerializationTestMessage types */
    if (msg.type == MSG_TYPE_SERIALIZATION_TEST) {
      SerializationTestSerializationTestMessage* src = &msg.data.serialization_test;
      messages[count].magic_number = src->magic_number;

      strncpy(messages[count].test_string, src->test_string.data, MAX_STRING_LENGTH - 1);
      messages[count].test_string[MAX_STRING_LENGTH - 1] = '\0';

      messages[count].test_float = src->test_float;
      messages[count].test_bool = src->test_bool;
      messages[count].test_array_count = src->test_array.count;

      for (size_t j = 0; j < src->test_array.count && j < MAX_ARRAY_LENGTH; j++) {
        messages[count].test_array[j] = src->test_array.data[j];
      }

      count++;
    }
  }

  return count;
}

/* Load mixed test messages - now uses hardcoded data instead of JSON */
size_t load_mixed_messages(mixed_message_t* messages, size_t max_count) {
  size_t count = 0;
  size_t total_count = get_test_message_count();

  for (size_t i = 0; i < total_count && i < max_count; i++) {
    if (!get_test_message(i, &messages[count])) {
      fprintf(stderr, "Error: Failed to get test message %zu\n", i);
      return 0;
    }
    count++;
  }

  return count;
}

void create_message_from_data(const test_message_t* test_msg, SerializationTestSerializationTestMessage* msg) {
  memset(msg, 0, sizeof(*msg));

  msg->magic_number = test_msg->magic_number;
  msg->test_string.length = strlen(test_msg->test_string);
  strncpy(msg->test_string.data, test_msg->test_string, sizeof(msg->test_string.data) - 1);
  msg->test_string.data[sizeof(msg->test_string.data) - 1] = '\0';
  msg->test_float = test_msg->test_float;
  msg->test_bool = test_msg->test_bool;
  msg->test_array.count = test_msg->test_array_count;
  for (size_t i = 0;
       i < test_msg->test_array_count && i < sizeof(msg->test_array.data) / sizeof(msg->test_array.data[0]); i++) {
    msg->test_array.data[i] = test_msg->test_array[i];
  }
}

bool validate_message(const SerializationTestSerializationTestMessage* msg, const test_message_t* test_msg) {
  if (msg->magic_number != test_msg->magic_number) {
    printf("  Value mismatch: magic_number (expected %u, got %u)\n", test_msg->magic_number, msg->magic_number);
    return false;
  }

  char decoded_str[MAX_STRING_LENGTH];
  strncpy(decoded_str, msg->test_string.data, msg->test_string.length);
  decoded_str[msg->test_string.length] = '\0';

  if (strcmp(decoded_str, test_msg->test_string) != 0) {
    printf("  Value mismatch: test_string (expected '%s', got '%s')\n", test_msg->test_string, decoded_str);
    return false;
  }

  if (fabs(msg->test_float - test_msg->test_float) > 0.01f) {
    printf("  Value mismatch: test_float (expected %f, got %f)\n", test_msg->test_float, msg->test_float);
    return false;
  }

  if (msg->test_bool != test_msg->test_bool) {
    printf("  Value mismatch: test_bool (expected %d, got %d)\n", test_msg->test_bool, msg->test_bool);
    return false;
  }

  if (msg->test_array.count != test_msg->test_array_count) {
    printf("  Value mismatch: test_array.count (expected %zu, got %u)\n", test_msg->test_array_count,
           msg->test_array.count);
    return false;
  }

  for (size_t i = 0; i < test_msg->test_array_count; i++) {
    if (msg->test_array.data[i] != test_msg->test_array[i]) {
      printf("  Value mismatch: test_array[%zu] (expected %d, got %d)\n", i, test_msg->test_array[i],
             msg->test_array.data[i]);
      return false;
    }
  }

  return true;
}

bool encode_test_messages(const char* format, uint8_t* buffer, size_t buffer_size, size_t* encoded_size) {
  // Select the appropriate encoder based on format
  encode_message_fn encoder = NULL;

  if (strcmp(format, "profile_standard") == 0) {
    encoder = basic_default_encode;
  } else if (strcmp(format, "profile_sensor") == 0) {
    encoder = tiny_minimal_encode;
  } else if (strcmp(format, "profile_ipc") == 0) {
    encoder = none_minimal_encode;
  } else if (strcmp(format, "profile_bulk") == 0) {
    encoder = basic_extended_encode;
  } else if (strcmp(format, "profile_network") == 0) {
    encoder = basic_extended_multi_system_stream_encode;
  } else {
    printf("  Unknown frame format: %s\n", format);
    return false;
  }

  // Use the streaming interface to write messages directly
  return write_test_messages(buffer, buffer_size, encoder, encoded_size);
}

bool decode_test_messages(const char* format, const uint8_t* buffer, size_t buffer_size, size_t* message_count) {
  mixed_message_t mixed_messages[MAX_TEST_MESSAGES];
  size_t msg_count = load_mixed_messages(mixed_messages, MAX_TEST_MESSAGES);

  if (msg_count == 0) {
    printf("  Failed to load mixed test messages\n");
    *message_count = 0;
    return false;
  }

  size_t offset = 0;
  *message_count = 0;

  while (offset < buffer_size && *message_count < msg_count) {
    frame_msg_info_t decode_result;

    if (strcmp(format, "profile_standard") == 0) {
      decode_result = basic_default_validate_packet(buffer + offset, buffer_size - offset);
    } else if (strcmp(format, "profile_sensor") == 0) {
      decode_result = tiny_minimal_validate_packet(buffer + offset, buffer_size - offset);
    } else if (strcmp(format, "profile_ipc") == 0) {
      decode_result = none_minimal_validate_packet(buffer + offset, buffer_size - offset);
    } else if (strcmp(format, "profile_bulk") == 0) {
      decode_result = basic_extended_validate_packet(buffer + offset, buffer_size - offset);
    } else if (strcmp(format, "profile_network") == 0) {
      decode_result = basic_extended_multi_system_stream_validate_packet(buffer + offset, buffer_size - offset);
    } else {
      printf("  Unknown frame format: %s\n", format);
      return false;
    }

    if (!decode_result.valid) {
      printf("  Decoding failed for message %zu at offset %zu\n", *message_count, offset);
      if (buffer_size - offset >= 6) {
        printf("  Buffer first bytes: %02x %02x %02x %02x %02x %02x\n", buffer[offset], buffer[offset + 1],
               buffer[offset + 2], buffer[offset + 3], buffer[offset + 4], buffer[offset + 5]);
      }
      return false;
    }

    // Validate msg_id matches expected type
    uint16_t expected_msg_id;
    if (mixed_messages[*message_count].type == MSG_TYPE_SERIALIZATION_TEST) {
      expected_msg_id = SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID;
    } else if (mixed_messages[*message_count].type == MSG_TYPE_BASIC_TYPES) {
      expected_msg_id = SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID;
    } else if (mixed_messages[*message_count].type == MSG_TYPE_UNION_TEST) {
      expected_msg_id = SERIALIZATION_TEST_UNION_TEST_MESSAGE_MSG_ID;
    } else {
      printf("  Unknown message type for message %zu\n", *message_count);
      return false;
    }

    if (decode_result.msg_id != expected_msg_id) {
      printf("  Message ID mismatch for message %zu: expected %u, got %u\n", *message_count, expected_msg_id,
             decode_result.msg_id);
      return false;
    }

    // Verify the decoded message matches expected data
    // For now, we just check that it decoded correctly
    // Full validation would require comparing all fields for both message types

    /* Calculate the size of this encoded message */
    size_t msg_size = 0;
    if (strcmp(format, "profile_standard") == 0) {
      msg_size = 4 + decode_result.msg_len + 2; /* header + payload + crc */
    } else if (strcmp(format, "profile_sensor") == 0) {
      msg_size = 2 + decode_result.msg_len; /* header + payload */
    } else if (strcmp(format, "profile_ipc") == 0) {
      msg_size = 1 + decode_result.msg_len; /* header + payload */
    } else if (strcmp(format, "profile_bulk") == 0) {
      msg_size = 6 + decode_result.msg_len + 2; /* header + payload + crc */
    } else if (strcmp(format, "profile_network") == 0) {
      msg_size = 9 + decode_result.msg_len + 2; /* header + payload + crc */
    }

    offset += msg_size;
    (*message_count)++;
  }

  if (*message_count != msg_count) {
    printf("  Expected %zu messages, but decoded %zu\n", msg_count, *message_count);
    return false;
  }

  if (offset != buffer_size) {
    printf("  Extra data after messages: expected %zu bytes, got %zu bytes\n", offset, buffer_size);
    return false;
  }

  return true;
}

/* Expected test values (from test_messages.json) - for backwards compatibility */
static const uint32_t EXPECTED_MAGIC_NUMBER = 3735928559; /* 0xDEADBEEF */
static const char* EXPECTED_TEST_STRING = "Cross-platform test!";
static const float EXPECTED_TEST_FLOAT = 3.14159f;
static const bool EXPECTED_TEST_BOOL = true;
static const int32_t EXPECTED_TEST_ARRAY[] = {100, 200, 300};
static const size_t EXPECTED_TEST_ARRAY_COUNT = 3;

void create_test_message(SerializationTestSerializationTestMessage* msg) {
  test_message_t test_msg;
  test_msg.magic_number = EXPECTED_MAGIC_NUMBER;
  strncpy(test_msg.test_string, EXPECTED_TEST_STRING, MAX_STRING_LENGTH - 1);
  test_msg.test_string[MAX_STRING_LENGTH - 1] = '\0';
  test_msg.test_float = EXPECTED_TEST_FLOAT;
  test_msg.test_bool = EXPECTED_TEST_BOOL;
  test_msg.test_array_count = EXPECTED_TEST_ARRAY_COUNT;
  for (size_t i = 0; i < EXPECTED_TEST_ARRAY_COUNT; i++) {
    test_msg.test_array[i] = EXPECTED_TEST_ARRAY[i];
  }

  create_message_from_data(&test_msg, msg);
}

bool validate_test_message(const SerializationTestSerializationTestMessage* msg) {
  test_message_t test_msg;
  test_msg.magic_number = EXPECTED_MAGIC_NUMBER;
  strncpy(test_msg.test_string, EXPECTED_TEST_STRING, MAX_STRING_LENGTH - 1);
  test_msg.test_string[MAX_STRING_LENGTH - 1] = '\0';
  test_msg.test_float = EXPECTED_TEST_FLOAT;
  test_msg.test_bool = EXPECTED_TEST_BOOL;
  test_msg.test_array_count = EXPECTED_TEST_ARRAY_COUNT;
  for (size_t i = 0; i < EXPECTED_TEST_ARRAY_COUNT; i++) {
    test_msg.test_array[i] = EXPECTED_TEST_ARRAY[i];
  }

  return validate_message(msg, &test_msg);
}

bool encode_test_message(const char* format, uint8_t* buffer, size_t buffer_size, size_t* encoded_size) {
  return encode_test_messages(format, buffer, buffer_size, encoded_size);
}

bool decode_test_message(const char* format, const uint8_t* buffer, size_t buffer_size,
                         SerializationTestSerializationTestMessage* msg) {
  size_t message_count = 0;
  return decode_test_messages(format, buffer, buffer_size, &message_count);
}
