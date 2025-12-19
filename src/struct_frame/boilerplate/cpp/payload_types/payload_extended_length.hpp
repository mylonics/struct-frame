/* Payload Extended Length (C++) */
/* Format: [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace PayloadTypes {

constexpr PayloadConfig PAYLOAD_EXTENDED_LENGTH_CONFIG = {
    PayloadType::EXTENDED_LENGTH,
    "ExtendedLength",
    true, 2, true, 2, false, false, false, false,
    "[LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2] - Extended length format with 2-byte length and CRC."
};

} // namespace PayloadTypes
} // namespace FrameParsers
