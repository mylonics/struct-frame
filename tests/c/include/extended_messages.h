/**
 * Extended test message definitions (header-only).
 * Hardcoded test messages for extended message ID and payload testing.
 *
 * Three representative extended IDs: boundary (256), mid (1000), high (4000).
 * Plus two large-payload messages and five variable-array instances.
 *
 * Message sequence (10 messages):
 *   0: ExtendedIdMessage10 (256)  - boundary ID
 *   1: ExtendedIdMessage2  (1000) - mid-range ID
 *   2: ExtendedIdMessage9  (4000) - high ID
 *   3: LargePayloadMessage1 (800) - payload > 255 bytes
 *   4: LargePayloadMessage2 (801) - large fixed array
 *   5-9: ExtendedVariableSingleArray - five fill levels
 */

#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "../../generated/c/extended_test.structframe.h"
#include "test_harness.h"

/* ============================================================================
 * Message count and order
 * ============================================================================ */

#define EXT_MESSAGE_COUNT 10

/* Message ID order array */
static const uint16_t ext_msg_id_order[EXT_MESSAGE_COUNT] = {
    EXTENDED_TEST_EXTENDED_ID_MESSAGE10_MSG_ID,          /* 0: 256  - boundary */
    EXTENDED_TEST_EXTENDED_ID_MESSAGE2_MSG_ID,           /* 1: 1000 - mid */
    EXTENDED_TEST_EXTENDED_ID_MESSAGE9_MSG_ID,           /* 2: 4000 - high */
    EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE1_MSG_ID,         /* 3: >255-byte payload */
    EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE2_MSG_ID,         /* 4: large fixed array */
    EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MSG_ID, /* 5: empty */
    EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MSG_ID, /* 6: single */
    EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MSG_ID, /* 7: 1/3 filled */
    EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MSG_ID, /* 8: one-empty */
    EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MSG_ID, /* 9: full */
};

static inline const uint16_t* ext_get_msg_id_order(void) { return ext_msg_id_order; }

/* ============================================================================
 * Helper functions to create messages
 * ============================================================================ */

static inline ExtendedTestExtendedIdMessage10 create_ext_id_10(void) {
  ExtendedTestExtendedIdMessage10 msg;
  memset(&msg, 0, sizeof(msg));
  msg.small_value = 256;
  strncpy(msg.short_text, "Boundary Test", 15);
  msg.short_text[15] = '\0';
  msg.flag = true;
  return msg;
}

static inline ExtendedTestExtendedIdMessage2 create_ext_id_2(void) {
  ExtendedTestExtendedIdMessage2 msg;
  memset(&msg, 0, sizeof(msg));
  msg.sensor_id = -42;
  msg.reading = 2.718281828;
  msg.status_code = 50000;
  const char* desc = "Extended ID test message 2";
  msg.description.length = (uint8_t)strlen(desc);
  strcpy(msg.description.data, desc);
  return msg;
}

static inline ExtendedTestExtendedIdMessage9 create_ext_id_9(void) {
  ExtendedTestExtendedIdMessage9 msg;
  memset(&msg, 0, sizeof(msg));
  msg.big_number = -9223372036854775807LL;
  msg.big_unsigned = 18446744073709551615ULL;
  msg.precision_value = 1.7976931348623157e+308;
  return msg;
}

static inline ExtendedTestLargePayloadMessage1 create_large_1(void) {
  ExtendedTestLargePayloadMessage1 msg;
  memset(&msg, 0, sizeof(msg));
  for (int i = 0; i < 64; i++) {
    msg.sensor_readings[i] = (float)(i + 1);
  }
  msg.reading_count = 64;
  msg.timestamp = 1704067200000000LL;
  strncpy(msg.device_name, "Large Sensor Array Device", 31);
  msg.device_name[31] = '\0';
  return msg;
}

static inline ExtendedTestLargePayloadMessage2 create_large_2(void) {
  ExtendedTestLargePayloadMessage2 msg;
  memset(&msg, 0, sizeof(msg));
  for (int i = 0; i < 256; i++) {
    msg.large_data[i] = (uint8_t)i;
  }
  for (int i = 256; i < 280; i++) {
    msg.large_data[i] = (uint8_t)(i - 256);
  }
  return msg;
}

/* ============================================================================
 * Message getters - return static instances of each message
 * ============================================================================ */

static inline const ExtendedTestExtendedIdMessage10* get_message_ext_10(void) {
  static ExtendedTestExtendedIdMessage10 msg;
  static bool initialized = false;
  if (!initialized) { msg = create_ext_id_10(); initialized = true; }
  return &msg;
}

static inline const ExtendedTestExtendedIdMessage2* get_message_ext_2(void) {
  static ExtendedTestExtendedIdMessage2 msg;
  static bool initialized = false;
  if (!initialized) { msg = create_ext_id_2(); initialized = true; }
  return &msg;
}

static inline const ExtendedTestExtendedIdMessage9* get_message_ext_9(void) {
  static ExtendedTestExtendedIdMessage9 msg;
  static bool initialized = false;
  if (!initialized) { msg = create_ext_id_9(); initialized = true; }
  return &msg;
}

static inline const ExtendedTestLargePayloadMessage1* get_message_large_1(void) {
  static ExtendedTestLargePayloadMessage1 msg;
  static bool initialized = false;
  if (!initialized) { msg = create_large_1(); initialized = true; }
  return &msg;
}

static inline const ExtendedTestLargePayloadMessage2* get_message_large_2(void) {
  static ExtendedTestLargePayloadMessage2 msg;
  static bool initialized = false;
  if (!initialized) { msg = create_large_2(); initialized = true; }
  return &msg;
}

/* Variable-array instances: five fill levels */
static ExtendedTestExtendedVariableSingleArray ext_var_single_msgs[5];
static bool ext_var_single_initialized = false;

static inline void init_ext_var_single_msgs(void) {
  if (ext_var_single_initialized) return;

  /* Empty payload (0 elements) */
  ext_var_single_msgs[0].timestamp = 0x0000000000000001ULL;
  ext_var_single_msgs[0].telemetry_data.count = 0;
  ext_var_single_msgs[0].crc = 0x00000001;

  /* Single element */
  ext_var_single_msgs[1].timestamp = 0x0000000000000002ULL;
  ext_var_single_msgs[1].telemetry_data.count = 1;
  ext_var_single_msgs[1].telemetry_data.data[0] = 42;
  ext_var_single_msgs[1].crc = 0x00000002;

  /* One-third filled (83 elements for max_size=250) */
  ext_var_single_msgs[2].timestamp = 0x0000000000000003ULL;
  ext_var_single_msgs[2].telemetry_data.count = 83;
  for (int i = 0; i < 83; i++) {
    ext_var_single_msgs[2].telemetry_data.data[i] = (uint8_t)i;
  }
  ext_var_single_msgs[2].crc = 0x00000003;

  /* One position empty (249 elements) */
  ext_var_single_msgs[3].timestamp = 0x0000000000000004ULL;
  ext_var_single_msgs[3].telemetry_data.count = 249;
  for (int i = 0; i < 249; i++) {
    ext_var_single_msgs[3].telemetry_data.data[i] = (uint8_t)(i % 256);
  }
  ext_var_single_msgs[3].crc = 0x00000004;

  /* Full (250 elements) */
  ext_var_single_msgs[4].timestamp = 0x0000000000000005ULL;
  ext_var_single_msgs[4].telemetry_data.count = 250;
  for (int i = 0; i < 250; i++) {
    ext_var_single_msgs[4].telemetry_data.data[i] = (uint8_t)(i % 256);
  }
  ext_var_single_msgs[4].crc = 0x00000005;

  ext_var_single_initialized = true;
}

static inline const ExtendedTestExtendedVariableSingleArray* get_ext_var_single_msg(size_t index) {
  init_ext_var_single_msgs();
  return &ext_var_single_msgs[index];
}

/* ============================================================================
 * Reset state
 * ============================================================================ */

static size_t ext_var_single_encode_idx = 0;
static size_t ext_var_single_validate_idx = 0;

static inline void ext_reset_state(void) {
  ext_var_single_encode_idx = 0;
  ext_var_single_validate_idx = 0;
}

/* ============================================================================
 * Encoder - writes messages by msg_id lookup
 * ============================================================================ */

static inline size_t ext_encode_message(buffer_writer_t* writer, size_t index) {
  uint16_t msg_id = ext_msg_id_order[index];
  uint8_t pkg_id = (uint8_t)((msg_id >> 8) & 0xFF);
  uint8_t low_msg_id = (uint8_t)(msg_id & 0xFF);

  switch (msg_id) {
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE10_MSG_ID: {
      const ExtendedTestExtendedIdMessage10* msg = get_message_ext_10();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_EXTENDED_ID_MESSAGE10_MAGIC1,
                                 EXTENDED_TEST_EXTENDED_ID_MESSAGE10_MAGIC2);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE2_MSG_ID: {
      const ExtendedTestExtendedIdMessage2* msg = get_message_ext_2();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_EXTENDED_ID_MESSAGE2_MAGIC1, EXTENDED_TEST_EXTENDED_ID_MESSAGE2_MAGIC2);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE9_MSG_ID: {
      const ExtendedTestExtendedIdMessage9* msg = get_message_ext_9();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_EXTENDED_ID_MESSAGE9_MAGIC1, EXTENDED_TEST_EXTENDED_ID_MESSAGE9_MAGIC2);
    }
    case EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE1_MSG_ID: {
      const ExtendedTestLargePayloadMessage1* msg = get_message_large_1();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE1_MAGIC1,
                                 EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE1_MAGIC2);
    }
    case EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE2_MSG_ID: {
      const ExtendedTestLargePayloadMessage2* msg = get_message_large_2();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE2_MAGIC1,
                                 EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE2_MAGIC2);
    }
    case EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MSG_ID: {
      const ExtendedTestExtendedVariableSingleArray* msg = get_ext_var_single_msg(ext_var_single_encode_idx++);
#ifdef EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_IS_VARIABLE
      if (writer->config->payload.has_length) {
        static uint8_t pack_buffer[EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MAX_SIZE];
        size_t packed_size = ExtendedTestExtendedVariableSingleArray_serialize_variable(msg, pack_buffer);
        return buffer_writer_write(writer, low_msg_id, pack_buffer, packed_size, 0, 0, 0, pkg_id,
                                   EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MAGIC1,
                                   EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MAGIC2);
      }
#endif
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MAGIC1,
                                 EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MAGIC2);
    }
    default:
      return 0;
  }
}

/* ============================================================================
 * Validator - validates decoded messages against expected data
 * ============================================================================ */

static inline bool ext_validate_message(uint16_t msg_id, const uint8_t* data, size_t size, size_t* index) {
  (void)index;

  switch (msg_id) {
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE10_MSG_ID: {
      const ExtendedTestExtendedIdMessage10* expected = get_message_ext_10();
      if (size != sizeof(*expected)) return false;
      const ExtendedTestExtendedIdMessage10* decoded = (const ExtendedTestExtendedIdMessage10*)data;
      return ExtendedTestExtendedIdMessage10_equals(decoded, expected);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE2_MSG_ID: {
      const ExtendedTestExtendedIdMessage2* expected = get_message_ext_2();
      if (size != sizeof(*expected)) return false;
      const ExtendedTestExtendedIdMessage2* decoded = (const ExtendedTestExtendedIdMessage2*)data;
      return ExtendedTestExtendedIdMessage2_equals(decoded, expected);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE9_MSG_ID: {
      const ExtendedTestExtendedIdMessage9* expected = get_message_ext_9();
      if (size != sizeof(*expected)) return false;
      const ExtendedTestExtendedIdMessage9* decoded = (const ExtendedTestExtendedIdMessage9*)data;
      return ExtendedTestExtendedIdMessage9_equals(decoded, expected);
    }
    case EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE1_MSG_ID: {
      const ExtendedTestLargePayloadMessage1* expected = get_message_large_1();
      if (size != sizeof(*expected)) return false;
      const ExtendedTestLargePayloadMessage1* decoded = (const ExtendedTestLargePayloadMessage1*)data;
      return ExtendedTestLargePayloadMessage1_equals(decoded, expected);
    }
    case EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE2_MSG_ID: {
      const ExtendedTestLargePayloadMessage2* expected = get_message_large_2();
      if (size != sizeof(*expected)) return false;
      const ExtendedTestLargePayloadMessage2* decoded = (const ExtendedTestLargePayloadMessage2*)data;
      return ExtendedTestLargePayloadMessage2_equals(decoded, expected);
    }
    case EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MSG_ID: {
      const ExtendedTestExtendedVariableSingleArray* expected = get_ext_var_single_msg(ext_var_single_validate_idx++);
      ExtendedTestExtendedVariableSingleArray decoded;
      if (ExtendedTestExtendedVariableSingleArray_deserialize(data, size, &decoded) == 0) return false;
      return ExtendedTestExtendedVariableSingleArray_equals(&decoded, expected);
    }
    default:
      return false;
  }
}

/* ============================================================================
 * Supports format check - extended tests only use bulk and network
 * ============================================================================ */

static inline bool ext_supports_format(const char* format) {
  return strcmp(format, "bulk") == 0 || strcmp(format, "network") == 0;
}

/* ============================================================================
 * Test configuration
 * ============================================================================ */

static const test_config_t ext_test_config = {
    .message_count = EXT_MESSAGE_COUNT,
    .buffer_size = 8192,
    .formats_help = "bulk, network",
    .test_name = "C Extended",
    .get_msg_id_order = ext_get_msg_id_order,
    .encode_message = ext_encode_message,
    .validate_message = ext_validate_message,
    .reset_state = ext_reset_state,
    .get_message_info = get_message_info,
    .supports_format = ext_supports_format,
};
