/* Payload Sequence (C++) */
/* Format: [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace PayloadTypes {

const PayloadConfig PAYLOAD_SEQ_CONFIG = {
    .payload_type = PayloadType::SEQ,
    .name = "Seq",
    .has_crc = true,
    .crc_bytes = 2,
    .has_length = true,
    .length_bytes = 1,
    .has_sequence = true,
    .has_system_id = false,
    .has_component_id = false,
    .has_package_id = false,
    .description = "[SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Sequence format for ordered messaging."
};

} // namespace PayloadTypes
} // namespace FrameParsers
