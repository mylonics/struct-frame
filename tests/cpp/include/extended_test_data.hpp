/**
 * Extended test message data definitions (header-only).
 * Hardcoded test messages for extended message ID and payload testing.
 *
 * Structure:
 * - Separate arrays for each message type (ExtendedId1-10, LargePayload1-2)
 * - A msg_id order array (length 12) defines the encode/decode sequence
 * - Encoding uses msg_id array to select which typed array to pull from
 * - Decoding uses decoded msg_id to find the right array for comparison
 */

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string>

#include "../../generated/cpp/extended_test.structframe.hpp"

namespace ExtendedTestMessages {

// ============================================================================
// Helper functions to create messages
// ============================================================================

inline ExtendedTestExtendedIdMessage1 create_ext_id_1() {
  ExtendedTestExtendedIdMessage1 msg{};
  msg.sequence_number = 12345678;
  std::strncpy(msg.label, "Test Label Extended 1", 31);
  msg.label[31] = '\0';
  msg.value = 3.14159f;
  msg.enabled = true;
  return msg;
}

inline ExtendedTestExtendedIdMessage2 create_ext_id_2() {
  ExtendedTestExtendedIdMessage2 msg{};
  msg.sensor_id = -42;
  msg.reading = 2.718281828;
  msg.status_code = 50000;
  msg.description.length = static_cast<uint8_t>(std::strlen("Extended ID test message 2"));
  std::strcpy(msg.description.data, "Extended ID test message 2");
  return msg;
}

inline ExtendedTestExtendedIdMessage3 create_ext_id_3() {
  ExtendedTestExtendedIdMessage3 msg{};
  msg.timestamp = 1704067200000000ULL;
  msg.temperature = -40;
  msg.humidity = 85;
  std::strncpy(msg.location, "Sensor Room A", 15);
  msg.location[15] = '\0';
  return msg;
}

inline ExtendedTestExtendedIdMessage4 create_ext_id_4() {
  ExtendedTestExtendedIdMessage4 msg{};
  msg.event_id = 999999;
  msg.event_type = 42;
  msg.event_time = 1704067200000LL;
  msg.event_data.length = static_cast<uint8_t>(std::strlen("Event payload with extended message ID"));
  std::strcpy(msg.event_data.data, "Event payload with extended message ID");
  return msg;
}

inline ExtendedTestExtendedIdMessage5 create_ext_id_5() {
  ExtendedTestExtendedIdMessage5 msg{};
  msg.x_position = 100.5f;
  msg.y_position = -200.25f;
  msg.z_position = 50.125f;
  msg.frame_number = 1000000;
  return msg;
}

inline ExtendedTestExtendedIdMessage6 create_ext_id_6() {
  ExtendedTestExtendedIdMessage6 msg{};
  msg.command_id = -12345;
  msg.parameter1 = 1000;
  msg.parameter2 = 2000;
  msg.acknowledged = false;
  std::strncpy(msg.command_name, "CALIBRATE_SENSOR", 23);
  msg.command_name[23] = '\0';
  return msg;
}

inline ExtendedTestExtendedIdMessage7 create_ext_id_7() {
  ExtendedTestExtendedIdMessage7 msg{};
  msg.counter = 4294967295U;
  msg.average = 123.456789;
  msg.minimum = -999.99f;
  msg.maximum = 999.99f;
  return msg;
}

inline ExtendedTestExtendedIdMessage8 create_ext_id_8() {
  ExtendedTestExtendedIdMessage8 msg{};
  msg.level = 255;
  msg.offset = -32768;
  msg.duration = 86400000;
  std::strncpy(msg.tag, "TEST123", 7);
  msg.tag[7] = '\0';
  return msg;
}

inline ExtendedTestExtendedIdMessage9 create_ext_id_9() {
  ExtendedTestExtendedIdMessage9 msg{};
  msg.big_number = -9223372036854775807LL;
  msg.big_unsigned = 18446744073709551615ULL;
  msg.precision_value = 1.7976931348623157e+308;
  return msg;
}

inline ExtendedTestExtendedIdMessage10 create_ext_id_10() {
  ExtendedTestExtendedIdMessage10 msg{};
  msg.small_value = 256;
  std::strncpy(msg.short_text, "Boundary Test", 15);
  msg.short_text[15] = '\0';
  msg.flag = true;
  return msg;
}

inline ExtendedTestLargePayloadMessage1 create_large_1() {
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

inline ExtendedTestLargePayloadMessage2 create_large_2() {
  ExtendedTestLargePayloadMessage2 msg{};
  for (int i = 0; i < 256; i++) {
    msg.large_data[i] = static_cast<uint8_t>(i);
  }
  for (int i = 256; i < 280; i++) {
    msg.large_data[i] = static_cast<uint8_t>(i - 256);
  }
  return msg;
}

inline ExtendedTestExtendedVariableSingleArray create_ext_var_single(uint64_t timestamp, const uint8_t* data,
                                                                     uint8_t length, uint32_t crc) {
  ExtendedTestExtendedVariableSingleArray msg{};
  msg.timestamp = timestamp;
  msg.telemetry_data.count = length;
  for (int i = 0; i < length; i++) {
    msg.telemetry_data.data[i] = data[i];
  }
  msg.crc = crc;
  return msg;
}

// ============================================================================
// Message getters - return static instances of each message
// ============================================================================

inline const ExtendedTestExtendedIdMessage1& get_message_ext_1() {
  static const auto msg = create_ext_id_1();
  return msg;
}

inline const ExtendedTestExtendedIdMessage2& get_message_ext_2() {
  static const auto msg = create_ext_id_2();
  return msg;
}

inline const ExtendedTestExtendedIdMessage3& get_message_ext_3() {
  static const auto msg = create_ext_id_3();
  return msg;
}

inline const ExtendedTestExtendedIdMessage4& get_message_ext_4() {
  static const auto msg = create_ext_id_4();
  return msg;
}

inline const ExtendedTestExtendedIdMessage5& get_message_ext_5() {
  static const auto msg = create_ext_id_5();
  return msg;
}

inline const ExtendedTestExtendedIdMessage6& get_message_ext_6() {
  static const auto msg = create_ext_id_6();
  return msg;
}

inline const ExtendedTestExtendedIdMessage7& get_message_ext_7() {
  static const auto msg = create_ext_id_7();
  return msg;
}

inline const ExtendedTestExtendedIdMessage8& get_message_ext_8() {
  static const auto msg = create_ext_id_8();
  return msg;
}

inline const ExtendedTestExtendedIdMessage9& get_message_ext_9() {
  static const auto msg = create_ext_id_9();
  return msg;
}

inline const ExtendedTestExtendedIdMessage10& get_message_ext_10() {
  static const auto msg = create_ext_id_10();
  return msg;
}

inline const ExtendedTestLargePayloadMessage1& get_message_large_1() {
  static const auto msg = create_large_1();
  return msg;
}

inline const ExtendedTestLargePayloadMessage2& get_message_large_2() {
  static const auto msg = create_large_2();
  return msg;
}

// Get ExtendedVariableSingleArray messages (5 with different fill levels for max_size=250)
inline const std::array<ExtendedTestExtendedVariableSingleArray, 5>& get_ext_var_single_messages() {
  static const auto msgs = []() {
    std::array<ExtendedTestExtendedVariableSingleArray, 5> arr{};

    // Empty payload (0 elements)
    arr[0].timestamp = 0x0000000000000001ULL;
    arr[0].telemetry_data.count = 0;
    arr[0].crc = 0x00000001;

    // Single element
    arr[1].timestamp = 0x0000000000000002ULL;
    arr[1].telemetry_data.count = 1;
    arr[1].telemetry_data.data[0] = 42;
    arr[1].crc = 0x00000002;

    // One-third filled (83 elements for max_size=250)
    arr[2].timestamp = 0x0000000000000003ULL;
    arr[2].telemetry_data.count = 83;
    for (int i = 0; i < 83; i++) {
      arr[2].telemetry_data.data[i] = static_cast<uint8_t>(i);
    }
    arr[2].crc = 0x00000003;

    // One position empty (249 elements)
    arr[3].timestamp = 0x0000000000000004ULL;
    arr[3].telemetry_data.count = 249;
    for (int i = 0; i < 249; i++) {
      arr[3].telemetry_data.data[i] = static_cast<uint8_t>(i % 256);
    }
    arr[3].crc = 0x00000004;

    // Full (250 elements)
    arr[4].timestamp = 0x0000000000000005ULL;
    arr[4].telemetry_data.count = 250;
    for (int i = 0; i < 250; i++) {
      arr[4].telemetry_data.data[i] = static_cast<uint8_t>(i % 256);
    }
    arr[4].crc = 0x00000005;

    return arr;
  }();
  return msgs;
}

// ============================================================================
// Message ID order array - defines the encode/decode sequence
// ============================================================================

// Message count constant
constexpr size_t MESSAGE_COUNT = 17;

// The msg_id order array - maps position to which message type to use
inline const std::array<uint16_t, MESSAGE_COUNT>& get_msg_id_order() {
  static const std::array<uint16_t, MESSAGE_COUNT> order = {
      ExtendedTestExtendedIdMessage1::MSG_ID,           // 0
      ExtendedTestExtendedIdMessage2::MSG_ID,           // 1
      ExtendedTestExtendedIdMessage3::MSG_ID,           // 2
      ExtendedTestExtendedIdMessage4::MSG_ID,           // 3
      ExtendedTestExtendedIdMessage5::MSG_ID,           // 4
      ExtendedTestExtendedIdMessage6::MSG_ID,           // 5
      ExtendedTestExtendedIdMessage7::MSG_ID,           // 6
      ExtendedTestExtendedIdMessage8::MSG_ID,           // 7
      ExtendedTestExtendedIdMessage9::MSG_ID,           // 8
      ExtendedTestExtendedIdMessage10::MSG_ID,          // 9
      ExtendedTestLargePayloadMessage1::MSG_ID,         // 10
      ExtendedTestLargePayloadMessage2::MSG_ID,         // 11
      ExtendedTestExtendedVariableSingleArray::MSG_ID,  // 12: empty
      ExtendedTestExtendedVariableSingleArray::MSG_ID,  // 13: single
      ExtendedTestExtendedVariableSingleArray::MSG_ID,  // 14: 1/3 filled
      ExtendedTestExtendedVariableSingleArray::MSG_ID,  // 15: one empty
      ExtendedTestExtendedVariableSingleArray::MSG_ID,  // 16: full
  };
  return order;
}

// ============================================================================
// Encoder helper - writes messages by msg_id lookup
// For variable messages, tracks indices since we have multiple instances
// ============================================================================

struct Encoder {
  size_t ext_var_single_idx = 0;

  template <typename WriterType>
  size_t write_message(WriterType& writer, uint16_t msg_id) {
    // Handle variable messages with index tracking
    if (msg_id == ExtendedTestExtendedVariableSingleArray::MSG_ID) {
      const auto& msg = get_ext_var_single_messages()[ext_var_single_idx++];
      return writer.write(msg);
    }

    switch (msg_id) {
      case ExtendedTestExtendedIdMessage1::MSG_ID:
        return writer.write(get_message_ext_1());
      case ExtendedTestExtendedIdMessage2::MSG_ID:
        return writer.write(get_message_ext_2());
      case ExtendedTestExtendedIdMessage3::MSG_ID:
        return writer.write(get_message_ext_3());
      case ExtendedTestExtendedIdMessage4::MSG_ID:
        return writer.write(get_message_ext_4());
      case ExtendedTestExtendedIdMessage5::MSG_ID:
        return writer.write(get_message_ext_5());
      case ExtendedTestExtendedIdMessage6::MSG_ID:
        return writer.write(get_message_ext_6());
      case ExtendedTestExtendedIdMessage7::MSG_ID:
        return writer.write(get_message_ext_7());
      case ExtendedTestExtendedIdMessage8::MSG_ID:
        return writer.write(get_message_ext_8());
      case ExtendedTestExtendedIdMessage9::MSG_ID:
        return writer.write(get_message_ext_9());
      case ExtendedTestExtendedIdMessage10::MSG_ID:
        return writer.write(get_message_ext_10());
      case ExtendedTestLargePayloadMessage1::MSG_ID:
        return writer.write(get_message_large_1());
      case ExtendedTestLargePayloadMessage2::MSG_ID:
        return writer.write(get_message_large_2());
      default:
        return 0;
    }
  }
};

// ============================================================================
// Validator helper - validates decoded messages against expected data
// For variable messages, tracks indices since we have multiple instances
// ============================================================================

struct Validator {
  size_t ext_var_single_idx = 0;

  bool get_expected(uint16_t msg_id, const uint8_t*& data, size_t& size) {
    // Handle variable messages with index tracking
    if (msg_id == ExtendedTestExtendedVariableSingleArray::MSG_ID) {
      const auto& msg = get_ext_var_single_messages()[ext_var_single_idx++];
      data = msg.data();
      size = msg.size();
      return true;
    }

    switch (msg_id) {
      case ExtendedTestExtendedIdMessage1::MSG_ID:
        data = get_message_ext_1().data();
        size = get_message_ext_1().size();
        return true;
      case ExtendedTestExtendedIdMessage2::MSG_ID:
        data = get_message_ext_2().data();
        size = get_message_ext_2().size();
        return true;
      case ExtendedTestExtendedIdMessage3::MSG_ID:
        data = get_message_ext_3().data();
        size = get_message_ext_3().size();
        return true;
      case ExtendedTestExtendedIdMessage4::MSG_ID:
        data = get_message_ext_4().data();
        size = get_message_ext_4().size();
        return true;
      case ExtendedTestExtendedIdMessage5::MSG_ID:
        data = get_message_ext_5().data();
        size = get_message_ext_5().size();
        return true;
      case ExtendedTestExtendedIdMessage6::MSG_ID:
        data = get_message_ext_6().data();
        size = get_message_ext_6().size();
        return true;
      case ExtendedTestExtendedIdMessage7::MSG_ID:
        data = get_message_ext_7().data();
        size = get_message_ext_7().size();
        return true;
      case ExtendedTestExtendedIdMessage8::MSG_ID:
        data = get_message_ext_8().data();
        size = get_message_ext_8().size();
        return true;
      case ExtendedTestExtendedIdMessage9::MSG_ID:
        data = get_message_ext_9().data();
        size = get_message_ext_9().size();
        return true;
      case ExtendedTestExtendedIdMessage10::MSG_ID:
        data = get_message_ext_10().data();
        size = get_message_ext_10().size();
        return true;
      case ExtendedTestLargePayloadMessage1::MSG_ID:
        data = get_message_large_1().data();
        size = get_message_large_1().size();
        return true;
      case ExtendedTestLargePayloadMessage2::MSG_ID:
        data = get_message_large_2().data();
        size = get_message_large_2().size();
        return true;
      default:
        return false;
    }
  }

  /** Validate decoded message using operator== (for equality testing) */
  bool validate_with_equals(const FrameParsers::FrameMsgInfo& frame_info) {
    switch (frame_info.msg_id) {
      case ExtendedTestExtendedIdMessage1::MSG_ID: {
        const auto& expected = get_message_ext_1();
        ExtendedTestExtendedIdMessage1 decoded;
        if (decoded.deserialize(frame_info) == 0) return false;
        return decoded == expected;
      }
      case ExtendedTestExtendedIdMessage2::MSG_ID: {
        const auto& expected = get_message_ext_2();
        ExtendedTestExtendedIdMessage2 decoded;
        if (decoded.deserialize(frame_info) == 0) return false;
        return decoded == expected;
      }
      case ExtendedTestExtendedIdMessage3::MSG_ID: {
        const auto& expected = get_message_ext_3();
        ExtendedTestExtendedIdMessage3 decoded;
        if (decoded.deserialize(frame_info) == 0) return false;
        return decoded == expected;
      }
      case ExtendedTestExtendedIdMessage4::MSG_ID: {
        const auto& expected = get_message_ext_4();
        ExtendedTestExtendedIdMessage4 decoded;
        if (decoded.deserialize(frame_info) == 0) return false;
        return decoded == expected;
      }
      case ExtendedTestExtendedIdMessage5::MSG_ID: {
        const auto& expected = get_message_ext_5();
        ExtendedTestExtendedIdMessage5 decoded;
        if (decoded.deserialize(frame_info) == 0) return false;
        return decoded == expected;
      }
      case ExtendedTestExtendedIdMessage6::MSG_ID: {
        const auto& expected = get_message_ext_6();
        ExtendedTestExtendedIdMessage6 decoded;
        if (decoded.deserialize(frame_info) == 0) return false;
        return decoded == expected;
      }
      case ExtendedTestExtendedIdMessage7::MSG_ID: {
        const auto& expected = get_message_ext_7();
        ExtendedTestExtendedIdMessage7 decoded;
        if (decoded.deserialize(frame_info) == 0) return false;
        return decoded == expected;
      }
      case ExtendedTestExtendedIdMessage8::MSG_ID: {
        const auto& expected = get_message_ext_8();
        ExtendedTestExtendedIdMessage8 decoded;
        if (decoded.deserialize(frame_info) == 0) return false;
        return decoded == expected;
      }
      case ExtendedTestExtendedIdMessage9::MSG_ID: {
        const auto& expected = get_message_ext_9();
        ExtendedTestExtendedIdMessage9 decoded;
        if (decoded.deserialize(frame_info) == 0) return false;
        return decoded == expected;
      }
      case ExtendedTestExtendedIdMessage10::MSG_ID: {
        const auto& expected = get_message_ext_10();
        ExtendedTestExtendedIdMessage10 decoded;
        if (decoded.deserialize(frame_info) == 0) return false;
        return decoded == expected;
      }
      case ExtendedTestLargePayloadMessage1::MSG_ID: {
        const auto& expected = get_message_large_1();
        ExtendedTestLargePayloadMessage1 decoded;
        if (decoded.deserialize(frame_info) == 0) return false;
        return decoded == expected;
      }
      case ExtendedTestLargePayloadMessage2::MSG_ID: {
        const auto& expected = get_message_large_2();
        ExtendedTestLargePayloadMessage2 decoded;
        if (decoded.deserialize(frame_info) == 0) return false;
        return decoded == expected;
      }
      case ExtendedTestExtendedVariableSingleArray::MSG_ID: {
        const auto& expected = get_ext_var_single_messages()[ext_var_single_validate_idx++];
        ExtendedTestExtendedVariableSingleArray decoded;
        if (decoded.deserialize(frame_info) == 0) return false;
        return decoded == expected;
      }
      default:
        return false;
    }
  }

  size_t ext_var_single_validate_idx = 0;
};

// ============================================================================
// Test configuration - provides all data for TestCodec templates
// ============================================================================

struct Config {
  static constexpr size_t MESSAGE_COUNT = ExtendedTestMessages::MESSAGE_COUNT;
  static constexpr size_t BUFFER_SIZE = 8192;  // Larger for extended payloads
  static constexpr const char* FORMATS_HELP = "profile_bulk, profile_network";
  static constexpr const char* TEST_NAME = "C++ Extended";

  using Encoder = ExtendedTestMessages::Encoder;
  using Validator = ExtendedTestMessages::Validator;

  static const std::array<uint16_t, MESSAGE_COUNT>& get_msg_id_order() {
    return ExtendedTestMessages::get_msg_id_order();
  }

  static FrameParsers::MessageInfo get_message_info(uint16_t msg_id) { return FrameParsers::get_message_info(msg_id); }

  static bool supports_format(const std::string& format) {
    return format == "profile_bulk" || format == "profile_network";
  }
};

}  // namespace ExtendedTestMessages
