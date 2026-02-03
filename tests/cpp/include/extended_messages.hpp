#pragma once

#include <cstring>
#include <variant>

#include "../../generated/cpp/extended_test.structframe.hpp"

// Message provider struct for use with TestRunner template
// Contains extended ID messages (1-10), large payload messages (1-2), and variable single array (5 instances)
struct ExtendedMessages {
  // Variant type for message return - includes all extended test message types
  using MessageVariant =
      std::variant<ExtendedTestExtendedIdMessage1, ExtendedTestExtendedIdMessage2, ExtendedTestExtendedIdMessage3,
                   ExtendedTestExtendedIdMessage4, ExtendedTestExtendedIdMessage5, ExtendedTestExtendedIdMessage6,
                   ExtendedTestExtendedIdMessage7, ExtendedTestExtendedIdMessage8, ExtendedTestExtendedIdMessage9,
                   ExtendedTestExtendedIdMessage10, ExtendedTestLargePayloadMessage1, ExtendedTestLargePayloadMessage2,
                   ExtendedTestExtendedVariableSingleArray>;

  // Total number of messages (10 extended IDs + 2 large payloads + 5 variable arrays = 17)
  static constexpr size_t MESSAGE_COUNT = 17;

  // Helper functions to create extended ID messages
  static ExtendedTestExtendedIdMessage1 create_ext_id_1() {
    ExtendedTestExtendedIdMessage1 msg{};
    msg.sequence_number = 12345678;
    std::strncpy(msg.label, "Test Label Extended 1", 31);
    msg.label[31] = '\0';
    msg.value = 3.14159f;
    msg.enabled = true;
    return msg;
  }

  static ExtendedTestExtendedIdMessage2 create_ext_id_2() {
    ExtendedTestExtendedIdMessage2 msg{};
    msg.sensor_id = -42;
    msg.reading = 2.718281828;
    msg.status_code = 50000;
    msg.description.length = static_cast<uint8_t>(std::strlen("Extended ID test message 2"));
    std::strcpy(msg.description.data, "Extended ID test message 2");
    return msg;
  }

  static ExtendedTestExtendedIdMessage3 create_ext_id_3() {
    ExtendedTestExtendedIdMessage3 msg{};
    msg.timestamp = 1704067200000000ULL;
    msg.temperature = -40;
    msg.humidity = 85;
    std::strncpy(msg.location, "Sensor Room A", 15);
    msg.location[15] = '\0';
    return msg;
  }

  static ExtendedTestExtendedIdMessage4 create_ext_id_4() {
    ExtendedTestExtendedIdMessage4 msg{};
    msg.event_id = 999999;
    msg.event_type = 42;
    msg.event_time = 1704067200000LL;
    msg.event_data.length = static_cast<uint8_t>(std::strlen("Event payload with extended message ID"));
    std::strcpy(msg.event_data.data, "Event payload with extended message ID");
    return msg;
  }

  static ExtendedTestExtendedIdMessage5 create_ext_id_5() {
    ExtendedTestExtendedIdMessage5 msg{};
    msg.x_position = 100.5f;
    msg.y_position = -200.25f;
    msg.z_position = 50.125f;
    msg.frame_number = 1000000;
    return msg;
  }

  static ExtendedTestExtendedIdMessage6 create_ext_id_6() {
    ExtendedTestExtendedIdMessage6 msg{};
    msg.command_id = -12345;
    msg.parameter1 = 1000;
    msg.parameter2 = 2000;
    msg.acknowledged = false;
    std::strncpy(msg.command_name, "CALIBRATE_SENSOR", 23);
    msg.command_name[23] = '\0';
    return msg;
  }

  static ExtendedTestExtendedIdMessage7 create_ext_id_7() {
    ExtendedTestExtendedIdMessage7 msg{};
    msg.counter = 4294967295U;
    msg.average = 123.456789;
    msg.minimum = -999.99f;
    msg.maximum = 999.99f;
    return msg;
  }

  static ExtendedTestExtendedIdMessage8 create_ext_id_8() {
    ExtendedTestExtendedIdMessage8 msg{};
    msg.level = 255;
    msg.offset = -32768;
    msg.duration = 86400000;
    std::strncpy(msg.tag, "TEST123", 7);
    msg.tag[7] = '\0';
    return msg;
  }

  static ExtendedTestExtendedIdMessage9 create_ext_id_9() {
    ExtendedTestExtendedIdMessage9 msg{};
    msg.big_number = -9223372036854775807LL;
    msg.big_unsigned = 18446744073709551615ULL;
    msg.precision_value = 1.7976931348623157e+308;
    return msg;
  }

  static ExtendedTestExtendedIdMessage10 create_ext_id_10() {
    ExtendedTestExtendedIdMessage10 msg{};
    msg.small_value = 256;
    std::strncpy(msg.short_text, "Boundary Test", 15);
    msg.short_text[15] = '\0';
    msg.flag = true;
    return msg;
  }

  // Helper functions to create large payload messages
  static ExtendedTestLargePayloadMessage1 create_large_1() {
    ExtendedTestLargePayloadMessage1 msg{};
    for (int i = 0; i < 64; i++) {
      msg.sensor_readings[i] = static_cast<float>(i + 1);
    }
    msg.reading_count = 64;
    msg.timestamp = 1704067200000000LL;
    std::strncpy(msg.device_name, "Large Sensor Array Device", 31);
    msg.device_name[31] = '\0';
    return msg;
  }

  static ExtendedTestLargePayloadMessage2 create_large_2() {
    ExtendedTestLargePayloadMessage2 msg{};
    for (int i = 0; i < 256; i++) {
      msg.large_data[i] = static_cast<uint8_t>(i);
    }
    for (int i = 256; i < 280; i++) {
      msg.large_data[i] = static_cast<uint8_t>(i - 256);
    }
    return msg;
  }

  // Helper function to create variable single array messages
  static ExtendedTestExtendedVariableSingleArray create_ext_var_single(uint64_t timestamp, uint8_t count,
                                                                       uint32_t crc, uint8_t start_value = 0) {
    ExtendedTestExtendedVariableSingleArray msg{};
    msg.timestamp = timestamp;
    msg.telemetry_data.count = count;
    for (int i = 0; i < count; i++) {
      msg.telemetry_data.data[i] = static_cast<uint8_t>((start_value + i) % 256);
    }
    msg.crc = crc;
    return msg;
  }

  // Single function that returns a message based on index
  // Message order: ExtendedId1-10, LargePayload1-2, ExtendedVariableSingleArray x5
  static MessageVariant get_message(size_t index) {
    switch (index) {
      // Extended ID messages (0-9)
      case 0:
        return create_ext_id_1();
      case 1:
        return create_ext_id_2();
      case 2:
        return create_ext_id_3();
      case 3:
        return create_ext_id_4();
      case 4:
        return create_ext_id_5();
      case 5:
        return create_ext_id_6();
      case 6:
        return create_ext_id_7();
      case 7:
        return create_ext_id_8();
      case 8:
        return create_ext_id_9();
      case 9:
        return create_ext_id_10();

      // Large payload messages (10-11)
      case 10:
        return create_large_1();
      case 11:
        return create_large_2();

      // Extended variable single array messages (12-16)
      // Different fill levels: empty, single, 1/3, one-empty, full
      case 12:
        return create_ext_var_single(0x0000000000000001ULL, 0, 0x00000001);  // Empty
      case 13:
        return create_ext_var_single(0x0000000000000002ULL, 1, 0x00000002, 42);  // Single element (starts at 42)
      case 14:
        return create_ext_var_single(0x0000000000000003ULL, 83, 0x00000003);  // 1/3 filled (83/250)
      case 15:
        return create_ext_var_single(0x0000000000000004ULL, 249, 0x00000004);  // One position empty
      case 16:
      default:
        return create_ext_var_single(0x0000000000000005ULL, 250, 0x00000005);  // Full (250/250)
    }
  }
};
