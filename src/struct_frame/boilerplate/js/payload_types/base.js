// Base definitions for payload types (JavaScript)
// Payload types define message structure (length fields, CRC, extra fields)

const PayloadType = {
    MINIMAL: 0,
    DEFAULT: 1,
    EXTENDED_MSG_IDS: 2,
    EXTENDED_LENGTH: 3,
    EXTENDED: 4,
    SYS_COMP: 5,
    SEQ: 6,
    MULTI_SYSTEM_STREAM: 7,
    EXTENDED_MULTI_SYSTEM_STREAM: 8
};

const MAX_PAYLOAD_TYPE_VALUE = 8;

function payloadConfigHeaderSize(config) {
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

function payloadConfigFooterSize(config) {
    return config.crcBytes;
}

function payloadConfigOverhead(config) {
    return payloadConfigHeaderSize(config) + payloadConfigFooterSize(config);
}

module.exports = {
    PayloadType,
    MAX_PAYLOAD_TYPE_VALUE,
    payloadConfigHeaderSize,
    payloadConfigFooterSize,
    payloadConfigOverhead
};
