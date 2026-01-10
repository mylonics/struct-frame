/**
 * Test message data definitions.
 * Hardcoded test messages for cross-platform compatibility testing.
 */

#include "test_messages_data.h"
#include <string.h>

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

#define CREATE_BASIC_TYPES(si, mi, ri, li, su, mu, ru, lu, sp, dp, fl, dev, desc) \
  { \
    .small_int = si, \
    .medium_int = mi, \
    .regular_int = ri, \
    .large_int = li, \
    .small_uint = su, \
    .medium_uint = mu, \
    .regular_uint = ru, \
    .large_uint = lu, \
    .single_precision = sp, \
    .double_precision = dp, \
    .flag = fl, \
    .device_id = {.data = dev}, \
    .description = {.length = strlen(desc), .data = desc} \
  }

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

    case 5: // BasicTypesMessage - basic_values
      out_message->type = MSG_TYPE_BASIC_TYPES;
      out_message->data.basic_types = (SerializationTestBasicTypesMessage)
        CREATE_BASIC_TYPES(42, 1000, 123456, 9876543210LL, 200, 50000, 4000000000U, 9223372036854775807ULL, 
                          3.14159f, 2.718281828459045, true, "DEVICE-001", "Basic test values");
      break;

    case 6: // BasicTypesMessage - zero_values
      out_message->type = MSG_TYPE_BASIC_TYPES;
      out_message->data.basic_types = (SerializationTestBasicTypesMessage)
        CREATE_BASIC_TYPES(0, 0, 0, 0, 0, 0, 0, 0, 0.0f, 0.0, false, "", "");
      break;

    case 7: // BasicTypesMessage - negative_values
      out_message->type = MSG_TYPE_BASIC_TYPES;
      out_message->data.basic_types = (SerializationTestBasicTypesMessage)
        CREATE_BASIC_TYPES(-128, -32768, -2147483648, -9223372036854775807LL, 255, 65535, 4294967295U, 9223372036854775807ULL,
                          -273.15f, -9999.999999, false, "NEG-TEST", "Negative and max values");
      break;

    case 8: { // UnionTestMessage - with_array_payload
      out_message->type = MSG_TYPE_UNION_TEST;
      SerializationTestUnionTestMessage* msg = &out_message->data.union_test;
      
      msg->payload_type = SERIALIZATION_TEST_UNION_PAYLOAD_COMPREHENSIVE_ARRAY;
      
      // Initialize array_payload
      SerializationTestComprehensiveArrayMessage* arr = &msg->payload.array_payload;
      memset(arr, 0, sizeof(*arr));
      
      // Fixed arrays
      arr->fixed_ints.data[0] = 10;
      arr->fixed_ints.data[1] = 20;
      arr->fixed_ints.data[2] = 30;
      arr->fixed_ints.count = 3;
      
      arr->fixed_floats.data[0] = 1.5f;
      arr->fixed_floats.data[1] = 2.5f;
      arr->fixed_floats.count = 2;
      
      arr->fixed_bools.data[0] = true;
      arr->fixed_bools.data[1] = false;
      arr->fixed_bools.data[2] = true;
      arr->fixed_bools.data[3] = false;
      arr->fixed_bools.count = 4;
      
      // Bounded arrays
      arr->bounded_uints.data[0] = 100;
      arr->bounded_uints.data[1] = 200;
      arr->bounded_uints.count = 2;
      
      arr->bounded_doubles.data[0] = 3.14159;
      arr->bounded_doubles.count = 1;
      
      // String arrays
      strcpy(arr->fixed_strings.data[0].data, "Hello");
      arr->fixed_strings.data[0].length = 5;
      strcpy(arr->fixed_strings.data[1].data, "World");
      arr->fixed_strings.data[1].length = 5;
      arr->fixed_strings.count = 2;
      
      strcpy(arr->bounded_strings.data[0].data, "Test");
      arr->bounded_strings.data[0].length = 4;
      arr->bounded_strings.count = 1;
      
      // Enum arrays
      arr->fixed_statuses.data[0] = SERIALIZATION_TEST_ACTIVE;
      arr->fixed_statuses.data[1] = SERIALIZATION_TEST_ERROR;
      arr->fixed_statuses.count = 2;
      
      arr->bounded_statuses.data[0] = SERIALIZATION_TEST_INACTIVE;
      arr->bounded_statuses.count = 1;
      
      // Sensor arrays
      arr->fixed_sensors.data[0].id = 1;
      arr->fixed_sensors.data[0].value = 25.5f;
      arr->fixed_sensors.data[0].status = SERIALIZATION_TEST_ACTIVE;
      strcpy(arr->fixed_sensors.data[0].name.data, "TempSensor");
      arr->fixed_sensors.data[0].name.length = 10;
      arr->fixed_sensors.count = 1;
      
      arr->bounded_sensors.count = 0;
      break;
    }

    case 9: { // UnionTestMessage - with_test_payload
      out_message->type = MSG_TYPE_UNION_TEST;
      SerializationTestUnionTestMessage* msg = &out_message->data.union_test;
      
      msg->payload_type = SERIALIZATION_TEST_UNION_PAYLOAD_SERIALIZATION_TEST;
      
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

    case 10: // BasicTypesMessage - negative_values (duplicate)
      out_message->type = MSG_TYPE_BASIC_TYPES;
      out_message->data.basic_types = (SerializationTestBasicTypesMessage)
        CREATE_BASIC_TYPES(-128, -32768, -2147483648, -9223372036854775807LL, 255, 65535, 4294967295U, 9223372036854775807ULL,
                          -273.15f, -9999.999999, false, "NEG-TEST", "Negative and max values");
      break;

    default:
      return false;
  }

  return true;
}
