/* Header UBX - 2 fixed start bytes */
/* Format: [0xB5] [0x62] */

#pragma once

#include "base.h"

/* UBX header configuration */
static const header_config_t HEADER_UBX_CONFIG = {
    .header_type = HEADER_UBX,
    .name = "UBX",
    .start_bytes = {UBX_SYNC1, UBX_SYNC2},
    .num_start_bytes = 2,
    .encodes_payload_type = false,
    .payload_type_byte_index = -1,
    .description = "2 start bytes [0xB5] [0x62] - UBX protocol framing"
};
