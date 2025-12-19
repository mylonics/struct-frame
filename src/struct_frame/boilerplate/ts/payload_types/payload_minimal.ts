// Payload Minimal (TypeScript)
// Format: [MSG_ID] [PACKET]

import { PayloadType, PayloadConfig } from './base';

export const PAYLOAD_MINIMAL_CONFIG: PayloadConfig = {
    payloadType: PayloadType.MINIMAL,
    name: 'Minimal',
    hasCrc: false,
    crcBytes: 0,
    hasLength: false,
    lengthBytes: 0,
    hasSequence: false,
    hasSystemId: false,
    hasComponentId: false,
    hasPackageId: false,
    description: '[MSG_ID] [PACKET] - Minimal format with no length field and no CRC.'
};
