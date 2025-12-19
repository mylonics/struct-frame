/* Header Mavlink V2 - 1 fixed start byte (C++) */
/* Format: [0xFD] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace FrameHeaders {

/* Mavlink V2 header configuration */
constexpr HeaderConfig HEADER_MAVLINK_V2_CONFIG = {
    HeaderType::MAVLINK_V2,
    "MavlinkV2",
    {MAVLINK_V2_STX, 0},
    1,
    false,
    -1,
    "1 start byte [0xFD] - MAVLink v2 protocol framing"
};

} // namespace FrameHeaders
} // namespace FrameParsers
