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

enum class MessageType { SerializationTest, BasicTypes, UnionTest };

struct MixedMessage {
  MessageType type;
  // Union-based storage for all message types
  union {
    SerializationTestSerializationTestMessage serial_test;
    SerializationTestBasicTypesMessage basic_types;
    SerializationTestUnionTestMessage union_test;
    uint8_t bytes[512];  // Ensure enough space for any message (UnionTestMessage is largest at 235 bytes)
  } data;

  MixedMessage() { std::memset(data.bytes, 0, sizeof(data.bytes)); }
};

/**
 * Load mixed messages from test_messages.json following MixedMessages sequence
 */
std::vector<MixedMessage> load_mixed_messages();

/**
 * Encode multiple test messages using the specified frame format.
 */
bool encode_test_messages(const std::string& format, uint8_t* buffer, size_t buffer_size, size_t& encoded_size);

/**
 * Decode multiple test messages using the specified frame format.
 */
bool decode_test_messages(const std::string& format, const uint8_t* buffer, size_t buffer_size, size_t& message_count);

#endif /* TEST_CODEC_HPP */
