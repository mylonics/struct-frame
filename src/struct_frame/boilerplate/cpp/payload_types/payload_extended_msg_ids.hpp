/* Payload Extended Message IDs (C++) */
/* Format: [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace PayloadTypes {

constexpr PayloadConfig PAYLOAD_EXTENDED_MSG_IDS_CONFIG = {
    PayloadType::EXTENDED_MSG_IDS,
    "ExtendedMsgIds",
    true, 2, true, 1, false, false, false, true,
    "[LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] - Extended message IDs format with package support."
};

} // namespace PayloadTypes
} // namespace FrameParsers
