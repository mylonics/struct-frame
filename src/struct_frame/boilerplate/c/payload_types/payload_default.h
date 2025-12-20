/* Payload Default */
/* Format: [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
/* 1-byte length, 2-byte CRC. Standard format. */

#pragma once

#include "base.h"

/* Default payload configuration */
static const payload_config_t PAYLOAD_DEFAULT_CONFIG = {
    .payload_type = PAYLOAD_DEFAULT,
    .name = "Default",
    .has_crc = true,
    .crc_bytes = 2,
    .has_length = true,
    .length_bytes = 1,
    .has_sequence = false,
    .has_system_id = false,
    .has_component_id = false,
    .has_package_id = false,
    .description = "[LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Standard format with 1-byte length and CRC."
};
