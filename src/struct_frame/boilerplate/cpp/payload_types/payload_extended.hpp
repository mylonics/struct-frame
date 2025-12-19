/* Payload Extended (C++) */
/* Format: [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace PayloadTypes {

constexpr PayloadConfig PAYLOAD_EXTENDED_CONFIG = {
    PayloadType::EXTENDED,
    "Extended",
    true, true, 2, false, false, false, true,
    "[LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] - Extended format with 2-byte length, package ID, and CRC."
};

} // namespace PayloadTypes
} // namespace FrameParsers
