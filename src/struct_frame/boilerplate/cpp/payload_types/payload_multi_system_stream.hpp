/* Payload Multi-System Stream (C++) */
/* Format: [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace PayloadTypes {

const PayloadConfig PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG = {
    .payload_type = PayloadType::MULTI_SYSTEM_STREAM,
    .name = "MultiSystemStream",
    .has_crc = true,
    .crc_bytes = 2,
    .has_length = true,
    .length_bytes = 1,
    .has_sequence = true,
    .has_system_id = true,
    .has_component_id = true,
    .has_package_id = false,
    .description = "[SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Multi-system stream format."
};

} // namespace PayloadTypes
} // namespace FrameParsers
