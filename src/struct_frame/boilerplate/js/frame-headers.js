"use strict";
/**
 * Frame Headers - Start byte patterns and header configurations (TypeScript)
 * Header types define start byte patterns and header-specific parsing
 *
 * This file mirrors the C++ frame_headers.hpp structure.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.HEADER_MAVLINK_V2_CONFIG = exports.HEADER_MAVLINK_V1_CONFIG = exports.HEADER_UBX_CONFIG = exports.HEADER_BASIC_CONFIG = exports.HEADER_TINY_CONFIG = exports.HEADER_NONE_CONFIG = exports.MAX_PAYLOAD_TYPE = exports.MAVLINK_V2_STX = exports.MAVLINK_V1_STX = exports.UBX_SYNC2 = exports.UBX_SYNC1 = exports.PAYLOAD_TYPE_BASE = exports.BASIC_START_BYTE = exports.HeaderType = void 0;
/** Header type enumeration */
var HeaderType;
(function (HeaderType) {
    HeaderType[HeaderType["NONE"] = 0] = "NONE";
    HeaderType[HeaderType["TINY"] = 1] = "TINY";
    HeaderType[HeaderType["BASIC"] = 2] = "BASIC";
    HeaderType[HeaderType["UBX"] = 3] = "UBX";
    HeaderType[HeaderType["MAVLINK_V1"] = 4] = "MAVLINK_V1";
    HeaderType[HeaderType["MAVLINK_V2"] = 5] = "MAVLINK_V2"; // 1 start byte [0xFD]
})(HeaderType || (exports.HeaderType = HeaderType = {}));
/** Constants used across headers */
exports.BASIC_START_BYTE = 0x90;
exports.PAYLOAD_TYPE_BASE = 0x70; // Payload type encoded as 0x70 + payload_type
exports.UBX_SYNC1 = 0xB5;
exports.UBX_SYNC2 = 0x62;
exports.MAVLINK_V1_STX = 0xFE;
exports.MAVLINK_V2_STX = 0xFD;
exports.MAX_PAYLOAD_TYPE = 8;
/** Pre-defined header configurations */
exports.HEADER_NONE_CONFIG = {
    headerType: HeaderType.NONE,
    startByte1: 0,
    startByte2: 0,
    numStartBytes: 0,
    encodesPayloadType: false,
};
exports.HEADER_TINY_CONFIG = {
    headerType: HeaderType.TINY,
    startByte1: 0, // Dynamic - 0x70 + payload_type
    startByte2: 0,
    numStartBytes: 1,
    encodesPayloadType: true,
};
exports.HEADER_BASIC_CONFIG = {
    headerType: HeaderType.BASIC,
    startByte1: exports.BASIC_START_BYTE, // 0x90, then dynamic 0x70 + payload_type
    startByte2: 0,
    numStartBytes: 2,
    encodesPayloadType: true,
};
exports.HEADER_UBX_CONFIG = {
    headerType: HeaderType.UBX,
    startByte1: exports.UBX_SYNC1, // 0xB5
    startByte2: exports.UBX_SYNC2, // 0x62
    numStartBytes: 2,
    encodesPayloadType: false,
};
exports.HEADER_MAVLINK_V1_CONFIG = {
    headerType: HeaderType.MAVLINK_V1,
    startByte1: exports.MAVLINK_V1_STX, // 0xFE
    startByte2: 0,
    numStartBytes: 1,
    encodesPayloadType: false,
};
exports.HEADER_MAVLINK_V2_CONFIG = {
    headerType: HeaderType.MAVLINK_V2,
    startByte1: exports.MAVLINK_V2_STX, // 0xFD
    startByte2: 0,
    numStartBytes: 1,
    encodesPayloadType: false,
};
