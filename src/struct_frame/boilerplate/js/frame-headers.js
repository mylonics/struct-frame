/**
 * Frame Headers - Start byte patterns and header configurations (JavaScript)
 * Header types define start byte patterns and header-specific parsing
 *
 * This file mirrors the C++ frame_headers.hpp structure.
 */

/** Header type enumeration */
const HeaderType = {
  NONE: 0,       // No start bytes
  TINY: 1,       // 1 start byte [0x70+PayloadType]
  BASIC: 2,      // 2 start bytes [0x90] [0x70+PayloadType]
  UBX: 3,        // 2 start bytes [0xB5] [0x62]
  MAVLINK_V1: 4, // 1 start byte [0xFE]
  MAVLINK_V2: 5  // 1 start byte [0xFD]
};

/** Constants used across headers */
const BASIC_START_BYTE = 0x90;
const PAYLOAD_TYPE_BASE = 0x70;  // Payload type encoded as 0x70 + payload_type
const UBX_SYNC1 = 0xB5;
const UBX_SYNC2 = 0x62;
const MAVLINK_V1_STX = 0xFE;
const MAVLINK_V2_STX = 0xFD;
const MAX_PAYLOAD_TYPE = 8;

/** Pre-defined header configurations */
const HEADER_NONE_CONFIG = {
  headerType: HeaderType.NONE,
  startByte1: 0,
  startByte2: 0,
  numStartBytes: 0,
  encodesPayloadType: false,
};

const HEADER_TINY_CONFIG = {
  headerType: HeaderType.TINY,
  startByte1: 0,  // Dynamic - 0x70 + payload_type
  startByte2: 0,
  numStartBytes: 1,
  encodesPayloadType: true,
};

const HEADER_BASIC_CONFIG = {
  headerType: HeaderType.BASIC,
  startByte1: BASIC_START_BYTE,  // 0x90, then dynamic 0x70 + payload_type
  startByte2: 0,
  numStartBytes: 2,
  encodesPayloadType: true,
};

const HEADER_UBX_CONFIG = {
  headerType: HeaderType.UBX,
  startByte1: UBX_SYNC1,  // 0xB5
  startByte2: UBX_SYNC2,  // 0x62
  numStartBytes: 2,
  encodesPayloadType: false,
};

const HEADER_MAVLINK_V1_CONFIG = {
  headerType: HeaderType.MAVLINK_V1,
  startByte1: MAVLINK_V1_STX,  // 0xFE
  startByte2: 0,
  numStartBytes: 1,
  encodesPayloadType: false,
};

const HEADER_MAVLINK_V2_CONFIG = {
  headerType: HeaderType.MAVLINK_V2,
  startByte1: MAVLINK_V2_STX,  // 0xFD
  startByte2: 0,
  numStartBytes: 1,
  encodesPayloadType: false,
};

module.exports = {
  HeaderType,
  BASIC_START_BYTE,
  PAYLOAD_TYPE_BASE,
  UBX_SYNC1,
  UBX_SYNC2,
  MAVLINK_V1_STX,
  MAVLINK_V2_STX,
  MAX_PAYLOAD_TYPE,
  HEADER_NONE_CONFIG,
  HEADER_TINY_CONFIG,
  HEADER_BASIC_CONFIG,
  HEADER_UBX_CONFIG,
  HEADER_MAVLINK_V1_CONFIG,
  HEADER_MAVLINK_V2_CONFIG,
};
