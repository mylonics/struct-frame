// Header Basic - 2 start bytes with payload type encoding (JavaScript)

const { HeaderType, BASIC_START_BYTE, PAYLOAD_TYPE_BASE, MAX_PAYLOAD_TYPE } = require('./base');

const HEADER_BASIC_CONFIG = {
    headerType: HeaderType.BASIC,
    name: 'Basic',
    startBytes: [BASIC_START_BYTE],
    numStartBytes: 2,
    encodesPayloadType: true,
    payloadTypeByteIndex: 1,
    description: '2 start bytes [0x90] [0x70+PayloadType] - standard framing'
};

function getBasicSecondStartByte(payloadTypeValue) {
    return PAYLOAD_TYPE_BASE + payloadTypeValue;
}

function isBasicSecondStartByte(byte) {
    return byte >= PAYLOAD_TYPE_BASE && byte <= (PAYLOAD_TYPE_BASE + MAX_PAYLOAD_TYPE);
}

function getPayloadTypeFromBasic(byte) {
    return byte - PAYLOAD_TYPE_BASE;
}

module.exports = {
    HEADER_BASIC_CONFIG,
    getBasicSecondStartByte,
    isBasicSecondStartByte,
    getPayloadTypeFromBasic
};
