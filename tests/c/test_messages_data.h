/**
 * Test message data definitions.
 * Hardcoded test messages for cross-platform compatibility testing.
 * Replaces JSON-based test data loading.
 */

#ifndef TEST_MESSAGES_DATA_H
#define TEST_MESSAGES_DATA_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "serialization_test.sf.h"

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
