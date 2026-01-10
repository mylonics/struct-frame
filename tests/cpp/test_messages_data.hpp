/**
 * Test message data definitions.
 * Hardcoded test messages for cross-platform compatibility testing.
 */

#ifndef TEST_MESSAGES_DATA_HPP
#define TEST_MESSAGES_DATA_HPP

#include <cstddef>
#include <cstdint>

#include "serialization_test.sf.hpp"

enum class MessageType {
  SerializationTest = 0,
  BasicTypes = 1,
  UnionTest = 2
};

union MessageData {
  SerializationTestSerializationTestMessage serialization_test;
  SerializationTestBasicTypesMessage basic_types;
  SerializationTestUnionTestMessage union_test;
};

struct MixedMessage {
  MessageType type;
  MessageData data;
};

/**
 * Get the total number of test messages.
 */
std::size_t get_test_message_count();

/**
 * Get a test message by index.
 * @param index Message index (0-based)
 * @param out_message Output message structure
 * @return true if index is valid, false otherwise
 */
bool get_test_message(std::size_t index, MixedMessage& out_message);

#endif /* TEST_MESSAGES_DATA_HPP */
