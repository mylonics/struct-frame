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

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string>

#include "../../generated/cpp/serialization_test.structframe.hpp"

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

// Create VariableSingleArray test messages with different fill levels
// 0: Empty (0 elements)
// 1: Single element (1 element)
// 2: One-third filled (67 elements for max_size=200)
// 3: One position empty (199 elements)
// 4: Full (200 elements)

inline SerializationTestVariableSingleArray create_variable_single_array_empty() {
  SerializationTestVariableSingleArray msg{};
  msg.message_id = 0x00000001;
  msg.payload.count = 0;
  msg.checksum = 0x0001;
  return msg;
}

inline SerializationTestVariableSingleArray create_variable_single_array_single() {
  SerializationTestVariableSingleArray msg{};
  msg.message_id = 0x00000002;
  msg.payload.data[0] = 42;
  msg.payload.count = 1;
  msg.checksum = 0x0002;
  return msg;
}

inline SerializationTestVariableSingleArray create_variable_single_array_third() {
  SerializationTestVariableSingleArray msg{};
  msg.message_id = 0x00000003;
  for (uint8_t i = 0; i < 67; i++) {
    msg.payload.data[i] = i;
  }
  msg.payload.count = 67;
  msg.checksum = 0x0003;
  return msg;
}

inline SerializationTestVariableSingleArray create_variable_single_array_almost() {
  SerializationTestVariableSingleArray msg{};
  msg.message_id = 0x00000004;
  for (uint8_t i = 0; i < 199; i++) {
    msg.payload.data[i] = i;
  }
  msg.payload.count = 199;
  msg.checksum = 0x0004;
  return msg;
}

inline SerializationTestVariableSingleArray create_variable_single_array_full() {
  SerializationTestVariableSingleArray msg{};
  msg.message_id = 0x00000005;
  for (int i = 0; i < 200; i++) {
    msg.payload.data[i] = static_cast<uint8_t>(i);
  }
  msg.payload.count = 200;
  msg.checksum = 0x0005;
  return msg;
}

inline SerializationTestMessage create_message_test() {
  SerializationTestMessage msg{};
  msg.severity = SerializationTestMsgSeverity::SEV_MSG;
  msg.module.length = 4;
  std::strcpy(msg.module.data, "test");
  msg.msg.length = 13;
  std::strcpy(msg.msg.data, "A really good");
  return msg;
}

// ============================================================================
// Typed message arrays (one per message type)
// ============================================================================

// SerializationTestMessage array (5 messages)
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

// BasicTypesMessage array (4 messages)
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

// UnionTestMessage array (2 messages)
inline const std::array<SerializationTestUnionTestMessage, 2>& get_union_test_messages() {
  static const std::array<SerializationTestUnionTestMessage, 2> messages = {
      create_union_with_array(),
      create_union_with_test(),
  };
  return messages;
}

// VariableSingleArray array (5 messages with different fill levels)
inline const std::array<SerializationTestVariableSingleArray, 5>& get_variable_single_array_messages() {
  static const std::array<SerializationTestVariableSingleArray, 5> messages = {
      create_variable_single_array_empty(),   // 0: Empty
      create_variable_single_array_single(),  // 1: Single element
      create_variable_single_array_third(),   // 2: One-third filled
      create_variable_single_array_almost(),  // 3: One position empty
      create_variable_single_array_full(),    // 4: Full
  };
  return messages;
}

// Message array (1 message)
inline const std::array<SerializationTestMessage, 1>& get_message_messages() {
  static const std::array<SerializationTestMessage, 1> messages = {
      create_message_test(),
  };
  return messages;
}

// ============================================================================
// Message ID order array - defines the encode/decode sequence
// ============================================================================

// Message count constant
constexpr size_t MESSAGE_COUNT = 17;

// The msg_id order array - maps position to which message type to use
inline const std::array<uint16_t, MESSAGE_COUNT>& get_msg_id_order() {
  static const std::array<uint16_t, MESSAGE_COUNT> order = {
      SerializationTestSerializationTestMessage::MSG_ID,  // 0: SerializationTest[0]
      SerializationTestSerializationTestMessage::MSG_ID,  // 1: SerializationTest[1]
      SerializationTestSerializationTestMessage::MSG_ID,  // 2: SerializationTest[2]
      SerializationTestSerializationTestMessage::MSG_ID,  // 3: SerializationTest[3]
      SerializationTestSerializationTestMessage::MSG_ID,  // 4: SerializationTest[4]
      SerializationTestBasicTypesMessage::MSG_ID,         // 5: BasicTypes[0]
      SerializationTestBasicTypesMessage::MSG_ID,         // 6: BasicTypes[1]
      SerializationTestBasicTypesMessage::MSG_ID,         // 7: BasicTypes[2]
      SerializationTestUnionTestMessage::MSG_ID,          // 8: UnionTest[0]
      SerializationTestUnionTestMessage::MSG_ID,          // 9: UnionTest[1]
      SerializationTestBasicTypesMessage::MSG_ID,         // 10: BasicTypes[3]
      SerializationTestVariableSingleArray::MSG_ID,       // 11: VariableSingleArray[0] - empty
      SerializationTestVariableSingleArray::MSG_ID,       // 12: VariableSingleArray[1] - single
      SerializationTestVariableSingleArray::MSG_ID,       // 13: VariableSingleArray[2] - 1/3 filled
      SerializationTestVariableSingleArray::MSG_ID,       // 14: VariableSingleArray[3] - one empty
      SerializationTestVariableSingleArray::MSG_ID,       // 15: VariableSingleArray[4] - full
      SerializationTestMessage::MSG_ID,                   // 16: Message[0]
  };
  return order;
}

// ============================================================================
// Encoder helper - writes messages in order using index tracking
// ============================================================================

struct Encoder {
  size_t serial_idx = 0;
  size_t basic_idx = 0;
  size_t union_idx = 0;
  size_t var_single_idx = 0;
  size_t message_idx = 0;

  template <typename WriterType>
  size_t write_message(WriterType& writer, uint16_t msg_id) {
    if (msg_id == SerializationTestSerializationTestMessage::MSG_ID) {
      return writer.write(get_serialization_test_messages()[serial_idx++]);
    } else if (msg_id == SerializationTestBasicTypesMessage::MSG_ID) {
      return writer.write(get_basic_types_messages()[basic_idx++]);
    } else if (msg_id == SerializationTestUnionTestMessage::MSG_ID) {
      return writer.write(get_union_test_messages()[union_idx++]);
    } else if (msg_id == SerializationTestVariableSingleArray::MSG_ID) {
      return writer.write(get_variable_single_array_messages()[var_single_idx++]);
    } else if (msg_id == SerializationTestMessage::MSG_ID) {
      return writer.write(get_message_messages()[message_idx++]);
    }
    return 0;
  }
};

// ============================================================================
// Validator helper - validates decoded messages against expected data
// ============================================================================

struct Validator {
  size_t serial_idx = 0;
  size_t basic_idx = 0;
  size_t union_idx = 0;
  size_t var_single_idx = 0;
  size_t message_idx = 0;

  bool get_expected(uint16_t msg_id, const uint8_t*& data, size_t& size) {
    if (msg_id == SerializationTestSerializationTestMessage::MSG_ID) {
      const auto& msg = get_serialization_test_messages()[serial_idx++];
      data = msg.data();
      size = msg.size();
      return true;
    } else if (msg_id == SerializationTestBasicTypesMessage::MSG_ID) {
      const auto& msg = get_basic_types_messages()[basic_idx++];
      data = msg.data();
      size = msg.size();
      return true;
    } else if (msg_id == SerializationTestUnionTestMessage::MSG_ID) {
      const auto& msg = get_union_test_messages()[union_idx++];
      data = msg.data();
      size = msg.size();
      return true;
    } else if (msg_id == SerializationTestVariableSingleArray::MSG_ID) {
      const auto& msg = get_variable_single_array_messages()[var_single_idx++];
      data = msg.data();
      size = msg.size();
      return true;
    } else if (msg_id == SerializationTestMessage::MSG_ID) {
      const auto& msg = get_message_messages()[message_idx++];
      data = msg.data();
      size = msg.size();
      return true;
    }
    return false;
  }

  /** Validate decoded message using operator== (for equality testing) */
  bool validate_with_equals(const FrameParsers::FrameMsgInfo& frame_info) {
    if (frame_info.msg_id == SerializationTestSerializationTestMessage::MSG_ID) {
      const auto& expected = get_serialization_test_messages()[serial_idx++];
      SerializationTestSerializationTestMessage decoded;
      size_t unpacked = decoded.deserialize(frame_info);
      if (unpacked == 0) return false;
      return decoded == expected;
    } else if (frame_info.msg_id == SerializationTestBasicTypesMessage::MSG_ID) {
      const auto& expected = get_basic_types_messages()[basic_idx++];
      SerializationTestBasicTypesMessage decoded;
      size_t unpacked = decoded.deserialize(frame_info);
      if (unpacked == 0) return false;
      return decoded == expected;
    } else if (frame_info.msg_id == SerializationTestUnionTestMessage::MSG_ID) {
      const auto& expected = get_union_test_messages()[union_idx++];
      SerializationTestUnionTestMessage decoded;
      size_t unpacked = decoded.deserialize(frame_info);
      if (unpacked == 0) return false;
      return decoded == expected;
    } else if (frame_info.msg_id == SerializationTestVariableSingleArray::MSG_ID) {
      const auto& expected = get_variable_single_array_messages()[var_single_idx++];
      SerializationTestVariableSingleArray decoded;
      size_t unpacked = decoded.deserialize(frame_info);
      if (unpacked == 0) return false;
      return decoded == expected;
    } else if (frame_info.msg_id == SerializationTestMessage::MSG_ID) {
      const auto& expected = get_message_messages()[message_idx++];
      SerializationTestMessage decoded;
      size_t unpacked = decoded.deserialize(frame_info);
      if (unpacked == 0) return false;
      return decoded == expected;
    }
    return false;
  }
};

// ============================================================================
// Test configuration - provides all data for TestCodec templates
// ============================================================================

struct Config {
  static constexpr size_t MESSAGE_COUNT = TestMessagesData::MESSAGE_COUNT;
  static constexpr size_t BUFFER_SIZE = 4096;
  static constexpr const char* FORMATS_HELP =
      "profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network";
  static constexpr const char* TEST_NAME = "C++";

  using Encoder = TestMessagesData::Encoder;
  using Validator = TestMessagesData::Validator;

  static const std::array<uint16_t, MESSAGE_COUNT>& get_msg_id_order() { return TestMessagesData::get_msg_id_order(); }

  static FrameParsers::MessageInfo get_message_info(uint16_t msg_id) { return FrameParsers::get_message_info(msg_id); }

  static bool supports_format(const std::string& format) {
    return format == "profile_standard" || format == "profile_sensor" || format == "profile_ipc" ||
           format == "profile_bulk" || format == "profile_network";
  }
};

}  // namespace TestMessagesData
