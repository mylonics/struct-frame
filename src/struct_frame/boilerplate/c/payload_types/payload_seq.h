/* Payload Sequence */
/* Format: [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
/* Sequence number, 1-byte length, 2-byte CRC. For ordered messaging. */

#pragma once

#include "base.h"

/* Sequence payload configuration */
static const payload_config_t PAYLOAD_SEQ_CONFIG = {
    .payload_type = PAYLOAD_SEQ,
    .name = "Seq",
    .has_crc = true,
    .crc_bytes = 2,
    .has_length = true,
    .length_bytes = 1,
    .has_sequence = true,
    .has_system_id = false,
    .has_component_id = false,
    .has_package_id = false,
    .description = "[SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Sequence format for ordered messaging."
};
