/**
 * Test message data definitions.
 * Hardcoded test messages for cross-platform compatibility testing.
 * Replaces JSON-based test data loading.
 * 
 * This module provides a streaming interface where messages are directly
 * encoded to a buffer using a callback function, eliminating intermediate
 * message array allocations.
 */

#ifndef TEST_MESSAGES_DATA_H
#define TEST_MESSAGES_DATA_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "test_codec.h"  // For message_type_t, message_data_t, mixed_message_t

/**
 * Callback function for encoding a single message.
 * @param buffer Output buffer
 * @param buffer_size Available buffer size
 * @param msg_id Message ID
 * @param msg_ptr Pointer to message data
 * @param msg_size Message size
 * @return Number of bytes encoded, or 0 on error
 */
typedef size_t (*encode_message_fn)(uint8_t* buffer, size_t buffer_size, 
                                    uint16_t msg_id, const uint8_t* msg_ptr, 
                                    size_t msg_size);

/**
 * Write all test messages to a buffer using the provided encoder.
 * This function iterates through all test messages and encodes them
 * directly to the buffer using the callback function.
 * 
 * @param buffer Output buffer
 * @param buffer_size Size of output buffer
 * @param encoder Callback function to encode each message
 * @param encoded_size Output: total number of bytes encoded
 * @return true on success, false on error
 */
bool write_test_messages(uint8_t* buffer, size_t buffer_size, 
                        encode_message_fn encoder, size_t* encoded_size);

/**
 * Get the total number of test messages.
 * @return Total message count
 */
size_t get_test_message_count(void);

/**
 * Get a test message by index (for validation/reading).
 * @param index Message index (0-based)
 * @param out_message Output message structure
 * @return true if index is valid, false otherwise
 */
bool get_test_message(size_t index, mixed_message_t* out_message);

#endif /* TEST_MESSAGES_DATA_H */
