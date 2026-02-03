#pragma once

#include <cstdint>
#include <variant>

#include "../../generated/cpp/serialization_test.structframe.hpp"

// Message provider struct for use with TestRunner template
// Tests variable flag truncation behavior:
// - TruncationTestNonVariable: does NOT truncate unused array space
// - TruncationTestVariable: DOES truncate unused array space (option variable = true)
struct VariableFlagMessages {
  // Variant type for message return
  using MessageVariant =
      std::variant<SerializationTestTruncationTestNonVariable, SerializationTestTruncationTestVariable>;

  // Total number of messages (1 non-variable + 1 variable = 2)
  static constexpr size_t MESSAGE_COUNT = 2;

  // Create non-variable message with 1/3 filled array (67 out of 200 bytes)
  // This message will NOT truncate - full 200 bytes are always serialized
  static SerializationTestTruncationTestNonVariable create_non_variable() {
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
  // This message WILL truncate - only 67 bytes are serialized due to variable flag
  static SerializationTestTruncationTestVariable create_variable() {
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

  // Single function that returns a message based on index
  // Order: non-variable first, then variable
  static MessageVariant get_message(size_t index) {
    switch (index) {
      case 0:
        return create_non_variable();
      case 1:
      default:
        return create_variable();
    }
  }
};
