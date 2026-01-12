/**
 * Test codec (header-only) - Encode/decode functions for all frame formats (C++).
 * Simplified to use MessageRef for unified message handling.
 */

#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>

#include "frame_parsers.hpp"
#include "test_messages_data.hpp"

/**
 * Encode all test messages using the specified frame format.
 */
inline bool encode_test_messages(const std::string& format, uint8_t* buffer, size_t buffer_size, size_t& encoded_size) {
  using namespace FrameParsers;

  const auto& order = TestMessagesData::get_message_order();
  encoded_size = 0;

  // Lambda to encode all messages using the provided writer
  auto encode_all = [&](auto& writer) -> bool {
    for (const auto& msg : order) {
      size_t written = writer.write_raw(msg.msg_id, msg.msg_data, msg.msg_size);
      if (written == 0) {
        std::cout << "  Encoding failed for message ID " << msg.msg_id << "\n";
        return false;
      }
    }
    encoded_size = writer.size();
    return true;
  };

  if (format == "profile_standard") {
    ProfileStandardWriter writer(buffer, buffer_size);
    return encode_all(writer);
  } else if (format == "profile_sensor") {
    ProfileSensorWriter writer(buffer, buffer_size);
    return encode_all(writer);
  } else if (format == "profile_ipc") {
    ProfileIPCWriter writer(buffer, buffer_size);
    return encode_all(writer);
  } else if (format == "profile_bulk") {
    ProfileBulkWriter writer(buffer, buffer_size);
    return encode_all(writer);
  } else if (format == "profile_network") {
    ProfileNetworkWriter writer(buffer, buffer_size);
    return encode_all(writer);
  }

  std::cout << "  Unknown frame format: " << format << "\n";
  return false;
}

/**
 * Decode and validate all test messages using the specified frame format.
 */
inline bool decode_test_messages(const std::string& format, const uint8_t* buffer, size_t buffer_size,
                                 size_t& message_count) {
  using namespace FrameParsers;

  const auto& order = TestMessagesData::get_message_order();
  const size_t total_messages = order.size();
  message_count = 0;

  // Split buffer into 3 chunks to test partial message handling
  size_t chunk1_size = buffer_size / 3;
  size_t chunk2_size = buffer_size / 3;
  size_t chunk3_size = buffer_size - chunk1_size - chunk2_size;

  const uint8_t* chunk1 = buffer;
  const uint8_t* chunk2 = buffer + chunk1_size;
  const uint8_t* chunk3 = buffer + chunk1_size + chunk2_size;

  // Lambda to validate a decoded message against the expected MessageRef
  auto validate = [&](const FrameMsgInfo& result) -> bool {
    if (!result.valid) {
      std::cout << "  Decoding failed for message " << message_count << "\n";
      return false;
    }

    if (message_count >= total_messages) {
      std::cout << "  Too many messages decoded: " << message_count << "\n";
      return false;
    }

    const MessageRef& expected = order[message_count];

    if (result.msg_id != expected.msg_id) {
      std::cout << "  Message " << message_count << " ID mismatch: expected " << expected.msg_id << ", got "
                << result.msg_id << "\n";
      return false;
    }

    if (result.msg_len != expected.msg_size) {
      std::cout << "  Message " << message_count << " size mismatch: expected " << expected.msg_size << ", got "
                << result.msg_len << "\n";
      return false;
    }

    if (std::memcmp(result.msg_data, expected.msg_data, expected.msg_size) != 0) {
      std::cout << "  Message " << message_count << " content mismatch\n";
      return false;
    }

    return true;
  };

  // Lambda to decode messages using AccumulatingReader with chunked input
  auto decode_all = [&](auto& reader) -> bool {
    // Process chunks
    const uint8_t* chunks[] = {chunk1, chunk2, chunk3};
    size_t sizes[] = {chunk1_size, chunk2_size, chunk3_size};

    for (int c = 0; c < 3; c++) {
      reader.add_data(chunks[c], sizes[c]);
      while (auto result = reader.next()) {
        if (!validate(result)) return false;
        message_count++;
      }
    }

    if (message_count != total_messages) {
      std::cout << "  Expected " << total_messages << " messages, decoded " << message_count << "\n";
      return false;
    }

    if (reader.has_partial()) {
      std::cout << "  Incomplete partial message: " << reader.partial_size() << " bytes\n";
      return false;
    }

    return true;
  };

  if (format == "profile_standard") {
    AccumulatingReader<ProfileStandardConfig> reader;
    return decode_all(reader);
  } else if (format == "profile_sensor") {
    AccumulatingReader<ProfileSensorConfig> reader(get_message_length);
    return decode_all(reader);
  } else if (format == "profile_ipc") {
    AccumulatingReader<ProfileIPCConfig> reader(get_message_length);
    return decode_all(reader);
  } else if (format == "profile_bulk") {
    AccumulatingReader<ProfileBulkConfig> reader;
    return decode_all(reader);
  } else if (format == "profile_network") {
    AccumulatingReader<ProfileNetworkConfig> reader;
    return decode_all(reader);
  }

  std::cout << "  Unknown frame format: " << format << "\n";
  return false;
}
