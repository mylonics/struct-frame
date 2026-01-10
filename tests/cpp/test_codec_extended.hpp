/**
 * Test codec header - Extended message ID and payload tests (C++).
 */

#ifndef TEST_CODEC_EXTENDED_HPP
#define TEST_CODEC_EXTENDED_HPP

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include "extended_test.sf.hpp"

enum class ExtendedMessageType {
  ExtendedId1,
  ExtendedId2,
  ExtendedId3,
  ExtendedId4,
  ExtendedId5,
  ExtendedId6,
  ExtendedId7,
  ExtendedId8,
  ExtendedId9,
  ExtendedId10,
  LargePayload1,
  LargePayload2
};

struct ExtendedMixedMessage {
  ExtendedMessageType type;
  // Union-based storage for all message types
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
    ExtendedTestLargePayloadMessage1 large_payload_1;
    ExtendedTestLargePayloadMessage2 large_payload_2;
    uint8_t bytes[512];
  } data;

  ExtendedMixedMessage() { std::memset(data.bytes, 0, sizeof(data.bytes)); }
};

/**
 * Load extended mixed messages from extended_messages.json
 */
std::vector<ExtendedMixedMessage> load_extended_messages();

/**
 * Encode multiple extended test messages using the specified frame format.
 */
bool encode_extended_messages(const std::string& format, uint8_t* buffer, size_t buffer_size, size_t& encoded_size);

/**
 * Decode multiple extended test messages using the specified frame format.
 */
bool decode_extended_messages(const std::string& format, const uint8_t* buffer, size_t buffer_size,
                              size_t& message_count);

#endif /* TEST_CODEC_EXTENDED_HPP */
