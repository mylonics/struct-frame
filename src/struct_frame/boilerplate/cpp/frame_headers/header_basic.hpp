/* Header Basic - 2 start bytes with payload type encoding (C++) */
/* Format: [0x90] [0x70+PayloadType] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace FrameHeaders {

/* Basic header configuration */
const HeaderConfig HEADER_BASIC_CONFIG = {
    HeaderType::BASIC,
    "Basic",
    {BASIC_START_BYTE, 0},  /* First byte fixed, second dynamic */
    2,
    true,
    1,
    "2 start bytes [0x90] [0x70+PayloadType] - standard framing"
};

/* Get the second start byte for a Basic frame with given payload type */
inline uint8_t get_basic_second_start_byte(uint8_t payload_type_value) {
    return PAYLOAD_TYPE_BASE + payload_type_value;
}

/* Check if byte is a valid Basic frame second start byte */
inline bool is_basic_second_start_byte(uint8_t byte) {
    return byte >= PAYLOAD_TYPE_BASE && byte <= (PAYLOAD_TYPE_BASE + MAX_PAYLOAD_TYPE);
}

/* Extract payload type value from Basic second start byte */
inline uint8_t get_payload_type_from_basic(uint8_t byte) {
    return byte - PAYLOAD_TYPE_BASE;
}

} // namespace FrameHeaders
} // namespace FrameParsers
