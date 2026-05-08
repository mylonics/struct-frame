#pragma once

#include <cstring>
#include <variant>

#include "../../generated/cpp/extended_test.structframe.hpp"
using namespace structframe::extended_test;

// Message provider struct for use with TestRunner template.
// Three representative extended IDs (boundary/mid/high) + two large-payload
// messages + five variable-array fill levels = 10 total.
struct ExtendedMessages {
  using MessageVariant =
      std::variant<ExtendedIdMessage10, ExtendedIdMessage2, ExtendedIdMessage9,
                   LargePayloadMessage1, LargePayloadMessage2,
                   ExtendedVariableSingleArray>;

  static constexpr size_t MESSAGE_COUNT = 10;

  static ExtendedIdMessage10 create_ext_id_10() {
    ExtendedIdMessage10 msg{};
    msg.small_value = 256;
    std::strncpy(msg.short_text, "Boundary Test", 15);
    msg.short_text[15] = '\0';
    msg.flag = true;
    return msg;
  }

  static ExtendedIdMessage2 create_ext_id_2() {
    ExtendedIdMessage2 msg{};
    msg.sensor_id = -42;
    msg.reading = 2.718281828;
    msg.status_code = 50000;
    msg.description.length = static_cast<uint8_t>(std::strlen("Extended ID test message 2"));
    std::strcpy(msg.description.data, "Extended ID test message 2");
    return msg;
  }

  static ExtendedIdMessage9 create_ext_id_9() {
    ExtendedIdMessage9 msg{};
    msg.big_number = -9223372036854775807LL;
    msg.big_unsigned = 18446744073709551615ULL;
    msg.precision_value = 1.7976931348623157e+308;
    return msg;
  }

  static LargePayloadMessage1 create_large_1() {
    LargePayloadMessage1 msg{};
    for (int i = 0; i < 64; i++) {
      msg.sensor_readings[i] = static_cast<float>(i + 1);
    }
    msg.reading_count = 64;
    msg.timestamp = 1704067200000000LL;
    std::strncpy(msg.device_name, "Large Sensor Array Device", 31);
    msg.device_name[31] = '\0';
    return msg;
  }

  static LargePayloadMessage2 create_large_2() {
    LargePayloadMessage2 msg{};
    for (int i = 0; i < 256; i++) {
      msg.large_data[i] = static_cast<uint8_t>(i);
    }
    for (int i = 256; i < 280; i++) {
      msg.large_data[i] = static_cast<uint8_t>(i - 256);
    }
    return msg;
  }

  static ExtendedVariableSingleArray create_ext_var_single(uint64_t timestamp, uint8_t count,
                                                            uint32_t crc, uint8_t start_value = 0) {
    ExtendedVariableSingleArray msg{};
    msg.timestamp = timestamp;
    msg.telemetry_data.count = count;
    for (int i = 0; i < count; i++) {
      msg.telemetry_data.data[i] = static_cast<uint8_t>((start_value + i) % 256);
    }
    msg.crc = crc;
    return msg;
  }

  // Message order: ExtendedId10, ExtendedId2, ExtendedId9, Large1, Large2, Var×5
  static MessageVariant get_message(size_t index) {
    switch (index) {
      case 0: return create_ext_id_10();
      case 1: return create_ext_id_2();
      case 2: return create_ext_id_9();
      case 3: return create_large_1();
      case 4: return create_large_2();
      case 5: return create_ext_var_single(0x0000000000000001ULL, 0,   0x00000001);
      case 6: return create_ext_var_single(0x0000000000000002ULL, 1,   0x00000002, 42);
      case 7: return create_ext_var_single(0x0000000000000003ULL, 83,  0x00000003);
      case 8: return create_ext_var_single(0x0000000000000004ULL, 249, 0x00000004);
      case 9:
      default:
        return create_ext_var_single(0x0000000000000005ULL, 250, 0x00000005);
    }
  }
};
