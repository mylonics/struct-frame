// Payload Minimal (JavaScript)

const { PayloadType } = require('./base');

const PAYLOAD_MINIMAL_CONFIG = {
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

module.exports = {
    PAYLOAD_MINIMAL_CONFIG
};
