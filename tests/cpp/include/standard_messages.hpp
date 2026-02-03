#pragma once

#include <cstring>
#include <variant>

#include "../../generated/cpp/serialization_test.structframe.hpp"

// Message provider struct for use with TestRunner template
struct StandardMessages {
  // Variant type for message return - includes all message types from standard_test_data
  using MessageVariant =
      std::variant<SerializationTestSerializationTestMessage, SerializationTestBasicTypesMessage,
                   SerializationTestUnionTestMessage, SerializationTestVariableSingleArray, SerializationTestMessage>;

  // Total number of messages (matches MESSAGE_COUNT from standard_test_data)
  static constexpr size_t MESSAGE_COUNT = 17;

  // Helper functions to create messages (same as standard_test_data)
  static SerializationTestSerializationTestMessage create_serialization_test(
      uint32_t magic, const char* str, float flt, bool bl, const std::initializer_list<int32_t>& arr) {
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

  static SerializationTestBasicTypesMessage create_basic_types(int8_t si, int16_t mi, int32_t ri, int64_t li,
                                                               uint8_t su, uint16_t mu, uint32_t ru, uint64_t lu,
                                                               float sp, double dp, bool fl, const char* dev,
                                                               const char* desc) {
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

  static SerializationTestUnionTestMessage create_union_with_array() {
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

  static SerializationTestUnionTestMessage create_union_with_test() {
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

  static SerializationTestVariableSingleArray create_variable_single_array_empty() {
    SerializationTestVariableSingleArray msg{};
    msg.message_id = 0x00000001;
    msg.payload.count = 0;
    msg.checksum = 0x0001;
    return msg;
  }

  static SerializationTestVariableSingleArray create_variable_single_array_single() {
    SerializationTestVariableSingleArray msg{};
    msg.message_id = 0x00000002;
    msg.payload.data[0] = 42;
    msg.payload.count = 1;
    msg.checksum = 0x0002;
    return msg;
  }

  static SerializationTestVariableSingleArray create_variable_single_array_third() {
    SerializationTestVariableSingleArray msg{};
    msg.message_id = 0x00000003;
    for (uint8_t i = 0; i < 67; i++) {
      msg.payload.data[i] = i;
    }
    msg.payload.count = 67;
    msg.checksum = 0x0003;
    return msg;
  }

  static SerializationTestVariableSingleArray create_variable_single_array_almost() {
    SerializationTestVariableSingleArray msg{};
    msg.message_id = 0x00000004;
    for (uint8_t i = 0; i < 199; i++) {
      msg.payload.data[i] = i;
    }
    msg.payload.count = 199;
    msg.checksum = 0x0004;
    return msg;
  }

  static SerializationTestVariableSingleArray create_variable_single_array_full() {
    SerializationTestVariableSingleArray msg{};
    msg.message_id = 0x00000005;
    for (int i = 0; i < 200; i++) {
      msg.payload.data[i] = static_cast<uint8_t>(i);
    }
    msg.payload.count = 200;
    msg.checksum = 0x0005;
    return msg;
  }

  static SerializationTestMessage create_message_test() {
    SerializationTestMessage msg{};
    msg.severity = SerializationTestMsgSeverity::SEV_MSG;
    msg.module.length = 4;
    std::strcpy(msg.module.data, "test");
    msg.msg.length = 13;
    std::strcpy(msg.msg.data, "A really good");
    return msg;
  }

  // Single function that returns a message based on index
  // Message order matches standard_test_data get_msg_id_order()
  static MessageVariant get_message(size_t index) {
    switch (index) {
      // SerializationTest messages (0-4)
      case 0:
        return create_serialization_test(0xDEADBEEF, "Cross-platform test!", 3.14159f, true, {100, 200, 300});
      case 1:
        return create_serialization_test(0, "", 0.0f, false, {});
      case 2:
        return create_serialization_test(0xFFFFFFFF, "Maximum length test string for coverage!", 999999.9f, true,
                                         {2147483647, static_cast<int32_t>(-2147483648), 0, 1, -1});
      case 3:
        return create_serialization_test(0xAAAAAAAA, "Negative test", -273.15f, false, {-100, -200, -300, -400});
      case 4:
        return create_serialization_test(1234567890, "Special: !@#$%^&*()", 2.71828f, true, {0, 1, 1, 2, 3});

      // BasicTypes messages (5-7, 10)
      case 5:
        return create_basic_types(42, 1000, 123456, 9876543210LL, 200, 50000, 4000000000U, 9223372036854775807ULL,
                                  3.14159f, 2.718281828459045, true, "DEVICE-001", "Basic test values");
      case 6:
        return create_basic_types(0, 0, 0, 0, 0, 0, 0, 0, 0.0f, 0.0, false, "", "");
      case 7:
        return create_basic_types(-128, -32768, -2147483648, -9223372036854775807LL, 255, 65535, 4294967295U,
                                  9223372036854775807ULL, -273.15f, -9999.999999, false, "NEG-TEST",
                                  "Negative and max values");

      // UnionTest messages (8-9)
      case 8:
        return create_union_with_array();
      case 9:
        return create_union_with_test();

      // BasicTypes message (10)
      case 10:
        return create_basic_types(-128, -32768, -2147483648, -9223372036854775807LL, 255, 65535, 4294967295U,
                                  9223372036854775807ULL, -273.15f, -9999.999999, false, "NEG-TEST",
                                  "Negative and max values");

      // VariableSingleArray messages (11-15)
      case 11:
        return create_variable_single_array_empty();
      case 12:
        return create_variable_single_array_single();
      case 13:
        return create_variable_single_array_third();
      case 14:
        return create_variable_single_array_almost();
      case 15:
        return create_variable_single_array_full();

      // Message (16)
      case 16:
      default:
        return create_message_test();
    }
  }
};
