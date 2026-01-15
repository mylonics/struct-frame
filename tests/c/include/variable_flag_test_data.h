/**
 * Variable flag truncation test data definitions (header-only).
 * Tests that messages with variable=true properly truncate unused array space.
 */

#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "../../generated/c/serialization_test.structframe.h"
#include "test_codec.h"

/* ============================================================================
 * Message count and order
 * ============================================================================ */

#define VAR_FLAG_MESSAGE_COUNT 2

/* Index tracking for encoding/validation */
static size_t var_non_var_idx = 0;
static size_t var_var_idx = 0;

/* Message ID order array */
static const uint16_t var_flag_msg_id_order[VAR_FLAG_MESSAGE_COUNT] = {
    SERIALIZATION_TEST_TRUNCATION_TEST_NON_VARIABLE_MSG_ID, /* 0: Non-variable message */
    SERIALIZATION_TEST_TRUNCATION_TEST_VARIABLE_MSG_ID,     /* 1: Variable message */
};

static inline const uint16_t* var_flag_get_msg_id_order(void) { return var_flag_msg_id_order; }

/* ============================================================================
 * Helper functions to create messages
 * ============================================================================ */

static inline SerializationTestTruncationTestNonVariable create_non_variable_1_3_filled(void) {
  SerializationTestTruncationTestNonVariable msg;
  memset(&msg, 0, sizeof(msg));
  msg.sequence_id = 0xDEADBEEF;

  /* Fill 1/3 of the array (67 out of 200 elements) */
  for (uint8_t i = 0; i < 67; i++) {
    msg.data_array.data[i] = i;
  }
  msg.data_array.count = 67;

  msg.footer = 0xCAFE;
  return msg;
}

static inline SerializationTestTruncationTestVariable create_variable_1_3_filled(void) {
  SerializationTestTruncationTestVariable msg;
  memset(&msg, 0, sizeof(msg));
  msg.sequence_id = 0xDEADBEEF;

  /* Fill 1/3 of the array (67 out of 200 elements) */
  for (uint8_t i = 0; i < 67; i++) {
    msg.data_array.data[i] = i;
  }
  msg.data_array.count = 67;

  msg.footer = 0xCAFE;
  return msg;
}

/* ============================================================================
 * Typed message arrays
 * ============================================================================ */

static inline const SerializationTestTruncationTestNonVariable* get_non_variable_messages(void) {
  static SerializationTestTruncationTestNonVariable messages[1];
  static bool initialized = false;
  if (!initialized) {
    messages[0] = create_non_variable_1_3_filled();
    initialized = true;
  }
  return messages;
}

static inline const SerializationTestTruncationTestVariable* get_variable_messages(void) {
  static SerializationTestTruncationTestVariable messages[1];
  static bool initialized = false;
  if (!initialized) {
    messages[0] = create_variable_1_3_filled();
    initialized = true;
  }
  return messages;
}

/* ============================================================================
 * Encoder helper - writes messages in order using index tracking
 * ============================================================================ */

static inline size_t var_flag_encode_message(buffer_writer_t* writer, size_t index) {
  uint16_t msg_id = var_flag_msg_id_order[index];

  if (msg_id == SERIALIZATION_TEST_TRUNCATION_TEST_NON_VARIABLE_MSG_ID) {
    const SerializationTestTruncationTestNonVariable* msg = &get_non_variable_messages()[var_non_var_idx++];
    size_t written = buffer_writer_write(writer, (uint8_t)(msg_id & 0xFF), (const uint8_t*)msg, sizeof(*msg), 0, 0, 0,
                                         0, SERIALIZATION_TEST_TRUNCATION_TEST_NON_VARIABLE_MAGIC1,
                                         SERIALIZATION_TEST_TRUNCATION_TEST_NON_VARIABLE_MAGIC2);
    printf("MSG1: %zu bytes (payload=%zu, no truncation)\n", written, sizeof(*msg));
    return written;
  } else if (msg_id == SERIALIZATION_TEST_TRUNCATION_TEST_VARIABLE_MSG_ID) {
    const SerializationTestTruncationTestVariable* msg = &get_variable_messages()[var_var_idx++];
    /* Variable message: use pack_variable if profile has length field */
    #ifdef SERIALIZATION_TEST_TRUNCATION_TEST_VARIABLE_IS_VARIABLE
    if (writer->config->payload.has_length) {
      static uint8_t pack_buffer[SERIALIZATION_TEST_TRUNCATION_TEST_VARIABLE_MAX_SIZE];
      size_t packed_size = SerializationTestTruncationTestVariable_serialize_variable(msg, pack_buffer);
      size_t written = buffer_writer_write(writer, (uint8_t)(msg_id & 0xFF), pack_buffer, packed_size, 0, 0, 0,
                                           0, SERIALIZATION_TEST_TRUNCATION_TEST_VARIABLE_MAGIC1,
                                           SERIALIZATION_TEST_TRUNCATION_TEST_VARIABLE_MAGIC2);
      printf("MSG2: %zu bytes (payload=%zu, TRUNCATED)\n", written, packed_size);
      return written;
    }
    #endif
    size_t written = buffer_writer_write(writer, (uint8_t)(msg_id & 0xFF), (const uint8_t*)msg, sizeof(*msg), 0, 0, 0,
                                         0, SERIALIZATION_TEST_TRUNCATION_TEST_VARIABLE_MAGIC1,
                                         SERIALIZATION_TEST_TRUNCATION_TEST_VARIABLE_MAGIC2);
    printf("MSG2: %zu bytes (payload=%zu, TRUNCATED)\n", written, sizeof(*msg));
    return written;
  }

  return 0;
}

/* ============================================================================
 * Validator helper - validates decoded messages against expected data
 * ============================================================================ */

static inline bool var_flag_validate_message(uint16_t msg_id, const uint8_t* data, size_t size, size_t* index) {
  (void)index; /* Not used for variable flag tests - index tracking via static vars */

  if (msg_id == SERIALIZATION_TEST_TRUNCATION_TEST_NON_VARIABLE_MSG_ID) {
    const SerializationTestTruncationTestNonVariable* expected = &get_non_variable_messages()[var_non_var_idx++];
    SerializationTestTruncationTestNonVariable decoded;
    if (SerializationTestTruncationTestNonVariable_deserialize(data, size, &decoded) == 0) return false;
    return SerializationTestTruncationTestNonVariable_equals(&decoded, expected);
  } else if (msg_id == SERIALIZATION_TEST_TRUNCATION_TEST_VARIABLE_MSG_ID) {
    const SerializationTestTruncationTestVariable* expected = &get_variable_messages()[var_var_idx++];
    SerializationTestTruncationTestVariable decoded;
    if (SerializationTestTruncationTestVariable_deserialize(data, size, &decoded) == 0) return false;
    return SerializationTestTruncationTestVariable_equals(&decoded, expected);
  }

  return false;
}

/* ============================================================================
 * Reset state
 * ============================================================================ */

static inline void var_flag_reset_state(void) {
  var_non_var_idx = 0;
  var_var_idx = 0;
}

/* ============================================================================
 * Supports format check
 * ============================================================================ */

static inline bool var_flag_supports_format(const char* format) { return strcmp(format, "profile_bulk") == 0; }

/* ============================================================================
 * Test configuration
 * ============================================================================ */

static const test_config_t var_flag_test_config = {
    .message_count = VAR_FLAG_MESSAGE_COUNT,
    .buffer_size = 4096,
    .formats_help = "profile_bulk",
    .test_name = "Variable Flag C",
    .get_msg_id_order = var_flag_get_msg_id_order,
    .encode_message = var_flag_encode_message,
    .validate_message = var_flag_validate_message,
    .reset_state = var_flag_reset_state,
    .get_message_info = get_message_info,
    .supports_format = var_flag_supports_format,
};
