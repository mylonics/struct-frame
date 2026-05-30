// Struct-frame boilerplate: frame parser base utilities
// NOTE: This file is the JavaScript twin of boilerplate/ts/frame-base.ts. Any algorithm
// fix to GenericFrameParser or related helpers MUST also be applied to the TypeScript source.


// Fletcher-16 checksum calculation
function fletcherChecksum(buffer, start = 0, end = undefined, init1 = 0, init2 = 0) {
    if (end === undefined) {
        end = buffer.length;
    }

    let byte1 = 0;
    let byte2 = 0;

    for (let i = start; i < end; i++) {
        byte1 = (byte1 + buffer[i]) % 256;
        byte2 = (byte2 + byte1) % 256;
    }

    // Add magic numbers at the end
    byte1 = (byte1 + init1) % 256;
    byte2 = (byte2 + byte1) % 256;
    byte1 = (byte1 + init2) % 256;
    byte2 = (byte2 + byte1) % 256;

    return [byte1, byte2];
}

// Extension-aware Fletcher-16 checksum.
// Computes: Fletcher(buffer[start:baseEnd]) -> mix magic1/magic2 -> Fletcher(buffer[baseEnd:end]).
// When baseEnd == end the result is identical to fletcherChecksum.
function fletcherChecksumExt(buffer, start, baseEnd, end, init1 = 0, init2 = 0) {
    let byte1 = 0;
    let byte2 = 0;
    for (let i = start; i < baseEnd; i++) {
        byte1 = (byte1 + buffer[i]) % 256;
        byte2 = (byte2 + byte1) % 256;
    }
    byte1 = (byte1 + init1) % 256;
    byte2 = (byte2 + byte1) % 256;
    byte1 = (byte1 + init2) % 256;
    byte2 = (byte2 + byte1) % 256;
    for (let i = baseEnd; i < end; i++) {
        byte1 = (byte1 + buffer[i]) % 256;
        byte2 = (byte2 + byte1) % 256;
    }
    return [byte1, byte2];
}

// Create default FrameMsgInfo
function createFrameMsgInfo() {
    return {
        valid: false,
        msgId: 0,
        msgLen: 0,
        msgData: new Uint8Array(0)
    };
}

// =============================================================================
// Shared Payload Parsing Functions
// =============================================================================
// These functions handle payload validation/encoding independent of framing.
// Frame formats (Tiny/Basic) use these for the common parsing logic.

/**
 * Validate a payload with CRC (shared by Default, Extended, etc. payload types).
 */
function validatePayloadWithCrc(buffer, headerSize, lengthBytes, crcStartOffset) {
    const result = createFrameMsgInfo();
    const footerSize = 2; // CRC is always 2 bytes
    const overhead = headerSize + footerSize;

    if (buffer.length < overhead) {
        return result;
    }

    const msgLength = buffer.length - overhead;

    // Calculate expected CRC range: from crcStartOffset to before the CRC bytes
    const crcDataLen = msgLength + 1 + lengthBytes; // msg_id (1) + lengthBytes + payload
    const ck = fletcherChecksum(buffer, crcStartOffset, crcStartOffset + crcDataLen);

    if (ck[0] === buffer[buffer.length - 2] && ck[1] === buffer[buffer.length - 1]) {
        result.valid = true;
        result.msgId = buffer[headerSize - 1]; // msg_id is last byte of header
        result.msgLen = msgLength;
        result.msgData = new Uint8Array(Array.prototype.slice.call(buffer, headerSize, buffer.length - footerSize));
    }

    return result;
}

/**
 * Validate a minimal payload (no CRC, no length field).
 */
function validatePayloadMinimal(buffer, headerSize) {
    const result = createFrameMsgInfo();

    if (buffer.length < headerSize) {
        return result;
    }

    result.valid = true;
    result.msgId = buffer[headerSize - 1]; // msg_id is last byte of header
    result.msgLen = buffer.length - headerSize;
    result.msgData = new Uint8Array(Array.prototype.slice.call(buffer, headerSize));

    return result;
}

/**
 * Encode payload with length and CRC (modifies output array in place).
 */
function encodePayloadWithCrc(output, msgId, msg, lengthBytes, crcStartOffset) {
    // Add length field
    if (lengthBytes === 1) {
        output.push(msg.length & 0xFF);
    } else {
        output.push(msg.length & 0xFF);
        output.push((msg.length >> 8) & 0xFF);
    }

    // Add msg_id
    output.push(msgId);

    // Add payload
    for (let i = 0; i < msg.length; i++) {
        output.push(msg[i]);
    }

    // Calculate and add CRC
    const crcDataLen = msg.length + 1 + lengthBytes;
    const ck = fletcherChecksum(output, crcStartOffset, crcStartOffset + crcDataLen);
    output.push(ck[0]);
    output.push(ck[1]);
}

/**
 * Encode minimal payload (no length, no CRC).
 */
function encodePayloadMinimal(output, msgId, msg) {
    output.push(msgId);
    for (let i = 0; i < msg.length; i++) {
        output.push(msg[i]);
    }
}

// =============================================================================
// Generic Frame Parser
// =============================================================================
// This class provides a reusable frame parser that can be configured
// for different frame formats, reducing code duplication.

/** Parser state enumeration */
const GenericParserState = {
    LOOKING_FOR_START1: 0,
    LOOKING_FOR_START2: 1,
    GETTING_MSG_ID: 2,
    GETTING_LENGTH: 3,
    GETTING_PAYLOAD: 4
};

/**
 * Generic frame parser that works with any frame format configuration.
 * This class eliminates the need for separate parser classes per format.
 */
class GenericFrameParser {
    constructor(config, getMsgLength = undefined) {
        this.config = config;
        this.getMsgLength = getMsgLength;
        this.state = this._getInitialState();
        this.buffer = [];
        this.packetSize = 0;
        this.msgId = 0;
        this.msgLength = 0;
        this.lengthLo = 0;
    }

    _getInitialState() {
        if (this.config.startBytes.length === 0) {
            return GenericParserState.GETTING_MSG_ID;
        } else {
            return GenericParserState.LOOKING_FOR_START1;
        }
    }

    reset() {
        this.state = this._getInitialState();
        this.buffer = [];
        this.packetSize = 0;
        this.msgId = 0;
        this.msgLength = 0;
        this.lengthLo = 0;
    }

    parseByte(byte) {
        const result = createFrameMsgInfo();
        const startBytes = this.config.startBytes;
        const overhead = this.config.headerSize + this.config.footerSize;

        switch (this.state) {
            case GenericParserState.LOOKING_FOR_START1:
                if (byte === startBytes[0]) {
                    this.buffer = [byte];
                    if (startBytes.length > 1) {
                        this.state = GenericParserState.LOOKING_FOR_START2;
                    } else {
                        this.state = GenericParserState.GETTING_MSG_ID;
                    }
                }
                break;

            case GenericParserState.LOOKING_FOR_START2:
                if (byte === startBytes[1]) {
                    this.buffer.push(byte);
                    this.state = GenericParserState.GETTING_MSG_ID;
                } else if (byte === startBytes[0]) {
                    this.buffer = [byte];
                    // Stay in LOOKING_FOR_START2
                } else {
                    this.state = GenericParserState.LOOKING_FOR_START1;
                }
                break;

            case GenericParserState.GETTING_MSG_ID:
                this.buffer.push(byte);
                this.msgId = byte;
                if (this.config.hasLength) {
                    this.state = GenericParserState.GETTING_LENGTH;
                } else if (this.getMsgLength) {
                    const msgLen = this.getMsgLength(byte);
                    if (msgLen !== undefined) {
                        this.packetSize = overhead + msgLen;
                        this.state = GenericParserState.GETTING_PAYLOAD;
                    } else {
                        this.state = this._getInitialState();
                    }
                } else {
                    this.state = this._getInitialState();
                }
                break;

            case GenericParserState.GETTING_LENGTH:
                this.buffer.push(byte);
                if (this.config.lengthBytes === 1) {
                    this.msgLength = byte;
                    this.packetSize = overhead + this.msgLength;
                    this.state = GenericParserState.GETTING_PAYLOAD;
                } else {
                    // 2-byte length
                    if (this.buffer.length === startBytes.length + 2) {
                        this.lengthLo = byte;
                    } else {
                        this.msgLength = this.lengthLo | (byte << 8);
                        this.packetSize = overhead + this.msgLength;
                        this.state = GenericParserState.GETTING_PAYLOAD;
                    }
                }
                break;

            case GenericParserState.GETTING_PAYLOAD:
                this.buffer.push(byte);
                if (this.buffer.length >= this.packetSize) {
                    if (this.config.hasCrc) {
                        const validationResult = validatePayloadWithCrc(
                            this.buffer, this.config.headerSize, this.config.lengthBytes, startBytes.length);
                        if (validationResult.valid) {
                            result.valid = validationResult.valid;
                            result.msgId = validationResult.msgId;
                            result.msgLen = validationResult.msgLen;
                            result.msgData = validationResult.msgData;
                        }
                    } else {
                        const validationResult = validatePayloadMinimal(this.buffer, this.config.headerSize);
                        result.valid = validationResult.valid;
                        result.msgId = validationResult.msgId;
                        result.msgLen = validationResult.msgLen;
                        result.msgData = validationResult.msgData;
                    }
                    this.state = this._getInitialState();
                }
                break;
        }

        return result;
    }

    /**
     * Encode a message using this format (static method)
     */
    static encode(config, msgId, msg) {
        const output = [];

        // Add start bytes
        for (const startByte of config.startBytes) {
            output.push(startByte);
        }

        // Use appropriate payload encoding
        if (config.hasCrc) {
            encodePayloadWithCrc(output, msgId, msg, config.lengthBytes, config.startBytes.length);
        } else {
            encodePayloadMinimal(output, msgId, msg);
        }

        return new Uint8Array(output);
    }

    /**
     * Validate a complete packet buffer using this format (static method)
     */
    static validateFrame(config, buffer) {
        const overhead = config.headerSize + config.footerSize;

        if (buffer.length < overhead) {
            return createFrameMsgInfo();
        }

        // Check start bytes
        for (let i = 0; i < config.startBytes.length; i++) {
            if (buffer[i] !== config.startBytes[i]) {
                return createFrameMsgInfo();
            }
        }

        // Validate payload
        if (config.hasCrc) {
            return validatePayloadWithCrc(buffer, config.headerSize, config.lengthBytes, config.startBytes.length);
        } else {
            return validatePayloadMinimal(buffer, config.headerSize);
        }
    }
}

/**
 * Create a frame parser class for a specific configuration.
 * This factory function provides pre-configured parser classes.
 */
function createFrameParserClass(config) {
    // Create a class that extends GenericFrameParser with the config baked in
    class ConfiguredFrameParser extends GenericFrameParser {
        constructor(getMsgLength = undefined) {
            super(config, getMsgLength);
        }

        static encode(msgId, msg) {
            return GenericFrameParser.encode(config, msgId, msg);
        }

        static validatePacket(buffer) {
            return GenericFrameParser.validateFrame(config, buffer);
        }
    }

    // Add static properties from config
    ConfiguredFrameParser.START_BYTES = config.startBytes;
    ConfiguredFrameParser.HEADER_SIZE = config.headerSize;
    ConfiguredFrameParser.FOOTER_SIZE = config.footerSize;
    ConfiguredFrameParser.OVERHEAD = config.headerSize + config.footerSize;
    ConfiguredFrameParser.HAS_LENGTH = config.hasLength;
    ConfiguredFrameParser.LENGTH_BYTES = config.lengthBytes;
    ConfiguredFrameParser.HAS_CRC = config.hasCrc;
    ConfiguredFrameParser.CONFIG = config;

    return ConfiguredFrameParser;
}

module.exports = {
    fletcherChecksum,
    fletcherChecksumExt,
    createFrameMsgInfo,
    validatePayloadWithCrc,
    validatePayloadMinimal,
    encodePayloadWithCrc,
    encodePayloadMinimal,
    GenericParserState,
    GenericFrameParser,
    createFrameParserClass,
};
