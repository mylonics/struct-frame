/* Payload System/Component (C++) */
/* Format: [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace PayloadTypes {

constexpr PayloadConfig PAYLOAD_SYS_COMP_CONFIG = {
    PayloadType::SYS_COMP,
    "SysComp",
    true, 2, true, 1, false, true, true, false,
    "[SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - System/Component format."
};

} // namespace PayloadTypes
} // namespace FrameParsers
