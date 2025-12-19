/* Header Tiny - 1 start byte encoding payload type */
/* Format: [0x70+PayloadType] */

#pragma once

#include "base.h"

/* Tiny header configuration */
static const header_config_t HEADER_TINY_CONFIG = {
    .header_type = HEADER_TINY,
    .name = "Tiny",
    .start_bytes = {0, 0},  /* Dynamic - depends on payload type */
    .num_start_bytes = 1,
    .encodes_payload_type = true,
    .payload_type_byte_index = 0,
    .description = "1 start byte [0x70+PayloadType] - compact framing"
};

/* Get the start byte for a Tiny frame with given payload type */
static inline uint8_t get_tiny_start_byte(uint8_t payload_type_value) {
    return PAYLOAD_TYPE_BASE + payload_type_value;
}

/* Check if byte is a valid Tiny frame start byte */
static inline bool is_tiny_start_byte(uint8_t byte) {
    return byte >= PAYLOAD_TYPE_BASE && byte <= (PAYLOAD_TYPE_BASE + MAX_PAYLOAD_TYPE);
}

/* Extract payload type value from Tiny start byte */
static inline uint8_t get_payload_type_from_tiny(uint8_t byte) {
    return byte - PAYLOAD_TYPE_BASE;
}
