/* Payload Multi-System Stream (C++) */
/* Format: [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace PayloadTypes {

constexpr PayloadConfig PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG = {
    PayloadType::MULTI_SYSTEM_STREAM,
    "MultiSystemStream",
    true, 2, true, 1, true, true, true, false,
    "[SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Multi-system stream format."
};

} // namespace PayloadTypes
} // namespace FrameParsers
