/**
 * Extended test message data definitions (header-only).
 * Hardcoded test messages for extended message ID and payload testing.
 *
 * Structure:
 * - One instance per message type (ExtendedId1-10, LargePayload1-2)
 * - A msg_id order array (length 12) defines the encode/decode sequence
 * - Encoding uses msg_id array to select which message to write
 * - Decoding uses decoded msg_id to find the right message for comparison
 */

#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "../../generated/c/extended_test.structframe.h"
#include "test_codec.h"

/* ============================================================================
 * Message count and order
 * ============================================================================ */

#define EXT_MESSAGE_COUNT 17

/* Message ID order array */
static const uint16_t ext_msg_id_order[EXT_MESSAGE_COUNT] = {
    EXTENDED_TEST_EXTENDED_ID_MESSAGE1_MSG_ID,           /* 0: 750 */
    EXTENDED_TEST_EXTENDED_ID_MESSAGE2_MSG_ID,           /* 1: 1000 */
    EXTENDED_TEST_EXTENDED_ID_MESSAGE3_MSG_ID,           /* 2: 500 */
    EXTENDED_TEST_EXTENDED_ID_MESSAGE4_MSG_ID,           /* 3: 2048 */
    EXTENDED_TEST_EXTENDED_ID_MESSAGE5_MSG_ID,           /* 4: 300 */
    EXTENDED_TEST_EXTENDED_ID_MESSAGE6_MSG_ID,           /* 5: 1500 */
    EXTENDED_TEST_EXTENDED_ID_MESSAGE7_MSG_ID,           /* 6: 999 */
    EXTENDED_TEST_EXTENDED_ID_MESSAGE8_MSG_ID,           /* 7: 1234 */
    EXTENDED_TEST_EXTENDED_ID_MESSAGE9_MSG_ID,           /* 8: 4000 */
    EXTENDED_TEST_EXTENDED_ID_MESSAGE10_MSG_ID,          /* 9: 256 */
    EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE1_MSG_ID,         /* 10: 800 */
    EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE2_MSG_ID,         /* 11: 801 */
    EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MSG_ID, /* 12: empty */
    EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MSG_ID, /* 13: single */
    EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MSG_ID, /* 14: 1/3 filled */
    EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MSG_ID, /* 15: one empty */
    EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MSG_ID, /* 16: full */
};

static inline const uint16_t* ext_get_msg_id_order(void) { return ext_msg_id_order; }

/* ============================================================================
 * Helper functions to create messages
 * ============================================================================ */

static inline ExtendedTestExtendedIdMessage1 create_ext_id_1(void) {
  ExtendedTestExtendedIdMessage1 msg;
  memset(&msg, 0, sizeof(msg));
  msg.sequence_number = 12345678;
  strncpy(msg.label, "Test Label Extended 1", 31);
  msg.label[31] = '\0';
  msg.value = 3.14159f;
  msg.enabled = true;
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

static inline ExtendedTestExtendedIdMessage3 create_ext_id_3(void) {
  ExtendedTestExtendedIdMessage3 msg;
  memset(&msg, 0, sizeof(msg));
  msg.timestamp = 1704067200000000ULL;
  msg.temperature = -40;
  msg.humidity = 85;
  strncpy(msg.location, "Sensor Room A", 15);
  msg.location[15] = '\0';
  return msg;
}

static inline ExtendedTestExtendedIdMessage4 create_ext_id_4(void) {
  ExtendedTestExtendedIdMessage4 msg;
  memset(&msg, 0, sizeof(msg));
  msg.event_id = 999999;
  msg.event_type = 42;
  msg.event_time = 1704067200000LL;
  const char* data = "Event payload with extended message ID";
  msg.event_data.length = (uint8_t)strlen(data);
  strcpy(msg.event_data.data, data);
  return msg;
}

static inline ExtendedTestExtendedIdMessage5 create_ext_id_5(void) {
  ExtendedTestExtendedIdMessage5 msg;
  memset(&msg, 0, sizeof(msg));
  msg.x_position = 100.5f;
  msg.y_position = -200.25f;
  msg.z_position = 50.125f;
  msg.frame_number = 1000000;
  return msg;
}

static inline ExtendedTestExtendedIdMessage6 create_ext_id_6(void) {
  ExtendedTestExtendedIdMessage6 msg;
  memset(&msg, 0, sizeof(msg));
  msg.command_id = -12345;
  msg.parameter1 = 1000;
  msg.parameter2 = 2000;
  msg.acknowledged = false;
  strncpy(msg.command_name, "CALIBRATE_SENSOR", 23);
  msg.command_name[23] = '\0';
  return msg;
}

static inline ExtendedTestExtendedIdMessage7 create_ext_id_7(void) {
  ExtendedTestExtendedIdMessage7 msg;
  memset(&msg, 0, sizeof(msg));
  msg.counter = 4294967295U;
  msg.average = 123.456789;
  msg.minimum = -999.99f;
  msg.maximum = 999.99f;
  return msg;
}

static inline ExtendedTestExtendedIdMessage8 create_ext_id_8(void) {
  ExtendedTestExtendedIdMessage8 msg;
  memset(&msg, 0, sizeof(msg));
  msg.level = 255;
  msg.offset = -32768;
  msg.duration = 86400000;
  strncpy(msg.tag, "TEST123", 7);
  msg.tag[7] = '\0';
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

static inline ExtendedTestExtendedIdMessage10 create_ext_id_10(void) {
  ExtendedTestExtendedIdMessage10 msg;
  memset(&msg, 0, sizeof(msg));
  msg.small_value = 256;
  strncpy(msg.short_text, "Boundary Test", 15);
  msg.short_text[15] = '\0';
  msg.flag = true;
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

/* Create ExtendedVariableSingleArray messages with different fill levels */
static inline ExtendedTestExtendedVariableSingleArray create_ext_var_single(uint64_t timestamp, const uint8_t* data, uint8_t length, uint32_t crc) {
  ExtendedTestExtendedVariableSingleArray msg;
  memset(&msg, 0, sizeof(msg));
  msg.timestamp = timestamp;
  msg.telemetry_data.count = length;
  for (int i = 0; i < length; i++) {
    msg.telemetry_data.data[i] = data[i];
  }
  msg.crc = crc;
  return msg;
}

/* ============================================================================
 * Message getters - return static instances of each message
 * ============================================================================ */

static inline const ExtendedTestExtendedIdMessage1* get_message_ext_1(void) {
  static ExtendedTestExtendedIdMessage1 msg;
  static bool initialized = false;
  if (!initialized) {
    msg = create_ext_id_1();
    initialized = true;
  }
  return &msg;
}

static inline const ExtendedTestExtendedIdMessage2* get_message_ext_2(void) {
  static ExtendedTestExtendedIdMessage2 msg;
  static bool initialized = false;
  if (!initialized) {
    msg = create_ext_id_2();
    initialized = true;
  }
  return &msg;
}

static inline const ExtendedTestExtendedIdMessage3* get_message_ext_3(void) {
  static ExtendedTestExtendedIdMessage3 msg;
  static bool initialized = false;
  if (!initialized) {
    msg = create_ext_id_3();
    initialized = true;
  }
  return &msg;
}

static inline const ExtendedTestExtendedIdMessage4* get_message_ext_4(void) {
  static ExtendedTestExtendedIdMessage4 msg;
  static bool initialized = false;
  if (!initialized) {
    msg = create_ext_id_4();
    initialized = true;
  }
  return &msg;
}

static inline const ExtendedTestExtendedIdMessage5* get_message_ext_5(void) {
  static ExtendedTestExtendedIdMessage5 msg;
  static bool initialized = false;
  if (!initialized) {
    msg = create_ext_id_5();
    initialized = true;
  }
  return &msg;
}

static inline const ExtendedTestExtendedIdMessage6* get_message_ext_6(void) {
  static ExtendedTestExtendedIdMessage6 msg;
  static bool initialized = false;
  if (!initialized) {
    msg = create_ext_id_6();
    initialized = true;
  }
  return &msg;
}

static inline const ExtendedTestExtendedIdMessage7* get_message_ext_7(void) {
  static ExtendedTestExtendedIdMessage7 msg;
  static bool initialized = false;
  if (!initialized) {
    msg = create_ext_id_7();
    initialized = true;
  }
  return &msg;
}

static inline const ExtendedTestExtendedIdMessage8* get_message_ext_8(void) {
  static ExtendedTestExtendedIdMessage8 msg;
  static bool initialized = false;
  if (!initialized) {
    msg = create_ext_id_8();
    initialized = true;
  }
  return &msg;
}

static inline const ExtendedTestExtendedIdMessage9* get_message_ext_9(void) {
  static ExtendedTestExtendedIdMessage9 msg;
  static bool initialized = false;
  if (!initialized) {
    msg = create_ext_id_9();
    initialized = true;
  }
  return &msg;
}

static inline const ExtendedTestExtendedIdMessage10* get_message_ext_10(void) {
  static ExtendedTestExtendedIdMessage10 msg;
  static bool initialized = false;
  if (!initialized) {
    msg = create_ext_id_10();
    initialized = true;
  }
  return &msg;
}

static inline const ExtendedTestLargePayloadMessage1* get_message_large_1(void) {
  static ExtendedTestLargePayloadMessage1 msg;
  static bool initialized = false;
  if (!initialized) {
    msg = create_large_1();
    initialized = true;
  }
  return &msg;
}

static inline const ExtendedTestLargePayloadMessage2* get_message_large_2(void) {
  static ExtendedTestLargePayloadMessage2 msg;
  static bool initialized = false;
  if (!initialized) {
    msg = create_large_2();
    initialized = true;
  }
  return &msg;
}

/* Get ExtendedVariableSingleArray messages (5 with different fill levels) */
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
 * Reset state - resets variable message indices
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
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE1_MSG_ID: {
      const ExtendedTestExtendedIdMessage1* msg = get_message_ext_1();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_EXTENDED_ID_MESSAGE1_MAGIC1, EXTENDED_TEST_EXTENDED_ID_MESSAGE1_MAGIC2);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE2_MSG_ID: {
      const ExtendedTestExtendedIdMessage2* msg = get_message_ext_2();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_EXTENDED_ID_MESSAGE2_MAGIC1, EXTENDED_TEST_EXTENDED_ID_MESSAGE2_MAGIC2);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE3_MSG_ID: {
      const ExtendedTestExtendedIdMessage3* msg = get_message_ext_3();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_EXTENDED_ID_MESSAGE3_MAGIC1, EXTENDED_TEST_EXTENDED_ID_MESSAGE3_MAGIC2);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE4_MSG_ID: {
      const ExtendedTestExtendedIdMessage4* msg = get_message_ext_4();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_EXTENDED_ID_MESSAGE4_MAGIC1, EXTENDED_TEST_EXTENDED_ID_MESSAGE4_MAGIC2);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE5_MSG_ID: {
      const ExtendedTestExtendedIdMessage5* msg = get_message_ext_5();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_EXTENDED_ID_MESSAGE5_MAGIC1, EXTENDED_TEST_EXTENDED_ID_MESSAGE5_MAGIC2);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE6_MSG_ID: {
      const ExtendedTestExtendedIdMessage6* msg = get_message_ext_6();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_EXTENDED_ID_MESSAGE6_MAGIC1, EXTENDED_TEST_EXTENDED_ID_MESSAGE6_MAGIC2);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE7_MSG_ID: {
      const ExtendedTestExtendedIdMessage7* msg = get_message_ext_7();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_EXTENDED_ID_MESSAGE7_MAGIC1, EXTENDED_TEST_EXTENDED_ID_MESSAGE7_MAGIC2);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE8_MSG_ID: {
      const ExtendedTestExtendedIdMessage8* msg = get_message_ext_8();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_EXTENDED_ID_MESSAGE8_MAGIC1, EXTENDED_TEST_EXTENDED_ID_MESSAGE8_MAGIC2);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE9_MSG_ID: {
      const ExtendedTestExtendedIdMessage9* msg = get_message_ext_9();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_EXTENDED_ID_MESSAGE9_MAGIC1, EXTENDED_TEST_EXTENDED_ID_MESSAGE9_MAGIC2);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE10_MSG_ID: {
      const ExtendedTestExtendedIdMessage10* msg = get_message_ext_10();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_EXTENDED_ID_MESSAGE10_MAGIC1, EXTENDED_TEST_EXTENDED_ID_MESSAGE10_MAGIC2);
    }
    case EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE1_MSG_ID: {
      const ExtendedTestLargePayloadMessage1* msg = get_message_large_1();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE1_MAGIC1, EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE1_MAGIC2);
    }
    case EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE2_MSG_ID: {
      const ExtendedTestLargePayloadMessage2* msg = get_message_large_2();
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE2_MAGIC1, EXTENDED_TEST_LARGE_PAYLOAD_MESSAGE2_MAGIC2);
    }
    case EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MSG_ID: {
      const ExtendedTestExtendedVariableSingleArray* msg = get_ext_var_single_msg(ext_var_single_encode_idx++);
      /* Variable message: use pack_variable if profile has length field */
      #ifdef EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_IS_VARIABLE
      if (writer->config->payload.has_length) {
        static uint8_t pack_buffer[EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MAX_SIZE];
        size_t packed_size = ExtendedTestExtendedVariableSingleArray_serialize_variable(msg, pack_buffer);
        return buffer_writer_write(writer, low_msg_id, pack_buffer, packed_size, 0, 0, 0, pkg_id,
                                   EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MAGIC1, EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MAGIC2);
      }
      #endif
      return buffer_writer_write(writer, low_msg_id, (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, pkg_id,
                                 EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MAGIC1, EXTENDED_TEST_EXTENDED_VARIABLE_SINGLE_ARRAY_MAGIC2);
    }
    default:
      return 0;
  }
}

/* ============================================================================
 * Validator - validates decoded messages against expected data using _equals()
 * ============================================================================ */

static inline bool ext_validate_message(uint16_t msg_id, const uint8_t* data, size_t size, size_t* index) {
  (void)index; /* Not used - stateless validation by msg_id */

  switch (msg_id) {
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE1_MSG_ID: {
      const ExtendedTestExtendedIdMessage1* expected = get_message_ext_1();
      if (size != sizeof(*expected)) return false;
      const ExtendedTestExtendedIdMessage1* decoded = (const ExtendedTestExtendedIdMessage1*)data;
      return ExtendedTestExtendedIdMessage1_equals(decoded, expected);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE2_MSG_ID: {
      const ExtendedTestExtendedIdMessage2* expected = get_message_ext_2();
      if (size != sizeof(*expected)) return false;
      const ExtendedTestExtendedIdMessage2* decoded = (const ExtendedTestExtendedIdMessage2*)data;
      return ExtendedTestExtendedIdMessage2_equals(decoded, expected);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE3_MSG_ID: {
      const ExtendedTestExtendedIdMessage3* expected = get_message_ext_3();
      if (size != sizeof(*expected)) return false;
      const ExtendedTestExtendedIdMessage3* decoded = (const ExtendedTestExtendedIdMessage3*)data;
      return ExtendedTestExtendedIdMessage3_equals(decoded, expected);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE4_MSG_ID: {
      const ExtendedTestExtendedIdMessage4* expected = get_message_ext_4();
      if (size != sizeof(*expected)) return false;
      const ExtendedTestExtendedIdMessage4* decoded = (const ExtendedTestExtendedIdMessage4*)data;
      return ExtendedTestExtendedIdMessage4_equals(decoded, expected);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE5_MSG_ID: {
      const ExtendedTestExtendedIdMessage5* expected = get_message_ext_5();
      if (size != sizeof(*expected)) return false;
      const ExtendedTestExtendedIdMessage5* decoded = (const ExtendedTestExtendedIdMessage5*)data;
      return ExtendedTestExtendedIdMessage5_equals(decoded, expected);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE6_MSG_ID: {
      const ExtendedTestExtendedIdMessage6* expected = get_message_ext_6();
      if (size != sizeof(*expected)) return false;
      const ExtendedTestExtendedIdMessage6* decoded = (const ExtendedTestExtendedIdMessage6*)data;
      return ExtendedTestExtendedIdMessage6_equals(decoded, expected);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE7_MSG_ID: {
      const ExtendedTestExtendedIdMessage7* expected = get_message_ext_7();
      if (size != sizeof(*expected)) return false;
      const ExtendedTestExtendedIdMessage7* decoded = (const ExtendedTestExtendedIdMessage7*)data;
      return ExtendedTestExtendedIdMessage7_equals(decoded, expected);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE8_MSG_ID: {
      const ExtendedTestExtendedIdMessage8* expected = get_message_ext_8();
      if (size != sizeof(*expected)) return false;
      const ExtendedTestExtendedIdMessage8* decoded = (const ExtendedTestExtendedIdMessage8*)data;
      return ExtendedTestExtendedIdMessage8_equals(decoded, expected);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE9_MSG_ID: {
      const ExtendedTestExtendedIdMessage9* expected = get_message_ext_9();
      if (size != sizeof(*expected)) return false;
      const ExtendedTestExtendedIdMessage9* decoded = (const ExtendedTestExtendedIdMessage9*)data;
      return ExtendedTestExtendedIdMessage9_equals(decoded, expected);
    }
    case EXTENDED_TEST_EXTENDED_ID_MESSAGE10_MSG_ID: {
      const ExtendedTestExtendedIdMessage10* expected = get_message_ext_10();
      if (size != sizeof(*expected)) return false;
      const ExtendedTestExtendedIdMessage10* decoded = (const ExtendedTestExtendedIdMessage10*)data;
      return ExtendedTestExtendedIdMessage10_equals(decoded, expected);
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
  return strcmp(format, "profile_bulk") == 0 || strcmp(format, "profile_network") == 0;
}

/* ============================================================================
 * Test configuration
 * ============================================================================ */

static const test_config_t ext_test_config = {
    .message_count = EXT_MESSAGE_COUNT,
    .buffer_size = 8192, /* Larger for extended payloads */
    .formats_help = "profile_bulk, profile_network",
    .test_name = "C Extended",
    .get_msg_id_order = ext_get_msg_id_order,
    .encode_message = ext_encode_message,
    .validate_message = ext_validate_message,
    .reset_state = ext_reset_state,
    .get_message_info = get_message_info,
    .supports_format = ext_supports_format,
};
