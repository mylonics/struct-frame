// Base definitions for frame headers (JavaScript)
// Header types define start byte patterns and header-specific parsing

const HeaderType = {
    NONE: 0,       // No start bytes
    TINY: 1,       // 1 start byte [0x70+PayloadType]
    BASIC: 2,      // 2 start bytes [0x90] [0x70+PayloadType]
    UBX: 3,        // 2 start bytes [0xB5] [0x62]
    MAVLINK_V1: 4, // 1 start byte [0xFE]
    MAVLINK_V2: 5  // 1 start byte [0xFD]
};

// Constants used across headers
const BASIC_START_BYTE = 0x90;
const PAYLOAD_TYPE_BASE = 0x70;
const UBX_SYNC1 = 0xB5;
const UBX_SYNC2 = 0x62;
const MAVLINK_V1_STX = 0xFE;
const MAVLINK_V2_STX = 0xFD;
const MAX_PAYLOAD_TYPE = 8;

module.exports = {
    HeaderType,
    BASIC_START_BYTE,
    PAYLOAD_TYPE_BASE,
    UBX_SYNC1,
    UBX_SYNC2,
    MAVLINK_V1_STX,
    MAVLINK_V2_STX,
    MAX_PAYLOAD_TYPE
};
