/* Payload Extended Length (C++) */
/* Format: [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace PayloadTypes {

const PayloadConfig PAYLOAD_EXTENDED_LENGTH_CONFIG = {
    .payload_type = PayloadType::EXTENDED_LENGTH,
    .name = "ExtendedLength",
    .has_crc = true,
    .crc_bytes = 2,
    .has_length = true,
    .length_bytes = 2,
    .has_sequence = false,
    .has_system_id = false,
    .has_component_id = false,
    .has_package_id = false,
    .description = "[LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2] - Extended length format with 2-byte length and CRC."
};

} // namespace PayloadTypes
} // namespace FrameParsers
