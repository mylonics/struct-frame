/* Payload Default (C++) */
/* Format: [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
/* 1-byte length, 2-byte CRC. Standard format. */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace PayloadTypes {

/* Default payload configuration */
constexpr PayloadConfig PAYLOAD_DEFAULT_CONFIG = {
    PayloadType::DEFAULT,
    "Default",
    true,  /* has_crc */
    2,     /* crc_bytes */
    true,  /* has_length */
    1,     /* length_bytes */
    false, /* has_sequence */
    false, /* has_system_id */
    false, /* has_component_id */
    false, /* has_package_id */
    "[LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Standard format with 1-byte length and CRC."
};

} // namespace PayloadTypes
} // namespace FrameParsers
