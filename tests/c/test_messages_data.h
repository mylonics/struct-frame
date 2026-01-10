/**
 * Test message data definitions.
 * Hardcoded test messages for cross-platform compatibility testing.
 * Replaces JSON-based test data loading.
 */

#ifndef TEST_MESSAGES_DATA_H
#define TEST_MESSAGES_DATA_H

#include <stdbool.h>
#include <stddef.h>

#include "test_codec.h"  // For message_type_t, message_data_t, mixed_message_t

/**
 * Get the total number of test messages.
 * @return Total message count
 */
size_t get_test_message_count(void);

/**
 * Get a test message by index.
 * @param index Message index (0-based)
 * @param out_message Output message structure
 * @return true if index is valid, false otherwise
 */
bool get_test_message(size_t index, mixed_message_t* out_message);

#endif /* TEST_MESSAGES_DATA_H */
