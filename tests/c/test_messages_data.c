/**
 * Test message data definitions.
 * Hardcoded test messages for cross-platform compatibility testing.
 */

#include "test_messages_data.h"
#include <stdio.h>
#include <string.h>

#include "serialization_test.sf.h"

// Helper macros for creating messages
#define CREATE_SERIALIZATION_TEST(name_var, magic, str, flt, bl, ...) \
  { \
    .magic_number = magic, \
    .test_string = {.length = strlen(str), .data = str}, \
    .test_float = flt, \
    .test_bool = bl, \
    .test_array = {.count = sizeof((int32_t[]){__VA_ARGS__}) / sizeof(int32_t), \
                   .data = {__VA_ARGS__}} \
  }

// Note: device_id is a fixed char array, description is a variable string struct
#define INIT_DEVICE_ID(msg, dev) strncpy((msg).device_id, dev, 31); (msg).device_id[31] = '\0'

#define INIT_DESCRIPTION(msg, desc) \
  (msg).description.length = strlen(desc); \
  strncpy((msg).description.data, desc, 128); \
  if ((msg).description.length > 128) (msg).description.length = 128

// Total number of test messages
#define TEST_MESSAGE_COUNT 11

size_t get_test_message_count(void) {
  return TEST_MESSAGE_COUNT;
}

bool get_test_message(size_t index, mixed_message_t* out_message) {
  if (index >= TEST_MESSAGE_COUNT || !out_message) {
    return false;
  }

  memset(out_message, 0, sizeof(mixed_message_t));

  switch (index) {
    case 0: // SerializationTestMessage - basic_values
      out_message->type = MSG_TYPE_SERIALIZATION_TEST;
      out_message->data.serialization_test = (SerializationTestSerializationTestMessage)
        CREATE_SERIALIZATION_TEST(msg, 0xDEADBEEF, "Cross-platform test!", 3.14159f, true, 100, 200, 300);
      break;

    case 1: // SerializationTestMessage - zero_values
      out_message->type = MSG_TYPE_SERIALIZATION_TEST;
      out_message->data.serialization_test = (SerializationTestSerializationTestMessage)
        CREATE_SERIALIZATION_TEST(msg, 0, "", 0.0f, false);
      break;

    case 2: // SerializationTestMessage - max_values
      out_message->type = MSG_TYPE_SERIALIZATION_TEST;
      out_message->data.serialization_test = (SerializationTestSerializationTestMessage)
        CREATE_SERIALIZATION_TEST(msg, 0xFFFFFFFF, "Maximum length test string for coverage!", 999999.9f, true, 2147483647, -2147483648, 0, 1, -1);
      break;

    case 3: // SerializationTestMessage - negative_values
      out_message->type = MSG_TYPE_SERIALIZATION_TEST;
      out_message->data.serialization_test = (SerializationTestSerializationTestMessage)
        CREATE_SERIALIZATION_TEST(msg, 0xAAAAAAAA, "Negative test", -273.15f, false, -100, -200, -300, -400);
      break;

    case 4: // SerializationTestMessage - special_chars
      out_message->type = MSG_TYPE_SERIALIZATION_TEST;
      out_message->data.serialization_test = (SerializationTestSerializationTestMessage)
        CREATE_SERIALIZATION_TEST(msg, 1234567890, "Special: !@#$%^&*()", 2.71828f, true, 0, 1, 1, 2, 3);
      break;

    case 5: { // BasicTypesMessage - basic_values
      out_message->type = MSG_TYPE_BASIC_TYPES;
      SerializationTestBasicTypesMessage* msg = &out_message->data.basic_types;
      memset(msg, 0, sizeof(*msg));
      msg->small_int = 42;
      msg->medium_int = 1000;
      msg->regular_int = 123456;
      msg->large_int = 9876543210LL;
      msg->small_uint = 200;
      msg->medium_uint = 50000;
      msg->regular_uint = 4000000000U;
      msg->large_uint = 9223372036854775807ULL;
      msg->single_precision = 3.14159f;
      msg->double_precision = 2.718281828459045;
      msg->flag = true;
      INIT_DEVICE_ID(*msg, "DEVICE-001");
      INIT_DESCRIPTION(*msg, "Basic test values");
      break;
    }

    case 6: { // BasicTypesMessage - zero_values
      out_message->type = MSG_TYPE_BASIC_TYPES;
      SerializationTestBasicTypesMessage* msg = &out_message->data.basic_types;
      memset(msg, 0, sizeof(*msg));
      break;
    }

    case 7: { // BasicTypesMessage - negative_values
      out_message->type = MSG_TYPE_BASIC_TYPES;
      SerializationTestBasicTypesMessage* msg = &out_message->data.basic_types;
      memset(msg, 0, sizeof(*msg));
      msg->small_int = -128;
      msg->medium_int = -32768;
      msg->regular_int = -2147483648;
      msg->large_int = -9223372036854775807LL;
      msg->small_uint = 255;
      msg->medium_uint = 65535;
      msg->regular_uint = 4294967295U;
      msg->large_uint = 9223372036854775807ULL;
      msg->single_precision = -273.15f;
      msg->double_precision = -9999.999999;
      msg->flag = false;
      INIT_DEVICE_ID(*msg, "NEG-TEST");
      INIT_DESCRIPTION(*msg, "Negative and max values");
      break;
    }

    case 8: { // UnionTestMessage - with_array_payload
      out_message->type = MSG_TYPE_UNION_TEST;
      SerializationTestUnionTestMessage* msg = &out_message->data.union_test;
      memset(msg, 0, sizeof(*msg));
      
      msg->payload_discriminator = SERIALIZATION_TEST_COMPREHENSIVE_ARRAY_MESSAGE_MSG_ID;
      
      // Initialize array_payload
      SerializationTestComprehensiveArrayMessage* arr = &msg->payload.array_payload;
      
      // Fixed arrays (direct arrays, no .data/.count)
      arr->fixed_ints[0] = 10;
      arr->fixed_ints[1] = 20;
      arr->fixed_ints[2] = 30;
      
      arr->fixed_floats[0] = 1.5f;
      arr->fixed_floats[1] = 2.5f;
      
      arr->fixed_bools[0] = true;
      arr->fixed_bools[1] = false;
      arr->fixed_bools[2] = true;
      arr->fixed_bools[3] = false;
      
      // Bounded arrays (have .count and .data)
      arr->bounded_uints.data[0] = 100;
      arr->bounded_uints.data[1] = 200;
      arr->bounded_uints.count = 2;
      
      arr->bounded_doubles.data[0] = 3.14159;
      arr->bounded_doubles.count = 1;
      
      // String arrays (fixed arrays are 2D char arrays)
      strcpy(arr->fixed_strings[0], "Hello");
      strcpy(arr->fixed_strings[1], "World");
      
      strcpy(arr->bounded_strings.data[0], "Test");
      arr->bounded_strings.count = 1;
      
      // Enum arrays (fixed is direct array)
      arr->fixed_statuses[0] = STATUS_ACTIVE;
      arr->fixed_statuses[1] = STATUS_ERROR;
      
      arr->bounded_statuses.data[0] = STATUS_INACTIVE;
      arr->bounded_statuses.count = 1;
      
      // Sensor arrays (fixed is direct array of structs)
      arr->fixed_sensors[0].id = 1;
      arr->fixed_sensors[0].value = 25.5f;
      arr->fixed_sensors[0].status = STATUS_ACTIVE;
      arr->fixed_sensors[0].name[0] = '\0';  // Initialize first
      strcpy(arr->fixed_sensors[0].name, "TempSensor");
      
      arr->bounded_sensors.count = 0;
      break;
    }

    case 9: { // UnionTestMessage - with_test_payload
      out_message->type = MSG_TYPE_UNION_TEST;
      SerializationTestUnionTestMessage* msg = &out_message->data.union_test;
      memset(msg, 0, sizeof(*msg));
      
      msg->payload_discriminator = SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID;
      
      // Initialize test_payload
      SerializationTestSerializationTestMessage* test = &msg->payload.test_payload;
      test->magic_number = 0x12345678;
      strcpy(test->test_string.data, "Union test message");
      test->test_string.length = 18;
      test->test_float = 99.99f;
      test->test_bool = true;
      test->test_array.data[0] = 1;
      test->test_array.data[1] = 2;
      test->test_array.data[2] = 3;
      test->test_array.data[3] = 4;
      test->test_array.data[4] = 5;
      test->test_array.count = 5;
      break;
    }

    case 10: { // BasicTypesMessage - negative_values (duplicate)
      out_message->type = MSG_TYPE_BASIC_TYPES;
      SerializationTestBasicTypesMessage* msg = &out_message->data.basic_types;
      memset(msg, 0, sizeof(*msg));
      msg->small_int = -128;
      msg->medium_int = -32768;
      msg->regular_int = -2147483648;
      msg->large_int = -9223372036854775807LL;
      msg->small_uint = 255;
      msg->medium_uint = 65535;
      msg->regular_uint = 4294967295U;
      msg->large_uint = 9223372036854775807ULL;
      msg->single_precision = -273.15f;
      msg->double_precision = -9999.999999;
      msg->flag = false;
      INIT_DEVICE_ID(*msg, "NEG-TEST");
      INIT_DESCRIPTION(*msg, "Negative and max values");
      break;
    }

    default:
      return false;
  }

  return true;
}

bool write_test_messages(uint8_t* buffer, size_t buffer_size, 
                        encode_message_fn encoder, size_t* encoded_size) {
  if (!buffer || !encoder || !encoded_size) {
    return false;
  }

  *encoded_size = 0;
  size_t offset = 0;
  size_t total_count = get_test_message_count();

  for (size_t i = 0; i < total_count; i++) {
    mixed_message_t msg;
    if (!get_test_message(i, &msg)) {
      fprintf(stderr, "Error: Failed to get test message %zu\n", i);
      return false;
    }

    // Determine message ID, pointer, and size based on type
    uint16_t msg_id;
    const uint8_t* msg_ptr;
    size_t msg_size;

    if (msg.type == MSG_TYPE_SERIALIZATION_TEST) {
      msg_id = SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID;
      msg_ptr = (const uint8_t*)&msg.data.serialization_test;
      msg_size = SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE;
    } else if (msg.type == MSG_TYPE_BASIC_TYPES) {
      msg_id = SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID;
      msg_ptr = (const uint8_t*)&msg.data.basic_types;
      msg_size = SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAX_SIZE;
    } else if (msg.type == MSG_TYPE_UNION_TEST) {
      msg_id = SERIALIZATION_TEST_UNION_TEST_MESSAGE_MSG_ID;
      msg_ptr = (const uint8_t*)&msg.data.union_test;
      msg_size = SERIALIZATION_TEST_UNION_TEST_MESSAGE_MAX_SIZE;
    } else {
      fprintf(stderr, "Error: Unknown message type for message %zu\n", i);
      return false;
    }

    // Encode the message using the callback
    size_t msg_encoded_size = encoder(buffer + offset, buffer_size - offset, 
                                      msg_id, msg_ptr, msg_size);

    if (msg_encoded_size == 0) {
      fprintf(stderr, "Error: Encoding failed for message %zu\n", i);
      return false;
    }

    offset += msg_encoded_size;
    *encoded_size = offset;
  }

  return true;
}
