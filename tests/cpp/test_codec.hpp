/**
 * Test codec header - Encode/decode functions for all frame formats (C++).
 */

#ifndef TEST_CODEC_HPP
#define TEST_CODEC_HPP

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include "serialization_test.sf.hpp"

enum class MessageType { SerializationTest, BasicTypes };

struct MixedMessage {
  MessageType type;
  // Union-based storage for both message types
  union {
    SerializationTestSerializationTestMessage serial_test;
    SerializationTestBasicTypesMessage basic_types;
    uint8_t bytes[256];  // Ensure enough space for either message
  } data;

  MixedMessage() { std::memset(data.bytes, 0, sizeof(data.bytes)); }
};

struct TestMessage {
  uint32_t magic_number;
  std::string test_string;
  float test_float;
  bool test_bool;
  std::vector<int32_t> test_array;
};

/**
 * Load mixed messages from test_messages.json following MixedMessages sequence
 */
std::vector<MixedMessage> load_mixed_messages();

/**
 * Load test messages from test_messages.json (legacy)
 */
std::vector<TestMessage> load_test_messages();

/**
 * Create a message struct from test message data.
 */
void create_message_from_data(const TestMessage& test_msg, SerializationTestSerializationTestMessage& msg);

/**
 * Validate that a decoded message matches expected test message data.
 */
bool validate_message(const SerializationTestSerializationTestMessage& msg, const TestMessage& test_msg);

/**
 * Encode multiple test messages using the specified frame format.
 */
bool encode_test_messages(const std::string& format, uint8_t* buffer, size_t buffer_size, size_t& encoded_size);

/**
 * Decode multiple test messages using the specified frame format.
 */
bool decode_test_messages(const std::string& format, const uint8_t* buffer, size_t buffer_size, size_t& message_count);

#endif /* TEST_CODEC_HPP */
