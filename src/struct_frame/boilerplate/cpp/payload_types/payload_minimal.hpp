/* Payload Minimal (C++) */
/* Format: [MSG_ID] [PACKET] */
/* No length field, no CRC. Requires external synchronization. */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace PayloadTypes {

/* Minimal payload configuration */
constexpr PayloadConfig PAYLOAD_MINIMAL_CONFIG = {
    PayloadType::MINIMAL,
    "Minimal",
    false, /* has_crc */
    0,     /* crc_bytes */
    false, /* has_length */
    0,     /* length_bytes */
    false, /* has_sequence */
    false, /* has_system_id */
    false, /* has_component_id */
    false, /* has_package_id */
    "[MSG_ID] [PACKET] - Minimal format with no length field and no CRC."
};

} // namespace PayloadTypes
} // namespace FrameParsers
