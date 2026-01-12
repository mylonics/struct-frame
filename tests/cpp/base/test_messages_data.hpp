/**
 * Test message data definitions (header-only).
 * Hardcoded test messages for cross-platform compatibility testing.
 * Uses separate arrays per message type with a unified MessageRef array for ordering.
 */

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>

#include "serialization_test.sf.hpp"

/**
 * A lightweight reference to a message that provides uniform access to
 * message ID, size, and data regardless of the concrete message type.
 */
struct MessageRef {
  uint16_t msg_id;
  size_t msg_size;
  const uint8_t* msg_data;

  template <typename T>
  static MessageRef from(const T& msg) {
    return {T::MSG_ID, T::MAX_SIZE, msg.data()};
  }
};

namespace TestMessagesData {

// ============================================================================
// Helper functions to create messages
// ============================================================================

inline SerializationTestSerializationTestMessage create_serialization_test(uint32_t magic, const char* str, float flt,
                                                                           bool bl,
                                                                           const std::initializer_list<int32_t>& arr) {
  SerializationTestSerializationTestMessage msg{};
  msg.magic_number = magic;
  msg.test_string.length = static_cast<uint8_t>(std::strlen(str));
  std::strcpy(msg.test_string.data, str);
  msg.test_float = flt;
  msg.test_bool = bl;
  size_t i = 0;
  for (auto val : arr) {
    if (i >= 5) break;
    msg.test_array.data[i++] = val;
  }
  msg.test_array.count = static_cast<uint8_t>(i);
  return msg;
}

inline SerializationTestBasicTypesMessage create_basic_types(int8_t si, int16_t mi, int32_t ri, int64_t li, uint8_t su,
                                                             uint16_t mu, uint32_t ru, uint64_t lu, float sp, double dp,
                                                             bool fl, const char* dev, const char* desc) {
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
  msg.description.length = static_cast<uint8_t>(std::strlen(desc));
  std::strncpy(msg.description.data, desc, 128);
  if (msg.description.length > 128) msg.description.length = 128;
  return msg;
}

inline SerializationTestUnionTestMessage create_union_with_array() {
  SerializationTestUnionTestMessage msg{};
  msg.payload_discriminator = SerializationTestComprehensiveArrayMessage::MSG_ID;

  auto& arr = msg.payload.array_payload;

  arr.fixed_ints[0] = 10;
  arr.fixed_ints[1] = 20;
  arr.fixed_ints[2] = 30;

  arr.fixed_floats[0] = 1.5f;
  arr.fixed_floats[1] = 2.5f;

  arr.fixed_bools[0] = true;
  arr.fixed_bools[1] = false;
  arr.fixed_bools[2] = true;
  arr.fixed_bools[3] = false;

  arr.bounded_uints.data[0] = 100;
  arr.bounded_uints.data[1] = 200;
  arr.bounded_uints.count = 2;

  arr.bounded_doubles.data[0] = 3.14159;
  arr.bounded_doubles.count = 1;

  std::strcpy(arr.fixed_strings[0], "Hello");
  std::strcpy(arr.fixed_strings[1], "World");

  std::strcpy(arr.bounded_strings.data[0], "Test");
  arr.bounded_strings.count = 1;

  arr.fixed_statuses[0] = SerializationTestStatus::ACTIVE;
  arr.fixed_statuses[1] = SerializationTestStatus::ERROR;

  arr.bounded_statuses.data[0] = SerializationTestStatus::INACTIVE;
  arr.bounded_statuses.count = 1;

  arr.fixed_sensors[0].id = 1;
  arr.fixed_sensors[0].value = 25.5f;
  arr.fixed_sensors[0].status = SerializationTestStatus::ACTIVE;
  std::strcpy(arr.fixed_sensors[0].name, "TempSensor");

  arr.bounded_sensors.count = 0;

  return msg;
}

inline SerializationTestUnionTestMessage create_union_with_test() {
  SerializationTestUnionTestMessage msg{};
  msg.payload_discriminator = SerializationTestSerializationTestMessage::MSG_ID;

  auto& test = msg.payload.test_payload;
  test.magic_number = 0x12345678;
  const char* str = "Union test message";
  test.test_string.length = static_cast<uint8_t>(std::strlen(str));
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

// ============================================================================
// Typed message arrays (one per message type)
// ============================================================================

inline const std::array<SerializationTestSerializationTestMessage, 5>& get_serialization_test_messages() {
  static const std::array<SerializationTestSerializationTestMessage, 5> messages = {
      create_serialization_test(0xDEADBEEF, "Cross-platform test!", 3.14159f, true, {100, 200, 300}),
      create_serialization_test(0, "", 0.0f, false, {}),
      create_serialization_test(0xFFFFFFFF, "Maximum length test string for coverage!", 999999.9f, true,
                                {2147483647, -2147483648, 0, 1, -1}),
      create_serialization_test(0xAAAAAAAA, "Negative test", -273.15f, false, {-100, -200, -300, -400}),
      create_serialization_test(1234567890, "Special: !@#$%^&*()", 2.71828f, true, {0, 1, 1, 2, 3}),
  };
  return messages;
}

inline const std::array<SerializationTestBasicTypesMessage, 4>& get_basic_types_messages() {
  static const std::array<SerializationTestBasicTypesMessage, 4> messages = {
      create_basic_types(42, 1000, 123456, 9876543210LL, 200, 50000, 4000000000U, 9223372036854775807ULL, 3.14159f,
                         2.718281828459045, true, "DEVICE-001", "Basic test values"),
      create_basic_types(0, 0, 0, 0, 0, 0, 0, 0, 0.0f, 0.0, false, "", ""),
      create_basic_types(-128, -32768, -2147483648, -9223372036854775807LL, 255, 65535, 4294967295U,
                         9223372036854775807ULL, -273.15f, -9999.999999, false, "NEG-TEST", "Negative and max values"),
      create_basic_types(-128, -32768, -2147483648, -9223372036854775807LL, 255, 65535, 4294967295U,
                         9223372036854775807ULL, -273.15f, -9999.999999, false, "NEG-TEST", "Negative and max values"),
  };
  return messages;
}

inline const std::array<SerializationTestUnionTestMessage, 2>& get_union_test_messages() {
  static const std::array<SerializationTestUnionTestMessage, 2> messages = {
      create_union_with_array(),
      create_union_with_test(),
  };
  return messages;
}

// ============================================================================
// Unified message reference array (defines encode/decode order)
// ============================================================================

inline const std::array<MessageRef, 11>& get_message_order() {
  static const std::array<MessageRef, 11> order = []() {
    const auto& serial = get_serialization_test_messages();
    const auto& basic = get_basic_types_messages();
    const auto& unions = get_union_test_messages();

    return std::array<MessageRef, 11>{
        MessageRef::from(serial[0]),  // 0: SerializationTest - basic_values
        MessageRef::from(serial[1]),  // 1: SerializationTest - zero_values
        MessageRef::from(serial[2]),  // 2: SerializationTest - max_values
        MessageRef::from(serial[3]),  // 3: SerializationTest - negative_values
        MessageRef::from(serial[4]),  // 4: SerializationTest - special_chars
        MessageRef::from(basic[0]),   // 5: BasicTypes - basic_values
        MessageRef::from(basic[1]),   // 6: BasicTypes - zero_values
        MessageRef::from(basic[2]),   // 7: BasicTypes - negative_values
        MessageRef::from(unions[0]),  // 8: UnionTest - with_array_payload
        MessageRef::from(unions[1]),  // 9: UnionTest - with_test_payload
        MessageRef::from(basic[3]),   // 10: BasicTypes - negative_values (duplicate)
    };
  }();
  return order;
}

}  // namespace TestMessagesData

/**
 * Get the total number of test messages.
 */
inline size_t get_test_message_count() { return TestMessagesData::get_message_order().size(); }

/**
 * Get a message reference by index.
 */
inline const MessageRef& get_test_message(size_t index) { return TestMessagesData::get_message_order()[index]; }
