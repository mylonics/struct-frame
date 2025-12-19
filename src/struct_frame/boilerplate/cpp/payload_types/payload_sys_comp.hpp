/* Payload System/Component (C++) */
/* Format: [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace PayloadTypes {

const PayloadConfig PAYLOAD_SYS_COMP_CONFIG = {
    .payload_type = PayloadType::SYS_COMP,
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

} // namespace PayloadTypes
} // namespace FrameParsers
