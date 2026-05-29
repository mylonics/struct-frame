#pragma once

#include <cstdint>
#include <variant>

#include "../../generated/cpp/serialization_test.structframe.hpp"
using namespace structframe::serialization_test;

// Message provider struct for use with TestRunner template
// Tests variable flag truncation behavior:
// - TruncationTestNonVariable: does NOT truncate unused array space
// - TruncationTestVariable: DOES truncate unused array space (option variable = true)
// - NestedVariableMessage: variable parent with nested struct containing variable fields
// - VariableMultipleArrays: multiple bounded arrays all truncated
// - VariableMixedFields: fixed fields plus variable array and variable string
// - VariableEnvelopeMessage: variable + is_envelope + field_order oneof (msgid 221)
// - VariableEnvelopeMsgIdMessage: variable + is_envelope + msgid oneof (msgid 222)
struct VariableFlagMessages {
  // Variant type for message return
  using MessageVariant =
      std::variant<TruncationTestNonVariable, TruncationTestVariable, NestedVariableMessage, VariableMultipleArrays,
                   VariableMixedFields, VariableEnvelopeMessage, VariableEnvelopeMsgIdMessage>;

  // Total number of messages
  static constexpr size_t MESSAGE_COUNT = 7;

  // Create non-variable message with 1/3 filled array (67 out of 200 bytes)
  // This message will NOT truncate - full 200 bytes are always serialized
  static TruncationTestNonVariable create_non_variable() {
    TruncationTestNonVariable msg{};
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
  static TruncationTestVariable create_variable() {
    TruncationTestVariable msg{};
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
  static NestedVariableMessage create_nested_variable() {
    NestedVariableMessage msg{};
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

  // Create multiple-arrays message: type=5, readings=[100,200,300] (3/50),
  // values=[1.5f,2.5f] (2/25), label="multi arrays test" (17/64)
  static VariableMultipleArrays create_multiple_arrays() {
    VariableMultipleArrays msg{};
    msg.type = 5;

    msg.readings.count = 3;
    msg.readings.data[0] = 100;
    msg.readings.data[1] = 200;
    msg.readings.data[2] = 300;

    msg.values.count = 2;
    msg.values.data[0] = 1.5f;
    msg.values.data[1] = 2.5f;

    const char* lbl = "multi arrays test";
    msg.label.length = static_cast<uint8_t>(std::strlen(lbl));
    std::memcpy(msg.label.data, lbl, msg.label.length);

    return msg;
  }

  // Create mixed-fields message: fixed fields + partial variable array + partial variable string
  static VariableMixedFields create_mixed_fields() {
    VariableMixedFields msg{};
    msg.fixed_id = 0xABCD1234;
    msg.fixed_value = 3.14f;
    std::memcpy(msg.fixed_name, "DeviceName", 10);  // 10 chars in 16-byte fixed field

    msg.variable_data.count = 5;
    msg.variable_data.data[0] = 1000;
    msg.variable_data.data[1] = 2000;
    msg.variable_data.data[2] = 3000;
    msg.variable_data.data[3] = 4000;
    msg.variable_data.data[4] = 5000;

    const char* vd = "mixed fields test";
    msg.variable_desc.length = static_cast<uint8_t>(std::strlen(vd));
    std::memcpy(msg.variable_desc.data, vd, msg.variable_desc.length);

    return msg;
  }

  // Single function that returns a message based on index
  static MessageVariant get_message(size_t index) {
    switch (index) {
      case 0:
        return create_non_variable();
      case 1:
        return create_variable();
      case 2:
        return create_nested_variable();
      case 3:
        return create_multiple_arrays();
      case 4:
        return create_mixed_fields();
      case 5:
        return create_variable_envelope_field_order();
      case 6:
      default:
        return create_variable_envelope_msgid();
    }
  }

  // VariableEnvelopeMessage: variable + is_envelope + field_order oneof (msgid 221)
  // Tests that the oneof discriminator + union are correctly serialized in variable format.
  static VariableEnvelopeMessage create_variable_envelope_field_order() {
    // Use wrap() helper to build envelope with payload_a active
    VarEnvPayloadA payload{};
    payload.code = 0x42;
    payload.value = 0x1234;
    return VariableEnvelopeMessage::wrap(7, payload);
  }

  // VariableEnvelopeMsgIdMessage: variable + is_envelope + msgid oneof (msgid 222)
  // Tests that a uint16 msgid discriminator is correctly serialized in variable format.
  static VariableEnvelopeMsgIdMessage create_variable_envelope_msgid() {
    BasicTypesMessage inner{};
    inner.flag = true;
    inner.small_uint = 0xAB;
    inner.medium_uint = 0xCDEF;
    inner.regular_uint = 0x12345678U;
    return VariableEnvelopeMsgIdMessage::wrap(3, inner);
  }
};
