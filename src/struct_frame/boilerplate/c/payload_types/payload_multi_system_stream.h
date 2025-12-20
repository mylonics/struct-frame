/* Payload Multi-System Stream */
/* Format: [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
/* Sequence, System ID, Component ID, 1-byte length, 2-byte CRC. For multi-system streams. */

#pragma once

#include "base.h"

/* Multi-System Stream payload configuration */
static const payload_config_t PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG = {
    .payload_type = PAYLOAD_MULTI_SYSTEM_STREAM,
    .name = "MultiSystemStream",
    .has_crc = true,
    .crc_bytes = 2,
    .has_length = true,
    .length_bytes = 1,
    .has_sequence = true,
    .has_system_id = true,
    .has_component_id = true,
    .has_package_id = false,
    .description = "[SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Multi-system stream format."
};
