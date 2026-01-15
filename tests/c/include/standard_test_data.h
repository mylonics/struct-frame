/**
 * Test message data definitions (header-only).
 * Hardcoded test messages for cross-platform compatibility testing.
 *
 * Structure:
 * - Separate arrays for each message type (SerializationTest, BasicTypes, UnionTest)
 * - Index variables track position within each typed array
 * - A msg_id order array (length 11) defines the encode/decode sequence
 * - Encoding uses msg_id array to select which typed array to pull from
 * - Decoding uses decoded msg_id to find the right array for comparison
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

#define STD_MESSAGE_COUNT 17

/* Index tracking for encoding/validation */
static size_t std_serial_idx = 0;
static size_t std_basic_idx = 0;
static size_t std_union_idx = 0;
static size_t std_var_single_idx = 0;
static size_t std_message_idx = 0;

/* Message ID order array */
static const uint16_t std_msg_id_order[STD_MESSAGE_COUNT] = {
    SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID, /* 0: SerializationTest[0] */
    SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID, /* 1: SerializationTest[1] */
    SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID, /* 2: SerializationTest[2] */
    SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID, /* 3: SerializationTest[3] */
    SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID, /* 4: SerializationTest[4] */
    SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,        /* 5: BasicTypes[0] */
    SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,        /* 6: BasicTypes[1] */
    SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,        /* 7: BasicTypes[2] */
    SERIALIZATION_TEST_UNION_TEST_MESSAGE_MSG_ID,         /* 8: UnionTest[0] */
    SERIALIZATION_TEST_UNION_TEST_MESSAGE_MSG_ID,         /* 9: UnionTest[1] */
    SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,        /* 10: BasicTypes[3] */
    SERIALIZATION_TEST_VARIABLE_SINGLE_ARRAY_MSG_ID,      /* 11: VariableSingleArray[0] - empty */
    SERIALIZATION_TEST_VARIABLE_SINGLE_ARRAY_MSG_ID,      /* 12: VariableSingleArray[1] - single */
    SERIALIZATION_TEST_VARIABLE_SINGLE_ARRAY_MSG_ID,      /* 13: VariableSingleArray[2] - 1/3 filled */
    SERIALIZATION_TEST_VARIABLE_SINGLE_ARRAY_MSG_ID,      /* 14: VariableSingleArray[3] - one empty */
    SERIALIZATION_TEST_VARIABLE_SINGLE_ARRAY_MSG_ID,      /* 15: VariableSingleArray[4] - full */
    SERIALIZATION_TEST_MESSAGE_MSG_ID,                    /* 16: Message[0] */
};

static inline const uint16_t* std_get_msg_id_order(void) { return std_msg_id_order; }

/* ============================================================================
 * Helper functions to create messages
 * ============================================================================ */

static inline SerializationTestSerializationTestMessage create_serialization_test(uint32_t magic, const char* str,
                                                                                  float flt, bool bl,
                                                                                  const int32_t* arr,
                                                                                  size_t arr_count) {
  SerializationTestSerializationTestMessage msg;
  memset(&msg, 0, sizeof(msg));
  msg.magic_number = magic;
  msg.test_string.length = (uint8_t)strlen(str);
  strncpy(msg.test_string.data, str, 64);
  msg.test_float = flt;
  msg.test_bool = bl;
  for (size_t i = 0; i < arr_count && i < 5; i++) {
    msg.test_array.data[i] = arr[i];
  }
  msg.test_array.count = (uint8_t)arr_count;
  return msg;
}

static inline SerializationTestBasicTypesMessage create_basic_types(int8_t si, int16_t mi, int32_t ri, int64_t li,
                                                                    uint8_t su, uint16_t mu, uint32_t ru, uint64_t lu,
                                                                    float sp, double dp, bool fl, const char* dev,
                                                                    const char* desc) {
  SerializationTestBasicTypesMessage msg;
  memset(&msg, 0, sizeof(msg));
  msg.small_int = si;
  msg.medium_int = mi;
  msg.regular_int = ri;
  msg.large_int = li;
  msg.small_uint = su;
  msg.medium_uint = mu;
  msg.regular_uint = ru;
  msg.large_uint = lu;
  msg.single_precision = sp;
  msg.double_precision = dp;
  msg.flag = fl;
  strncpy(msg.device_id, dev, 31);
  msg.device_id[31] = '\0';
  msg.description.length = (uint8_t)strlen(desc);
  strncpy(msg.description.data, desc, 128);
  if (msg.description.length > 128) msg.description.length = 128;
  return msg;
}

static inline SerializationTestUnionTestMessage create_union_with_array(void) {
  SerializationTestUnionTestMessage msg;
  memset(&msg, 0, sizeof(msg));
  msg.payload_discriminator = SERIALIZATION_TEST_COMPREHENSIVE_ARRAY_MESSAGE_MSG_ID;

  SerializationTestComprehensiveArrayMessage* arr = &msg.payload.array_payload;

  arr->fixed_ints[0] = 10;
  arr->fixed_ints[1] = 20;
  arr->fixed_ints[2] = 30;

  arr->fixed_floats[0] = 1.5f;
  arr->fixed_floats[1] = 2.5f;

  arr->fixed_bools[0] = true;
  arr->fixed_bools[1] = false;
  arr->fixed_bools[2] = true;
  arr->fixed_bools[3] = false;

  arr->bounded_uints.data[0] = 100;
  arr->bounded_uints.data[1] = 200;
  arr->bounded_uints.count = 2;

  arr->bounded_doubles.data[0] = 3.14159;
  arr->bounded_doubles.count = 1;

  strcpy(arr->fixed_strings[0], "Hello");
  strcpy(arr->fixed_strings[1], "World");

  strcpy(arr->bounded_strings.data[0], "Test");
  arr->bounded_strings.count = 1;

  arr->fixed_statuses[0] = STATUS_ACTIVE;
  arr->fixed_statuses[1] = STATUS_ERROR;

  arr->bounded_statuses.data[0] = STATUS_INACTIVE;
  arr->bounded_statuses.count = 1;

  arr->fixed_sensors[0].id = 1;
  arr->fixed_sensors[0].value = 25.5f;
  arr->fixed_sensors[0].status = STATUS_ACTIVE;
  strcpy(arr->fixed_sensors[0].name, "TempSensor");

  arr->bounded_sensors.count = 0;

  return msg;
}

static inline SerializationTestUnionTestMessage create_union_with_test(void) {
  SerializationTestUnionTestMessage msg;
  memset(&msg, 0, sizeof(msg));
  msg.payload_discriminator = SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID;

  SerializationTestSerializationTestMessage* test = &msg.payload.test_payload;
  test->magic_number = 0x12345678;
  const char* str = "Union test message";
  test->test_string.length = (uint8_t)strlen(str);
  strcpy(test->test_string.data, str);
  test->test_float = 99.99f;
  test->test_bool = true;
  test->test_array.data[0] = 1;
  test->test_array.data[1] = 2;
  test->test_array.data[2] = 3;
  test->test_array.data[3] = 4;
  test->test_array.data[4] = 5;
  test->test_array.count = 5;

  return msg;
}

/* ============================================================================
 * Typed message arrays (one per message type)
 * ============================================================================ */

/* SerializationTestMessage array (5 messages) */
static inline const SerializationTestSerializationTestMessage* get_serialization_test_messages(void) {
  static SerializationTestSerializationTestMessage messages[5];
  static bool initialized = false;

  if (!initialized) {
    int32_t arr0[] = {100, 200, 300};
    int32_t arr1[] = {0}; /* empty */
    int32_t arr2[] = {2147483647, -2147483648, 0, 1, -1};
    int32_t arr3[] = {-100, -200, -300, -400};
    int32_t arr4[] = {0, 1, 1, 2, 3};

    messages[0] = create_serialization_test(0xDEADBEEF, "Cross-platform test!", 3.14159f, true, arr0, 3);
    messages[1] = create_serialization_test(0, "", 0.0f, false, arr1, 0);
    messages[2] =
        create_serialization_test(0xFFFFFFFF, "Maximum length test string for coverage!", 999999.9f, true, arr2, 5);
    messages[3] = create_serialization_test(0xAAAAAAAA, "Negative test", -273.15f, false, arr3, 4);
    messages[4] = create_serialization_test(1234567890, "Special: !@#$%^&*()", 2.71828f, true, arr4, 5);

    initialized = true;
  }

  return messages;
}

/* BasicTypesMessage array (4 messages) */
static inline const SerializationTestBasicTypesMessage* get_basic_types_messages(void) {
  static SerializationTestBasicTypesMessage messages[4];
  static bool initialized = false;

  if (!initialized) {
    messages[0] = create_basic_types(42, 1000, 123456, 9876543210LL, 200, 50000, 4000000000U, 9223372036854775807ULL,
                                     3.14159f, 2.718281828459045, true, "DEVICE-001", "Basic test values");
    messages[1] = create_basic_types(0, 0, 0, 0, 0, 0, 0, 0, 0.0f, 0.0, false, "", "");
    messages[2] = create_basic_types(-128, -32768, -2147483648, -9223372036854775807LL, 255, 65535, 4294967295U,
                                     9223372036854775807ULL, -273.15f, -9999.999999, false, "NEG-TEST",
                                     "Negative and max values");
    messages[3] = create_basic_types(-128, -32768, -2147483648, -9223372036854775807LL, 255, 65535, 4294967295U,
                                     9223372036854775807ULL, -273.15f, -9999.999999, false, "NEG-TEST",
                                     "Negative and max values");

    initialized = true;
  }

  return messages;
}

/* UnionTestMessage array (2 messages) */
static inline const SerializationTestUnionTestMessage* get_union_test_messages(void) {
  static SerializationTestUnionTestMessage messages[2];
  static bool initialized = false;

  if (!initialized) {
    messages[0] = create_union_with_array();
    messages[1] = create_union_with_test();

    initialized = true;
  }

  return messages;
}

/* Create VariableSingleArray test messages with different fill levels */
/* 0: Empty (0 elements) */
/* 1: Single element (1 element) */
/* 2: One-third filled (67 elements for max_size=200) */
/* 3: One position empty (199 elements) */
/* 4: Full (200 elements) */

static inline SerializationTestVariableSingleArray create_variable_single_array_empty(void) {
  SerializationTestVariableSingleArray msg;
  memset(&msg, 0, sizeof(msg));
  msg.message_id = 0x00000001;
  msg.payload.count = 0;
  msg.checksum = 0x0001;
  return msg;
}

static inline SerializationTestVariableSingleArray create_variable_single_array_single(void) {
  SerializationTestVariableSingleArray msg;
  memset(&msg, 0, sizeof(msg));
  msg.message_id = 0x00000002;
  msg.payload.data[0] = 42;
  msg.payload.count = 1;
  msg.checksum = 0x0002;
  return msg;
}

static inline SerializationTestVariableSingleArray create_variable_single_array_third(void) {
  SerializationTestVariableSingleArray msg;
  memset(&msg, 0, sizeof(msg));
  msg.message_id = 0x00000003;
  for (uint8_t i = 0; i < 67; i++) {
    msg.payload.data[i] = i;
  }
  msg.payload.count = 67;
  msg.checksum = 0x0003;
  return msg;
}

static inline SerializationTestVariableSingleArray create_variable_single_array_almost(void) {
  SerializationTestVariableSingleArray msg;
  memset(&msg, 0, sizeof(msg));
  msg.message_id = 0x00000004;
  for (uint8_t i = 0; i < 199; i++) {
    msg.payload.data[i] = i;
  }
  msg.payload.count = 199;
  msg.checksum = 0x0004;
  return msg;
}

static inline SerializationTestVariableSingleArray create_variable_single_array_full(void) {
  SerializationTestVariableSingleArray msg;
  memset(&msg, 0, sizeof(msg));
  msg.message_id = 0x00000005;
  for (int i = 0; i < 200; i++) {
    msg.payload.data[i] = (uint8_t)i;
  }
  msg.payload.count = 200;
  msg.checksum = 0x0005;
  return msg;
}

/* VariableSingleArray array (5 messages with different fill levels) */
static inline const SerializationTestVariableSingleArray* get_variable_single_array_messages(void) {
  static SerializationTestVariableSingleArray messages[5];
  static bool initialized = false;

  if (!initialized) {
    messages[0] = create_variable_single_array_empty();   /* Empty */
    messages[1] = create_variable_single_array_single();  /* Single element */
    messages[2] = create_variable_single_array_third();   /* One-third filled */
    messages[3] = create_variable_single_array_almost();  /* One position empty */
    messages[4] = create_variable_single_array_full();    /* Full */
    initialized = true;
  }

  return messages;
}

/* Message array (1 message) */
static inline SerializationTestMessage create_message_test(void) {
  SerializationTestMessage msg;
  memset(&msg, 0, sizeof(msg));
  msg.severity = MSG_SEVERITY_SEV_MSG;
  msg.module.length = 4;
  strcpy(msg.module.data, "test");
  msg.msg.length = 13;
  strcpy(msg.msg.data, "A really good");
  return msg;
}

static inline const SerializationTestMessage* get_message_messages(void) {
  static SerializationTestMessage messages[1];
  static bool initialized = false;

  if (!initialized) {
    messages[0] = create_message_test();
    initialized = true;
  }

  return messages;
}

/* ============================================================================
 * Reset state for new encode/decode run
 * ============================================================================ */

static inline void std_reset_state(void) {
  std_serial_idx = 0;
  std_basic_idx = 0;
  std_union_idx = 0;
  std_var_single_idx = 0;
  std_message_idx = 0;
}

/* ============================================================================
 * Encoder - writes messages in order using index tracking
 * ============================================================================ */

static inline size_t std_encode_message(buffer_writer_t* writer, size_t index) {
  uint16_t msg_id = std_msg_id_order[index];

  if (msg_id == SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID) {
    const SerializationTestSerializationTestMessage* msg = &get_serialization_test_messages()[std_serial_idx++];
    return buffer_writer_write(writer, (uint8_t)(msg_id & 0xFF), (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, 0,
                               SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAGIC1, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAGIC2);
  } else if (msg_id == SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID) {
    const SerializationTestBasicTypesMessage* msg = &get_basic_types_messages()[std_basic_idx++];
    return buffer_writer_write(writer, (uint8_t)(msg_id & 0xFF), (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, 0,
                               SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  } else if (msg_id == SERIALIZATION_TEST_UNION_TEST_MESSAGE_MSG_ID) {
    const SerializationTestUnionTestMessage* msg = &get_union_test_messages()[std_union_idx++];
    return buffer_writer_write(writer, (uint8_t)(msg_id & 0xFF), (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, 0,
                               SERIALIZATION_TEST_UNION_TEST_MESSAGE_MAGIC1, SERIALIZATION_TEST_UNION_TEST_MESSAGE_MAGIC2);
  } else if (msg_id == SERIALIZATION_TEST_VARIABLE_SINGLE_ARRAY_MSG_ID) {
    const SerializationTestVariableSingleArray* msg = &get_variable_single_array_messages()[std_var_single_idx++];
    /* Variable message: use pack_variable if profile has length field */
    #ifdef SERIALIZATION_TEST_VARIABLE_SINGLE_ARRAY_IS_VARIABLE
    if (writer->config->payload.has_length) {
      static uint8_t pack_buffer[SERIALIZATION_TEST_VARIABLE_SINGLE_ARRAY_MAX_SIZE];
      size_t packed_size = SerializationTestVariableSingleArray_serialize_variable(msg, pack_buffer);
      return buffer_writer_write(writer, (uint8_t)(msg_id & 0xFF), pack_buffer, packed_size, 0, 0, 0, 0,
                                 SERIALIZATION_TEST_VARIABLE_SINGLE_ARRAY_MAGIC1, SERIALIZATION_TEST_VARIABLE_SINGLE_ARRAY_MAGIC2);
    }
    #endif
    return buffer_writer_write(writer, (uint8_t)(msg_id & 0xFF), (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, 0,
                               SERIALIZATION_TEST_VARIABLE_SINGLE_ARRAY_MAGIC1, SERIALIZATION_TEST_VARIABLE_SINGLE_ARRAY_MAGIC2);
  } else if (msg_id == SERIALIZATION_TEST_MESSAGE_MSG_ID) {
    const SerializationTestMessage* msg = &get_message_messages()[std_message_idx++];
    /* Variable message: use pack_variable if profile has length field */
    #ifdef SERIALIZATION_TEST_MESSAGE_IS_VARIABLE
    if (writer->config->payload.has_length) {
      static uint8_t pack_buffer[SERIALIZATION_TEST_MESSAGE_MAX_SIZE];
      size_t packed_size = SerializationTestMessage_serialize_variable(msg, pack_buffer);
      return buffer_writer_write(writer, (uint8_t)(msg_id & 0xFF), pack_buffer, packed_size, 0, 0, 0, 0,
                                 SERIALIZATION_TEST_MESSAGE_MAGIC1, SERIALIZATION_TEST_MESSAGE_MAGIC2);
    }
    #endif
    return buffer_writer_write(writer, (uint8_t)(msg_id & 0xFF), (const uint8_t*)msg, sizeof(*msg), 0, 0, 0, 0,
                               SERIALIZATION_TEST_MESSAGE_MAGIC1, SERIALIZATION_TEST_MESSAGE_MAGIC2);
  }

  return 0;
}

/* ============================================================================
 * Validator - validates decoded messages against expected data using _equals()
 * ============================================================================ */

static inline bool std_validate_message(uint16_t msg_id, const uint8_t* data, size_t size, size_t* index) {
  (void)index; /* Not used for standard tests - index tracking via static vars */

  if (msg_id == SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID) {
    const SerializationTestSerializationTestMessage* expected = &get_serialization_test_messages()[std_serial_idx++];
    if (size != sizeof(*expected)) return false;
    const SerializationTestSerializationTestMessage* decoded = (const SerializationTestSerializationTestMessage*)data;
    return SerializationTestSerializationTestMessage_equals(decoded, expected);
  } else if (msg_id == SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID) {
    const SerializationTestBasicTypesMessage* expected = &get_basic_types_messages()[std_basic_idx++];
    if (size != sizeof(*expected)) return false;
    const SerializationTestBasicTypesMessage* decoded = (const SerializationTestBasicTypesMessage*)data;
    return SerializationTestBasicTypesMessage_equals(decoded, expected);
  } else if (msg_id == SERIALIZATION_TEST_UNION_TEST_MESSAGE_MSG_ID) {
    const SerializationTestUnionTestMessage* expected = &get_union_test_messages()[std_union_idx++];
    if (size != sizeof(*expected)) return false;
    const SerializationTestUnionTestMessage* decoded = (const SerializationTestUnionTestMessage*)data;
    return SerializationTestUnionTestMessage_equals(decoded, expected);
  } else if (msg_id == SERIALIZATION_TEST_VARIABLE_SINGLE_ARRAY_MSG_ID) {
    const SerializationTestVariableSingleArray* expected = &get_variable_single_array_messages()[std_var_single_idx++];
    /* Variable message: use unified unpack() for both MAX_SIZE and variable encoding */
    SerializationTestVariableSingleArray decoded;
    if (!SerializationTestVariableSingleArray_deserialize(data, size, &decoded)) {
      return false;
    }
    return SerializationTestVariableSingleArray_equals(&decoded, expected);
  } else if (msg_id == SERIALIZATION_TEST_MESSAGE_MSG_ID) {
    const SerializationTestMessage* expected = &get_message_messages()[std_message_idx++];
    /* Variable message: use unified unpack() for both MAX_SIZE and variable encoding */
    SerializationTestMessage decoded;
    if (!SerializationTestMessage_deserialize(data, size, &decoded)) {
      return false;
    }
    return SerializationTestMessage_equals(&decoded, expected);
  }

  return false;
}

/* ============================================================================
 * Supports format check
 * ============================================================================ */

static inline bool std_supports_format(const char* format) {
  return strcmp(format, "profile_standard") == 0 || strcmp(format, "profile_sensor") == 0 ||
         strcmp(format, "profile_ipc") == 0 || strcmp(format, "profile_bulk") == 0 ||
         strcmp(format, "profile_network") == 0;
}

/* ============================================================================
 * Test configuration
 * ============================================================================ */

static const test_config_t std_test_config = {
    .message_count = STD_MESSAGE_COUNT,
    .buffer_size = 4096,
    .formats_help = "profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network",
    .test_name = "C",
    .get_msg_id_order = std_get_msg_id_order,
    .encode_message = std_encode_message,
    .validate_message = std_validate_message,
    .reset_state = std_reset_state,
    .get_message_info = get_message_info,
    .supports_format = std_supports_format,
};
