#pragma once

#include <cstddef>
#include <cstdint>
#include <variant>

#include "../../generated/cpp/frame_profiles.hpp"

// Function pointer type for get_message_info
using GetMessageInfoFn = FrameParsers::MessageInfo (*)(uint16_t);

// ProfileRunner - Low-level encoding and decoding for a specific MessageProvider and Config
//
// Template parameters:
//   - MessageProvider: struct with MessageVariant, MESSAGE_COUNT, get_message()
//   - Config: frame profile config (e.g., ProfileStandardConfig)
//   - GetMsgInfo: function pointer to get_message_info for the message set

template <typename MessageProvider, typename Config, GetMessageInfoFn GetMsgInfo>
class ProfileRunner {
 public:
  static constexpr size_t BUFFER_SIZE = 16384;

  // Encode all messages to buffer using BufferWriter
  // Returns total bytes written
  static size_t encode(uint8_t* buffer, size_t buffer_size) {
    using Writer = FrameParsers::BufferWriter<Config>;
    Writer writer(buffer, buffer_size);

    for (size_t i = 0; i < MessageProvider::MESSAGE_COUNT; i++) {
      auto msg = MessageProvider::get_message(i);
      std::visit([&writer](auto&& m) { writer.write(m); }, msg);
    }

    return writer.size();
  }

  // Parse all messages from buffer using AccumulatingReader
  // Returns the number of messages that matched (MESSAGE_COUNT if all pass)
  static size_t parse(const uint8_t* buffer, size_t buffer_size) {
    using Reader = FrameParsers::AccumulatingReader<Config, BUFFER_SIZE, GetMessageInfoFn>;

    Reader reader(GetMsgInfo);
    reader.add_data(buffer, buffer_size);

    size_t message_count = 0;

    while (auto result = reader.next()) {
      if (!result.valid) break;

      auto expected = MessageProvider::get_message(message_count);
      bool match = std::visit(
          [&result](auto&& exp) -> bool {
            using ExpType = std::decay_t<decltype(exp)>;
            if (result.msg_id != ExpType::MSG_ID) return false;
            ExpType decoded{};
            decoded.deserialize(result);
            return decoded == exp;
          },
          expected);

      if (!match) break;
      message_count++;
    }

    return message_count;
  }
};

// Function pointer types for profile dispatch
using EncodeFn = size_t (*)(uint8_t*, size_t);
using ParseFn = size_t (*)(const uint8_t*, size_t);

struct ProfileOps {
  EncodeFn encode;
  ParseFn parse;
};
