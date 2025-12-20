/* Base definitions for frame headers (C++) */
/* Header types define start byte patterns and header-specific parsing */

#pragma once

#include <cstdint>
#include <string>
#include <array>

namespace FrameParsers {
namespace FrameHeaders {

/* Header type enumeration */
enum class HeaderType {
    NONE = 0,       /* No start bytes */
    TINY = 1,       /* 1 start byte [0x70+PayloadType] */
    BASIC = 2,      /* 2 start bytes [0x90] [0x70+PayloadType] */
    UBX = 3,        /* 2 start bytes [0xB5] [0x62] */
    MAVLINK_V1 = 4, /* 1 start byte [0xFE] */
    MAVLINK_V2 = 5  /* 1 start byte [0xFD] */
};

/* Configuration for a header type */
struct HeaderConfig {
    HeaderType header_type;
    std::string name;
    std::array<uint8_t, 2> start_bytes;  /* Fixed start bytes (0 for dynamic) */
    uint8_t num_start_bytes;              /* Number of start bytes (0, 1, or 2) */
    bool encodes_payload_type;            /* True if start byte encodes payload type */
    int8_t payload_type_byte_index;       /* Which byte encodes payload type (-1 if none) */
    std::string description;
};

/* Constants used across headers */
constexpr uint8_t BASIC_START_BYTE = 0x90;
constexpr uint8_t PAYLOAD_TYPE_BASE = 0x70;  /* Payload type encoded as 0x70 + payload_type */
constexpr uint8_t UBX_SYNC1 = 0xB5;
constexpr uint8_t UBX_SYNC2 = 0x62;
constexpr uint8_t MAVLINK_V1_STX = 0xFE;
constexpr uint8_t MAVLINK_V2_STX = 0xFD;
constexpr uint8_t MAX_PAYLOAD_TYPE = 8;

} // namespace FrameHeaders
} // namespace FrameParsers
