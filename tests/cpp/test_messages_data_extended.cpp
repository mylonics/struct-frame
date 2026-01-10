/**
 * Extended test message data definitions.
 * Hardcoded test messages for extended message ID and payload testing.
 */

#include "test_messages_data_extended.hpp"
#include <array>
#include <cstring>

namespace ExtendedTestMessages {

// Helper functions to create messages
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
  msg.description.length = std::strlen("Extended ID test message 2");
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
  msg.event_data.length = std::strlen("Event payload with extended message ID");
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

// Static array of all extended test messages
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

size_t get_extended_test_message_count() {
  return extended_test_messages.size();
}

const MixedMessage& get_extended_test_message(size_t index) {
  return extended_test_messages[index];
}

const std::array<MixedMessage, 12>& get_messages_array() {
  return extended_test_messages;
}

} // namespace ExtendedTestMessages
