// Header Tiny - 1 start byte encoding payload type (TypeScript)
// Format: [0x70+PayloadType]

import { HeaderType, HeaderConfig, PAYLOAD_TYPE_BASE, MAX_PAYLOAD_TYPE } from './base';

export const HEADER_TINY_CONFIG: HeaderConfig = {
    headerType: HeaderType.TINY,
    name: 'Tiny',
    startBytes: [],  // Dynamic - depends on payload type
    numStartBytes: 1,
    encodesPayloadType: true,
    payloadTypeByteIndex: 0,
    description: '1 start byte [0x70+PayloadType] - compact framing'
};

export function getTinyStartByte(payloadTypeValue: number): number {
    return PAYLOAD_TYPE_BASE + payloadTypeValue;
}

export function isTinyStartByte(byte: number): boolean {
    return byte >= PAYLOAD_TYPE_BASE && byte <= (PAYLOAD_TYPE_BASE + MAX_PAYLOAD_TYPE);
}

export function getPayloadTypeFromTiny(byte: number): number {
    return byte - PAYLOAD_TYPE_BASE;
}
