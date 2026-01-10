/**
 * Test message data definitions.
 * Hardcoded test messages for cross-platform compatibility testing.
 */

#include "test_messages_data.hpp"
#include <cstring>

constexpr std::size_t TEST_MESSAGE_COUNT = 11;

std::size_t get_test_message_count() {
  return TEST_MESSAGE_COUNT;
}

bool get_test_message(std::size_t index, MixedMessage& out_message) {
  if (index >= TEST_MESSAGE_COUNT) {
    return false;
  }

  std::memset(&out_message, 0, sizeof(MixedMessage));

  switch (index) {
    case 0: { // SerializationTestMessage - basic_values
      out_message.type = MessageType::SerializationTest;
      auto& msg = out_message.data.serialization_test;
      msg.magic_number = 0xDEADBEEF;
      const char* str = "Cross-platform test!";
      msg.test_string.length = std::strlen(str);
      std::strcpy(msg.test_string.data, str);
      msg.test_float = 3.14159f;
      msg.test_bool = true;
      msg.test_array.data[0] = 100;
      msg.test_array.data[1] = 200;
      msg.test_array.data[2] = 300;
      msg.test_array.count = 3;
      break;
    }

    case 1: { // SerializationTestMessage - zero_values
      out_message.type = MessageType::SerializationTest;
      auto& msg = out_message.data.serialization_test;
      msg.magic_number = 0;
      msg.test_string.length = 0;
      msg.test_string.data[0] = '\0';
      msg.test_float = 0.0f;
      msg.test_bool = false;
      msg.test_array.count = 0;
      break;
    }

    case 2: { // SerializationTestMessage - max_values
      out_message.type = MessageType::SerializationTest;
      auto& msg = out_message.data.serialization_test;
      msg.magic_number = 0xFFFFFFFF;
      const char* str = "Maximum length test string for coverage!";
      msg.test_string.length = std::strlen(str);
      std::strcpy(msg.test_string.data, str);
      msg.test_float = 999999.9f;
      msg.test_bool = true;
      msg.test_array.data[0] = 2147483647;
      msg.test_array.data[1] = -2147483648;
      msg.test_array.data[2] = 0;
      msg.test_array.data[3] = 1;
      msg.test_array.data[4] = -1;
      msg.test_array.count = 5;
      break;
    }

    case 3: { // SerializationTestMessage - negative_values
      out_message.type = MessageType::SerializationTest;
      auto& msg = out_message.data.serialization_test;
      msg.magic_number = 0xAAAAAAAA;
      const char* str = "Negative test";
      msg.test_string.length = std::strlen(str);
      std::strcpy(msg.test_string.data, str);
      msg.test_float = -273.15f;
      msg.test_bool = false;
      msg.test_array.data[0] = -100;
      msg.test_array.data[1] = -200;
      msg.test_array.data[2] = -300;
      msg.test_array.data[3] = -400;
      msg.test_array.count = 4;
      break;
    }

    case 4: { // SerializationTestMessage - special_chars
      out_message.type = MessageType::SerializationTest;
      auto& msg = out_message.data.serialization_test;
      msg.magic_number = 1234567890;
      const char* str = "Special: !@#$%^&*()";
      msg.test_string.length = std::strlen(str);
      std::strcpy(msg.test_string.data, str);
      msg.test_float = 2.71828f;
      msg.test_bool = true;
      msg.test_array.data[0] = 0;
      msg.test_array.data[1] = 1;
      msg.test_array.data[2] = 1;
      msg.test_array.data[3] = 2;
      msg.test_array.data[4] = 3;
      msg.test_array.count = 5;
      break;
    }

    case 5: { // BasicTypesMessage - basic_values
      out_message.type = MessageType::BasicTypes;
      auto& msg = out_message.data.basic_types;
      msg.small_int = 42;
      msg.medium_int = 1000;
      msg.regular_int = 123456;
      msg.large_int = 9876543210LL;
      msg.small_uint = 200;
      msg.medium_uint = 50000;
      msg.regular_uint = 4000000000U;
      msg.large_uint = 9223372036854775807ULL;
      msg.single_precision = 3.14159f;
      msg.double_precision = 2.718281828459045;
      msg.flag = true;
      std::strcpy(msg.device_id.data, "DEVICE-001");
      const char* desc = "Basic test values";
      msg.description.length = std::strlen(desc);
      std::strcpy(msg.description.data, desc);
      break;
    }

    case 6: { // BasicTypesMessage - zero_values
      out_message.type = MessageType::BasicTypes;
      auto& msg = out_message.data.basic_types;
      msg.small_int = 0;
      msg.medium_int = 0;
      msg.regular_int = 0;
      msg.large_int = 0;
      msg.small_uint = 0;
      msg.medium_uint = 0;
      msg.regular_uint = 0;
      msg.large_uint = 0;
      msg.single_precision = 0.0f;
      msg.double_precision = 0.0;
      msg.flag = false;
      msg.device_id.data[0] = '\0';
      msg.description.length = 0;
      msg.description.data[0] = '\0';
      break;
    }

    case 7: { // BasicTypesMessage - negative_values
      out_message.type = MessageType::BasicTypes;
      auto& msg = out_message.data.basic_types;
      msg.small_int = -128;
      msg.medium_int = -32768;
      msg.regular_int = -2147483648;
      msg.large_int = -9223372036854775807LL;
      msg.small_uint = 255;
      msg.medium_uint = 65535;
      msg.regular_uint = 4294967295U;
      msg.large_uint = 9223372036854775807ULL;
      msg.single_precision = -273.15f;
      msg.double_precision = -9999.999999;
      msg.flag = false;
      std::strcpy(msg.device_id.data, "NEG-TEST");
      const char* desc = "Negative and max values";
      msg.description.length = std::strlen(desc);
      std::strcpy(msg.description.data, desc);
      break;
    }

    case 8: { // UnionTestMessage - with_array_payload
      out_message.type = MessageType::UnionTest;
      auto& msg = out_message.data.union_test;
      msg.payload_type = SERIALIZATION_TEST_UNION_PAYLOAD_COMPREHENSIVE_ARRAY;
      
      auto& arr = msg.payload.array_payload;
      std::memset(&arr, 0, sizeof(arr));
      
      // Fixed arrays
      arr.fixed_ints.data[0] = 10;
      arr.fixed_ints.data[1] = 20;
      arr.fixed_ints.data[2] = 30;
      arr.fixed_ints.count = 3;
      
      arr.fixed_floats.data[0] = 1.5f;
      arr.fixed_floats.data[1] = 2.5f;
      arr.fixed_floats.count = 2;
      
      arr.fixed_bools.data[0] = true;
      arr.fixed_bools.data[1] = false;
      arr.fixed_bools.data[2] = true;
      arr.fixed_bools.data[3] = false;
      arr.fixed_bools.count = 4;
      
      // Bounded arrays
      arr.bounded_uints.data[0] = 100;
      arr.bounded_uints.data[1] = 200;
      arr.bounded_uints.count = 2;
      
      arr.bounded_doubles.data[0] = 3.14159;
      arr.bounded_doubles.count = 1;
      
      // String arrays
      std::strcpy(arr.fixed_strings.data[0].data, "Hello");
      arr.fixed_strings.data[0].length = 5;
      std::strcpy(arr.fixed_strings.data[1].data, "World");
      arr.fixed_strings.data[1].length = 5;
      arr.fixed_strings.count = 2;
      
      std::strcpy(arr.bounded_strings.data[0].data, "Test");
      arr.bounded_strings.data[0].length = 4;
      arr.bounded_strings.count = 1;
      
      // Enum arrays
      arr.fixed_statuses.data[0] = SERIALIZATION_TEST_ACTIVE;
      arr.fixed_statuses.data[1] = SERIALIZATION_TEST_ERROR;
      arr.fixed_statuses.count = 2;
      
      arr.bounded_statuses.data[0] = SERIALIZATION_TEST_INACTIVE;
      arr.bounded_statuses.count = 1;
      
      // Sensor arrays
      arr.fixed_sensors.data[0].id = 1;
      arr.fixed_sensors.data[0].value = 25.5f;
      arr.fixed_sensors.data[0].status = SERIALIZATION_TEST_ACTIVE;
      std::strcpy(arr.fixed_sensors.data[0].name.data, "TempSensor");
      arr.fixed_sensors.data[0].name.length = 10;
      arr.fixed_sensors.count = 1;
      
      arr.bounded_sensors.count = 0;
      break;
    }

    case 9: { // UnionTestMessage - with_test_payload
      out_message.type = MessageType::UnionTest;
      auto& msg = out_message.data.union_test;
      msg.payload_type = SERIALIZATION_TEST_UNION_PAYLOAD_SERIALIZATION_TEST;
      
      auto& test = msg.payload.test_payload;
      test.magic_number = 0x12345678;
      const char* str = "Union test message";
      test.test_string.length = std::strlen(str);
      std::strcpy(test.test_string.data, str);
      test.test_float = 99.99f;
      test.test_bool = true;
      test.test_array.data[0] = 1;
      test.test_array.data[1] = 2;
      test.test_array.data[2] = 3;
      test.test_array.data[3] = 4;
      test.test_array.data[4] = 5;
      test.test_array.count = 5;
      break;
    }

    case 10: { // BasicTypesMessage - negative_values (duplicate)
      out_message.type = MessageType::BasicTypes;
      auto& msg = out_message.data.basic_types;
      msg.small_int = -128;
      msg.medium_int = -32768;
      msg.regular_int = -2147483648;
      msg.large_int = -9223372036854775807LL;
      msg.small_uint = 255;
      msg.medium_uint = 65535;
      msg.regular_uint = 4294967295U;
      msg.large_uint = 9223372036854775807ULL;
      msg.single_precision = -273.15f;
      msg.double_precision = -9999.999999;
      msg.flag = false;
      std::strcpy(msg.device_id.data, "NEG-TEST");
      const char* desc = "Negative and max values";
      msg.description.length = std::strlen(desc);
      std::strcpy(msg.description.data, desc);
      break;
    }

    default:
      return false;
  }

  return true;
}
