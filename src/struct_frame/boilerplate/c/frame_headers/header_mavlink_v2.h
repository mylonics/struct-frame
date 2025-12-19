/* Header Mavlink V2 - 1 fixed start byte */
/* Format: [0xFD] */

#pragma once

#include "base.h"

/* Mavlink V2 header configuration */
static const header_config_t HEADER_MAVLINK_V2_CONFIG = {
    .header_type = HEADER_MAVLINK_V2,
    .name = "MavlinkV2",
    .start_bytes = {MAVLINK_V2_STX, 0},
    .num_start_bytes = 1,
    .encodes_payload_type = false,
    .payload_type_byte_index = -1,
    .description = "1 start byte [0xFD] - MAVLink v2 protocol framing"
};
