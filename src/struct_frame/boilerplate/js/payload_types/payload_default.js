// Payload Default (JavaScript)

const { PayloadType } = require('./base');

const PAYLOAD_DEFAULT_CONFIG = {
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

module.exports = {
    PAYLOAD_DEFAULT_CONFIG
};
