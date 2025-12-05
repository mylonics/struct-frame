/**
 * Test codec header - Encode/decode functions for all frame formats.
 */

#ifndef TEST_CODEC_H
#define TEST_CODEC_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "serialization_test.sf.h"

/**
 * Create and populate a test message with expected values.
 * @param msg Pointer to message struct to populate
 */
void create_test_message(SerializationTestSerializationTestMessage* msg);

/**
 * Validate that a decoded message matches expected values.
 * @param msg Pointer to decoded message
 * @return true if all values match, false otherwise
 */
bool validate_test_message(const SerializationTestSerializationTestMessage* msg);

/**
 * Encode a test message using the specified frame format.
 * @param format Frame format name (e.g., "basic_default", "basic_minimal", etc.)
 * @param buffer Output buffer for encoded data
 * @param buffer_size Size of output buffer
 * @param encoded_size Output: actual encoded size
 * @return true on success, false on failure
 */
bool encode_test_message(const char* format, uint8_t* buffer, size_t buffer_size, size_t* encoded_size);

/**
 * Decode a test message using the specified frame format.
 * @param format Frame format name
 * @param buffer Input buffer containing encoded data
 * @param buffer_size Size of input data
 * @param msg Output: decoded message
 * @return true on success, false on failure
 */
bool decode_test_message(const char* format, const uint8_t* buffer, size_t buffer_size,
                         SerializationTestSerializationTestMessage* msg);

#endif /* TEST_CODEC_H */
