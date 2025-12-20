/* Payload Extended Multi-System Stream */
/* Format: [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
/* Sequence, System ID, Component ID, 2-byte length, Package ID, 2-byte CRC. For complex multi-system streams. */

#pragma once

#include "base.h"

/* Extended Multi-System Stream payload configuration */
static const payload_config_t PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG = {
    .payload_type = PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM,
    .name = "ExtendedMultiSystemStream",
    .has_crc = true,
    .crc_bytes = 2,
    .has_length = true,
    .length_bytes = 2,
    .has_sequence = true,
    .has_system_id = true,
    .has_component_id = true,
    .has_package_id = true,
    .description = "[SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] - Extended multi-system stream format."
};
