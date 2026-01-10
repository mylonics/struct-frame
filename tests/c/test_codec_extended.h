/**
 * Test codec header - Extended message ID and payload tests (C).
 */

#ifndef TEST_CODEC_EXTENDED_H
#define TEST_CODEC_EXTENDED_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/**
 * Encode extended test messages into a buffer.
 *
 * @param format Frame format name (profile_bulk or profile_network)
 * @param buffer Output buffer
 * @param buffer_size Size of the output buffer
 * @param encoded_size Pointer to receive the total encoded size
 * @return true on success, false on failure
 */
bool encode_extended_messages(const char* format, uint8_t* buffer, size_t buffer_size, size_t* encoded_size);

/**
 * Decode and validate extended test messages from a buffer.
 *
 * @param format Frame format name (profile_bulk or profile_network)
 * @param buffer Input buffer
 * @param buffer_size Size of the input buffer
 * @param message_count Pointer to receive the number of messages decoded
 * @return true on success, false on failure
 */
bool decode_extended_messages(const char* format, const uint8_t* buffer, size_t buffer_size, size_t* message_count);

#endif /* TEST_CODEC_EXTENDED_H */
