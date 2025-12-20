/* Payload Extended Message IDs (C++) */
/* Format: [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace PayloadTypes {

const PayloadConfig PAYLOAD_EXTENDED_MSG_IDS_CONFIG = {
    .payload_type = PayloadType::EXTENDED_MSG_IDS,
    .name = "ExtendedMsgIds",
    .has_crc = true,
    .crc_bytes = 2,
    .has_length = true,
    .length_bytes = 1,
    .has_sequence = false,
    .has_system_id = false,
    .has_component_id = false,
    .has_package_id = true,
    .description = "[LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] - Extended message IDs format with package support."
};

} // namespace PayloadTypes
} // namespace FrameParsers
