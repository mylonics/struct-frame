// Base definitions for frame headers (TypeScript)
// Header types define start byte patterns and header-specific parsing

export enum HeaderType {
    NONE = 0,       // No start bytes
    TINY = 1,       // 1 start byte [0x70+PayloadType]
    BASIC = 2,      // 2 start bytes [0x90] [0x70+PayloadType]
    UBX = 3,        // 2 start bytes [0xB5] [0x62]
    MAVLINK_V1 = 4, // 1 start byte [0xFE]
    MAVLINK_V2 = 5  // 1 start byte [0xFD]
}

export interface HeaderConfig {
    readonly headerType: HeaderType;
    readonly name: string;
    readonly startBytes: readonly number[];  // Fixed start bytes (empty for dynamic)
    readonly numStartBytes: number;           // Number of start bytes (0, 1, or 2)
    readonly encodesPayloadType: boolean;     // True if start byte encodes payload type
    readonly payloadTypeByteIndex: number;    // Which byte encodes payload type (-1 if none)
    readonly description: string;
}

// Constants used across headers
export const BASIC_START_BYTE = 0x90;
export const PAYLOAD_TYPE_BASE = 0x70;  // Payload type encoded as 0x70 + payload_type
export const UBX_SYNC1 = 0xB5;
export const UBX_SYNC2 = 0x62;
export const MAVLINK_V1_STX = 0xFE;
export const MAVLINK_V2_STX = 0xFD;
export const MAX_PAYLOAD_TYPE = 8;
