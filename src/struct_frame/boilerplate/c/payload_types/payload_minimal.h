/* Payload Minimal */
/* Format: [MSG_ID] [PACKET] */
/* No length field, no CRC. Requires external synchronization. */

#pragma once

#include "base.h"

/* Minimal payload configuration */
static const payload_config_t PAYLOAD_MINIMAL_CONFIG = {
    .payload_type = PAYLOAD_MINIMAL,
    .name = "Minimal",
    .has_crc = false,
    .crc_bytes = 0,
    .has_length = false,
    .length_bytes = 0,
    .has_sequence = false,
    .has_system_id = false,
    .has_component_id = false,
    .has_package_id = false,
    .description = "[MSG_ID] [PACKET] - Minimal format with no length field and no CRC."
};
