/**
 * Frame Headers - Start byte patterns and header configurations (TypeScript)
 * Header types define start byte patterns and header-specific parsing
 *
 * This file mirrors the C++ frame_headers.hpp structure.
 */

/** Header type enumeration */
export enum HeaderType {
    NONE = 0,       // No start bytes
    TINY = 1,       // 1 start byte [0x70+PayloadType]
    BASIC = 2,      // 2 start bytes [0x90] [0x70+PayloadType]
    UBX = 3,        // 2 start bytes [0xB5] [0x62]
    MAVLINK_V1 = 4, // 1 start byte [0xFE]
    MAVLINK_V2 = 5  // 1 start byte [0xFD]
}

/** Constants used across headers */
export const BASIC_START_BYTE = 0x90;
export const PAYLOAD_TYPE_BASE = 0x70;  // Payload type encoded as 0x70 + payload_type
export const UBX_SYNC1 = 0xB5;
export const UBX_SYNC2 = 0x62;
export const MAVLINK_V1_STX = 0xFE;
export const MAVLINK_V2_STX = 0xFD;
export const MAX_PAYLOAD_TYPE = 8;

/**
 * Configuration for a header type.
 */
export interface HeaderConfig {
    readonly headerType: HeaderType;
    readonly startByte1: number;         // First start byte (0 if none or dynamic)
    readonly startByte2: number;         // Second start byte (0 if none or dynamic)
    readonly numStartBytes: number;      // Number of start bytes (0, 1, or 2)
    readonly encodesPayloadType: boolean; // True if start byte encodes payload type
}

/** Pre-defined header configurations */
export const HEADER_NONE_CONFIG: HeaderConfig = {
    headerType: HeaderType.NONE,
    startByte1: 0,
    startByte2: 0,
    numStartBytes: 0,
    encodesPayloadType: false,
};

export const HEADER_TINY_CONFIG: HeaderConfig = {
    headerType: HeaderType.TINY,
    startByte1: 0,  // Dynamic - 0x70 + payload_type
    startByte2: 0,
    numStartBytes: 1,
    encodesPayloadType: true,
};

export const HEADER_BASIC_CONFIG: HeaderConfig = {
    headerType: HeaderType.BASIC,
    startByte1: BASIC_START_BYTE,  // 0x90, then dynamic 0x70 + payload_type
    startByte2: 0,
    numStartBytes: 2,
    encodesPayloadType: true,
};

export const HEADER_UBX_CONFIG: HeaderConfig = {
    headerType: HeaderType.UBX,
    startByte1: UBX_SYNC1,  // 0xB5
    startByte2: UBX_SYNC2,  // 0x62
    numStartBytes: 2,
    encodesPayloadType: false,
};

export const HEADER_MAVLINK_V1_CONFIG: HeaderConfig = {
    headerType: HeaderType.MAVLINK_V1,
    startByte1: MAVLINK_V1_STX,  // 0xFE
    startByte2: 0,
    numStartBytes: 1,
    encodesPayloadType: false,
};

export const HEADER_MAVLINK_V2_CONFIG: HeaderConfig = {
    headerType: HeaderType.MAVLINK_V2,
    startByte1: MAVLINK_V2_STX,  // 0xFD
    startByte2: 0,
    numStartBytes: 1,
    encodesPayloadType: false,
};
