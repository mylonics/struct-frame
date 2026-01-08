/**
 * Test codec - Encode/decode functions for all frame formats (C++).
 */

#include "test_codec.hpp"

#include <cstring>
#include <fstream>
#include <iostream>

#include "frame_parsers.hpp"
#include "json.hpp"
#include "serialization_test.sf.hpp"

using json = nlohmann::json;
using namespace FrameParsers;

std::vector<MixedMessage> load_mixed_messages() {
  std::vector<std::string> possible_paths = {"../test_messages.json", "../../test_messages.json", "test_messages.json",
                                             "../../../tests/test_messages.json"};

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
        json serial_msgs = data["SerializationTestMessage"];
        json basic_msgs = data["BasicTypesMessage"];
        json union_msgs = data.contains("UnionTestMessage") ? data["UnionTestMessage"] : json::array();

        std::vector<MixedMessage> messages;

        for (const auto& item : mixed_array) {
          std::string msg_type = item["type"];
          std::string msg_name = item["name"];

          MixedMessage mixed_msg;

          if (msg_type == "SerializationTestMessage") {
            mixed_msg.type = MessageType::SerializationTest;

            // Find message by name
            for (const auto& msg_data : serial_msgs) {
              if (msg_data["name"] == msg_name) {
                SerializationTestSerializationTestMessage msg;
                std::memset(&msg, 0, sizeof(msg));

                msg.magic_number = msg_data["magic_number"];
                std::string str = msg_data["test_string"];
                msg.test_string.length = str.length();
                std::strncpy(msg.test_string.data, str.c_str(), sizeof(msg.test_string.data) - 1);
                msg.test_float = msg_data["test_float"];
                msg.test_bool = msg_data["test_bool"];

                if (msg_data.contains("test_array") && msg_data["test_array"].is_array()) {
                  size_t idx = 0;
                  for (const auto& val : msg_data["test_array"]) {
                    if (idx >= 5) break;
                    msg.test_array.data[idx++] = val;
                  }
                  msg.test_array.count = idx;
                }

                mixed_msg.data.serial_test = msg;
                break;
              }
            }
          } else if (msg_type == "BasicTypesMessage") {
            mixed_msg.type = MessageType::BasicTypes;

            // Find message by name
            for (const auto& msg_data : basic_msgs) {
              if (msg_data["name"] == msg_name) {
                SerializationTestBasicTypesMessage msg;
                std::memset(&msg, 0, sizeof(msg));

                msg.small_int = msg_data["small_int"];
                msg.medium_int = msg_data["medium_int"];
                msg.regular_int = msg_data["regular_int"];
                // large_int is stored as string in JSON to preserve precision
                if (msg_data["large_int"].is_string()) {
                  msg.large_int = std::stoll(msg_data["large_int"].get<std::string>());
                } else {
                  msg.large_int = msg_data["large_int"];
                }
                msg.small_uint = msg_data["small_uint"];
                msg.medium_uint = msg_data["medium_uint"];
                msg.regular_uint = msg_data["regular_uint"];
                // large_uint is stored as string in JSON to preserve precision
                if (msg_data["large_uint"].is_string()) {
                  msg.large_uint = std::stoull(msg_data["large_uint"].get<std::string>());
                } else {
                  msg.large_uint = msg_data["large_uint"];
                }
                msg.single_precision = msg_data["single_precision"];
                msg.double_precision = msg_data["double_precision"];
                msg.flag = msg_data["flag"];
                std::string device_id = msg_data["device_id"];
                std::strncpy(msg.device_id, device_id.c_str(), sizeof(msg.device_id) - 1);

                std::string description = msg_data["description"];
                msg.description.length = description.length();
                std::strncpy(msg.description.data, description.c_str(), sizeof(msg.description.data) - 1);

                mixed_msg.data.basic_types = msg;
                break;
              }
            }
          } else if (msg_type == "UnionTestMessage") {
            mixed_msg.type = MessageType::UnionTest;

            // Find message by name
            for (const auto& msg_data : union_msgs) {
              if (msg_data["name"] == msg_name) {
                SerializationTestUnionTestMessage msg;
                std::memset(&msg, 0, sizeof(msg));

                // Set the discriminator from the message ID of whichever message is being used
                // Note: payload_type in JSON is legacy - we now use auto-discriminator
                if (msg_data.contains("array_payload") && !msg_data["array_payload"].is_null()) {
                  msg.payload_discriminator = SerializationTestComprehensiveArrayMessage::MSG_ID;
                  const auto& ap = msg_data["array_payload"];

                  // fixed_ints
                  if (ap.contains("fixed_ints")) {
                    size_t idx = 0;
                    for (const auto& val : ap["fixed_ints"]) {
                      if (idx >= 3) break;
                      msg.payload.array_payload.fixed_ints[idx++] = val;
                    }
                  }
                  // fixed_floats
                  if (ap.contains("fixed_floats")) {
                    size_t idx = 0;
                    for (const auto& val : ap["fixed_floats"]) {
                      if (idx >= 2) break;
                      msg.payload.array_payload.fixed_floats[idx++] = val;
                    }
                  }
                  // fixed_bools
                  if (ap.contains("fixed_bools")) {
                    size_t idx = 0;
                    for (const auto& val : ap["fixed_bools"]) {
                      if (idx >= 4) break;
                      msg.payload.array_payload.fixed_bools[idx++] = val;
                    }
                  }
                  // bounded_uints
                  if (ap.contains("bounded_uints")) {
                    size_t idx = 0;
                    for (const auto& val : ap["bounded_uints"]) {
                      if (idx >= 3) break;
                      msg.payload.array_payload.bounded_uints.data[idx++] = val;
                    }
                    msg.payload.array_payload.bounded_uints.count = idx;
                  }
                  // bounded_doubles
                  if (ap.contains("bounded_doubles")) {
                    size_t idx = 0;
                    for (const auto& val : ap["bounded_doubles"]) {
                      if (idx >= 2) break;
                      msg.payload.array_payload.bounded_doubles.data[idx++] = val;
                    }
                    msg.payload.array_payload.bounded_doubles.count = idx;
                  }
                  // fixed_strings
                  if (ap.contains("fixed_strings")) {
                    size_t idx = 0;
                    for (const auto& val : ap["fixed_strings"]) {
                      if (idx >= 2) break;
                      std::string s = val;
                      std::strncpy(msg.payload.array_payload.fixed_strings[idx], s.c_str(), 7);
                      idx++;
                    }
                  }
                  // bounded_strings
                  if (ap.contains("bounded_strings")) {
                    size_t idx = 0;
                    for (const auto& val : ap["bounded_strings"]) {
                      if (idx >= 2) break;
                      std::string s = val;
                      std::strncpy(msg.payload.array_payload.bounded_strings.data[idx], s.c_str(), 11);
                      idx++;
                    }
                    msg.payload.array_payload.bounded_strings.count = idx;
                  }
                  // fixed_statuses
                  if (ap.contains("fixed_statuses")) {
                    size_t idx = 0;
                    for (const auto& val : ap["fixed_statuses"]) {
                      if (idx >= 2) break;
                      msg.payload.array_payload.fixed_statuses[idx++] =
                          static_cast<SerializationTestStatus>(val.get<int>());
                    }
                  }
                  // bounded_statuses
                  if (ap.contains("bounded_statuses")) {
                    size_t idx = 0;
                    for (const auto& val : ap["bounded_statuses"]) {
                      if (idx >= 2) break;
                      msg.payload.array_payload.bounded_statuses.data[idx++] =
                          static_cast<SerializationTestStatus>(val.get<int>());
                    }
                    msg.payload.array_payload.bounded_statuses.count = idx;
                  }
                  // fixed_sensors
                  if (ap.contains("fixed_sensors")) {
                    size_t idx = 0;
                    for (const auto& sensor : ap["fixed_sensors"]) {
                      if (idx >= 1) break;
                      msg.payload.array_payload.fixed_sensors[idx].id = sensor["id"];
                      msg.payload.array_payload.fixed_sensors[idx].value = sensor["value"];
                      msg.payload.array_payload.fixed_sensors[idx].status =
                          static_cast<SerializationTestStatus>(sensor["status"].get<int>());
                      std::string name = sensor["name"];
                      std::strncpy(msg.payload.array_payload.fixed_sensors[idx].name, name.c_str(), 15);
                      idx++;
                    }
                  }
                  // bounded_sensors
                  if (ap.contains("bounded_sensors")) {
                    size_t idx = 0;
                    for (const auto& sensor : ap["bounded_sensors"]) {
                      if (idx >= 1) break;
                      msg.payload.array_payload.bounded_sensors.data[idx].id = sensor["id"];
                      msg.payload.array_payload.bounded_sensors.data[idx].value = sensor["value"];
                      msg.payload.array_payload.bounded_sensors.data[idx].status =
                          static_cast<SerializationTestStatus>(sensor["status"].get<int>());
                      std::string name = sensor["name"];
                      std::strncpy(msg.payload.array_payload.bounded_sensors.data[idx].name, name.c_str(), 15);
                      idx++;
                    }
                    msg.payload.array_payload.bounded_sensors.count = idx;
                  }
                }

                // Load test_payload if present
                if (msg_data.contains("test_payload") && !msg_data["test_payload"].is_null()) {
                  msg.payload_discriminator = SerializationTestSerializationTestMessage::MSG_ID;
                  const auto& tp = msg_data["test_payload"];
                  msg.payload.test_payload.magic_number = tp["magic_number"];
                  std::string str = tp["test_string"];
                  msg.payload.test_payload.test_string.length = str.length();
                  std::strncpy(msg.payload.test_payload.test_string.data, str.c_str(),
                               sizeof(msg.payload.test_payload.test_string.data) - 1);
                  msg.payload.test_payload.test_float = tp["test_float"];
                  msg.payload.test_payload.test_bool = tp["test_bool"];
                  if (tp.contains("test_array") && tp["test_array"].is_array()) {
                    size_t idx = 0;
                    for (const auto& val : tp["test_array"]) {
                      if (idx >= 5) break;
                      msg.payload.test_payload.test_array.data[idx++] = val;
                    }
                    msg.payload.test_payload.test_array.count = idx;
                  }
                }

                mixed_msg.data.union_test = msg;
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

  std::cerr << "Error: Could not load mixed messages from test_messages.json\n";
  return std::vector<MixedMessage>();
}

bool encode_test_messages(const std::string& format, uint8_t* buffer, size_t buffer_size, size_t& encoded_size) {
  auto mixed_messages = load_mixed_messages();
  if (mixed_messages.empty()) {
    std::cout << "  Failed to load mixed test messages\n";
    return false;
  }

  encoded_size = 0;
  size_t offset = 0;

  for (const auto& mixed_msg : mixed_messages) {
    size_t msg_encoded_size = 0;

    /* Lambda to encode any message type with the appropriate profile */
    auto encode_msg = [&](const auto& msg) -> size_t {
      if (format == "profile_standard") {
        return encode_profile_standard(buffer + offset, buffer_size - offset, msg);
      } else if (format == "profile_sensor") {
        return encode_profile_sensor(buffer + offset, buffer_size - offset, msg);
      } else if (format == "profile_ipc") {
        return encode_profile_ipc(buffer + offset, buffer_size - offset, msg);
      } else if (format == "profile_bulk") {
        return encode_profile_bulk(buffer + offset, buffer_size - offset, msg);
      } else if (format == "profile_network") {
        return encode_profile_network(buffer + offset, buffer_size - offset, 0, 0, 0, msg);
      }
      return 0;
    };

    if (mixed_msg.type == MessageType::SerializationTest) {
      msg_encoded_size = encode_msg(mixed_msg.data.serial_test);
    } else if (mixed_msg.type == MessageType::BasicTypes) {
      msg_encoded_size = encode_msg(mixed_msg.data.basic_types);
    } else if (mixed_msg.type == MessageType::UnionTest) {
      msg_encoded_size = encode_msg(mixed_msg.data.union_test);
    } else {
      std::cout << "  Unknown message type\n";
      return false;
    }

    if (msg_encoded_size == 0) {
      std::cout << "  Encoding failed for message\n";
      return false;
    }

    offset += msg_encoded_size;
    encoded_size = offset;
  }

  return encoded_size > 0;
}

bool decode_test_messages(const std::string& format, const uint8_t* buffer, size_t buffer_size, size_t& message_count) {
  auto mixed_messages = load_mixed_messages();
  if (mixed_messages.empty()) {
    std::cout << "  Failed to load mixed test messages\n";
    message_count = 0;
    return false;
  }

  size_t offset = 0;
  message_count = 0;

  while (offset < buffer_size && message_count < mixed_messages.size()) {
    FrameMsgInfo decode_result;

    if (format == "profile_standard") {
      decode_result = parse_profile_standard_buffer(buffer + offset, buffer_size - offset);
    } else if (format == "profile_sensor") {
      decode_result = parse_profile_sensor_buffer(buffer + offset, buffer_size - offset, get_message_length);
    } else if (format == "profile_ipc") {
      decode_result = parse_profile_ipc_buffer(buffer + offset, buffer_size - offset, get_message_length);
    } else if (format == "profile_bulk") {
      decode_result = parse_profile_bulk_buffer(buffer + offset, buffer_size - offset);
    } else if (format == "profile_network") {
      decode_result = parse_profile_network_buffer(buffer + offset, buffer_size - offset);
    } else {
      std::cout << "  Unknown frame format: " << format << "\n";
      return false;
    }

    if (!decode_result.valid) {
      std::cout << "  Decoding failed for message " << message_count << "\n";
      return false;
    }

    // Validate msg_id matches expected type using MessageBase MSG_ID constants
    const auto& mixed_msg = mixed_messages[message_count];
    uint16_t expected_msg_id;

    if (mixed_msg.type == MessageType::SerializationTest) {
      expected_msg_id = SerializationTestSerializationTestMessage::MSG_ID;
    } else if (mixed_msg.type == MessageType::BasicTypes) {
      expected_msg_id = SerializationTestBasicTypesMessage::MSG_ID;
    } else if (mixed_msg.type == MessageType::UnionTest) {
      expected_msg_id = SerializationTestUnionTestMessage::MSG_ID;
    } else {
      std::cout << "  Unknown message type for message " << message_count << "\n";
      return false;
    }

    if (decode_result.msg_id != expected_msg_id) {
      std::cout << "  Message ID mismatch for message " << message_count << ": expected " << (int)expected_msg_id
                << ", got " << (int)decode_result.msg_id << "\n";
      return false;
    }

    // Validate message content by comparing decoded payload bytes against original message
    const uint8_t* expected_data = nullptr;
    size_t expected_size = 0;

    if (mixed_msg.type == MessageType::SerializationTest) {
      expected_data = mixed_msg.data.serial_test.data();
      expected_size = SerializationTestSerializationTestMessage::MAX_SIZE;
    } else if (mixed_msg.type == MessageType::BasicTypes) {
      expected_data = mixed_msg.data.basic_types.data();
      expected_size = SerializationTestBasicTypesMessage::MAX_SIZE;
    } else if (mixed_msg.type == MessageType::UnionTest) {
      expected_data = mixed_msg.data.union_test.data();
      expected_size = SerializationTestUnionTestMessage::MAX_SIZE;
    }

    if (expected_data && decode_result.msg_data) {
      if (decode_result.msg_len != expected_size) {
        std::cout << "  Message " << message_count << " size mismatch: expected " << expected_size << ", got "
                  << decode_result.msg_len << "\n";
        return false;
      }

      if (std::memcmp(decode_result.msg_data, expected_data, expected_size) != 0) {
        std::cout << "  Message " << message_count << " content mismatch (decoded " << message_count << " messages successfully)\n";
        return false;
      }
    }

    // Calculate the size of this encoded message
    size_t msg_size = 0;
    if (format == "profile_standard") {
      msg_size = 4 + decode_result.msg_len + 2;  // header + payload + crc
    } else if (format == "profile_sensor") {
      msg_size = 2 + decode_result.msg_len;  // header + payload
    } else if (format == "profile_ipc") {
      msg_size = 1 + decode_result.msg_len;  // header + payload
    } else if (format == "profile_bulk") {
      msg_size = 6 + decode_result.msg_len + 2;  // header + payload + crc
    } else if (format == "profile_network") {
      msg_size = 9 + decode_result.msg_len + 2;  // header + payload + crc
    }

    offset += msg_size;
    message_count++;
  }

  if (message_count != mixed_messages.size()) {
    std::cout << "  Expected " << mixed_messages.size() << " messages, but decoded " << message_count << "\n";
    return false;
  }

  if (offset != buffer_size) {
    std::cout << "  Extra data after messages: expected " << offset << " bytes, got " << buffer_size << " bytes\n";
    return false;
  }

  return true;
}
