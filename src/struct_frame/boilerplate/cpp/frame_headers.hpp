/* Frame Headers - Start byte patterns and header configurations (C++) */
/* Header types define start byte patterns and header-specific parsing */

#pragma once

#include <cstdint>

namespace FrameParsers {
namespace FrameHeaders {

/* Header type enumeration */
enum class HeaderType : uint8_t {
  NONE = 0,       /* No start bytes */
  TINY = 1,       /* 1 start byte [0x70+PayloadType] */
  BASIC = 2,      /* 2 start bytes [0x90] [0x70+PayloadType] */
  UBX = 3,        /* 2 start bytes [0xB5] [0x62] */
  MAVLINK_V1 = 4, /* 1 start byte [0xFE] */
  MAVLINK_V2 = 5  /* 1 start byte [0xFD] */
};

/* Constants used across headers */
constexpr uint8_t BASIC_START_BYTE = 0x90;
constexpr uint8_t PAYLOAD_TYPE_BASE = 0x70; /* Payload type encoded as 0x70 + payload_type */
constexpr uint8_t UBX_SYNC1 = 0xB5;
constexpr uint8_t UBX_SYNC2 = 0x62;
constexpr uint8_t MAVLINK_V1_STX = 0xFE;
constexpr uint8_t MAVLINK_V2_STX = 0xFD;
constexpr uint8_t MAX_PAYLOAD_TYPE = 8;

/**
 * Compile-time configuration for a header type.
 * All members are constexpr for zero runtime overhead.
 */
struct HeaderConfig {
  HeaderType header_type;
  uint8_t start_byte1;       /* First start byte (0 if none or dynamic) */
  uint8_t start_byte2;       /* Second start byte (0 if none or dynamic) */
  uint8_t num_start_bytes;   /* Number of start bytes (0, 1, or 2) */
  bool encodes_payload_type; /* True if start byte encodes payload type */

  /* Calculate total header contribution (just start bytes) */
  constexpr uint8_t size() const { return num_start_bytes; }
};

/* Pre-defined header configurations */
constexpr HeaderConfig HEADER_NONE_CONFIG = {
    HeaderType::NONE, 0, 0, /* no start bytes */
    0,                      /* num_start_bytes */
    false                   /* encodes_payload_type */
};

constexpr HeaderConfig HEADER_TINY_CONFIG = {
    HeaderType::TINY, 0, 0, /* dynamic - 0x70 + payload_type */
    1,                      /* num_start_bytes */
    true                    /* encodes_payload_type */
};

constexpr HeaderConfig HEADER_BASIC_CONFIG = {
    HeaderType::BASIC, BASIC_START_BYTE, 0, /* 0x90, then dynamic 0x70 + payload_type */
    2,                                      /* num_start_bytes */
    true                                    /* encodes_payload_type */
};

constexpr HeaderConfig HEADER_UBX_CONFIG = {
    HeaderType::UBX, UBX_SYNC1, UBX_SYNC2, /* 0xB5, 0x62 */
    2,                                     /* num_start_bytes */
    false                                  /* encodes_payload_type */
};

constexpr HeaderConfig HEADER_MAVLINK_V1_CONFIG = {
    HeaderType::MAVLINK_V1, MAVLINK_V1_STX, 0, /* 0xFE */
    1,                                         /* num_start_bytes */
    false                                      /* encodes_payload_type */
};

constexpr HeaderConfig HEADER_MAVLINK_V2_CONFIG = {
    HeaderType::MAVLINK_V2, MAVLINK_V2_STX, 0, /* 0xFD */
    1,                                         /* num_start_bytes */
    false                                      /* encodes_payload_type */
};

}  // namespace FrameHeaders
}  // namespace FrameParsers
