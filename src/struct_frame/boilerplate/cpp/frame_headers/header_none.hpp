/* Header None - No start bytes (C++) */
/* Format: No start bytes, payload begins immediately */

#pragma once

#include "base.hpp"

namespace FrameParsers {
namespace FrameHeaders {

/* None header configuration */
const HeaderConfig HEADER_NONE_CONFIG = {
    HeaderType::NONE,
    "None",
    {0, 0},
    0,
    false,
    -1,
    "No start bytes - payload begins immediately (requires external sync)"
};

} // namespace FrameHeaders
} // namespace FrameParsers
