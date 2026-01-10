/**
 * Test message data definitions.
 * Hardcoded test messages for cross-platform compatibility testing.
 * Uses std::array for efficient storage instead of switch statement.
 */

#include "test_messages_data.hpp"
#include <array>
#include <cstring>

// Helper function to create SerializationTestMessage
static SerializationTestSerializationTestMessage create_serialization_test(
    uint32_t magic, const char* str, float flt, bool bl, 
    const std::initializer_list<int32_t>& arr) {
  SerializationTestSerializationTestMessage msg{};
  msg.magic_number = magic;
  msg.test_string.length = std::strlen(str);
  std::strcpy(msg.test_string.data, str);
  msg.test_float = flt;
  msg.test_bool = bl;
  size_t i = 0;
  for (auto val : arr) {
    if (i >= 5) break;
    msg.test_array.data[i++] = val;
  }
  msg.test_array.count = i;
  return msg;
}

// Helper function to create BasicTypesMessage
static SerializationTestBasicTypesMessage create_basic_types(
    int8_t si, int16_t mi, int32_t ri, int64_t li,
    uint8_t su, uint16_t mu, uint32_t ru, uint64_t lu,
    float sp, double dp, bool fl,
    const char* dev, const char* desc) {
  SerializationTestBasicTypesMessage msg{};
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
  std::strncpy(msg.device_id, dev, 31);
  msg.device_id[31] = '\0';
  msg.description.length = std::strlen(desc);
  std::strncpy(msg.description.data, desc, 128);
  if (msg.description.length > 128) msg.description.length = 128;
  return msg;
}

// Helper function to create UnionTestMessage with array payload
static SerializationTestUnionTestMessage create_union_with_array() {
  SerializationTestUnionTestMessage msg{};
  msg.payload_discriminator = SerializationTestComprehensiveArrayMessage::MSG_ID;
  
  auto& arr = msg.payload.array_payload;
  
  // Fixed arrays (direct access, not .data/.count)
  arr.fixed_ints[0] = 10;
  arr.fixed_ints[1] = 20;
  arr.fixed_ints[2] = 30;
  
  arr.fixed_floats[0] = 1.5f;
  arr.fixed_floats[1] = 2.5f;
  
  arr.fixed_bools[0] = true;
  arr.fixed_bools[1] = false;
  arr.fixed_bools[2] = true;
  arr.fixed_bools[3] = false;
  
  // Bounded arrays (have .data and .count)
  arr.bounded_uints.data[0] = 100;
  arr.bounded_uints.data[1] = 200;
  arr.bounded_uints.count = 2;
  
  arr.bounded_doubles.data[0] = 3.14159;
  arr.bounded_doubles.count = 1;
  
  // Fixed string arrays (2D char arrays)
  std::strcpy(arr.fixed_strings[0], "Hello");
  std::strcpy(arr.fixed_strings[1], "World");
  
  // Bounded string arrays
  std::strcpy(arr.bounded_strings.data[0], "Test");
  arr.bounded_strings.count = 1;
  
  // Enum arrays (fixed is direct array)
  arr.fixed_statuses[0] = SerializationTestStatus::ACTIVE;
  arr.fixed_statuses[1] = SerializationTestStatus::ERROR;
  
  arr.bounded_statuses.data[0] = SerializationTestStatus::INACTIVE;
  arr.bounded_statuses.count = 1;
  
  // Sensor arrays
  arr.fixed_sensors[0].id = 1;
  arr.fixed_sensors[0].value = 25.5f;
  arr.fixed_sensors[0].status = SerializationTestStatus::ACTIVE;
  std::strcpy(arr.fixed_sensors[0].name, "TempSensor");
  
  arr.bounded_sensors.count = 0;
  
  return msg;
}

// Helper function to create UnionTestMessage with test payload
static SerializationTestUnionTestMessage create_union_with_test() {
  SerializationTestUnionTestMessage msg{};
  msg.payload_discriminator = SerializationTestSerializationTestMessage::MSG_ID;
  
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
  
  return msg;
}

// Static array of all test messages - more efficient than switch statement
static const std::array<MixedMessage, 11> test_messages = []() {
  std::array<MixedMessage, 11> messages{};
  
  // 0: SerializationTestMessage - basic_values
  messages[0].type = MessageType::SerializationTest;
  messages[0].data.serialization_test = create_serialization_test(
      0xDEADBEEF, "Cross-platform test!", 3.14159f, true, {100, 200, 300});
  
  // 1: SerializationTestMessage - zero_values
  messages[1].type = MessageType::SerializationTest;
  messages[1].data.serialization_test = create_serialization_test(
      0, "", 0.0f, false, {});
  
  // 2: SerializationTestMessage - max_values
  messages[2].type = MessageType::SerializationTest;
  messages[2].data.serialization_test = create_serialization_test(
      0xFFFFFFFF, "Maximum length test string for coverage!", 999999.9f, true,
      {2147483647, -2147483648, 0, 1, -1});
  
  // 3: SerializationTestMessage - negative_values
  messages[3].type = MessageType::SerializationTest;
  messages[3].data.serialization_test = create_serialization_test(
      0xAAAAAAAA, "Negative test", -273.15f, false, {-100, -200, -300, -400});
  
  // 4: SerializationTestMessage - special_chars
  messages[4].type = MessageType::SerializationTest;
  messages[4].data.serialization_test = create_serialization_test(
      1234567890, "Special: !@#$%^&*()", 2.71828f, true, {0, 1, 1, 2, 3});
  
  // 5: BasicTypesMessage - basic_values
  messages[5].type = MessageType::BasicTypes;
  messages[5].data.basic_types = create_basic_types(
      42, 1000, 123456, 9876543210LL, 200, 50000, 4000000000U, 9223372036854775807ULL,
      3.14159f, 2.718281828459045, true, "DEVICE-001", "Basic test values");
  
  // 6: BasicTypesMessage - zero_values
  messages[6].type = MessageType::BasicTypes;
  messages[6].data.basic_types = create_basic_types(
      0, 0, 0, 0, 0, 0, 0, 0, 0.0f, 0.0, false, "", "");
  
  // 7: BasicTypesMessage - negative_values
  messages[7].type = MessageType::BasicTypes;
  messages[7].data.basic_types = create_basic_types(
      -128, -32768, -2147483648, -9223372036854775807LL, 255, 65535, 4294967295U,
      9223372036854775807ULL, -273.15f, -9999.999999, false, "NEG-TEST",
      "Negative and max values");
  
  // 8: UnionTestMessage - with_array_payload
  messages[8].type = MessageType::UnionTest;
  messages[8].data.union_test = create_union_with_array();
  
  // 9: UnionTestMessage - with_test_payload
  messages[9].type = MessageType::UnionTest;
  messages[9].data.union_test = create_union_with_test();
  
  // 10: BasicTypesMessage - negative_values (duplicate)
  messages[10].type = MessageType::BasicTypes;
  messages[10].data.basic_types = create_basic_types(
      -128, -32768, -2147483648, -9223372036854775807LL, 255, 65535, 4294967295U,
      9223372036854775807ULL, -273.15f, -9999.999999, false, "NEG-TEST",
      "Negative and max values");
  
  return messages;
}();

std::size_t get_test_message_count() {
  return test_messages.size();
}

bool get_test_message(std::size_t index, MixedMessage& out_message) {
  if (index >= test_messages.size()) {
    return false;
  }
  
  out_message = test_messages[index];
  return true;
}
