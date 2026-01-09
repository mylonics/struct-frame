/**
 * Frame Profiles - Pre-defined Header + Payload combinations for JavaScript
 * 
 * This module provides ready-to-use encode/parse functions for the 5 standard profiles:
 * - ProfileStandard: Basic + Default (General serial/UART)
 * - ProfileSensor: Tiny + Minimal (Low-bandwidth sensors)
 * - ProfileIPC: None + Minimal (Trusted inter-process communication)
 * - ProfileBulk: Basic + Extended (Large data transfers with package namespacing)
 * - ProfileNetwork: Basic + ExtendedMultiSystemStream (Multi-system networked communication)
 * 
 * This module builds on the existing frame_headers and payload_types boilerplate code,
 * providing maximum code reuse through a generic FrameProfileConfig.
 */

const { BASIC_START_BYTE, PAYLOAD_TYPE_BASE } = require('./frame_headers/base');
const { fletcher_checksum, createFrameMsgInfo } = require('./frame_base');

// =============================================================================
// Profile Configurations
// =============================================================================

/**
 * Profile Standard: Basic + Default
 * Frame: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * 6 bytes overhead, 255 bytes max payload
 */
const ProfileStandardConfig = {
    name: 'ProfileStandard',
    numStartBytes: 2,
    startByte1: BASIC_START_BYTE,
    startByte2: PAYLOAD_TYPE_BASE + 1, // DEFAULT = 1
    headerSize: 4,   // start1 + start2 + len + msg_id
    footerSize: 2,   // CRC
    hasLength: true,
    lengthBytes: 1,
    hasCrc: true,
    hasPkgId: false,
    hasSeq: false,
    hasSysId: false,
    hasCompId: false,
};

/**
 * Profile Sensor: Tiny + Minimal
 * Frame: [0x70] [MSG_ID] [PAYLOAD]
 * 2 bytes overhead, no length field (requires get_msg_length callback)
 */
const ProfileSensorConfig = {
    name: 'ProfileSensor',
    numStartBytes: 1,
    startByte1: PAYLOAD_TYPE_BASE + 0, // MINIMAL = 0
    startByte2: 0,
    headerSize: 2,   // start + msg_id
    footerSize: 0,
    hasLength: false,
    lengthBytes: 0,
    hasCrc: false,
    hasPkgId: false,
    hasSeq: false,
    hasSysId: false,
    hasCompId: false,
};

/**
 * Profile IPC: None + Minimal
 * Frame: [MSG_ID] [PAYLOAD]
 * 1 byte overhead, no start bytes (requires get_msg_length callback)
 */
const ProfileIPCConfig = {
    name: 'ProfileIPC',
    numStartBytes: 0,
    startByte1: 0,
    startByte2: 0,
    headerSize: 1,   // msg_id only
    footerSize: 0,
    hasLength: false,
    lengthBytes: 0,
    hasCrc: false,
    hasPkgId: false,
    hasSeq: false,
    hasSysId: false,
    hasCompId: false,
};

/**
 * Profile Bulk: Basic + Extended
 * Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * 8 bytes overhead, 64KB max payload
 */
const ProfileBulkConfig = {
    name: 'ProfileBulk',
    numStartBytes: 2,
    startByte1: BASIC_START_BYTE,
    startByte2: PAYLOAD_TYPE_BASE + 4, // EXTENDED = 4
    headerSize: 6,   // start1 + start2 + len16 + pkg_id + msg_id
    footerSize: 2,   // CRC
    hasLength: true,
    lengthBytes: 2,
    hasCrc: true,
    hasPkgId: true,
    hasSeq: false,
    hasSysId: false,
    hasCompId: false,
};

/**
 * Profile Network: Basic + ExtendedMultiSystemStream
 * Frame: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * 11 bytes overhead, 64KB max payload
 */
const ProfileNetworkConfig = {
    name: 'ProfileNetwork',
    numStartBytes: 2,
    startByte1: BASIC_START_BYTE,
    startByte2: PAYLOAD_TYPE_BASE + 8, // EXTENDED_MULTI_SYSTEM_STREAM = 8
    headerSize: 9,   // start1 + start2 + seq + sys + comp + len16 + pkg_id + msg_id
    footerSize: 2,   // CRC
    hasLength: true,
    lengthBytes: 2,
    hasCrc: true,
    hasPkgId: true,
    hasSeq: true,
    hasSysId: true,
    hasCompId: true,
};

// =============================================================================
// Generic Encode/Parse Functions
// =============================================================================

/**
 * Generic encode function for frames with CRC.
 * @param {Object} config - Frame format configuration
 * @param {number} msgId - Message ID (0-255)
 * @param {Uint8Array} payload - Message payload bytes
 * @param {Object} options - Optional fields (seq, sysId, compId, pkgId)
 * @returns {Uint8Array} Encoded frame
 */
function encodeFrameWithCrc(config, msgId, payload, options = {}) {
    const { seq = 0, sysId = 0, compId = 0, pkgId = 0 } = options;
    const payloadSize = payload.length;
    const totalSize = config.headerSize + payloadSize + config.footerSize;
    
    const buffer = new Uint8Array(totalSize);
    let idx = 0;
    
    // Write start bytes
    if (config.numStartBytes >= 1) {
        buffer[idx++] = config.startByte1;
    }
    if (config.numStartBytes >= 2) {
        buffer[idx++] = config.startByte2;
    }
    
    const crcStart = idx;
    
    // Write optional fields before length
    if (config.hasSeq) {
        buffer[idx++] = seq & 0xFF;
    }
    if (config.hasSysId) {
        buffer[idx++] = sysId & 0xFF;
    }
    if (config.hasCompId) {
        buffer[idx++] = compId & 0xFF;
    }
    
    // Write length field
    if (config.hasLength) {
        if (config.lengthBytes === 1) {
            buffer[idx++] = payloadSize & 0xFF;
        } else {
            buffer[idx++] = payloadSize & 0xFF;
            buffer[idx++] = (payloadSize >> 8) & 0xFF;
        }
    }
    
    // Write package ID if present
    if (config.hasPkgId) {
        buffer[idx++] = pkgId & 0xFF;
    }
    
    // Write message ID
    buffer[idx++] = msgId & 0xFF;
    
    // Write payload
    buffer.set(payload, idx);
    idx += payloadSize;
    
    // Calculate and write CRC
    const crcLen = idx - crcStart;
    const ck = fletcher_checksum(buffer, crcStart, crcStart + crcLen);
    buffer[idx++] = ck[0];
    buffer[idx++] = ck[1];
    
    return buffer;
}

/**
 * Generic encode function for minimal frames (no length, no CRC).
 * @param {Object} config - Frame format configuration
 * @param {number} msgId - Message ID (0-255)
 * @param {Uint8Array} payload - Message payload bytes
 * @returns {Uint8Array} Encoded frame
 */
function encodeFrameMinimal(config, msgId, payload) {
    const totalSize = config.headerSize + payload.length;
    const buffer = new Uint8Array(totalSize);
    let idx = 0;
    
    // Write start bytes
    if (config.numStartBytes >= 1) {
        buffer[idx++] = config.startByte1;
    }
    if (config.numStartBytes >= 2) {
        buffer[idx++] = config.startByte2;
    }
    
    // Write message ID
    buffer[idx++] = msgId & 0xFF;
    
    // Write payload
    buffer.set(payload, idx);
    
    return buffer;
}

/**
 * Generic parse function for frames with CRC.
 * @param {Object} config - Frame format configuration
 * @param {Uint8Array} buffer - Buffer containing the complete frame
 * @returns {Object} FrameMsgInfo with valid=true if frame is valid
 */
function parseFrameWithCrc(config, buffer) {
    const result = createFrameMsgInfo();
    const length = buffer.length;
    
    if (length < config.headerSize + config.footerSize) {
        return result;
    }
    
    let idx = 0;
    
    // Verify start bytes
    if (config.numStartBytes >= 1) {
        if (buffer[idx++] !== config.startByte1) {
            return result;
        }
    }
    if (config.numStartBytes >= 2) {
        if (buffer[idx++] !== config.startByte2) {
            return result;
        }
    }
    
    const crcStart = idx;
    
    // Skip optional fields before length
    if (config.hasSeq) idx++;
    if (config.hasSysId) idx++;
    if (config.hasCompId) idx++;
    
    // Read length field
    let msgLen = 0;
    if (config.hasLength) {
        if (config.lengthBytes === 1) {
            msgLen = buffer[idx++];
        } else {
            msgLen = buffer[idx] | (buffer[idx + 1] << 8);
            idx += 2;
        }
    }
    
    // Skip package ID
    if (config.hasPkgId) idx++;
    
    // Read message ID
    const msgId = buffer[idx++];
    
    // Verify total size
    const totalSize = config.headerSize + msgLen + config.footerSize;
    if (length < totalSize) {
        return result;
    }
    
    // Verify CRC
    const crcLen = totalSize - crcStart - config.footerSize;
    const ck = fletcher_checksum(buffer, crcStart, crcStart + crcLen);
    if (ck[0] !== buffer[totalSize - 2] || ck[1] !== buffer[totalSize - 1]) {
        return result;
    }
    
    // Extract message data
    result.valid = true;
    result.msg_id = msgId;
    result.msg_len = msgLen;
    result.msg_data = buffer.slice(config.headerSize, config.headerSize + msgLen);
    
    return result;
}

/**
 * Generic parse function for minimal frames (requires get_msg_length callback).
 * @param {Object} config - Frame format configuration
 * @param {Uint8Array} buffer - Buffer containing the complete frame
 * @param {Function} getMsgLength - Callback to get expected message length from msg_id
 * @returns {Object} FrameMsgInfo with valid=true if frame is valid
 */
function parseFrameMinimal(config, buffer, getMsgLength) {
    const result = createFrameMsgInfo();
    
    if (buffer.length < config.headerSize) {
        return result;
    }
    
    let idx = 0;
    
    // Verify start bytes
    if (config.numStartBytes >= 1) {
        if (buffer[idx++] !== config.startByte1) {
            return result;
        }
    }
    if (config.numStartBytes >= 2) {
        if (buffer[idx++] !== config.startByte2) {
            return result;
        }
    }
    
    // Read message ID
    const msgId = buffer[idx];
    
    // Get message length from callback
    const msgLen = getMsgLength(msgId);
    if (msgLen === undefined || msgLen === null) {
        return result;
    }
    
    const totalSize = config.headerSize + msgLen;
    if (buffer.length < totalSize) {
        return result;
    }
    
    // Extract message data
    result.valid = true;
    result.msg_id = msgId;
    result.msg_len = msgLen;
    result.msg_data = buffer.slice(config.headerSize, config.headerSize + msgLen);
    
    return result;
}

// =============================================================================
// Profile-Specific Convenience Functions
// =============================================================================

/**
 * Encode using Profile Standard (Basic + Default)
 */
function encodeProfileStandard(msgId, payload) {
    return encodeFrameWithCrc(ProfileStandardConfig, msgId, payload);
}

/**
 * Parse Profile Standard frame from buffer
 */
function parseProfileStandardBuffer(buffer) {
    return parseFrameWithCrc(ProfileStandardConfig, buffer);
}

/**
 * Encode using Profile Sensor (Tiny + Minimal)
 */
function encodeProfileSensor(msgId, payload) {
    return encodeFrameMinimal(ProfileSensorConfig, msgId, payload);
}

/**
 * Parse Profile Sensor frame from buffer (requires getMsgLength callback)
 */
function parseProfileSensorBuffer(buffer, getMsgLength) {
    return parseFrameMinimal(ProfileSensorConfig, buffer, getMsgLength);
}

/**
 * Encode using Profile IPC (None + Minimal)
 */
function encodeProfileIPC(msgId, payload) {
    return encodeFrameMinimal(ProfileIPCConfig, msgId, payload);
}

/**
 * Parse Profile IPC frame from buffer (requires getMsgLength callback)
 */
function parseProfileIPCBuffer(buffer, getMsgLength) {
    return parseFrameMinimal(ProfileIPCConfig, buffer, getMsgLength);
}

/**
 * Encode using Profile Bulk (Basic + Extended)
 */
function encodeProfileBulk(msgId, payload, pkgId = 0) {
    return encodeFrameWithCrc(ProfileBulkConfig, msgId, payload, { pkgId });
}

/**
 * Parse Profile Bulk frame from buffer
 */
function parseProfileBulkBuffer(buffer) {
    return parseFrameWithCrc(ProfileBulkConfig, buffer);
}

/**
 * Encode using Profile Network (Basic + ExtendedMultiSystemStream)
 */
function encodeProfileNetwork(msgId, payload, options = {}) {
    return encodeFrameWithCrc(ProfileNetworkConfig, msgId, payload, options);
}

/**
 * Parse Profile Network frame from buffer
 */
function parseProfileNetworkBuffer(buffer) {
    return parseFrameWithCrc(ProfileNetworkConfig, buffer);
}

// =============================================================================
// Profile Parser Classes (for compatibility with test codec)
// =============================================================================

/**
 * Create a profile parser class with encodeMsg and validatePacket static methods.
 * This provides compatibility with the existing test codec interface.
 */
function createProfileParserClass(config) {
    return {
        config: config,
        
        encodeMsg: function(msgId, payload) {
            if (config.hasCrc) {
                return encodeFrameWithCrc(config, msgId, payload);
            } else {
                return encodeFrameMinimal(config, msgId, payload);
            }
        },
        
        validatePacket: function(buffer, getMsgLength) {
            if (config.hasCrc) {
                return parseFrameWithCrc(config, buffer);
            } else {
                return parseFrameMinimal(config, buffer, getMsgLength);
            }
        }
    };
}

// Pre-configured profile parsers
const ProfileStandard = createProfileParserClass(ProfileStandardConfig);
const ProfileSensor = createProfileParserClass(ProfileSensorConfig);
const ProfileIPC = createProfileParserClass(ProfileIPCConfig);
const ProfileBulk = createProfileParserClass(ProfileBulkConfig);
const ProfileNetwork = createProfileParserClass(ProfileNetworkConfig);

// =============================================================================
// BufferReader - Iterate through multiple frames in a buffer
// =============================================================================

/**
 * BufferReader - Iterate through a buffer parsing multiple frames.
 *
 * Usage:
 *   const reader = new BufferReader(ProfileStandardConfig, buffer);
 *   let result = reader.next();
 *   while (result.valid) {
 *       // Process result.msg_id, result.msg_data, result.msg_len
 *       result = reader.next();
 *   }
 */
class BufferReader {
    constructor(config, buffer, getMsgLength = undefined) {
        this.config = config;
        this.buffer = buffer;
        this.size = buffer.length;
        this._offset = 0;
        this.getMsgLength = getMsgLength;
    }

    next() {
        if (this._offset >= this.size) {
            return createFrameMsgInfo();
        }

        const remaining = this.buffer.slice(this._offset);
        let result;

        if (this.config.hasCrc || this.config.hasLength) {
            result = parseFrameWithCrc(this.config, remaining);
        } else {
            if (!this.getMsgLength) {
                // No more valid data to parse without length callback
                this._offset = this.size;
                return createFrameMsgInfo();
            }
            result = parseFrameMinimal(this.config, remaining, this.getMsgLength);
        }

        if (result.valid) {
            const frameSize = this.config.headerSize + result.msg_len + this.config.footerSize;
            this._offset += frameSize;
        } else {
            // No more valid frames - stop parsing
            this._offset = this.size;
        }

        return result;
    }

    reset() {
        this._offset = 0;
    }

    get offset() {
        return this._offset;
    }

    get remaining() {
        return Math.max(0, this.size - this._offset);
    }

    hasMore() {
        return this._offset < this.size;
    }
}

// =============================================================================
// BufferWriter - Encode multiple frames with automatic offset tracking
// =============================================================================

/**
 * BufferWriter - Encode multiple frames into a buffer with automatic offset tracking.
 */
class BufferWriter {
    constructor(config, capacity) {
        this.config = config;
        this.capacity = capacity;
        this.buffer = new Uint8Array(capacity);
        this._offset = 0;
    }

    write(msgId, payload, options = {}) {
        let encoded;

        if (this.config.hasCrc || this.config.hasLength) {
            encoded = encodeFrameWithCrc(this.config, msgId, payload, options);
        } else {
            encoded = encodeFrameMinimal(this.config, msgId, payload);
        }

        const written = encoded.length;
        if (this._offset + written > this.capacity) {
            return 0;
        }

        this.buffer.set(encoded, this._offset);
        this._offset += written;
        return written;
    }

    reset() {
        this._offset = 0;
    }

    get size() {
        return this._offset;
    }

    get remaining() {
        return Math.max(0, this.capacity - this._offset);
    }

    data() {
        return this.buffer.slice(0, this._offset);
    }
}

// =============================================================================
// AccumulatingReader - Unified parser for buffer and byte-by-byte streaming
// =============================================================================

const AccumulatingReaderState = {
    IDLE: 0,
    LOOKING_FOR_START1: 1,
    LOOKING_FOR_START2: 2,
    COLLECTING_HEADER: 3,
    COLLECTING_PAYLOAD: 4,
    BUFFER_MODE: 5
};

/**
 * AccumulatingReader - Unified parser for buffer and byte-by-byte streaming input.
 */
class AccumulatingReader {
    constructor(config, getMsgLength = undefined, bufferSize = 1024) {
        this.config = config;
        this.getMsgLength = getMsgLength;
        this.bufferSize = bufferSize;

        this.internalBuffer = new Uint8Array(bufferSize);
        this.internalDataLen = 0;
        this.expectedFrameSize = 0;
        this._state = AccumulatingReaderState.IDLE;

        this.currentBuffer = null;
        this.currentSize = 0;
        this.currentOffset = 0;
    }

    // Buffer Mode API
    addData(buffer) {
        this.currentBuffer = buffer;
        this.currentSize = buffer.length;
        this.currentOffset = 0;
        this._state = AccumulatingReaderState.BUFFER_MODE;

        if (this.internalDataLen > 0) {
            const spaceAvailable = this.bufferSize - this.internalDataLen;
            const bytesToCopy = Math.min(buffer.length, spaceAvailable);
            this.internalBuffer.set(buffer.slice(0, bytesToCopy), this.internalDataLen);
            this.internalDataLen += bytesToCopy;
        }
    }

    next() {
        if (this._state !== AccumulatingReaderState.BUFFER_MODE) {
            return createFrameMsgInfo();
        }

        if (this.internalDataLen > 0 && this.currentOffset === 0) {
            const internalBytes = this.internalBuffer.slice(0, this.internalDataLen);
            const result = this._parseBuffer(internalBytes);

            if (result.valid) {
                const frameSize = this.config.headerSize + result.msg_len + this.config.footerSize;
                const partialLen = this.internalDataLen > this.currentSize ? this.internalDataLen - this.currentSize : 0;
                const bytesFromCurrent = frameSize > partialLen ? frameSize - partialLen : 0;
                this.currentOffset = bytesFromCurrent;

                this.internalDataLen = 0;
                this.expectedFrameSize = 0;

                return result;
            } else {
                return createFrameMsgInfo();
            }
        }

        if (this.currentBuffer === null || this.currentOffset >= this.currentSize) {
            return createFrameMsgInfo();
        }

        const remaining = this.currentBuffer.slice(this.currentOffset);
        const result = this._parseBuffer(remaining);

        if (result.valid) {
            const frameSize = this.config.headerSize + result.msg_len + this.config.footerSize;
            this.currentOffset += frameSize;
            return result;
        }

        const remainingLen = this.currentSize - this.currentOffset;
        if (remainingLen > 0 && remainingLen < this.bufferSize) {
            this.internalBuffer.set(remaining, 0);
            this.internalDataLen = remainingLen;
            this.currentOffset = this.currentSize;
        }

        return createFrameMsgInfo();
    }

    // Stream Mode API
    pushByte(byte) {
        if (this._state === AccumulatingReaderState.IDLE || this._state === AccumulatingReaderState.BUFFER_MODE) {
            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
            this.internalDataLen = 0;
            this.expectedFrameSize = 0;
        }

        switch (this._state) {
            case AccumulatingReaderState.LOOKING_FOR_START1:
                return this._handleLookingForStart1(byte);
            case AccumulatingReaderState.LOOKING_FOR_START2:
                return this._handleLookingForStart2(byte);
            case AccumulatingReaderState.COLLECTING_HEADER:
                return this._handleCollectingHeader(byte);
            case AccumulatingReaderState.COLLECTING_PAYLOAD:
                return this._handleCollectingPayload(byte);
            default:
                this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                return createFrameMsgInfo();
        }
    }

    _handleLookingForStart1(byte) {
        if (this.config.numStartBytes === 0) {
            this.internalBuffer[0] = byte;
            this.internalDataLen = 1;

            if (!this.config.hasLength && !this.config.hasCrc) {
                return this._handleMinimalMsgId(byte);
            } else {
                this._state = AccumulatingReaderState.COLLECTING_HEADER;
            }
        } else {
            if (byte === this.config.startByte1) {
                this.internalBuffer[0] = byte;
                this.internalDataLen = 1;

                if (this.config.numStartBytes === 1) {
                    this._state = AccumulatingReaderState.COLLECTING_HEADER;
                } else {
                    this._state = AccumulatingReaderState.LOOKING_FOR_START2;
                }
            }
        }
        return createFrameMsgInfo();
    }

    _handleLookingForStart2(byte) {
        if (byte === this.config.startByte2) {
            this.internalBuffer[this.internalDataLen++] = byte;
            this._state = AccumulatingReaderState.COLLECTING_HEADER;
        } else if (byte === this.config.startByte1) {
            this.internalBuffer[0] = byte;
            this.internalDataLen = 1;
        } else {
            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
            this.internalDataLen = 0;
        }
        return createFrameMsgInfo();
    }

    _handleCollectingHeader(byte) {
        if (this.internalDataLen >= this.bufferSize) {
            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
            this.internalDataLen = 0;
            return createFrameMsgInfo();
        }

        this.internalBuffer[this.internalDataLen++] = byte;

        if (this.internalDataLen >= this.config.headerSize) {
            if (!this.config.hasLength && !this.config.hasCrc) {
                const msgId = this.internalBuffer[this.config.headerSize - 1];
                if (this.getMsgLength) {
                    const msgLen = this.getMsgLength(msgId);
                    if (msgLen !== undefined) {
                        this.expectedFrameSize = this.config.headerSize + msgLen;

                        if (this.expectedFrameSize > this.bufferSize) {
                            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                            this.internalDataLen = 0;
                            return createFrameMsgInfo();
                        }

                        if (msgLen === 0) {
                            const result = createFrameMsgInfo();
                            result.valid = true;
                            result.msg_id = msgId;
                            result.msg_len = 0;
                            result.msg_data = new Uint8Array(0);
                            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                            this.internalDataLen = 0;
                            this.expectedFrameSize = 0;
                            return result;
                        }

                        this._state = AccumulatingReaderState.COLLECTING_PAYLOAD;
                    } else {
                        this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                        this.internalDataLen = 0;
                    }
                } else {
                    this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                    this.internalDataLen = 0;
                }
            } else {
                let lenOffset = this.config.numStartBytes;
                if (this.config.hasSeq) lenOffset++;
                if (this.config.hasSysId) lenOffset++;
                if (this.config.hasCompId) lenOffset++;

                let payloadLen = 0;
                if (this.config.hasLength) {
                    if (this.config.lengthBytes === 1) {
                        payloadLen = this.internalBuffer[lenOffset];
                    } else {
                        payloadLen = this.internalBuffer[lenOffset] | (this.internalBuffer[lenOffset + 1] << 8);
                    }
                }

                this.expectedFrameSize = this.config.headerSize + payloadLen + this.config.footerSize;

                if (this.expectedFrameSize > this.bufferSize) {
                    this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                    this.internalDataLen = 0;
                    return createFrameMsgInfo();
                }

                if (this.internalDataLen >= this.expectedFrameSize) {
                    return this._validateAndReturn();
                }

                this._state = AccumulatingReaderState.COLLECTING_PAYLOAD;
            }
        }

        return createFrameMsgInfo();
    }

    _handleCollectingPayload(byte) {
        if (this.internalDataLen >= this.bufferSize) {
            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
            this.internalDataLen = 0;
            return createFrameMsgInfo();
        }

        this.internalBuffer[this.internalDataLen++] = byte;

        if (this.internalDataLen >= this.expectedFrameSize) {
            return this._validateAndReturn();
        }

        return createFrameMsgInfo();
    }

    _handleMinimalMsgId(msgId) {
        if (this.getMsgLength) {
            const msgLen = this.getMsgLength(msgId);
            if (msgLen !== undefined) {
                this.expectedFrameSize = this.config.headerSize + msgLen;

                if (this.expectedFrameSize > this.bufferSize) {
                    this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                    this.internalDataLen = 0;
                    return createFrameMsgInfo();
                }

                if (msgLen === 0) {
                    const result = createFrameMsgInfo();
                    result.valid = true;
                    result.msg_id = msgId;
                    result.msg_len = 0;
                    result.msg_data = new Uint8Array(0);
                    this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                    this.internalDataLen = 0;
                    this.expectedFrameSize = 0;
                    return result;
                }

                this._state = AccumulatingReaderState.COLLECTING_PAYLOAD;
            } else {
                this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                this.internalDataLen = 0;
            }
        } else {
            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
            this.internalDataLen = 0;
        }
        return createFrameMsgInfo();
    }

    _validateAndReturn() {
        const internalBytes = this.internalBuffer.slice(0, this.internalDataLen);
        const result = this._parseBuffer(internalBytes);

        this._state = AccumulatingReaderState.LOOKING_FOR_START1;
        this.internalDataLen = 0;
        this.expectedFrameSize = 0;

        return result;
    }

    _parseBuffer(buffer) {
        if (this.config.hasCrc || this.config.hasLength) {
            return parseFrameWithCrc(this.config, buffer);
        } else {
            if (!this.getMsgLength) {
                return createFrameMsgInfo();
            }
            return parseFrameMinimal(this.config, buffer, this.getMsgLength);
        }
    }

    // Common API
    hasMore() {
        if (this._state !== AccumulatingReaderState.BUFFER_MODE) return false;
        return (this.internalDataLen > 0) || (this.currentBuffer !== null && this.currentOffset < this.currentSize);
    }

    hasPartial() {
        return this.internalDataLen > 0;
    }

    partialSize() {
        return this.internalDataLen;
    }

    get state() {
        return this._state;
    }

    reset() {
        this.internalDataLen = 0;
        this.expectedFrameSize = 0;
        this._state = AccumulatingReaderState.IDLE;
        this.currentBuffer = null;
        this.currentSize = 0;
        this.currentOffset = 0;
    }
}

// =============================================================================
// Convenience factory functions for standard profiles
// =============================================================================

function createProfileStandardReader(buffer) {
    return new BufferReader(ProfileStandardConfig, buffer);
}

function createProfileStandardWriter(capacity = 1024) {
    return new BufferWriter(ProfileStandardConfig, capacity);
}

function createProfileStandardAccumulatingReader(bufferSize = 1024) {
    return new AccumulatingReader(ProfileStandardConfig, undefined, bufferSize);
}

function createProfileSensorReader(buffer, getMsgLength) {
    return new BufferReader(ProfileSensorConfig, buffer, getMsgLength);
}

function createProfileSensorWriter(capacity = 1024) {
    return new BufferWriter(ProfileSensorConfig, capacity);
}

function createProfileSensorAccumulatingReader(getMsgLength, bufferSize = 1024) {
    return new AccumulatingReader(ProfileSensorConfig, getMsgLength, bufferSize);
}

function createProfileIPCReader(buffer, getMsgLength) {
    return new BufferReader(ProfileIPCConfig, buffer, getMsgLength);
}

function createProfileIPCWriter(capacity = 1024) {
    return new BufferWriter(ProfileIPCConfig, capacity);
}

function createProfileIPCAccumulatingReader(getMsgLength, bufferSize = 1024) {
    return new AccumulatingReader(ProfileIPCConfig, getMsgLength, bufferSize);
}

function createProfileBulkReader(buffer) {
    return new BufferReader(ProfileBulkConfig, buffer);
}

function createProfileBulkWriter(capacity = 1024) {
    return new BufferWriter(ProfileBulkConfig, capacity);
}

function createProfileBulkAccumulatingReader(bufferSize = 1024) {
    return new AccumulatingReader(ProfileBulkConfig, undefined, bufferSize);
}

function createProfileNetworkReader(buffer) {
    return new BufferReader(ProfileNetworkConfig, buffer);
}

function createProfileNetworkWriter(capacity = 1024) {
    return new BufferWriter(ProfileNetworkConfig, capacity);
}

function createProfileNetworkAccumulatingReader(bufferSize = 1024) {
    return new AccumulatingReader(ProfileNetworkConfig, undefined, bufferSize);
}

module.exports = {
    // Profile configurations
    ProfileStandardConfig,
    ProfileSensorConfig,
    ProfileIPCConfig,
    ProfileBulkConfig,
    ProfileNetworkConfig,
    
    // Generic encode/parse functions
    encodeFrameWithCrc,
    encodeFrameMinimal,
    parseFrameWithCrc,
    parseFrameMinimal,
    
    // Profile-specific convenience functions
    encodeProfileStandard,
    parseProfileStandardBuffer,
    encodeProfileSensor,
    parseProfileSensorBuffer,
    encodeProfileIPC,
    parseProfileIPCBuffer,
    encodeProfileBulk,
    parseProfileBulkBuffer,
    encodeProfileNetwork,
    parseProfileNetworkBuffer,
    
    // Profile parser classes (for test codec compatibility)
    createProfileParserClass,
    ProfileStandard,
    ProfileSensor,
    ProfileIPC,
    ProfileBulk,
    ProfileNetwork,
    
    // BufferReader/BufferWriter/AccumulatingReader classes
    BufferReader,
    BufferWriter,
    AccumulatingReader,
    AccumulatingReaderState,
    
    // Convenience factory functions for profiles
    createProfileStandardReader,
    createProfileStandardWriter,
    createProfileStandardAccumulatingReader,
    createProfileSensorReader,
    createProfileSensorWriter,
    createProfileSensorAccumulatingReader,
    createProfileIPCReader,
    createProfileIPCWriter,
    createProfileIPCAccumulatingReader,
    createProfileBulkReader,
    createProfileBulkWriter,
    createProfileBulkAccumulatingReader,
    createProfileNetworkReader,
    createProfileNetworkWriter,
    createProfileNetworkAccumulatingReader,
};
