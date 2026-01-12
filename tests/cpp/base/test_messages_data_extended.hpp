/**
 * Extended test message data definitions (header-only).
 * Hardcoded test messages for extended message ID and payload testing.
 * Uses std::array for efficient compile-time initialization.
 */

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>

#include "extended_test.sf.hpp"

namespace ExtendedTestMessages {

enum class MessageType {
  EXT_ID_1,
  EXT_ID_2,
  EXT_ID_3,
  EXT_ID_4,
  EXT_ID_5,
  EXT_ID_6,
  EXT_ID_7,
  EXT_ID_8,
  EXT_ID_9,
  EXT_ID_10,
  LARGE_1,
  LARGE_2
};

struct MixedMessage {
  MessageType type;
  union {
    ExtendedTestExtendedIdMessage1 ext_id_1;
    ExtendedTestExtendedIdMessage2 ext_id_2;
    ExtendedTestExtendedIdMessage3 ext_id_3;
    ExtendedTestExtendedIdMessage4 ext_id_4;
    ExtendedTestExtendedIdMessage5 ext_id_5;
    ExtendedTestExtendedIdMessage6 ext_id_6;
    ExtendedTestExtendedIdMessage7 ext_id_7;
    ExtendedTestExtendedIdMessage8 ext_id_8;
    ExtendedTestExtendedIdMessage9 ext_id_9;
    ExtendedTestExtendedIdMessage10 ext_id_10;
    ExtendedTestLargePayloadMessage1 large_1;
    ExtendedTestLargePayloadMessage2 large_2;
  } data;
};

// Helper functions to create messages
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

/* Returns the static array of extended test messages using Meyers' singleton pattern */
inline const std::array<MixedMessage, 12>& get_messages_array() {
  static const std::array<MixedMessage, 12> extended_test_messages = []() {
    std::array<MixedMessage, 12> messages{};

    messages[0] = MixedMessage{MessageType::EXT_ID_1, {.ext_id_1 = create_ext_id_1()}};
    messages[1] = MixedMessage{MessageType::EXT_ID_2, {.ext_id_2 = create_ext_id_2()}};
    messages[2] = MixedMessage{MessageType::EXT_ID_3, {.ext_id_3 = create_ext_id_3()}};
    messages[3] = MixedMessage{MessageType::EXT_ID_4, {.ext_id_4 = create_ext_id_4()}};
    messages[4] = MixedMessage{MessageType::EXT_ID_5, {.ext_id_5 = create_ext_id_5()}};
    messages[5] = MixedMessage{MessageType::EXT_ID_6, {.ext_id_6 = create_ext_id_6()}};
    messages[6] = MixedMessage{MessageType::EXT_ID_7, {.ext_id_7 = create_ext_id_7()}};
    messages[7] = MixedMessage{MessageType::EXT_ID_8, {.ext_id_8 = create_ext_id_8()}};
    messages[8] = MixedMessage{MessageType::EXT_ID_9, {.ext_id_9 = create_ext_id_9()}};
    messages[9] = MixedMessage{MessageType::EXT_ID_10, {.ext_id_10 = create_ext_id_10()}};
    messages[10] = MixedMessage{MessageType::LARGE_1, {.large_1 = create_large_1()}};
    messages[11] = MixedMessage{MessageType::LARGE_2, {.large_2 = create_large_2()}};

    return messages;
  }();
  return extended_test_messages;
}

/**
 * Get the total number of extended test messages.
 */
inline size_t get_extended_test_message_count() { return get_messages_array().size(); }

/**
 * Get a specific extended test message by index (for validation).
 */
inline const MixedMessage& get_extended_test_message(size_t index) { return get_messages_array()[index]; }

/**
 * Write all extended test messages using the provided writer.
 * Template function that works with any BufferWriter type.
 */
template <typename WriterType>
bool write_extended_test_messages(WriterType& writer, size_t& encoded_size) {
  const auto& messages = get_messages_array();

  for (const auto& msg : messages) {
    size_t written = 0;

    switch (msg.type) {
      case MessageType::EXT_ID_1:
        written = writer.write(msg.data.ext_id_1);
        break;
      case MessageType::EXT_ID_2:
        written = writer.write(msg.data.ext_id_2);
        break;
      case MessageType::EXT_ID_3:
        written = writer.write(msg.data.ext_id_3);
        break;
      case MessageType::EXT_ID_4:
        written = writer.write(msg.data.ext_id_4);
        break;
      case MessageType::EXT_ID_5:
        written = writer.write(msg.data.ext_id_5);
        break;
      case MessageType::EXT_ID_6:
        written = writer.write(msg.data.ext_id_6);
        break;
      case MessageType::EXT_ID_7:
        written = writer.write(msg.data.ext_id_7);
        break;
      case MessageType::EXT_ID_8:
        written = writer.write(msg.data.ext_id_8);
        break;
      case MessageType::EXT_ID_9:
        written = writer.write(msg.data.ext_id_9);
        break;
      case MessageType::EXT_ID_10:
        written = writer.write(msg.data.ext_id_10);
        break;
      case MessageType::LARGE_1:
        written = writer.write(msg.data.large_1);
        break;
      case MessageType::LARGE_2:
        written = writer.write(msg.data.large_2);
        break;
      default:
        std::cerr << "  Unknown extended message type\n";
        return false;
    }

    if (written == 0) {
      std::cerr << "  Encoding failed for extended message\n";
      return false;
    }
  }

  encoded_size = writer.size();
  return true;
}

}  // namespace ExtendedTestMessages
