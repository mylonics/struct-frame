// Base definitions for payload types (TypeScript)
// Payload types define message structure (length fields, CRC, extra fields)

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

export const MAX_PAYLOAD_TYPE_VALUE = 8;

export interface PayloadConfig {
    readonly payloadType: PayloadType;
    readonly name: string;
    readonly hasCrc: boolean;
    readonly crcBytes: number;
    readonly hasLength: boolean;
    readonly lengthBytes: number;  // 1 or 2
    readonly hasSequence: boolean;
    readonly hasSystemId: boolean;
    readonly hasComponentId: boolean;
    readonly hasPackageId: boolean;
    readonly description: string;
}

export function payloadConfigHeaderSize(config: PayloadConfig): number {
    let size = 1;  // msg_id
    if (config.hasLength) {
        size += config.lengthBytes;
    }
    if (config.hasSequence) {
        size += 1;
    }
    if (config.hasSystemId) {
        size += 1;
    }
    if (config.hasComponentId) {
        size += 1;
    }
    if (config.hasPackageId) {
        size += 1;
    }
    return size;
}

export function payloadConfigFooterSize(config: PayloadConfig): number {
    return config.crcBytes;
}

export function payloadConfigOverhead(config: PayloadConfig): number {
    return payloadConfigHeaderSize(config) + payloadConfigFooterSize(config);
}
