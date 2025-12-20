/* Header None - No start bytes */
/* Format: No start bytes, payload begins immediately */

#pragma once

#include "base.h"

/* None header configuration */
static const header_config_t HEADER_NONE_CONFIG = {
    .header_type = HEADER_NONE,
    .name = "None",
    .start_bytes = {0, 0},
    .num_start_bytes = 0,
    .encodes_payload_type = false,
    .payload_type_byte_index = -1,
    .description = "No start bytes - payload begins immediately (requires external sync)"
};
