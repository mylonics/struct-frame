/**
 * Extended test message data definitions.
 * Hardcoded test messages for extended message ID and payload testing.
 * Uses std::array for efficient compile-time initialization.
 */

#ifndef TEST_MESSAGES_DATA_EXTENDED_HPP
#define TEST_MESSAGES_DATA_EXTENDED_HPP

#include <cstddef>
#include <cstdint>
#include "extended_test.sf.hpp"

namespace ExtendedTestMessages {

enum class MessageType {
  EXT_ID_1,
  EXT_ID_2,
  EXT_ID_3,
  EXT_ID_4,
  EXT_ID_5,
  EXT_ID_6,
  EXT_ID_7,
  EXT_ID_8,
  EXT_ID_9,
  EXT_ID_10,
  LARGE_1,
  LARGE_2
};

struct MixedMessage {
  MessageType type;
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
};

/**
 * Write all extended test messages using the provided writer.
 * Template function that works with any BufferWriter type.
 */
template<typename WriterType>
bool write_extended_test_messages(WriterType& writer, size_t& encoded_size);

/**
 * Get the total number of extended test messages.
 */
size_t get_extended_test_message_count();

/**
 * Get a specific extended test message by index (for validation).
 */
const MixedMessage& get_extended_test_message(size_t index);

} // namespace ExtendedTestMessages

// Include the template implementation
#include "test_messages_data_extended_impl.hpp"

#endif // TEST_MESSAGES_DATA_EXTENDED_HPP
