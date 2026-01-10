/**
 * Test codec - Extended message ID and payload tests (C++).
 */

#include "test_codec_extended.hpp"

#include <cstring>
#include <fstream>
#include <iostream>

#include "frame_parsers.hpp"
#include "json.hpp"
#include "extended_test.sf.hpp"

using json = nlohmann::json;
using namespace FrameParsers;

std::vector<ExtendedMixedMessage> load_extended_messages() {
  std::vector<std::string> possible_paths = {"../extended_messages.json", "../../extended_messages.json",
                                             "extended_messages.json", "../../../tests/extended_messages.json"};

  for (const auto& filepath : possible_paths) {
    std::ifstream file(filepath);
    if (file.is_open()) {
      try {
        json data;
        file >> data;

        if (!data.contains("MixedMessages")) {
          continue;
        }

        json mixed_array = data["MixedMessages"];
        std::vector<ExtendedMixedMessage> messages;

        for (const auto& item : mixed_array) {
          std::string msg_type = item["type"];
          std::string msg_name = item["name"];

          ExtendedMixedMessage mixed_msg;

          if (msg_type == "ExtendedIdMessage1") {
            mixed_msg.type = ExtendedMessageType::ExtendedId1;
            auto msg_data_arr = data["ExtendedIdMessage1"];
            for (const auto& msg_data : msg_data_arr) {
              if (msg_data["name"] == msg_name) {
                ExtendedTestExtendedIdMessage1 msg;
                std::memset(&msg, 0, sizeof(msg));
                msg.sequence_number = msg_data["sequence_number"];
                std::string label = msg_data["label"];
                std::strncpy(msg.label, label.c_str(), sizeof(msg.label) - 1);
                msg.value = msg_data["value"];
                msg.enabled = msg_data["enabled"];
                mixed_msg.data.ext_id_1 = msg;
                break;
              }
            }
          } else if (msg_type == "ExtendedIdMessage2") {
            mixed_msg.type = ExtendedMessageType::ExtendedId2;
            auto msg_data_arr = data["ExtendedIdMessage2"];
            for (const auto& msg_data : msg_data_arr) {
              if (msg_data["name"] == msg_name) {
                ExtendedTestExtendedIdMessage2 msg;
                std::memset(&msg, 0, sizeof(msg));
                msg.sensor_id = msg_data["sensor_id"];
                msg.reading = msg_data["reading"];
                msg.status_code = msg_data["status_code"];
                std::string desc = msg_data["description"];
                msg.description.length = desc.length();
                std::strncpy(msg.description.data, desc.c_str(), sizeof(msg.description.data) - 1);
                mixed_msg.data.ext_id_2 = msg;
                break;
              }
            }
          } else if (msg_type == "ExtendedIdMessage3") {
            mixed_msg.type = ExtendedMessageType::ExtendedId3;
            auto msg_data_arr = data["ExtendedIdMessage3"];
            for (const auto& msg_data : msg_data_arr) {
              if (msg_data["name"] == msg_name) {
                ExtendedTestExtendedIdMessage3 msg;
                std::memset(&msg, 0, sizeof(msg));
                if (msg_data["timestamp"].is_string()) {
                  msg.timestamp = std::stoull(msg_data["timestamp"].get<std::string>());
                } else {
                  msg.timestamp = msg_data["timestamp"];
                }
                msg.temperature = msg_data["temperature"];
                msg.humidity = msg_data["humidity"];
                std::string loc = msg_data["location"];
                std::strncpy(msg.location, loc.c_str(), sizeof(msg.location) - 1);
                mixed_msg.data.ext_id_3 = msg;
                break;
              }
            }
          } else if (msg_type == "ExtendedIdMessage4") {
            mixed_msg.type = ExtendedMessageType::ExtendedId4;
            auto msg_data_arr = data["ExtendedIdMessage4"];
            for (const auto& msg_data : msg_data_arr) {
              if (msg_data["name"] == msg_name) {
                ExtendedTestExtendedIdMessage4 msg;
                std::memset(&msg, 0, sizeof(msg));
                msg.event_id = msg_data["event_id"];
                msg.event_type = msg_data["event_type"];
                if (msg_data["event_time"].is_string()) {
                  msg.event_time = std::stoll(msg_data["event_time"].get<std::string>());
                } else {
                  msg.event_time = msg_data["event_time"];
                }
                std::string ev_data = msg_data["event_data"];
                msg.event_data.length = ev_data.length();
                std::strncpy(msg.event_data.data, ev_data.c_str(), sizeof(msg.event_data.data) - 1);
                mixed_msg.data.ext_id_4 = msg;
                break;
              }
            }
          } else if (msg_type == "ExtendedIdMessage5") {
            mixed_msg.type = ExtendedMessageType::ExtendedId5;
            auto msg_data_arr = data["ExtendedIdMessage5"];
            for (const auto& msg_data : msg_data_arr) {
              if (msg_data["name"] == msg_name) {
                ExtendedTestExtendedIdMessage5 msg;
                std::memset(&msg, 0, sizeof(msg));
                msg.x_position = msg_data["x_position"];
                msg.y_position = msg_data["y_position"];
                msg.z_position = msg_data["z_position"];
                msg.frame_number = msg_data["frame_number"];
                mixed_msg.data.ext_id_5 = msg;
                break;
              }
            }
          } else if (msg_type == "ExtendedIdMessage6") {
            mixed_msg.type = ExtendedMessageType::ExtendedId6;
            auto msg_data_arr = data["ExtendedIdMessage6"];
            for (const auto& msg_data : msg_data_arr) {
              if (msg_data["name"] == msg_name) {
                ExtendedTestExtendedIdMessage6 msg;
                std::memset(&msg, 0, sizeof(msg));
                msg.command_id = msg_data["command_id"];
                msg.parameter1 = msg_data["parameter1"];
                msg.parameter2 = msg_data["parameter2"];
                msg.acknowledged = msg_data["acknowledged"];
                std::string cmd_name = msg_data["command_name"];
                std::strncpy(msg.command_name, cmd_name.c_str(), sizeof(msg.command_name) - 1);
                mixed_msg.data.ext_id_6 = msg;
                break;
              }
            }
          } else if (msg_type == "ExtendedIdMessage7") {
            mixed_msg.type = ExtendedMessageType::ExtendedId7;
            auto msg_data_arr = data["ExtendedIdMessage7"];
            for (const auto& msg_data : msg_data_arr) {
              if (msg_data["name"] == msg_name) {
                ExtendedTestExtendedIdMessage7 msg;
                std::memset(&msg, 0, sizeof(msg));
                msg.counter = msg_data["counter"];
                msg.average = msg_data["average"];
                msg.minimum = msg_data["minimum"];
                msg.maximum = msg_data["maximum"];
                mixed_msg.data.ext_id_7 = msg;
                break;
              }
            }
          } else if (msg_type == "ExtendedIdMessage8") {
            mixed_msg.type = ExtendedMessageType::ExtendedId8;
            auto msg_data_arr = data["ExtendedIdMessage8"];
            for (const auto& msg_data : msg_data_arr) {
              if (msg_data["name"] == msg_name) {
                ExtendedTestExtendedIdMessage8 msg;
                std::memset(&msg, 0, sizeof(msg));
                msg.level = msg_data["level"];
                msg.offset = msg_data["offset"];
                msg.duration = msg_data["duration"];
                std::string tag = msg_data["tag"];
                std::strncpy(msg.tag, tag.c_str(), sizeof(msg.tag) - 1);
                mixed_msg.data.ext_id_8 = msg;
                break;
              }
            }
          } else if (msg_type == "ExtendedIdMessage9") {
            mixed_msg.type = ExtendedMessageType::ExtendedId9;
            auto msg_data_arr = data["ExtendedIdMessage9"];
            for (const auto& msg_data : msg_data_arr) {
              if (msg_data["name"] == msg_name) {
                ExtendedTestExtendedIdMessage9 msg;
                std::memset(&msg, 0, sizeof(msg));
                if (msg_data["big_number"].is_string()) {
                  msg.big_number = std::stoll(msg_data["big_number"].get<std::string>());
                } else {
                  msg.big_number = msg_data["big_number"];
                }
                if (msg_data["big_unsigned"].is_string()) {
                  msg.big_unsigned = std::stoull(msg_data["big_unsigned"].get<std::string>());
                } else {
                  msg.big_unsigned = msg_data["big_unsigned"];
                }
                msg.precision_value = msg_data["precision_value"];
                mixed_msg.data.ext_id_9 = msg;
                break;
              }
            }
          } else if (msg_type == "ExtendedIdMessage10") {
            mixed_msg.type = ExtendedMessageType::ExtendedId10;
            auto msg_data_arr = data["ExtendedIdMessage10"];
            for (const auto& msg_data : msg_data_arr) {
              if (msg_data["name"] == msg_name) {
                ExtendedTestExtendedIdMessage10 msg;
                std::memset(&msg, 0, sizeof(msg));
                msg.small_value = msg_data["small_value"];
                std::string txt = msg_data["short_text"];
                std::strncpy(msg.short_text, txt.c_str(), sizeof(msg.short_text) - 1);
                msg.flag = msg_data["flag"];
                mixed_msg.data.ext_id_10 = msg;
                break;
              }
            }
          } else if (msg_type == "LargePayloadMessage1") {
            mixed_msg.type = ExtendedMessageType::LargePayload1;
            auto msg_data_arr = data["LargePayloadMessage1"];
            for (const auto& msg_data : msg_data_arr) {
              if (msg_data["name"] == msg_name) {
                ExtendedTestLargePayloadMessage1 msg;
                std::memset(&msg, 0, sizeof(msg));
                if (msg_data.contains("sensor_readings")) {
                  size_t idx = 0;
                  for (const auto& val : msg_data["sensor_readings"]) {
                    if (idx >= 64) break;
                    msg.sensor_readings[idx++] = val;
                  }
                }
                msg.reading_count = msg_data["reading_count"];
                if (msg_data["timestamp"].is_string()) {
                  msg.timestamp = std::stoll(msg_data["timestamp"].get<std::string>());
                } else {
                  msg.timestamp = msg_data["timestamp"];
                }
                std::string dev_name = msg_data["device_name"];
                std::strncpy(msg.device_name, dev_name.c_str(), sizeof(msg.device_name) - 1);
                mixed_msg.data.large_payload_1 = msg;
                break;
              }
            }
          } else if (msg_type == "LargePayloadMessage2") {
            mixed_msg.type = ExtendedMessageType::LargePayload2;
            auto msg_data_arr = data["LargePayloadMessage2"];
            for (const auto& msg_data : msg_data_arr) {
              if (msg_data["name"] == msg_name) {
                ExtendedTestLargePayloadMessage2 msg;
                std::memset(&msg, 0, sizeof(msg));
                if (msg_data.contains("large_data")) {
                  size_t idx = 0;
                  for (const auto& val : msg_data["large_data"]) {
                    if (idx >= 280) break;
                    msg.large_data[idx++] = val;
                  }
                }
                mixed_msg.data.large_payload_2 = msg;
                break;
              }
            }
          }

          messages.push_back(mixed_msg);
        }

        return messages;
      } catch (const std::exception& e) {
        continue;
      }
    }
  }

  std::cerr << "Error: Could not load extended messages from extended_messages.json\n";
  return std::vector<ExtendedMixedMessage>();
}

/* Helper function to validate a decoded extended message */
bool validate_extended_message(const FrameMsgInfo& decode_result, const std::vector<ExtendedMixedMessage>& messages,
                               size_t message_index) {
  if (!decode_result.valid) {
    std::cout << "  Decoding failed for message " << message_index << "\n";
    return false;
  }

  if (message_index >= messages.size()) {
    std::cout << "  Too many messages decoded: " << message_index << "\n";
    return false;
  }

  const auto& mixed_msg = messages[message_index];
  uint16_t expected_msg_id;

  switch (mixed_msg.type) {
    case ExtendedMessageType::ExtendedId1:
      expected_msg_id = ExtendedTestExtendedIdMessage1::MSG_ID;
      break;
    case ExtendedMessageType::ExtendedId2:
      expected_msg_id = ExtendedTestExtendedIdMessage2::MSG_ID;
      break;
    case ExtendedMessageType::ExtendedId3:
      expected_msg_id = ExtendedTestExtendedIdMessage3::MSG_ID;
      break;
    case ExtendedMessageType::ExtendedId4:
      expected_msg_id = ExtendedTestExtendedIdMessage4::MSG_ID;
      break;
    case ExtendedMessageType::ExtendedId5:
      expected_msg_id = ExtendedTestExtendedIdMessage5::MSG_ID;
      break;
    case ExtendedMessageType::ExtendedId6:
      expected_msg_id = ExtendedTestExtendedIdMessage6::MSG_ID;
      break;
    case ExtendedMessageType::ExtendedId7:
      expected_msg_id = ExtendedTestExtendedIdMessage7::MSG_ID;
      break;
    case ExtendedMessageType::ExtendedId8:
      expected_msg_id = ExtendedTestExtendedIdMessage8::MSG_ID;
      break;
    case ExtendedMessageType::ExtendedId9:
      expected_msg_id = ExtendedTestExtendedIdMessage9::MSG_ID;
      break;
    case ExtendedMessageType::ExtendedId10:
      expected_msg_id = ExtendedTestExtendedIdMessage10::MSG_ID;
      break;
    case ExtendedMessageType::LargePayload1:
      expected_msg_id = ExtendedTestLargePayloadMessage1::MSG_ID;
      break;
    case ExtendedMessageType::LargePayload2:
      expected_msg_id = ExtendedTestLargePayloadMessage2::MSG_ID;
      break;
    default:
      std::cout << "  Unknown message type for message " << message_index << "\n";
      return false;
  }

  if (decode_result.msg_id != expected_msg_id) {
    std::cout << "  Message ID mismatch for message " << message_index << ": expected " << (int)expected_msg_id
              << ", got " << (int)decode_result.msg_id << "\n";
    return false;
  }

  // Validate message content by comparing decoded payload bytes against original message
  const uint8_t* expected_data = nullptr;
  size_t expected_size = 0;

  switch (mixed_msg.type) {
    case ExtendedMessageType::ExtendedId1:
      expected_data = mixed_msg.data.ext_id_1.data();
      expected_size = ExtendedTestExtendedIdMessage1::MAX_SIZE;
      break;
    case ExtendedMessageType::ExtendedId2:
      expected_data = mixed_msg.data.ext_id_2.data();
      expected_size = ExtendedTestExtendedIdMessage2::MAX_SIZE;
      break;
    case ExtendedMessageType::ExtendedId3:
      expected_data = mixed_msg.data.ext_id_3.data();
      expected_size = ExtendedTestExtendedIdMessage3::MAX_SIZE;
      break;
    case ExtendedMessageType::ExtendedId4:
      expected_data = mixed_msg.data.ext_id_4.data();
      expected_size = ExtendedTestExtendedIdMessage4::MAX_SIZE;
      break;
    case ExtendedMessageType::ExtendedId5:
      expected_data = mixed_msg.data.ext_id_5.data();
      expected_size = ExtendedTestExtendedIdMessage5::MAX_SIZE;
      break;
    case ExtendedMessageType::ExtendedId6:
      expected_data = mixed_msg.data.ext_id_6.data();
      expected_size = ExtendedTestExtendedIdMessage6::MAX_SIZE;
      break;
    case ExtendedMessageType::ExtendedId7:
      expected_data = mixed_msg.data.ext_id_7.data();
      expected_size = ExtendedTestExtendedIdMessage7::MAX_SIZE;
      break;
    case ExtendedMessageType::ExtendedId8:
      expected_data = mixed_msg.data.ext_id_8.data();
      expected_size = ExtendedTestExtendedIdMessage8::MAX_SIZE;
      break;
    case ExtendedMessageType::ExtendedId9:
      expected_data = mixed_msg.data.ext_id_9.data();
      expected_size = ExtendedTestExtendedIdMessage9::MAX_SIZE;
      break;
    case ExtendedMessageType::ExtendedId10:
      expected_data = mixed_msg.data.ext_id_10.data();
      expected_size = ExtendedTestExtendedIdMessage10::MAX_SIZE;
      break;
    case ExtendedMessageType::LargePayload1:
      expected_data = mixed_msg.data.large_payload_1.data();
      expected_size = ExtendedTestLargePayloadMessage1::MAX_SIZE;
      break;
    case ExtendedMessageType::LargePayload2:
      expected_data = mixed_msg.data.large_payload_2.data();
      expected_size = ExtendedTestLargePayloadMessage2::MAX_SIZE;
      break;
    default:
      return false;
  }

  if (expected_data && decode_result.msg_data) {
    if (decode_result.msg_len != expected_size) {
      std::cout << "  Message " << message_index << " size mismatch: expected " << expected_size << ", got "
                << decode_result.msg_len << "\n";
      return false;
    }

    if (std::memcmp(decode_result.msg_data, expected_data, expected_size) != 0) {
      std::cout << "  Message " << message_index << " content mismatch\n";
      return false;
    }
  }

  return true;
}

bool encode_extended_messages(const std::string& format, uint8_t* buffer, size_t buffer_size, size_t& encoded_size) {
  auto messages = load_extended_messages();
  if (messages.empty()) {
    std::cout << "  Failed to load extended test messages\n";
    return false;
  }

  encoded_size = 0;

  /* Lambda to encode messages using the appropriate profile's BufferWriter */
  auto encode_all = [&](auto& writer) -> bool {
    for (const auto& mixed_msg : messages) {
      size_t written = 0;
      switch (mixed_msg.type) {
        case ExtendedMessageType::ExtendedId1:
          written = writer.write(mixed_msg.data.ext_id_1);
          break;
        case ExtendedMessageType::ExtendedId2:
          written = writer.write(mixed_msg.data.ext_id_2);
          break;
        case ExtendedMessageType::ExtendedId3:
          written = writer.write(mixed_msg.data.ext_id_3);
          break;
        case ExtendedMessageType::ExtendedId4:
          written = writer.write(mixed_msg.data.ext_id_4);
          break;
        case ExtendedMessageType::ExtendedId5:
          written = writer.write(mixed_msg.data.ext_id_5);
          break;
        case ExtendedMessageType::ExtendedId6:
          written = writer.write(mixed_msg.data.ext_id_6);
          break;
        case ExtendedMessageType::ExtendedId7:
          written = writer.write(mixed_msg.data.ext_id_7);
          break;
        case ExtendedMessageType::ExtendedId8:
          written = writer.write(mixed_msg.data.ext_id_8);
          break;
        case ExtendedMessageType::ExtendedId9:
          written = writer.write(mixed_msg.data.ext_id_9);
          break;
        case ExtendedMessageType::ExtendedId10:
          written = writer.write(mixed_msg.data.ext_id_10);
          break;
        case ExtendedMessageType::LargePayload1:
          written = writer.write(mixed_msg.data.large_payload_1);
          break;
        case ExtendedMessageType::LargePayload2:
          written = writer.write(mixed_msg.data.large_payload_2);
          break;
        default:
          std::cout << "  Unknown message type\n";
          return false;
      }
      if (written == 0) {
        std::cout << "  Encoding failed for message\n";
        return false;
      }
    }
    encoded_size = writer.size();
    return true;
  };

  // Only extended profiles support msg_id > 255
  if (format == "profile_bulk") {
    ProfileBulkWriter writer(buffer, buffer_size);
    return encode_all(writer);
  } else if (format == "profile_network") {
    ProfileNetworkWriter writer(buffer, buffer_size);
    return encode_all(writer);
  }

  std::cout << "  Frame format not supported for extended messages: " << format << "\n";
  std::cout << "  Only profile_bulk and profile_network support extended message IDs\n";
  return false;
}

bool decode_extended_messages(const std::string& format, const uint8_t* buffer, size_t buffer_size,
                              size_t& message_count) {
  auto messages = load_extended_messages();
  if (messages.empty()) {
    std::cout << "  Failed to load extended test messages\n";
    message_count = 0;
    return false;
  }

  message_count = 0;

  /* Split buffer into 3 chunks to simulate partial message scenarios */
  size_t chunk1_size = buffer_size / 3;
  size_t chunk2_size = buffer_size / 3;
  size_t chunk3_size = buffer_size - chunk1_size - chunk2_size;

  const uint8_t* chunk1 = buffer;
  const uint8_t* chunk2 = buffer + chunk1_size;
  const uint8_t* chunk3 = buffer + chunk1_size + chunk2_size;

  /* Lambda to decode and validate messages using AccumulatingReader */
  auto decode_all = [&](auto& reader) -> bool {
    // Add first chunk
    reader.add_data(chunk1, chunk1_size);
    while (auto decode_result = reader.next()) {
      if (!validate_extended_message(decode_result, messages, message_count)) {
        return false;
      }
      message_count++;
    }

    // Add second chunk
    reader.add_data(chunk2, chunk2_size);
    while (auto decode_result = reader.next()) {
      if (!validate_extended_message(decode_result, messages, message_count)) {
        return false;
      }
      message_count++;
    }

    // Add third chunk
    reader.add_data(chunk3, chunk3_size);
    while (auto decode_result = reader.next()) {
      if (!validate_extended_message(decode_result, messages, message_count)) {
        return false;
      }
      message_count++;
    }

    if (message_count != messages.size()) {
      std::cout << "  Expected " << messages.size() << " messages, but decoded " << message_count << "\n";
      return false;
    }

    if (reader.has_partial()) {
      std::cout << "  Incomplete partial message remaining: " << reader.partial_size() << " bytes\n";
      return false;
    }

    return true;
  };

  // Only extended profiles support msg_id > 255
  if (format == "profile_bulk") {
    AccumulatingReader<ProfileBulkConfig> reader;
    return decode_all(reader);
  } else if (format == "profile_network") {
    AccumulatingReader<ProfileNetworkConfig> reader;
    return decode_all(reader);
  }

  std::cout << "  Frame format not supported for extended messages: " << format << "\n";
  return false;
}
