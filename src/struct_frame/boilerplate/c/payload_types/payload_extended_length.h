/* Payload Extended Length */
/* Format: [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2] */
/* 2-byte length, 2-byte CRC. For large messages. */

#pragma once

#include "base.h"

/* Extended Length payload configuration */
static const payload_config_t PAYLOAD_EXTENDED_LENGTH_CONFIG = {
    .payload_type = PAYLOAD_EXTENDED_LENGTH,
    .name = "ExtendedLength",
    .has_crc = true,
    .crc_bytes = 2,
    .has_length = true,
    .length_bytes = 2,
    .has_sequence = false,
    .has_system_id = false,
    .has_component_id = false,
    .has_package_id = false,
    .description = "[LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2] - Extended length format with 2-byte length and CRC."
};
