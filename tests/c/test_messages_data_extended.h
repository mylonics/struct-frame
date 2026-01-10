/**
 * Extended test message data definitions.
 * Hardcoded test messages for extended message ID and payload testing.
 * Replaces JSON-based test data loading for extended_messages.json.
 */

#ifndef TEST_MESSAGES_DATA_EXTENDED_H
#define TEST_MESSAGES_DATA_EXTENDED_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "extended_test.sf.h"

/**
 * Extended message type identifiers.
 */
typedef enum {
  EXT_MSG_TYPE_ID1 = 0,
  EXT_MSG_TYPE_ID2,
  EXT_MSG_TYPE_ID3,
  EXT_MSG_TYPE_ID4,
  EXT_MSG_TYPE_ID5,
  EXT_MSG_TYPE_ID6,
  EXT_MSG_TYPE_ID7,
  EXT_MSG_TYPE_ID8,
  EXT_MSG_TYPE_ID9,
  EXT_MSG_TYPE_ID10,
  EXT_MSG_TYPE_LARGE1,
  EXT_MSG_TYPE_LARGE2
} extended_message_type_t;

/**
 * Extended mixed message union.
 */
typedef struct {
  extended_message_type_t type;
  union {
    ExtendedTestExtendedIdMessage1 ext_id_1;
    ExtendedTestExtendedIdMessage2 ext_id_2;
    ExtendedTestExtendedIdMessage3 ext_id_3;
    ExtendedTestExtendedIdMessage4 ext_id_4;
    ExtendedTestExtendedIdMessage5 ext_id_5;
    ExtendedTestExtendedIdMessage6 ext_id_6;
    ExtendedTestExtendedIdMessage7 ext_id_7;
    ExtendedTestExtendedIdMessage8 ext_id_8;
    ExtendedTestExtendedIdMessage9 ext_id_9;
    ExtendedTestExtendedIdMessage10 ext_id_10;
    ExtendedTestLargePayloadMessage1 large_1;
    ExtendedTestLargePayloadMessage2 large_2;
  } data;
} extended_mixed_message_t;

/**
 * Callback function for encoding a single extended message.
 */
typedef size_t (*encode_extended_message_fn)(uint8_t* buffer, size_t buffer_size, 
                                             uint16_t msg_id, const uint8_t* msg_ptr, 
                                             size_t msg_size);

/**
 * Write all extended test messages to a buffer using the provided encoder.
 * 
 * @param buffer Output buffer
 * @param buffer_size Size of output buffer
 * @param encoder Callback function to encode each message
 * @param encoded_size Output: total number of bytes encoded
 * @return true on success, false on error
 */
bool write_extended_test_messages(uint8_t* buffer, size_t buffer_size, 
                                  encode_extended_message_fn encoder, size_t* encoded_size);

/**
 * Get the total number of extended test messages.
 * @return Total message count
 */
size_t get_extended_test_message_count(void);

/**
 * Get an extended test message by index (for validation/reading).
 * @param index Message index (0-based)
 * @param out_message Output message structure
 * @return true if index is valid, false otherwise
 */
bool get_extended_test_message(size_t index, extended_mixed_message_t* out_message);

#endif /* TEST_MESSAGES_DATA_EXTENDED_H */
