/* Payload System/Component */
/* Format: [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
/* System ID, Component ID, 1-byte length, 2-byte CRC. For multi-component systems. */

#pragma once

#include "base.h"

/* System/Component payload configuration */
static const payload_config_t PAYLOAD_SYS_COMP_CONFIG = {
    .payload_type = PAYLOAD_SYS_COMP,
    .name = "SysComp",
    .has_crc = true,
    .crc_bytes = 2,
    .has_length = true,
    .length_bytes = 1,
    .has_sequence = false,
    .has_system_id = true,
    .has_component_id = true,
    .has_package_id = false,
    .description = "[SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - System/Component format."
};
