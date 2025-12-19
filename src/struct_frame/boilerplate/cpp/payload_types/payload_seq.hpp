/* Payload Sequence (C++) */
/* Format: [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace PayloadTypes {

constexpr PayloadConfig PAYLOAD_SEQ_CONFIG = {
    PayloadType::SEQ,
    "Seq",
    true, 2, true, 1, true, false, false, false,
    "[SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Sequence format for ordered messaging."
};

} // namespace PayloadTypes
} // namespace FrameParsers
