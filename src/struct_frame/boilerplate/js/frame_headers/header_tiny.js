// Header Tiny - 1 start byte encoding payload type (JavaScript)

const { HeaderType, PAYLOAD_TYPE_BASE, MAX_PAYLOAD_TYPE } = require('./base');

const HEADER_TINY_CONFIG = {
    headerType: HeaderType.TINY,
    name: 'Tiny',
    startBytes: [],
    numStartBytes: 1,
    encodesPayloadType: true,
    payloadTypeByteIndex: 0,
    description: '1 start byte [0x70+PayloadType] - compact framing'
};

function getTinyStartByte(payloadTypeValue) {
    return PAYLOAD_TYPE_BASE + payloadTypeValue;
}

function isTinyStartByte(byte) {
    return byte >= PAYLOAD_TYPE_BASE && byte <= (PAYLOAD_TYPE_BASE + MAX_PAYLOAD_TYPE);
}

function getPayloadTypeFromTiny(byte) {
    return byte - PAYLOAD_TYPE_BASE;
}

module.exports = {
    HEADER_TINY_CONFIG,
    getTinyStartByte,
    isTinyStartByte,
    getPayloadTypeFromTiny
};
