/* Header Mavlink V1 - 1 fixed start byte (C++) */
/* Format: [0xFE] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace FrameHeaders {

/* Mavlink V1 header configuration */
const HeaderConfig HEADER_MAVLINK_V1_CONFIG = {
    HeaderType::MAVLINK_V1,
    "MavlinkV1",
    {MAVLINK_V1_STX, 0},
    1,
    false,
    -1,
    "1 start byte [0xFE] - MAVLink v1 protocol framing"
};

} // namespace FrameHeaders
} // namespace FrameParsers
