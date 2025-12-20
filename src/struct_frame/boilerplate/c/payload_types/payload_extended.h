/* Payload Extended */
/* Format: [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
/* 2-byte length, package ID, 2-byte CRC. For large messages with package support. */

#pragma once

#include "base.h"

/* Extended payload configuration */
static const payload_config_t PAYLOAD_EXTENDED_CONFIG = {
    .payload_type = PAYLOAD_EXTENDED,
    .name = "Extended",
    .has_crc = true,
    .crc_bytes = 2,
    .has_length = true,
    .length_bytes = 2,
    .has_sequence = false,
    .has_system_id = false,
    .has_component_id = false,
    .has_package_id = true,
    .description = "[LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] - Extended format with 2-byte length, package ID, and CRC."
};
