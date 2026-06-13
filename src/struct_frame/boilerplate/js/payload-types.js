"use strict";
/**
 * Payload Types - Message structure configurations (TypeScript)
 * Payload types define message structure (length fields, CRC, extra fields)
 *
 * This file mirrors the C++ payload_types.hpp structure.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG = exports.PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG = exports.PAYLOAD_SEQ_CONFIG = exports.PAYLOAD_SYS_COMP_CONFIG = exports.PAYLOAD_EXTENDED_CONFIG = exports.PAYLOAD_EXTENDED_LENGTH_CONFIG = exports.PAYLOAD_EXTENDED_MSG_IDS_CONFIG = exports.PAYLOAD_DEFAULT_CONFIG = exports.PAYLOAD_MINIMAL_CONFIG = exports.MAX_PAYLOAD_TYPE_VALUE = exports.PayloadType = void 0;
exports.payloadHeaderSize = payloadHeaderSize;
exports.payloadFooterSize = payloadFooterSize;
exports.payloadOverhead = payloadOverhead;
exports.payloadMaxPayload = payloadMaxPayload;
/** Payload type enumeration */
var PayloadType;
(function (PayloadType) {
    PayloadType[PayloadType["MINIMAL"] = 0] = "MINIMAL";
    PayloadType[PayloadType["DEFAULT"] = 1] = "DEFAULT";
    PayloadType[PayloadType["EXTENDED_MSG_IDS"] = 2] = "EXTENDED_MSG_IDS";
    PayloadType[PayloadType["EXTENDED_LENGTH"] = 3] = "EXTENDED_LENGTH";
    PayloadType[PayloadType["EXTENDED"] = 4] = "EXTENDED";
    PayloadType[PayloadType["SYS_COMP"] = 5] = "SYS_COMP";
    PayloadType[PayloadType["SEQ"] = 6] = "SEQ";
    PayloadType[PayloadType["MULTI_SYSTEM_STREAM"] = 7] = "MULTI_SYSTEM_STREAM";
    PayloadType[PayloadType["EXTENDED_MULTI_SYSTEM_STREAM"] = 8] = "EXTENDED_MULTI_SYSTEM_STREAM"; // [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
})(PayloadType || (exports.PayloadType = PayloadType = {}));
/** Maximum payload type value (for range checking) */
exports.MAX_PAYLOAD_TYPE_VALUE = 8;
/** Calculate header size (fields before payload, excluding start bytes) */
function payloadHeaderSize(config) {
    let size = 1; // msg_id always present
    if (config.hasLength)
        size += config.lengthBytes;
    if (config.hasSeq)
        size += 1;
    if (config.hasSysId)
        size += 1;
    if (config.hasCompId)
        size += 1;
    if (config.hasPkgId)
        size += 1;
    return size;
}
/** Calculate footer size */
function payloadFooterSize(config) {
    return config.crcBytes;
}
/** Calculate total overhead (header + footer, excluding start bytes) */
function payloadOverhead(config) {
    return payloadHeaderSize(config) + payloadFooterSize(config);
}
/** Calculate max payload size based on length field */
function payloadMaxPayload(config) {
    if (config.lengthBytes === 1)
        return 255;
    if (config.lengthBytes === 2)
        return 65535;
    return 0; // No length field - requires external knowledge
}
/** Pre-defined payload configurations */
exports.PAYLOAD_MINIMAL_CONFIG = {
    payloadType: PayloadType.MINIMAL,
    hasCrc: false,
    crcBytes: 0,
    hasLength: false,
    lengthBytes: 0,
    hasSeq: false,
    hasSysId: false,
    hasCompId: false,
    hasPkgId: false,
};
exports.PAYLOAD_DEFAULT_CONFIG = {
    payloadType: PayloadType.DEFAULT,
    hasCrc: true,
    crcBytes: 2,
    hasLength: true,
    lengthBytes: 1,
    hasSeq: false,
    hasSysId: false,
    hasCompId: false,
    hasPkgId: false,
};
exports.PAYLOAD_EXTENDED_MSG_IDS_CONFIG = {
    payloadType: PayloadType.EXTENDED_MSG_IDS,
    hasCrc: true,
    crcBytes: 2,
    hasLength: true,
    lengthBytes: 1,
    hasSeq: false,
    hasSysId: false,
    hasCompId: false,
    hasPkgId: true,
};
exports.PAYLOAD_EXTENDED_LENGTH_CONFIG = {
    payloadType: PayloadType.EXTENDED_LENGTH,
    hasCrc: true,
    crcBytes: 2,
    hasLength: true,
    lengthBytes: 2,
    hasSeq: false,
    hasSysId: false,
    hasCompId: false,
    hasPkgId: false,
};
exports.PAYLOAD_EXTENDED_CONFIG = {
    payloadType: PayloadType.EXTENDED,
    hasCrc: true,
    crcBytes: 2,
    hasLength: true,
    lengthBytes: 2,
    hasSeq: false,
    hasSysId: false,
    hasCompId: false,
    hasPkgId: true,
};
exports.PAYLOAD_SYS_COMP_CONFIG = {
    payloadType: PayloadType.SYS_COMP,
    hasCrc: true,
    crcBytes: 2,
    hasLength: true,
    lengthBytes: 1,
    hasSeq: false,
    hasSysId: true,
    hasCompId: true,
    hasPkgId: false,
};
exports.PAYLOAD_SEQ_CONFIG = {
    payloadType: PayloadType.SEQ,
    hasCrc: true,
    crcBytes: 2,
    hasLength: true,
    lengthBytes: 1,
    hasSeq: true,
    hasSysId: false,
    hasCompId: false,
    hasPkgId: false,
};
exports.PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG = {
    payloadType: PayloadType.MULTI_SYSTEM_STREAM,
    hasCrc: true,
    crcBytes: 2,
    hasLength: true,
    lengthBytes: 1,
    hasSeq: true,
    hasSysId: true,
    hasCompId: true,
    hasPkgId: false,
};
exports.PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG = {
    payloadType: PayloadType.EXTENDED_MULTI_SYSTEM_STREAM,
    hasCrc: true,
    crcBytes: 2,
    hasLength: true,
    lengthBytes: 2,
    hasSeq: true,
    hasSysId: true,
    hasCompId: true,
    hasPkgId: true,
};
