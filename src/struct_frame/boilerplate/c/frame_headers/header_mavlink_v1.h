/* Header Mavlink V1 - 1 fixed start byte */
/* Format: [0xFE] */

#pragma once

#include "base.h"

/* Mavlink V1 header configuration */
static const header_config_t HEADER_MAVLINK_V1_CONFIG = {
    .header_type = HEADER_MAVLINK_V1,
    .name = "MavlinkV1",
    .start_bytes = {MAVLINK_V1_STX, 0},
    .num_start_bytes = 1,
    .encodes_payload_type = false,
    .payload_type_byte_index = -1,
    .description = "1 start byte [0xFE] - MAVLink v1 protocol framing"
};
