/* Payload Extended (C++) */
/* Format: [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace PayloadTypes {

const PayloadConfig PAYLOAD_EXTENDED_CONFIG = {
    .payload_type = PayloadType::EXTENDED,
    .name = "Extended",
    .has_crc = true,
    .crc_bytes = 2,
    .has_length = true,
    .length_bytes = 2,
    .has_sequence = false,
    .has_system_id = false,
    .has_component_id = false,
    .has_package_id = true,
    .description = "[LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] - Extended format with 2-byte length, package ID, and CRC."
};

} // namespace PayloadTypes
} // namespace FrameParsers
