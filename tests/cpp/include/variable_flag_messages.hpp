#pragma once

#include <cstdint>
#include <variant>

#include "../../generated/cpp/serialization_test.structframe.hpp"

// Message provider struct for use with TestRunner template
// Tests variable flag truncation behavior:
// - TruncationTestNonVariable: does NOT truncate unused array space
// - TruncationTestVariable: DOES truncate unused array space (option variable = true)
// - NestedVariableMessage: variable parent with nested struct containing variable fields
struct VariableFlagMessages {
  // Variant type for message return
  using MessageVariant =
      std::variant<SerializationTestTruncationTestNonVariable, SerializationTestTruncationTestVariable,
                   SerializationTestNestedVariableMessage>;

  // Total number of messages (1 non-variable + 1 variable + 1 nested variable = 3)
  static constexpr size_t MESSAGE_COUNT = 3;

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

  // Create nested variable message: parent with option variable = true, nested struct with
  // variable-length fields (variable string + variable array)
  static SerializationTestNestedVariableMessage create_nested_variable() {
    SerializationTestNestedVariableMessage msg{};
    msg.sequence = 0x12345678;

    // Nested payload: id=7, label="Hello" (5 chars), samples=[10,20,30] (3 elements)
    msg.payload.id = 7;
    msg.payload.label.length = 5;
    std::memcpy(msg.payload.label.data, "Hello", 5);
    msg.payload.samples.count = 3;
    msg.payload.samples.data[0] = 10;
    msg.payload.samples.data[1] = 20;
    msg.payload.samples.data[2] = 30;

    // Top-level variable string
    const char* desc = "nested variable test";
    msg.description.length = static_cast<uint8_t>(std::strlen(desc));
    std::memcpy(msg.description.data, desc, msg.description.length);

    return msg;
  }

  // Single function that returns a message based on index
  // Order: non-variable first, then variable, then nested variable
  static MessageVariant get_message(size_t index) {
    switch (index) {
      case 0:
        return create_non_variable();
      case 1:
        return create_variable();
      case 2:
      default:
        return create_nested_variable();
    }
  }
};
