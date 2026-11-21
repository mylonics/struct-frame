"use strict";
// Struct-frame boilerplate: frame parser package
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.ProfileBulkConfig = exports.ProfileIPCConfig = exports.ProfileSensorConfig = exports.ProfileStandardConfig = exports.profileOverhead = exports.profileFooterSize = exports.profileHeaderSize = exports.createProfileConfig = exports.PAYLOAD_SYSTEM_CONFIG = exports.PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG = exports.PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG = exports.PAYLOAD_SEQ_CONFIG = exports.PAYLOAD_SYS_COMP_CONFIG = exports.PAYLOAD_EXTENDED_CONFIG = exports.PAYLOAD_EXTENDED_LENGTH_CONFIG = exports.PAYLOAD_EXTENDED_MSG_IDS_CONFIG = exports.PAYLOAD_DEFAULT_CONFIG = exports.PAYLOAD_MINIMAL_CONFIG = exports.payloadMaxPayload = exports.payloadOverhead = exports.payloadFooterSize = exports.payloadHeaderSize = exports.MAX_PAYLOAD_TYPE_VALUE = exports.PayloadType = exports.HEADER_MAVLINK_V2_CONFIG = exports.HEADER_MAVLINK_V1_CONFIG = exports.HEADER_UBX_CONFIG = exports.HEADER_BASIC_CONFIG = exports.HEADER_TINY_CONFIG = exports.HEADER_NONE_CONFIG = exports.MAX_PAYLOAD_TYPE = exports.MAVLINK_V2_STX = exports.MAVLINK_V1_STX = exports.UBX_SYNC2 = exports.UBX_SYNC1 = exports.PAYLOAD_TYPE_BASE = exports.BASIC_START_BYTE = exports.HeaderType = exports.encodePayloadMinimal = exports.encodePayloadWithCrc = exports.validatePayloadMinimal = exports.validatePayloadWithCrc = exports.createFrameParserClass = exports.GenericParserState = exports.GenericFrameParser = exports.fletcherChecksumExt = exports.fletcherChecksum = exports.createFrameMsgInfo = exports.FrameMsgStatus = exports.MessageBase = void 0;
exports.sfSystem = exports.decodeSystemMessage = exports.encodeSystemMessage = exports.systemMessageClass = exports.systemMessageInfo = exports.systemProfileConfig = exports.supportsSystemFrames = exports.SYSTEM_TAIL_MESSAGES = exports.SYSTEM_MAX_TAIL = exports.SYSTEM_START_BYTE = exports.SYSTEM_PAYLOAD_TYPE_VALUE = exports.AccumulatingReaderState = exports.AccumulatingReader = exports.BufferWriter = exports.BufferReader = exports.parseFrameMinimal = exports.parseFrameWithCrc = exports.encodeMessage = exports.ProfileNetworkConfig = void 0;
// Struct base class for message types
var struct_base_1 = require("./struct-base");
Object.defineProperty(exports, "MessageBase", { enumerable: true, get: function () { return struct_base_1.MessageBase; } });
var frame_base_1 = require("./frame-base");
Object.defineProperty(exports, "FrameMsgStatus", { enumerable: true, get: function () { return frame_base_1.FrameMsgStatus; } });
Object.defineProperty(exports, "createFrameMsgInfo", { enumerable: true, get: function () { return frame_base_1.createFrameMsgInfo; } });
Object.defineProperty(exports, "fletcherChecksum", { enumerable: true, get: function () { return frame_base_1.fletcherChecksum; } });
Object.defineProperty(exports, "fletcherChecksumExt", { enumerable: true, get: function () { return frame_base_1.fletcherChecksumExt; } });
// Generic parser class (use createFrameParserClass for type-safe wrappers)
Object.defineProperty(exports, "GenericFrameParser", { enumerable: true, get: function () { return frame_base_1.GenericFrameParser; } });
Object.defineProperty(exports, "GenericParserState", { enumerable: true, get: function () { return frame_base_1.GenericParserState; } });
Object.defineProperty(exports, "createFrameParserClass", { enumerable: true, get: function () { return frame_base_1.createFrameParserClass; } });
// Shared payload parsing functions
Object.defineProperty(exports, "validatePayloadWithCrc", { enumerable: true, get: function () { return frame_base_1.validatePayloadWithCrc; } });
Object.defineProperty(exports, "validatePayloadMinimal", { enumerable: true, get: function () { return frame_base_1.validatePayloadMinimal; } });
Object.defineProperty(exports, "encodePayloadWithCrc", { enumerable: true, get: function () { return frame_base_1.encodePayloadWithCrc; } });
Object.defineProperty(exports, "encodePayloadMinimal", { enumerable: true, get: function () { return frame_base_1.encodePayloadMinimal; } });
var frame_headers_1 = require("./frame-headers");
Object.defineProperty(exports, "HeaderType", { enumerable: true, get: function () { return frame_headers_1.HeaderType; } });
Object.defineProperty(exports, "BASIC_START_BYTE", { enumerable: true, get: function () { return frame_headers_1.BASIC_START_BYTE; } });
Object.defineProperty(exports, "PAYLOAD_TYPE_BASE", { enumerable: true, get: function () { return frame_headers_1.PAYLOAD_TYPE_BASE; } });
Object.defineProperty(exports, "UBX_SYNC1", { enumerable: true, get: function () { return frame_headers_1.UBX_SYNC1; } });
Object.defineProperty(exports, "UBX_SYNC2", { enumerable: true, get: function () { return frame_headers_1.UBX_SYNC2; } });
Object.defineProperty(exports, "MAVLINK_V1_STX", { enumerable: true, get: function () { return frame_headers_1.MAVLINK_V1_STX; } });
Object.defineProperty(exports, "MAVLINK_V2_STX", { enumerable: true, get: function () { return frame_headers_1.MAVLINK_V2_STX; } });
Object.defineProperty(exports, "MAX_PAYLOAD_TYPE", { enumerable: true, get: function () { return frame_headers_1.MAX_PAYLOAD_TYPE; } });
Object.defineProperty(exports, "HEADER_NONE_CONFIG", { enumerable: true, get: function () { return frame_headers_1.HEADER_NONE_CONFIG; } });
Object.defineProperty(exports, "HEADER_TINY_CONFIG", { enumerable: true, get: function () { return frame_headers_1.HEADER_TINY_CONFIG; } });
Object.defineProperty(exports, "HEADER_BASIC_CONFIG", { enumerable: true, get: function () { return frame_headers_1.HEADER_BASIC_CONFIG; } });
Object.defineProperty(exports, "HEADER_UBX_CONFIG", { enumerable: true, get: function () { return frame_headers_1.HEADER_UBX_CONFIG; } });
Object.defineProperty(exports, "HEADER_MAVLINK_V1_CONFIG", { enumerable: true, get: function () { return frame_headers_1.HEADER_MAVLINK_V1_CONFIG; } });
Object.defineProperty(exports, "HEADER_MAVLINK_V2_CONFIG", { enumerable: true, get: function () { return frame_headers_1.HEADER_MAVLINK_V2_CONFIG; } });
var payload_types_1 = require("./payload-types");
Object.defineProperty(exports, "PayloadType", { enumerable: true, get: function () { return payload_types_1.PayloadType; } });
Object.defineProperty(exports, "MAX_PAYLOAD_TYPE_VALUE", { enumerable: true, get: function () { return payload_types_1.MAX_PAYLOAD_TYPE_VALUE; } });
Object.defineProperty(exports, "payloadHeaderSize", { enumerable: true, get: function () { return payload_types_1.payloadHeaderSize; } });
Object.defineProperty(exports, "payloadFooterSize", { enumerable: true, get: function () { return payload_types_1.payloadFooterSize; } });
Object.defineProperty(exports, "payloadOverhead", { enumerable: true, get: function () { return payload_types_1.payloadOverhead; } });
Object.defineProperty(exports, "payloadMaxPayload", { enumerable: true, get: function () { return payload_types_1.payloadMaxPayload; } });
Object.defineProperty(exports, "PAYLOAD_MINIMAL_CONFIG", { enumerable: true, get: function () { return payload_types_1.PAYLOAD_MINIMAL_CONFIG; } });
Object.defineProperty(exports, "PAYLOAD_DEFAULT_CONFIG", { enumerable: true, get: function () { return payload_types_1.PAYLOAD_DEFAULT_CONFIG; } });
Object.defineProperty(exports, "PAYLOAD_EXTENDED_MSG_IDS_CONFIG", { enumerable: true, get: function () { return payload_types_1.PAYLOAD_EXTENDED_MSG_IDS_CONFIG; } });
Object.defineProperty(exports, "PAYLOAD_EXTENDED_LENGTH_CONFIG", { enumerable: true, get: function () { return payload_types_1.PAYLOAD_EXTENDED_LENGTH_CONFIG; } });
Object.defineProperty(exports, "PAYLOAD_EXTENDED_CONFIG", { enumerable: true, get: function () { return payload_types_1.PAYLOAD_EXTENDED_CONFIG; } });
Object.defineProperty(exports, "PAYLOAD_SYS_COMP_CONFIG", { enumerable: true, get: function () { return payload_types_1.PAYLOAD_SYS_COMP_CONFIG; } });
Object.defineProperty(exports, "PAYLOAD_SEQ_CONFIG", { enumerable: true, get: function () { return payload_types_1.PAYLOAD_SEQ_CONFIG; } });
Object.defineProperty(exports, "PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG", { enumerable: true, get: function () { return payload_types_1.PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG; } });
Object.defineProperty(exports, "PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG", { enumerable: true, get: function () { return payload_types_1.PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG; } });
Object.defineProperty(exports, "PAYLOAD_SYSTEM_CONFIG", { enumerable: true, get: function () { return payload_types_1.PAYLOAD_SYSTEM_CONFIG; } });
var frame_profiles_1 = require("./frame-profiles");
// Profile helper functions
Object.defineProperty(exports, "createProfileConfig", { enumerable: true, get: function () { return frame_profiles_1.createProfileConfig; } });
Object.defineProperty(exports, "profileHeaderSize", { enumerable: true, get: function () { return frame_profiles_1.profileHeaderSize; } });
Object.defineProperty(exports, "profileFooterSize", { enumerable: true, get: function () { return frame_profiles_1.profileFooterSize; } });
Object.defineProperty(exports, "profileOverhead", { enumerable: true, get: function () { return frame_profiles_1.profileOverhead; } });
// Profile configurations
Object.defineProperty(exports, "ProfileStandardConfig", { enumerable: true, get: function () { return frame_profiles_1.ProfileStandardConfig; } });
Object.defineProperty(exports, "ProfileSensorConfig", { enumerable: true, get: function () { return frame_profiles_1.ProfileSensorConfig; } });
Object.defineProperty(exports, "ProfileIPCConfig", { enumerable: true, get: function () { return frame_profiles_1.ProfileIPCConfig; } });
Object.defineProperty(exports, "ProfileBulkConfig", { enumerable: true, get: function () { return frame_profiles_1.ProfileBulkConfig; } });
Object.defineProperty(exports, "ProfileNetworkConfig", { enumerable: true, get: function () { return frame_profiles_1.ProfileNetworkConfig; } });
// Generic encode/parse functions
Object.defineProperty(exports, "encodeMessage", { enumerable: true, get: function () { return frame_profiles_1.encodeMessage; } });
Object.defineProperty(exports, "parseFrameWithCrc", { enumerable: true, get: function () { return frame_profiles_1.parseFrameWithCrc; } });
Object.defineProperty(exports, "parseFrameMinimal", { enumerable: true, get: function () { return frame_profiles_1.parseFrameMinimal; } });
// BufferReader/BufferWriter/AccumulatingReader base classes
Object.defineProperty(exports, "BufferReader", { enumerable: true, get: function () { return frame_profiles_1.BufferReader; } });
Object.defineProperty(exports, "BufferWriter", { enumerable: true, get: function () { return frame_profiles_1.BufferWriter; } });
Object.defineProperty(exports, "AccumulatingReader", { enumerable: true, get: function () { return frame_profiles_1.AccumulatingReader; } });
Object.defineProperty(exports, "AccumulatingReaderState", { enumerable: true, get: function () { return frame_profiles_1.AccumulatingReaderState; } });
var system_frames_1 = require("./system-frames");
Object.defineProperty(exports, "SYSTEM_PAYLOAD_TYPE_VALUE", { enumerable: true, get: function () { return system_frames_1.SYSTEM_PAYLOAD_TYPE_VALUE; } });
Object.defineProperty(exports, "SYSTEM_START_BYTE", { enumerable: true, get: function () { return system_frames_1.SYSTEM_START_BYTE; } });
Object.defineProperty(exports, "SYSTEM_MAX_TAIL", { enumerable: true, get: function () { return system_frames_1.MAX_TAIL; } });
Object.defineProperty(exports, "SYSTEM_TAIL_MESSAGES", { enumerable: true, get: function () { return system_frames_1.TAIL_MESSAGES; } });
Object.defineProperty(exports, "supportsSystemFrames", { enumerable: true, get: function () { return system_frames_1.supportsSystemFrames; } });
Object.defineProperty(exports, "systemProfileConfig", { enumerable: true, get: function () { return system_frames_1.systemProfileConfig; } });
Object.defineProperty(exports, "systemMessageInfo", { enumerable: true, get: function () { return system_frames_1.systemMessageInfo; } });
Object.defineProperty(exports, "systemMessageClass", { enumerable: true, get: function () { return system_frames_1.systemMessageClass; } });
Object.defineProperty(exports, "encodeSystemMessage", { enumerable: true, get: function () { return system_frames_1.encodeSystemMessage; } });
Object.defineProperty(exports, "decodeSystemMessage", { enumerable: true, get: function () { return system_frames_1.decodeSystemMessage; } });
exports.sfSystem = __importStar(require("./sf-system.structframe"));
