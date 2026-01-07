/**
 * Test codec header - Encode/decode functions for all frame formats.
 */

#ifndef TEST_CODEC_H
#define TEST_CODEC_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "serialization_test.sf.h"

#define MAX_TEST_MESSAGES 15
#define MAX_STRING_LENGTH 100
#define MAX_ARRAY_LENGTH 20

// Message type enum
typedef enum {
  MSG_TYPE_SERIALIZATION_TEST = 0,
  MSG_TYPE_BASIC_TYPES = 1,
  MSG_TYPE_UNION_TEST = 2
} message_type_t;

// Union to hold either message type
typedef union {
  SerializationTestSerializationTestMessage serialization_test;
  SerializationTestBasicTypesMessage basic_types;
  SerializationTestUnionTestMessage union_test;
} message_data_t;

// Wrapper structure for mixed message types
typedef struct {
  message_type_t type;
  message_data_t data;
} mixed_message_t;

typedef struct {
  uint32_t magic_number;
  char test_string[MAX_STRING_LENGTH];
  float test_float;
  bool test_bool;
  int32_t test_array[MAX_ARRAY_LENGTH];
  size_t test_array_count;
} test_message_t;

/**
 * Load mixed test messages from test_messages.json
 * @param messages Output array of mixed messages
 * @param max_count Maximum number of messages to load
 * @return Number of messages loaded
 */
size_t load_mixed_messages(mixed_message_t* messages, size_t max_count);

/**
 * Load test messages from test_messages.json (alternative format)
 * @param messages Output array of test messages
 * @param max_count Maximum number of messages to load
 * @return Number of messages loaded
 */
size_t load_test_messages(test_message_t* messages, size_t max_count);

/**
 * Create a message struct from test message data.
 * @param test_msg Test message data
 * @param msg Pointer to message struct to populate
 */
void create_message_from_data(const test_message_t* test_msg, SerializationTestSerializationTestMessage* msg);

/**
 * Validate that a decoded message matches expected test message data.
 * @param msg Pointer to decoded message
 * @param test_msg Expected test message data
 * @return true if all values match, false otherwise
 */
bool validate_message(const SerializationTestSerializationTestMessage* msg, const test_message_t* test_msg);

/**
 * Create and populate a test message with expected values (backwards compat).
 * @param msg Pointer to message struct to populate
 */
void create_test_message(SerializationTestSerializationTestMessage* msg);

/**
 * Validate that a decoded message matches expected values (backwards compat).
 * @param msg Pointer to decoded message
 * @return true if all values match, false otherwise
 */
bool validate_test_message(const SerializationTestSerializationTestMessage* msg);

/**
 * Encode multiple test messages using the specified frame format.
 * @param format Frame format name (e.g., "profile_standard", "profile_sensor", etc.)
 * @param buffer Output buffer for encoded data
 * @param buffer_size Size of output buffer
 * @param encoded_size Output: actual encoded size
 * @return true on success, false on failure
 */
bool encode_test_messages(const char* format, uint8_t* buffer, size_t buffer_size, size_t* encoded_size);

/**
 * Encode test messages (wrapper for backwards compatibility).
 * @param format Frame format name
 * @param buffer Output buffer for encoded data
 * @param buffer_size Size of output buffer
 * @param encoded_size Output: actual encoded size
 * @return true on success, false on failure
 */
bool encode_test_message(const char* format, uint8_t* buffer, size_t buffer_size, size_t* encoded_size);

/**
 * Decode and validate multiple test messages using the specified frame format.
 * @param format Frame format name
 * @param buffer Input buffer containing encoded data
 * @param buffer_size Size of input data
 * @param message_count Output: number of messages decoded
 * @return true if all messages decoded and validated successfully, false otherwise
 */
bool decode_test_messages(const char* format, const uint8_t* buffer, size_t buffer_size, size_t* message_count);

/**
 * Decode test messages (wrapper for backwards compatibility).
 * @param format Frame format name
 * @param buffer Input buffer containing encoded data
 * @param buffer_size Size of input data
 * @param msg Output: decoded message (not used in multi-message mode)
 * @return true on success, false on failure
 */
bool decode_test_message(const char* format, const uint8_t* buffer, size_t buffer_size,
                         SerializationTestSerializationTestMessage* msg);

#endif /* TEST_CODEC_H */
