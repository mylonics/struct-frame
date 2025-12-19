/* Header Tiny - 1 start byte encoding payload type (C++) */
/* Format: [0x70+PayloadType] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace FrameHeaders {

/* Tiny header configuration */
const HeaderConfig HEADER_TINY_CONFIG = {
    HeaderType::TINY,
    "Tiny",
    {0, 0},  /* Dynamic - depends on payload type */
    1,
    true,
    0,
    "1 start byte [0x70+PayloadType] - compact framing"
};

/* Get the start byte for a Tiny frame with given payload type */
inline uint8_t get_tiny_start_byte(uint8_t payload_type_value) {
    return PAYLOAD_TYPE_BASE + payload_type_value;
}

/* Check if byte is a valid Tiny frame start byte */
inline bool is_tiny_start_byte(uint8_t byte) {
    return byte >= PAYLOAD_TYPE_BASE && byte <= (PAYLOAD_TYPE_BASE + MAX_PAYLOAD_TYPE);
}

/* Extract payload type value from Tiny start byte */
inline uint8_t get_payload_type_from_tiny(uint8_t byte) {
    return byte - PAYLOAD_TYPE_BASE;
}

} // namespace FrameHeaders
} // namespace FrameParsers
