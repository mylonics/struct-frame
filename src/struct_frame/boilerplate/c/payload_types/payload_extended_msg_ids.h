/* Payload Extended Message IDs */
/* Format: [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
/* 1-byte length, package ID, 2-byte CRC. For package support. */

#pragma once

#include "base.h"

/* Extended Message IDs payload configuration */
static const payload_config_t PAYLOAD_EXTENDED_MSG_IDS_CONFIG = {
    .payload_type = PAYLOAD_EXTENDED_MSG_IDS,
    .name = "ExtendedMsgIds",
    .has_crc = true,
    .crc_bytes = 2,
    .has_length = true,
    .length_bytes = 1,
    .has_sequence = false,
    .has_system_id = false,
    .has_component_id = false,
    .has_package_id = true,
    .description = "[LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] - Extended message IDs format with package support."
};
