/* Payload Extended Multi-System Stream (C++) */
/* Format: [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace PayloadTypes {

constexpr PayloadConfig PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG = {
    PayloadType::EXTENDED_MULTI_SYSTEM_STREAM,
    "ExtendedMultiSystemStream",
    true, 2, true, 2, true, true, true, true,
    "[SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] - Extended multi-system stream format."
};

} // namespace PayloadTypes
} // namespace FrameParsers
