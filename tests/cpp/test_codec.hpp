/**
 * Test codec header - Encode/decode functions for all frame formats (C++).
 */

#ifndef TEST_CODEC_HPP
#define TEST_CODEC_HPP

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

#include "serialization_test.sf.hpp"

struct TestMessage {
  uint32_t magic_number;
  std::string test_string;
  float test_float;
  bool test_bool;
  std::vector<int32_t> test_array;
};

/**
 * Load test messages from test_messages.json
 * @return Vector of test messages
 */
std::vector<TestMessage> load_test_messages();

/**
 * Create a message struct from test message data.
 * @param test_msg Test message data
 * @param msg Reference to message struct to populate
 */
void create_message_from_data(const TestMessage& test_msg, SerializationTestSerializationTestMessage& msg);

/**
 * Validate that a decoded message matches expected test message data.
 * @param msg Reference to decoded message
 * @param test_msg Expected test message data
 * @return true if all values match, false otherwise
 */
bool validate_message(const SerializationTestSerializationTestMessage& msg, const TestMessage& test_msg);

/**
 * Encode multiple test messages using the specified frame format.
 * @param format Frame format name (e.g., "profile_standard", "profile_sensor", etc.)
 * @param buffer Output buffer for encoded data
 * @param buffer_size Size of output buffer
 * @param encoded_size Output: actual encoded size
 * @return true on success, false on failure
 */
bool encode_test_messages(const std::string& format, uint8_t* buffer, size_t buffer_size, size_t& encoded_size);

/**
 * Decode multiple test messages using the specified frame format.
 * @param format Frame format name
 * @param buffer Input buffer containing encoded data
 * @param buffer_size Size of input data
 * @return true if all messages decoded and validated successfully, false otherwise
 */
bool decode_test_messages(const std::string& format, const uint8_t* buffer, size_t buffer_size);

#endif /* TEST_CODEC_HPP */
