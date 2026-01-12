/**
 * Test codec (header-only) - Extended message ID and payload tests (C++).
 * Refactored to use hardcoded message data with full decode validation.
 */

#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>

#include "frame_parsers.hpp"
#include "test_messages_data_extended.hpp"

namespace TestCodecExtended {

using namespace FrameParsers;
using namespace ExtendedTestMessages;

/* Helper function to get expected message ID from message type */
inline uint16_t get_expected_msg_id(MessageType type) {
  switch (type) {
    case MessageType::EXT_ID_1:
      return ExtendedTestExtendedIdMessage1::MSG_ID;
    case MessageType::EXT_ID_2:
      return ExtendedTestExtendedIdMessage2::MSG_ID;
    case MessageType::EXT_ID_3:
      return ExtendedTestExtendedIdMessage3::MSG_ID;
    case MessageType::EXT_ID_4:
      return ExtendedTestExtendedIdMessage4::MSG_ID;
    case MessageType::EXT_ID_5:
      return ExtendedTestExtendedIdMessage5::MSG_ID;
    case MessageType::EXT_ID_6:
      return ExtendedTestExtendedIdMessage6::MSG_ID;
    case MessageType::EXT_ID_7:
      return ExtendedTestExtendedIdMessage7::MSG_ID;
    case MessageType::EXT_ID_8:
      return ExtendedTestExtendedIdMessage8::MSG_ID;
    case MessageType::EXT_ID_9:
      return ExtendedTestExtendedIdMessage9::MSG_ID;
    case MessageType::EXT_ID_10:
      return ExtendedTestExtendedIdMessage10::MSG_ID;
    case MessageType::LARGE_1:
      return ExtendedTestLargePayloadMessage1::MSG_ID;
    case MessageType::LARGE_2:
      return ExtendedTestLargePayloadMessage2::MSG_ID;
    default:
      return 0;
  }
}

/* Helper function to get expected message data and size */
inline bool get_expected_data(const MixedMessage& msg, const uint8_t*& data, size_t& size) {
  switch (msg.type) {
    case MessageType::EXT_ID_1:
      data = msg.data.ext_id_1.data();
      size = ExtendedTestExtendedIdMessage1::MAX_SIZE;
      return true;
    case MessageType::EXT_ID_2:
      data = msg.data.ext_id_2.data();
      size = ExtendedTestExtendedIdMessage2::MAX_SIZE;
      return true;
    case MessageType::EXT_ID_3:
      data = msg.data.ext_id_3.data();
      size = ExtendedTestExtendedIdMessage3::MAX_SIZE;
      return true;
    case MessageType::EXT_ID_4:
      data = msg.data.ext_id_4.data();
      size = ExtendedTestExtendedIdMessage4::MAX_SIZE;
      return true;
    case MessageType::EXT_ID_5:
      data = msg.data.ext_id_5.data();
      size = ExtendedTestExtendedIdMessage5::MAX_SIZE;
      return true;
    case MessageType::EXT_ID_6:
      data = msg.data.ext_id_6.data();
      size = ExtendedTestExtendedIdMessage6::MAX_SIZE;
      return true;
    case MessageType::EXT_ID_7:
      data = msg.data.ext_id_7.data();
      size = ExtendedTestExtendedIdMessage7::MAX_SIZE;
      return true;
    case MessageType::EXT_ID_8:
      data = msg.data.ext_id_8.data();
      size = ExtendedTestExtendedIdMessage8::MAX_SIZE;
      return true;
    case MessageType::EXT_ID_9:
      data = msg.data.ext_id_9.data();
      size = ExtendedTestExtendedIdMessage9::MAX_SIZE;
      return true;
    case MessageType::EXT_ID_10:
      data = msg.data.ext_id_10.data();
      size = ExtendedTestExtendedIdMessage10::MAX_SIZE;
      return true;
    case MessageType::LARGE_1:
      data = msg.data.large_1.data();
      size = ExtendedTestLargePayloadMessage1::MAX_SIZE;
      return true;
    case MessageType::LARGE_2:
      data = msg.data.large_2.data();
      size = ExtendedTestLargePayloadMessage2::MAX_SIZE;
      return true;
    default:
      return false;
  }
}

/* Helper function to validate a decoded message against expected data */
inline bool validate_message(const FrameMsgInfo& decode_result, size_t message_index, size_t total_messages) {
  if (!decode_result.valid) {
    std::cout << "  Decoding failed for message " << message_index << "\n";
    return false;
  }

  if (message_index >= total_messages) {
    std::cout << "  Too many messages decoded: " << message_index << "\n";
    return false;
  }

  const MixedMessage& msg = get_extended_test_message(message_index);
  uint16_t expected_msg_id = get_expected_msg_id(msg.type);

  if (decode_result.msg_id != expected_msg_id) {
    std::cout << "  Message ID mismatch for message " << message_index << ": expected " << expected_msg_id << ", got "
              << decode_result.msg_id << "\n";
    return false;
  }

  const uint8_t* expected_data = nullptr;
  size_t expected_size = 0;
  if (!get_expected_data(msg, expected_data, expected_size)) {
    std::cout << "  Unknown message type for message " << message_index << "\n";
    return false;
  }

  if (decode_result.msg_len != expected_size) {
    std::cout << "  Message " << message_index << " size mismatch: expected " << expected_size << ", got "
              << decode_result.msg_len << "\n";
    return false;
  }

  if (decode_result.msg_data && std::memcmp(decode_result.msg_data, expected_data, expected_size) != 0) {
    std::cout << "  Message " << message_index << " content mismatch\n";
    return false;
  }

  return true;
}

}  // namespace TestCodecExtended

/**
 * Encode multiple extended test messages using the specified frame format.
 */
inline bool encode_extended_messages(const std::string& format, uint8_t* buffer, size_t buffer_size,
                                     size_t& encoded_size) {
  using namespace FrameParsers;
  using namespace ExtendedTestMessages;

  encoded_size = 0;

  // Lambda to encode messages using the appropriate profile's BufferWriter
  auto encode_all = [&](auto& writer) -> bool { return write_extended_test_messages(writer, encoded_size); };

  if (format == "profile_bulk") {
    ProfileBulkWriter writer(buffer, buffer_size);
    return encode_all(writer);
  } else if (format == "profile_network") {
    ProfileNetworkWriter writer(buffer, buffer_size);
    return encode_all(writer);
  }

  std::cerr << "  Unknown or unsupported frame format for extended tests: " << format << std::endl;
  return false;
}

/**
 * Decode multiple extended test messages using the specified frame format.
 */
inline bool decode_extended_messages(const std::string& format, const uint8_t* buffer, size_t buffer_size,
                                     size_t& message_count) {
  using namespace FrameParsers;
  using namespace ExtendedTestMessages;

  size_t total_messages = get_extended_test_message_count();
  if (total_messages == 0) {
    std::cout << "  No extended test messages available\n";
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

  /* Lambda to decode and validate messages using AccumulatingReader with split buffers */
  auto decode_all = [&](auto& reader) -> bool {
    // Add first chunk
    reader.add_data(chunk1, chunk1_size);
    while (auto decode_result = reader.next()) {
      if (!TestCodecExtended::validate_message(decode_result, message_count, total_messages)) {
        return false;
      }
      message_count++;
    }

    // Add second chunk (may complete a partial message)
    reader.add_data(chunk2, chunk2_size);
    while (auto decode_result = reader.next()) {
      if (!TestCodecExtended::validate_message(decode_result, message_count, total_messages)) {
        return false;
      }
      message_count++;
    }

    // Add third chunk (may complete a partial message)
    reader.add_data(chunk3, chunk3_size);
    while (auto decode_result = reader.next()) {
      if (!TestCodecExtended::validate_message(decode_result, message_count, total_messages)) {
        return false;
      }
      message_count++;
    }

    if (message_count != total_messages) {
      std::cout << "  Expected " << total_messages << " messages, but decoded " << message_count << "\n";
      return false;
    }

    if (reader.has_partial()) {
      std::cout << "  Incomplete partial message remaining: " << reader.partial_size() << " bytes\n";
      return false;
    }

    return true;
  };

  if (format == "profile_bulk") {
    AccumulatingReader<ProfileBulkConfig> reader;
    return decode_all(reader);
  } else if (format == "profile_network") {
    AccumulatingReader<ProfileNetworkConfig> reader;
    return decode_all(reader);
  }

  std::cout << "  Unknown frame format: " << format << "\n";
  return false;
}
