/* Header Basic - 2 start bytes with payload type encoding */
/* Format: [0x90] [0x70+PayloadType] */

#pragma once

#include "base.h"

/* Basic header configuration */
static const header_config_t HEADER_BASIC_CONFIG = {
    .header_type = HEADER_BASIC,
    .name = "Basic",
    .start_bytes = {BASIC_START_BYTE, 0},  /* First byte fixed, second dynamic */
    .num_start_bytes = 2,
    .encodes_payload_type = true,
    .payload_type_byte_index = 1,
    .description = "2 start bytes [0x90] [0x70+PayloadType] - standard framing"
};

/* Get the second start byte for a Basic frame with given payload type */
static inline uint8_t get_basic_second_start_byte(uint8_t payload_type_value) {
    return PAYLOAD_TYPE_BASE + payload_type_value;
}

/* Check if byte is a valid Basic frame second start byte */
static inline bool is_basic_second_start_byte(uint8_t byte) {
    return byte >= PAYLOAD_TYPE_BASE && byte <= (PAYLOAD_TYPE_BASE + MAX_PAYLOAD_TYPE);
}

/* Extract payload type value from Basic second start byte */
static inline uint8_t get_payload_type_from_basic(uint8_t byte) {
    return byte - PAYLOAD_TYPE_BASE;
}
