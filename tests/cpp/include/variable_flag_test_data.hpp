/**
 * Variable flag truncation test data definitions (header-only).
 * Tests that messages with variable=true properly truncate unused array space.
 *
 * Structure:
 * - Two identical messages (TruncationTestNonVariable and TruncationTestVariable)
 * - Only difference: TruncationTestVariable has option variable = true
 * - Both have data_array filled to 1/3 capacity (67 out of 200 bytes)
 * - Tests that variable message gets truncated and non-variable does not
 */

#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>

#include "../../generated/cpp/serialization_test.structframe.hpp"

namespace VariableFlagTestData {

// ============================================================================
// Helper functions to create messages
// ============================================================================

// Create non-variable message with 1/3 filled array (67 out of 200 bytes)
inline SerializationTestTruncationTestNonVariable create_non_variable_1_3_filled() {
  SerializationTestTruncationTestNonVariable msg{};
  msg.sequence_id = 0xDEADBEEF;

  // Fill 1/3 of the array (67 out of 200 elements)
  for (uint8_t i = 0; i < 67; i++) {
    msg.data_array.data[i] = i;
  }
  msg.data_array.count = 67;

  msg.footer = 0xCAFE;
  return msg;
}

// Create variable message with 1/3 filled array (67 out of 200 bytes)
// This should be identical in content but will serialize smaller due to variable flag
inline SerializationTestTruncationTestVariable create_variable_1_3_filled() {
  SerializationTestTruncationTestVariable msg{};
  msg.sequence_id = 0xDEADBEEF;

  // Fill 1/3 of the array (67 out of 200 elements)
  for (uint8_t i = 0; i < 67; i++) {
    msg.data_array.data[i] = i;
  }
  msg.data_array.count = 67;

  msg.footer = 0xCAFE;
  return msg;
}

// ============================================================================
// Typed message arrays
// ============================================================================

// Non-variable message array (1 message)
inline const std::array<SerializationTestTruncationTestNonVariable, 1>& get_non_variable_messages() {
  static const std::array<SerializationTestTruncationTestNonVariable, 1> messages = {
      create_non_variable_1_3_filled(),
  };
  return messages;
}

// Variable message array (1 message)
inline const std::array<SerializationTestTruncationTestVariable, 1>& get_variable_messages() {
  static const std::array<SerializationTestTruncationTestVariable, 1> messages = {
      create_variable_1_3_filled(),
  };
  return messages;
}

// Message count constant
constexpr size_t MESSAGE_COUNT = 2;

// The msg_id order array - maps position to which message type to use
inline const std::array<uint16_t, MESSAGE_COUNT>& get_msg_id_order() {
  static const std::array<uint16_t, MESSAGE_COUNT> order = {
      SerializationTestTruncationTestNonVariable::MSG_ID,  // 0: Non-variable message
      SerializationTestTruncationTestVariable::MSG_ID,     // 1: Variable message
  };
  return order;
}

// ============================================================================
// Encoder helper - writes messages in order using index tracking
// ============================================================================

struct Encoder {
  size_t non_var_idx = 0;
  size_t var_idx = 0;

  template <typename WriterType>
  size_t write_message(WriterType& writer, uint16_t msg_id) {
    size_t written = 0;

    if (msg_id == SerializationTestTruncationTestNonVariable::MSG_ID) {
      const auto& msg = get_non_variable_messages()[non_var_idx++];
      written = writer.write(msg);
      std::cout << "MSG1: " << written << " bytes (payload=" << msg.size() << ", no truncation)\n";
    } else if (msg_id == SerializationTestTruncationTestVariable::MSG_ID) {
      const auto& msg = get_variable_messages()[var_idx++];
      written = writer.write(msg);
      std::cout << "MSG2: " << written << " bytes (payload=" << msg.size() << ", TRUNCATED)\n";
    }
    return written;
  }
};

// ============================================================================
// Validator helper - validates decoded messages against expected data
// ============================================================================

struct Validator {
  size_t non_var_idx = 0;
  size_t var_idx = 0;

  bool get_expected(uint16_t msg_id, const uint8_t*& data, size_t& size) {
    if (msg_id == SerializationTestTruncationTestNonVariable::MSG_ID) {
      const auto& msg = get_non_variable_messages()[non_var_idx++];
      data = msg.data();
      size = msg.size();
      return true;
    } else if (msg_id == SerializationTestTruncationTestVariable::MSG_ID) {
      const auto& msg = get_variable_messages()[var_idx++];
      data = msg.data();
      size = msg.size();
      return true;
    }
    return false;
  }

  /** Validate decoded message using operator== (for equality testing) */
  bool validate_with_equals(const FrameParsers::FrameMsgInfo& frame_info) {
    if (frame_info.msg_id == SerializationTestTruncationTestNonVariable::MSG_ID) {
      const auto& expected = get_non_variable_messages()[non_var_idx++];
      SerializationTestTruncationTestNonVariable decoded;
      if (decoded.deserialize(frame_info) == 0) return false;
      return decoded == expected;
    } else if (frame_info.msg_id == SerializationTestTruncationTestVariable::MSG_ID) {
      const auto& expected = get_variable_messages()[var_idx++];
      SerializationTestTruncationTestVariable decoded;
      if (decoded.deserialize(frame_info) == 0) return false;
      return decoded == expected;
    }
    return false;
  }
};

// ============================================================================
// Test configuration - provides all data for TestCodec templates
// ============================================================================

struct Config {
  static constexpr size_t MESSAGE_COUNT = VariableFlagTestData::MESSAGE_COUNT;
  static constexpr size_t BUFFER_SIZE = 4096;
  static constexpr const char* FORMATS_HELP = "profile_bulk";
  static constexpr const char* TEST_NAME = "Variable Flag C++";

  using Encoder = VariableFlagTestData::Encoder;
  using Validator = VariableFlagTestData::Validator;

  static const std::array<uint16_t, MESSAGE_COUNT>& get_msg_id_order() {
    return VariableFlagTestData::get_msg_id_order();
  }

  static FrameParsers::MessageInfo get_message_info(uint16_t msg_id) { return FrameParsers::get_message_info(msg_id); }

  static bool supports_format(const std::string& format) { return format == "profile_bulk"; }
};

}  // namespace VariableFlagTestData
