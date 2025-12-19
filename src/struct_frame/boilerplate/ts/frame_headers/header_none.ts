// Header None - No start bytes (TypeScript)
// Format: No start bytes, payload begins immediately

import { HeaderType, HeaderConfig } from './base';

export const HEADER_NONE_CONFIG: HeaderConfig = {
    headerType: HeaderType.NONE,
    name: 'None',
    startBytes: [],
    numStartBytes: 0,
    encodesPayloadType: false,
    payloadTypeByteIndex: -1,
    description: 'No start bytes - payload begins immediately (requires external sync)'
};
