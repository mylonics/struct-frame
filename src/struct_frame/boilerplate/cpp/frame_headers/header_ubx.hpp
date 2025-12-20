/* Header UBX - 2 fixed start bytes (C++) */
/* Format: [0xB5] [0x62] */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace FrameHeaders {

/* UBX header configuration */
const HeaderConfig HEADER_UBX_CONFIG = {
    HeaderType::UBX,
    "UBX",
    {UBX_SYNC1, UBX_SYNC2},
    2,
    false,
    -1,
    "2 start bytes [0xB5] [0x62] - UBX protocol framing"
};

} // namespace FrameHeaders
} // namespace FrameParsers
