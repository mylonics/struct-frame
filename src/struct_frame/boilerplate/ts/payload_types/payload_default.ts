// Payload Default (TypeScript)
// Format: [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]

import { PayloadType, PayloadConfig } from './base';

export const PAYLOAD_DEFAULT_CONFIG: PayloadConfig = {
    payloadType: PayloadType.DEFAULT,
    name: 'Default',
    hasCrc: true,
    crcBytes: 2,
    hasLength: true,
    lengthBytes: 1,
    hasSequence: false,
    hasSystemId: false,
    hasComponentId: false,
    hasPackageId: false,
    description: '[LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Standard format with 1-byte length and CRC.'
};
