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
};
