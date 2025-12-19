// Header Basic - 2 start bytes with payload type encoding (TypeScript)
// Format: [0x90] [0x70+PayloadType]

import { HeaderType, HeaderConfig, BASIC_START_BYTE, PAYLOAD_TYPE_BASE, MAX_PAYLOAD_TYPE } from './base';

export const HEADER_BASIC_CONFIG: HeaderConfig = {
    headerType: HeaderType.BASIC,
    name: 'Basic',
    startBytes: [BASIC_START_BYTE],  // First byte fixed, second dynamic
    numStartBytes: 2,
    encodesPayloadType: true,
    payloadTypeByteIndex: 1,
    description: '2 start bytes [0x90] [0x70+PayloadType] - standard framing'
};

export function getBasicSecondStartByte(payloadTypeValue: number): number {
    return PAYLOAD_TYPE_BASE + payloadTypeValue;
}

export function isBasicSecondStartByte(byte: number): boolean {
    return byte >= PAYLOAD_TYPE_BASE && byte <= (PAYLOAD_TYPE_BASE + MAX_PAYLOAD_TYPE);
}

export function getPayloadTypeFromBasic(byte: number): number {
    return byte - PAYLOAD_TYPE_BASE;
}
