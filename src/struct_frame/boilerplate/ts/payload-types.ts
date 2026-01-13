/**
 * Payload Types - Message structure configurations (TypeScript)
 * Payload types define message structure (length fields, CRC, extra fields)
 *
 * This file mirrors the C++ payload_types.hpp structure.
 */

/** Payload type enumeration */
export enum PayloadType {
    MINIMAL = 0,                      // [MSG_ID] [PACKET]
    DEFAULT = 1,                      // [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
    EXTENDED_MSG_IDS = 2,             // [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
    EXTENDED_LENGTH = 3,              // [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2]
    EXTENDED = 4,                     // [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
    SYS_COMP = 5,                     // [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
    SEQ = 6,                          // [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
    MULTI_SYSTEM_STREAM = 7,          // [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
    EXTENDED_MULTI_SYSTEM_STREAM = 8  // [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
}

/** Maximum payload type value (for range checking) */
export const MAX_PAYLOAD_TYPE_VALUE = 8;

/**
 * Configuration for a payload type.
 */
export interface PayloadConfig {
    readonly payloadType: PayloadType;
    readonly hasCrc: boolean;
    readonly crcBytes: number;        // 0 or 2
    readonly hasLength: boolean;
    readonly lengthBytes: number;     // 0, 1, or 2
    readonly hasSeq: boolean;
    readonly hasSysId: boolean;
    readonly hasCompId: boolean;
    readonly hasPkgId: boolean;
}

/** Calculate header size (fields before payload, excluding start bytes) */
export function payloadHeaderSize(config: PayloadConfig): number {
    let size = 1;  // msg_id always present
    if (config.hasLength) size += config.lengthBytes;
    if (config.hasSeq) size += 1;
    if (config.hasSysId) size += 1;
    if (config.hasCompId) size += 1;
    if (config.hasPkgId) size += 1;
    return size;
}

/** Calculate footer size */
export function payloadFooterSize(config: PayloadConfig): number {
    return config.crcBytes;
}

/** Calculate total overhead (header + footer, excluding start bytes) */
export function payloadOverhead(config: PayloadConfig): number {
    return payloadHeaderSize(config) + payloadFooterSize(config);
}

/** Calculate max payload size based on length field */
export function payloadMaxPayload(config: PayloadConfig): number {
    if (config.lengthBytes === 1) return 255;
    if (config.lengthBytes === 2) return 65535;
    return 0;  // No length field - requires external knowledge
}

/** Pre-defined payload configurations */
export const PAYLOAD_MINIMAL_CONFIG: PayloadConfig = {
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

export const PAYLOAD_DEFAULT_CONFIG: PayloadConfig = {
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

export const PAYLOAD_EXTENDED_MSG_IDS_CONFIG: PayloadConfig = {
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

export const PAYLOAD_EXTENDED_LENGTH_CONFIG: PayloadConfig = {
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

export const PAYLOAD_EXTENDED_CONFIG: PayloadConfig = {
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

export const PAYLOAD_SYS_COMP_CONFIG: PayloadConfig = {
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

export const PAYLOAD_SEQ_CONFIG: PayloadConfig = {
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

export const PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG: PayloadConfig = {
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

export const PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG: PayloadConfig = {
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
