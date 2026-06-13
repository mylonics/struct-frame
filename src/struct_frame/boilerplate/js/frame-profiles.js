"use strict";
/**
 * Frame Profiles - Pre-defined Header + Payload combinations for TypeScript
 *
 * This module provides ready-to-use encode/parse functions for the 5 standard profiles:
 * - ProfileStandard: Basic + Default (General serial/UART)
 * - ProfileSensor: Tiny + Minimal (Low-bandwidth sensors)
 * - ProfileIPC: None + Minimal (Trusted inter-process communication)
 * - ProfileBulk: Basic + Extended (Large data transfers with package namespacing)
 * - ProfileNetwork: Basic + ExtendedMultiSystemStream (Multi-system networked communication)
 *
 * This module builds on frame_headers and payload_types, composing profiles from
 * header + payload configurations (mirroring the C++ FrameProfiles.hpp structure).
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.ProfileNetworkAccumulatingReader = exports.ProfileNetworkWriter = exports.ProfileNetworkReader = exports.ProfileBulkAccumulatingReader = exports.ProfileBulkWriter = exports.ProfileBulkReader = exports.ProfileIPCAccumulatingReader = exports.ProfileIPCWriter = exports.ProfileIPCReader = exports.ProfileSensorAccumulatingReader = exports.ProfileSensorWriter = exports.ProfileSensorReader = exports.ProfileStandardAccumulatingReader = exports.ProfileStandardWriter = exports.ProfileStandardReader = exports.AccumulatingReader = exports.AccumulatingReaderState = exports.BufferWriter = exports.BufferReader = exports.ProfileNetworkConfig = exports.ProfileBulkConfig = exports.ProfileIPCConfig = exports.ProfileSensorConfig = exports.ProfileStandardConfig = void 0;
exports.profileHeaderSize = profileHeaderSize;
exports.profileFooterSize = profileFooterSize;
exports.profileOverhead = profileOverhead;
exports.encodeMessage = encodeMessage;
exports.parseFrameWithCrc = parseFrameWithCrc;
exports.parseFrameMinimal = parseFrameMinimal;
const frame_headers_1 = require("./frame-headers");
const payload_types_1 = require("./payload-types");
const frame_base_1 = require("./frame-base");
// =============================================================================
// Profile Helper Functions
// =============================================================================
/** Get the total header size for a profile (start bytes + payload header fields) */
function profileHeaderSize(config) {
    return config.header.numStartBytes + (0, payload_types_1.payloadHeaderSize)(config.payload);
}
/** Get the footer size for a profile */
function profileFooterSize(config) {
    return (0, payload_types_1.payloadFooterSize)(config.payload);
}
/** Get the total overhead for a profile (header + footer) */
function profileOverhead(config) {
    return profileHeaderSize(config) + profileFooterSize(config);
}
// =============================================================================
// Profile Configuration Factory
// =============================================================================
/**
 * Create a profile configuration from header and payload configs.
 */
function createProfileConfig(name, header, payload) {
    // Compute start byte1 dynamically for Tiny header (single byte encodes payload type)
    const computedStartByte1 = header.encodesPayloadType && header.numStartBytes === 1
        ? frame_headers_1.PAYLOAD_TYPE_BASE + payload.payloadType
        : header.startByte1;
    // Compute start byte2 dynamically for headers that encode payload type
    const computedStartByte2 = header.encodesPayloadType && header.numStartBytes === 2
        ? frame_headers_1.PAYLOAD_TYPE_BASE + payload.payloadType
        : header.startByte2;
    return {
        name,
        header,
        payload,
        startByte1: computedStartByte1,
        startByte2: computedStartByte2,
    };
}
// =============================================================================
// Profile Configurations
// =============================================================================
/**
 * Profile Standard: Basic + Default
 * Frame: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * 6 bytes overhead, 255 bytes max payload
 */
exports.ProfileStandardConfig = createProfileConfig('ProfileStandard', frame_headers_1.HEADER_BASIC_CONFIG, payload_types_1.PAYLOAD_DEFAULT_CONFIG);
/**
 * Profile Sensor: Tiny + Minimal
 * Frame: [0x70] [MSG_ID] [PAYLOAD]
 * 2 bytes overhead, no length field (requires getMsgLength callback)
 */
exports.ProfileSensorConfig = createProfileConfig('ProfileSensor', frame_headers_1.HEADER_TINY_CONFIG, payload_types_1.PAYLOAD_MINIMAL_CONFIG);
/**
 * Profile IPC: None + Minimal
 * Frame: [MSG_ID] [PAYLOAD]
 * 1 byte overhead, no start bytes (requires getMsgLength callback)
 */
exports.ProfileIPCConfig = createProfileConfig('ProfileIPC', frame_headers_1.HEADER_NONE_CONFIG, payload_types_1.PAYLOAD_MINIMAL_CONFIG);
/**
 * Profile Bulk: Basic + Extended
 * Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * 8 bytes overhead, 64KB max payload
 */
exports.ProfileBulkConfig = createProfileConfig('ProfileBulk', frame_headers_1.HEADER_BASIC_CONFIG, payload_types_1.PAYLOAD_EXTENDED_CONFIG);
/**
 * Profile Network: Basic + ExtendedMultiSystemStream
 * Frame: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * 11 bytes overhead, 64KB max payload
 */
exports.ProfileNetworkConfig = createProfileConfig('ProfileNetwork', frame_headers_1.HEADER_BASIC_CONFIG, payload_types_1.PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG);
// =============================================================================
// Generic Encode/Parse Functions
// =============================================================================
/**
 * Encode a message object.
 * Automatically extracts msgId, payload, and magic numbers from the message.
 */
function encodeMessage(config, msg, options = {}) {
    const msgId = msg.getMsgId();
    if (msgId === undefined) {
        throw new Error('Message struct must have _msgid static property');
    }
    // Check if this is a variable message
    const isVariable = msg.isVariable?.() ?? false;
    // Get payload - use serialize() for all messages
    // serialize() returns variable-length data for variable messages,
    // and MAX_SIZE data for non-variable messages
    // Note: Minimal profiles (no length field) use MAX_SIZE even for variable messages
    let payload;
    if (isVariable && config.payload.hasLength && typeof msg.serialize === 'function') {
        // Variable message with length field - serialize() returns only used bytes
        payload = new Uint8Array(msg.serialize());
    }
    else {
        // Non-variable message OR minimal profile - use full buffer
        payload = new Uint8Array(msg._buffer);
    }
    const magic1 = msg.getMagic1();
    const magic2 = msg.getMagic2();
    const { seq = 0, sysId = 0, compId = 0 } = options;
    // For extended profiles with pkg_id, split the 16-bit msgId into pkg_id and msg_id.
    // If pkgId is explicitly provided in options, use it; otherwise derive from high byte.
    let pkgIdValue;
    let msgIdValue;
    if (config.payload.hasPkgId) {
        pkgIdValue = options.pkgId ?? ((msgId >> 8) & 0xFF);
        msgIdValue = msgId & 0xFF;
    }
    else {
        pkgIdValue = options.pkgId ?? 0;
        msgIdValue = msgId;
    }
    const payloadSize = payload.length;
    const headerSize = profileHeaderSize(config);
    const footerSize = profileFooterSize(config);
    const totalSize = headerSize + payloadSize + footerSize;
    const buffer = new Uint8Array(totalSize);
    let idx = 0;
    // Write start bytes
    if (config.header.numStartBytes >= 1) {
        buffer[idx++] = config.startByte1;
    }
    if (config.header.numStartBytes >= 2) {
        buffer[idx++] = config.startByte2;
    }
    const crcStart = idx;
    // Write optional fields before length
    if (config.payload.hasSeq) {
        buffer[idx++] = seq & 0xFF;
    }
    if (config.payload.hasSysId) {
        buffer[idx++] = sysId & 0xFF;
    }
    if (config.payload.hasCompId) {
        buffer[idx++] = compId & 0xFF;
    }
    // Write length field
    if (config.payload.hasLength) {
        if (config.payload.lengthBytes === 1) {
            buffer[idx++] = payloadSize & 0xFF;
        }
        else {
            buffer[idx++] = payloadSize & 0xFF;
            buffer[idx++] = (payloadSize >> 8) & 0xFF;
        }
    }
    // Write package ID if present
    if (config.payload.hasPkgId) {
        buffer[idx++] = pkgIdValue & 0xFF;
    }
    // Write message ID
    buffer[idx++] = msgIdValue & 0xFF;
    // Write payload
    buffer.set(payload, idx);
    idx += payloadSize;
    // Calculate and write CRC (extension-aware)
    const crcLen = idx - crcStart;
    const baseSize = msg.getBaseSize?.() ?? payloadSize;
    let ck;
    if (config.payload.hasLength && baseSize < payloadSize) {
        const baseEnd = crcStart + (crcLen - payloadSize) + baseSize;
        ck = (0, frame_base_1.fletcherChecksumExt)(buffer, crcStart, baseEnd, crcStart + crcLen, magic1, magic2);
    }
    else {
        ck = (0, frame_base_1.fletcherChecksum)(buffer, crcStart, crcStart + crcLen, magic1, magic2);
    }
    buffer[idx++] = ck[0];
    buffer[idx++] = ck[1];
    return buffer;
}
/**
 * Generic parse function for frames with CRC.
 * @param config Profile configuration
 * @param buffer Buffer containing frame data
 * @param getMessageInfo Optional callback to get message info (size and magic numbers)
 */
function parseFrameWithCrc(config, buffer, getMessageInfo) {
    const result = (0, frame_base_1.createFrameMsgInfo)();
    const length = buffer.length;
    const headerSize = profileHeaderSize(config);
    const footerSize = profileFooterSize(config);
    if (length < headerSize + footerSize) {
        return result;
    }
    let idx = 0;
    // Verify start bytes
    if (config.header.numStartBytes >= 1) {
        if (buffer[idx++] !== config.startByte1) {
            return result;
        }
    }
    if (config.header.numStartBytes >= 2) {
        if (buffer[idx++] !== config.startByte2) {
            return result;
        }
    }
    const crcStart = idx;
    // Skip optional fields before length
    if (config.payload.hasSeq)
        idx++;
    if (config.payload.hasSysId)
        idx++;
    if (config.payload.hasCompId)
        idx++;
    // Read length field
    let msgLen = 0;
    if (config.payload.hasLength) {
        if (config.payload.lengthBytes === 1) {
            msgLen = buffer[idx++];
        }
        else {
            msgLen = buffer[idx] | (buffer[idx + 1] << 8);
            idx += 2;
        }
    }
    // Read message ID (16-bit: high byte is pkg_id when hasPkgId, low byte is msg_id)
    let msgId = 0;
    if (config.payload.hasPkgId) {
        msgId = buffer[idx++] << 8; // pkg_id (high byte)
    }
    msgId |= buffer[idx++]; // msg_id (low byte)
    // Verify total size
    const totalSize = headerSize + msgLen + footerSize;
    if (length < totalSize) {
        return result;
    }
    // Verify CRC (extension-aware)
    const crcLen = totalSize - crcStart - footerSize;
    // Get magic numbers and base_size for this message type
    let magic1 = 0, magic2 = 0;
    let baseSize = msgLen;
    if (getMessageInfo) {
        const info = getMessageInfo(msgId);
        if (info) {
            magic1 = info.magic1;
            magic2 = info.magic2;
            baseSize = info.baseSize ?? msgLen;
        }
    }
    let ck;
    if (config.payload.hasLength && baseSize < msgLen) {
        const baseEnd = crcStart + (crcLen - msgLen) + baseSize;
        ck = (0, frame_base_1.fletcherChecksumExt)(buffer, crcStart, baseEnd, crcStart + crcLen, magic1, magic2);
    }
    else {
        ck = (0, frame_base_1.fletcherChecksum)(buffer, crcStart, crcStart + crcLen, magic1, magic2);
    }
    if (ck[0] !== buffer[totalSize - 2] || ck[1] !== buffer[totalSize - 1]) {
        // A complete frame was found but failed CRC. Expose frameSize so callers
        // can skip this frame and continue scanning subsequent frames.
        result.status = frame_base_1.FrameMsgStatus.CrcFailure;
        result.frameSize = totalSize;
        return result;
    }
    // Extract message data
    result.valid = true;
    result.msgId = msgId;
    result.msgLen = msgLen;
    result.msgData = buffer.subarray(headerSize, headerSize + msgLen);
    result.frameSize = totalSize;
    return result;
}
/**
 * Generic parse function for minimal frames (requires getMessageInfo callback for size).
 * @param config Profile configuration
 * @param buffer Buffer containing frame data
 * @param getMessageInfo Callback to get message info (size is required, magic numbers ignored for minimal frames)
 */
function parseFrameMinimal(config, buffer, getMessageInfo) {
    const result = (0, frame_base_1.createFrameMsgInfo)();
    const headerSize = profileHeaderSize(config);
    if (buffer.length < headerSize) {
        return result;
    }
    let idx = 0;
    // Verify start bytes
    if (config.header.numStartBytes >= 1) {
        if (buffer[idx++] !== config.startByte1) {
            return result;
        }
    }
    if (config.header.numStartBytes >= 2) {
        if (buffer[idx++] !== config.startByte2) {
            return result;
        }
    }
    // Read message ID
    const msgId = buffer[idx];
    // Get message length from callback
    const info = getMessageInfo(msgId);
    if (!info) {
        return result;
    }
    const msgLen = info.size;
    const totalSize = headerSize + msgLen;
    if (buffer.length < totalSize) {
        return result;
    }
    // Extract message data
    result.valid = true;
    result.msgId = msgId;
    result.msgLen = msgLen;
    result.msgData = buffer.subarray(headerSize, headerSize + msgLen);
    result.frameSize = totalSize;
    return result;
}
// =============================================================================
// BufferReader - Iterate through multiple frames in a buffer
// =============================================================================
/**
 * BufferReader - Iterate through a buffer parsing multiple frames.
 *
 * Usage:
 *   const reader = new BufferReader(ProfileStandardConfig, buffer, getMessageInfo);
 *   let result = reader.next();
 *   while (result.valid) {
 *       // Process result.msgId, result.msgData, result.msgLen
 *       result = reader.next();
 *   }
 */
class BufferReader {
    constructor(config, buffer, getMessageInfo) {
        this.config = config;
        this.buffer = buffer;
        this.size = buffer.length;
        this._offset = 0;
        this.getMessageInfo = getMessageInfo;
    }
    /**
     * Parse the next frame in the buffer.
     * Returns FrameMsgInfo with valid=true if successful, valid=false if no more frames.
     */
    next() {
        if (this._offset >= this.size) {
            return (0, frame_base_1.createFrameMsgInfo)();
        }
        const remaining = this.buffer.subarray(this._offset);
        let result;
        if (this.config.payload.hasCrc || this.config.payload.hasLength) {
            result = parseFrameWithCrc(this.config, remaining, this.getMessageInfo);
        }
        else {
            if (!this.getMessageInfo) {
                // No more valid data to parse without message info callback
                this._offset = this.size;
                return (0, frame_base_1.createFrameMsgInfo)();
            }
            result = parseFrameMinimal(this.config, remaining, this.getMessageInfo);
        }
        if (result.valid) {
            const frameSize = profileHeaderSize(this.config) + result.msgLen + profileFooterSize(this.config);
            this._offset += frameSize;
        }
        else {
            // If a complete frame failed CRC, skip it and continue on next call.
            if (result.status === frame_base_1.FrameMsgStatus.CrcFailure && (result.frameSize ?? 0) > 0) {
                this._offset += result.frameSize;
            }
            else {
                // No more valid frames - stop parsing
                this._offset = this.size;
            }
        }
        return result;
    }
    /** Reset the reader to the beginning of the buffer. */
    reset() {
        this._offset = 0;
    }
    /** Get the current offset in the buffer. */
    get offset() {
        return this._offset;
    }
    /** Get the remaining bytes in the buffer. */
    get remaining() {
        return Math.max(0, this.size - this._offset);
    }
    /** Check if there are more bytes to parse. */
    hasMore() {
        return this._offset < this.size;
    }
}
exports.BufferReader = BufferReader;
// =============================================================================
// BufferWriter - Encode multiple frames with automatic offset tracking
// =============================================================================
/**
 * BufferWriter - Encode multiple frames into a buffer with automatic offset tracking.
 *
 * Usage:
 *   const writer = new BufferWriter(ProfileStandardConfig, 1024);
 *   writer.write(msg1);  // msg1 is a struct instance with _msgid and _buffer
 *   writer.write(msg2);
 *   const encodedData = writer.data();
 *   const totalBytes = writer.size;
 *
 * For profiles with extra header fields:
 *   const writer = new BufferWriter(ProfileNetworkConfig, 1024);
 *   writer.write(msg, { seq: 1, sysId: 1, compId: 1 });
 */
class BufferWriter {
    constructor(config, capacity) {
        this.config = config;
        this.capacity = capacity;
        this.buffer = new Uint8Array(capacity);
        this._offset = 0;
    }
    /**
     * Write a message to the buffer.
     * The message must be a MessageBase instance (generated struct class).
     * Magic numbers for checksum are automatically extracted from the message class
     * if _magic1/_magic2 static properties are present.
     * Returns the number of bytes written, or 0 on failure.
     */
    write(msg, options = {}) {
        const encoded = encodeMessage(this.config, msg, options);
        const written = encoded.length;
        if (this._offset + written > this.capacity) {
            return 0;
        }
        this.buffer.set(encoded, this._offset);
        this._offset += written;
        return written;
    }
    /** Reset the writer to the beginning of the buffer. */
    reset() {
        this._offset = 0;
    }
    /** Get the total number of bytes written. */
    get size() {
        return this._offset;
    }
    /** Get the remaining capacity in the buffer. */
    get remaining() {
        return Math.max(0, this.capacity - this._offset);
    }
    /** Get the written data as a new Uint8Array. */
    data() {
        return this.buffer.slice(0, this._offset);
    }
}
exports.BufferWriter = BufferWriter;
// =============================================================================
// AccumulatingReader - Unified parser for buffer and byte-by-byte streaming
// =============================================================================
/** Parser state for streaming mode */
var AccumulatingReaderState;
(function (AccumulatingReaderState) {
    AccumulatingReaderState[AccumulatingReaderState["IDLE"] = 0] = "IDLE";
    AccumulatingReaderState[AccumulatingReaderState["LOOKING_FOR_START1"] = 1] = "LOOKING_FOR_START1";
    AccumulatingReaderState[AccumulatingReaderState["LOOKING_FOR_START2"] = 2] = "LOOKING_FOR_START2";
    AccumulatingReaderState[AccumulatingReaderState["COLLECTING_HEADER"] = 3] = "COLLECTING_HEADER";
    AccumulatingReaderState[AccumulatingReaderState["COLLECTING_PAYLOAD"] = 4] = "COLLECTING_PAYLOAD";
    AccumulatingReaderState[AccumulatingReaderState["BUFFER_MODE"] = 5] = "BUFFER_MODE";
})(AccumulatingReaderState || (exports.AccumulatingReaderState = AccumulatingReaderState = {}));
/**
 * AccumulatingReader - Unified parser for buffer and byte-by-byte streaming input.
 *
 * Handles partial messages across buffer boundaries and supports both:
 * - Buffer mode: addData() for processing chunks of data
 * - Stream mode: pushByte() for byte-by-byte processing (e.g., UART)
 *
 * Buffer mode usage:
 *   const reader = new AccumulatingReader(ProfileStandardConfig, getMessageInfo);
 *   reader.addData(chunk1);
 *   let result = reader.next();
 *   while (result.valid) {
 *       // Process complete messages
 *       result = reader.next();
 *   }
 *
 * Stream mode usage:
 *   const reader = new AccumulatingReader(ProfileStandardConfig, getMessageInfo);
 *   while (receiving) {
 *       const byte = readByte();
 *       const result = reader.pushByte(byte);
 *       if (result.valid) {
 *           // Process complete message
 *       }
 *   }
 */
class AccumulatingReader {
    constructor(config, getMessageInfo, bufferSize = 1024) {
        this.config = config;
        this.getMessageInfo = getMessageInfo;
        this.bufferSize = bufferSize;
        this.internalBuffer = new Uint8Array(bufferSize);
        this.internalDataLen = 0;
        this.expectedFrameSize = 0;
        this._state = AccumulatingReaderState.IDLE;
        this.currentBuffer = null;
        this.currentSize = 0;
        this.currentOffset = 0;
        this._diagnostics = { cntCrcFailures: 0, cntSyncRecoveries: 0, cntFailedBytes: 0, cntLenErrors: 0, cntSeqGaps: 0 };
        this._lastSeq = null;
    }
    // =========================================================================
    // Buffer Mode API
    // =========================================================================
    /**
     * Add a new buffer of data to process.
     */
    addData(buffer) {
        this.currentBuffer = buffer;
        this.currentSize = buffer.length;
        this.currentOffset = 0;
        this._state = AccumulatingReaderState.BUFFER_MODE;
        // If we have partial data in internal buffer, try to complete it
        if (this.internalDataLen > 0) {
            const spaceAvailable = this.bufferSize - this.internalDataLen;
            if (buffer.length <= spaceAvailable) {
                this.internalBuffer.set(buffer, this.internalDataLen);
                this.internalDataLen += buffer.length;
            }
            else {
                // Partial data won't fit: discard it and start fresh from the new buffer
                this._diagnostics.cntFailedBytes += this.internalDataLen;
                this._diagnostics.cntSyncRecoveries++;
                this.internalDataLen = 0;
                this.expectedFrameSize = 0;
            }
        }
    }
    /**
     * Parse the next frame (buffer mode).
     */
    next() {
        if (this._state !== AccumulatingReaderState.BUFFER_MODE) {
            return this.withDiagnostics((0, frame_base_1.createFrameMsgInfo)());
        }
        // First, try to complete a partial message from the internal buffer
        if (this.internalDataLen > 0 && this.currentOffset === 0) {
            const internalBytes = this.internalBuffer.subarray(0, this.internalDataLen);
            const result = this.parseBuffer(internalBytes);
            if (result.valid) {
                result.msgData = result.msgData.slice(); // own copy — internalBuffer is reused
                const frameSize = profileHeaderSize(this.config) + result.msgLen + profileFooterSize(this.config);
                const partialLen = this.internalDataLen > this.currentSize ? this.internalDataLen - this.currentSize : 0;
                const bytesFromCurrent = frameSize > partialLen ? frameSize - partialLen : 0;
                this.currentOffset = bytesFromCurrent;
                this.internalDataLen = 0;
                this.expectedFrameSize = 0;
                return this.withDiagnostics(result);
            }
            else {
                if (result.status === frame_base_1.FrameMsgStatus.CrcFailure && (result.frameSize ?? 0) > 0) {
                    // Consume failed frame bytes from internal accumulation to avoid permanent retries.
                    this._diagnostics.cntCrcFailures++;
                    this._diagnostics.cntFailedBytes += result.frameSize;
                    this._diagnostics.cntSyncRecoveries++;
                    const consumed = Math.min(result.frameSize, this.internalDataLen);
                    const remainingBytes = this.internalDataLen - consumed;
                    if (remainingBytes > 0) {
                        this.internalBuffer.copyWithin(0, consumed, this.internalDataLen);
                    }
                    this.internalDataLen = remainingBytes;
                    this.expectedFrameSize = 0;
                }
                return this.withDiagnostics((0, frame_base_1.createFrameMsgInfo)());
            }
        }
        // Parse from current buffer
        if (this.currentBuffer === null || this.currentOffset >= this.currentSize) {
            return this.withDiagnostics((0, frame_base_1.createFrameMsgInfo)());
        }
        const remaining = this.currentBuffer.subarray(this.currentOffset);
        const result = this.parseBuffer(remaining);
        if (result.valid) {
            const frameSize = profileHeaderSize(this.config) + result.msgLen + profileFooterSize(this.config);
            this.currentOffset += frameSize;
            return this.withDiagnostics(result);
        }
        if (result.status === frame_base_1.FrameMsgStatus.CrcFailure && (result.frameSize ?? 0) > 0) {
            // CRC-failed complete frame: skip it and keep scanning remaining data.
            this._diagnostics.cntCrcFailures++;
            this._diagnostics.cntFailedBytes += result.frameSize;
            this._diagnostics.cntSyncRecoveries++;
            this.currentOffset += result.frameSize;
            return this.withDiagnostics(result);
        }
        // Parse failed - might be partial message at end of buffer
        const remainingLen = this.currentSize - this.currentOffset;
        if (remainingLen > 0 && remainingLen < this.bufferSize) {
            this.internalBuffer.set(remaining, 0);
            this.internalDataLen = remainingLen;
            this.currentOffset = this.currentSize;
        }
        return this.withDiagnostics((0, frame_base_1.createFrameMsgInfo)());
    }
    // =========================================================================
    // Stream Mode API
    // =========================================================================
    /**
     * Push a single byte for parsing (stream mode).
     */
    pushByte(byte) {
        // Initialize state on first byte if idle
        if (this._state === AccumulatingReaderState.IDLE || this._state === AccumulatingReaderState.BUFFER_MODE) {
            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
            this.internalDataLen = 0;
            this.expectedFrameSize = 0;
        }
        switch (this._state) {
            case AccumulatingReaderState.LOOKING_FOR_START1:
                return this.handleLookingForStart1(byte);
            case AccumulatingReaderState.LOOKING_FOR_START2:
                return this.handleLookingForStart2(byte);
            case AccumulatingReaderState.COLLECTING_HEADER:
                return this.handleCollectingHeader(byte);
            case AccumulatingReaderState.COLLECTING_PAYLOAD:
                return this.handleCollectingPayload(byte);
            default:
                this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                return this.withDiagnostics((0, frame_base_1.createFrameMsgInfo)());
        }
    }
    handleLookingForStart1(byte) {
        if (this.config.header.numStartBytes === 0) {
            this.internalBuffer[0] = byte;
            this.internalDataLen = 1;
            if (!this.config.payload.hasLength && !this.config.payload.hasCrc) {
                return this.handleMinimalMsgId(byte);
            }
            else {
                this._state = AccumulatingReaderState.COLLECTING_HEADER;
            }
        }
        else {
            if (byte === this.config.startByte1) {
                this.internalBuffer[0] = byte;
                this.internalDataLen = 1;
                if (this.config.header.numStartBytes === 1) {
                    this._state = AccumulatingReaderState.COLLECTING_HEADER;
                }
                else {
                    this._state = AccumulatingReaderState.LOOKING_FOR_START2;
                }
            }
        }
        const r = (0, frame_base_1.createFrameMsgInfo)();
        r.status = (this._state === AccumulatingReaderState.LOOKING_FOR_START1)
            ? frame_base_1.FrameMsgStatus.WaitingForStart
            : frame_base_1.FrameMsgStatus.Collecting;
        return this.withDiagnostics(r);
    }
    handleLookingForStart2(byte) {
        if (byte === this.config.startByte2) {
            this.internalBuffer[this.internalDataLen++] = byte;
            this._state = AccumulatingReaderState.COLLECTING_HEADER;
        }
        else if (byte === this.config.startByte1) {
            this.internalBuffer[0] = byte;
            this.internalDataLen = 1;
        }
        else {
            this._diagnostics.cntFailedBytes += this.internalDataLen + 1;
            this._diagnostics.cntSyncRecoveries++;
            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
            this.internalDataLen = 0;
            const r = (0, frame_base_1.createFrameMsgInfo)();
            r.status = frame_base_1.FrameMsgStatus.SyncRecovery;
            return this.withDiagnostics(r);
        }
        const r = (0, frame_base_1.createFrameMsgInfo)();
        r.status = frame_base_1.FrameMsgStatus.Collecting;
        return this.withDiagnostics(r);
    }
    handleCollectingHeader(byte) {
        if (this.internalDataLen >= this.bufferSize) {
            this._diagnostics.cntFailedBytes += this.internalDataLen + 1;
            this._diagnostics.cntSyncRecoveries++;
            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
            this.internalDataLen = 0;
            const r = (0, frame_base_1.createFrameMsgInfo)();
            r.status = frame_base_1.FrameMsgStatus.SyncRecovery;
            return this.withDiagnostics(r);
        }
        this.internalBuffer[this.internalDataLen++] = byte;
        const headerSize = profileHeaderSize(this.config);
        const footerSize = profileFooterSize(this.config);
        if (this.internalDataLen >= headerSize) {
            if (!this.config.payload.hasLength && !this.config.payload.hasCrc) {
                const msgId = this.internalBuffer[headerSize - 1];
                if (this.getMessageInfo) {
                    const info = this.getMessageInfo(msgId);
                    if (info !== undefined) {
                        const msgLen = info.size;
                        this.expectedFrameSize = headerSize + msgLen;
                        if (this.expectedFrameSize > this.bufferSize) {
                            this._diagnostics.cntFailedBytes += this.internalDataLen;
                            this._diagnostics.cntSyncRecoveries++;
                            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                            this.internalDataLen = 0;
                            const r = (0, frame_base_1.createFrameMsgInfo)();
                            r.status = frame_base_1.FrameMsgStatus.SyncRecovery;
                            return this.withDiagnostics(r);
                        }
                        if (msgLen === 0) {
                            const result = (0, frame_base_1.createFrameMsgInfo)();
                            result.valid = true;
                            result.msgId = msgId;
                            result.msgLen = 0;
                            result.msgData = new Uint8Array(0);
                            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                            this.internalDataLen = 0;
                            this.expectedFrameSize = 0;
                            return this.withDiagnostics(result);
                        }
                        this._state = AccumulatingReaderState.COLLECTING_PAYLOAD;
                    }
                    else {
                        this._diagnostics.cntFailedBytes += this.internalDataLen;
                        this._diagnostics.cntSyncRecoveries++;
                        this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                        this.internalDataLen = 0;
                        const r = (0, frame_base_1.createFrameMsgInfo)();
                        r.status = frame_base_1.FrameMsgStatus.SyncRecovery;
                        return this.withDiagnostics(r);
                    }
                }
                else {
                    this._diagnostics.cntFailedBytes += this.internalDataLen;
                    this._diagnostics.cntSyncRecoveries++;
                    this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                    this.internalDataLen = 0;
                    const r = (0, frame_base_1.createFrameMsgInfo)();
                    r.status = frame_base_1.FrameMsgStatus.SyncRecovery;
                    return this.withDiagnostics(r);
                }
            }
            else {
                let lenOffset = this.config.header.numStartBytes;
                if (this.config.payload.hasSeq)
                    lenOffset++;
                if (this.config.payload.hasSysId)
                    lenOffset++;
                if (this.config.payload.hasCompId)
                    lenOffset++;
                let payloadLen = 0;
                if (this.config.payload.hasLength) {
                    if (this.config.payload.lengthBytes === 1) {
                        payloadLen = this.internalBuffer[lenOffset];
                    }
                    else {
                        payloadLen = this.internalBuffer[lenOffset] | (this.internalBuffer[lenOffset + 1] << 8);
                    }
                }
                // Check for length mismatch against expected message struct size
                if (this.config.payload.hasLength && this.getMessageInfo) {
                    let fullMsgId = 0;
                    if (this.config.payload.hasPkgId) {
                        fullMsgId = (this.internalBuffer[headerSize - 2] << 8);
                    }
                    fullMsgId |= this.internalBuffer[headerSize - 1];
                    const info = this.getMessageInfo(fullMsgId);
                    if (info !== undefined) {
                        const minSize = info.minSize ?? (info.isVariable ? 0 : info.size);
                        if (payloadLen > info.size || payloadLen < minSize) {
                            this._diagnostics.cntLenErrors++;
                        }
                    }
                }
                this.expectedFrameSize = headerSize + payloadLen + footerSize;
                if (this.expectedFrameSize > this.bufferSize) {
                    this._diagnostics.cntFailedBytes += this.internalDataLen;
                    this._diagnostics.cntSyncRecoveries++;
                    this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                    this.internalDataLen = 0;
                    const r = (0, frame_base_1.createFrameMsgInfo)();
                    r.status = frame_base_1.FrameMsgStatus.SyncRecovery;
                    return this.withDiagnostics(r);
                }
                if (this.internalDataLen >= this.expectedFrameSize) {
                    return this.withDiagnostics(this.validateAndReturn());
                }
                this._state = AccumulatingReaderState.COLLECTING_PAYLOAD;
            }
        }
        const r = (0, frame_base_1.createFrameMsgInfo)();
        r.status = frame_base_1.FrameMsgStatus.Collecting;
        return this.withDiagnostics(r);
    }
    handleCollectingPayload(byte) {
        if (this.internalDataLen >= this.bufferSize) {
            this._diagnostics.cntFailedBytes += this.internalDataLen + 1;
            this._diagnostics.cntSyncRecoveries++;
            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
            this.internalDataLen = 0;
            const r = (0, frame_base_1.createFrameMsgInfo)();
            r.status = frame_base_1.FrameMsgStatus.SyncRecovery;
            return this.withDiagnostics(r);
        }
        this.internalBuffer[this.internalDataLen++] = byte;
        if (this.internalDataLen >= this.expectedFrameSize) {
            return this.withDiagnostics(this.validateAndReturn());
        }
        const r = (0, frame_base_1.createFrameMsgInfo)();
        r.status = frame_base_1.FrameMsgStatus.Collecting;
        return this.withDiagnostics(r);
    }
    handleMinimalMsgId(msgId) {
        if (this.getMessageInfo) {
            const info = this.getMessageInfo(msgId);
            if (info !== undefined) {
                const msgLen = info.size;
                const headerSize = profileHeaderSize(this.config);
                this.expectedFrameSize = headerSize + msgLen;
                if (this.expectedFrameSize > this.bufferSize) {
                    this._diagnostics.cntFailedBytes += this.internalDataLen;
                    this._diagnostics.cntSyncRecoveries++;
                    this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                    this.internalDataLen = 0;
                    const r = (0, frame_base_1.createFrameMsgInfo)();
                    r.status = frame_base_1.FrameMsgStatus.SyncRecovery;
                    return this.withDiagnostics(r);
                }
                if (msgLen === 0) {
                    const result = (0, frame_base_1.createFrameMsgInfo)();
                    result.valid = true;
                    result.msgId = msgId;
                    result.msgLen = 0;
                    result.msgData = new Uint8Array(0);
                    this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                    this.internalDataLen = 0;
                    this.expectedFrameSize = 0;
                    return this.withDiagnostics(result);
                }
                this._state = AccumulatingReaderState.COLLECTING_PAYLOAD;
            }
            else {
                this._diagnostics.cntFailedBytes += this.internalDataLen;
                this._diagnostics.cntSyncRecoveries++;
                this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                this.internalDataLen = 0;
                const r = (0, frame_base_1.createFrameMsgInfo)();
                r.status = frame_base_1.FrameMsgStatus.SyncRecovery;
                return this.withDiagnostics(r);
            }
        }
        else {
            this._diagnostics.cntFailedBytes += this.internalDataLen;
            this._diagnostics.cntSyncRecoveries++;
            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
            this.internalDataLen = 0;
            const r = (0, frame_base_1.createFrameMsgInfo)();
            r.status = frame_base_1.FrameMsgStatus.SyncRecovery;
            return this.withDiagnostics(r);
        }
        const r = (0, frame_base_1.createFrameMsgInfo)();
        r.status = frame_base_1.FrameMsgStatus.Collecting;
        return this.withDiagnostics(r);
    }
    validateAndReturn() {
        const internalBytes = this.internalBuffer.subarray(0, this.internalDataLen);
        const result = this.parseBuffer(internalBytes);
        this._state = AccumulatingReaderState.LOOKING_FOR_START1;
        this.internalDataLen = 0;
        this.expectedFrameSize = 0;
        if (result.valid) {
            result.msgData = result.msgData.slice(); // own copy — internalBuffer is reused
            // Check for sequence gap on profiles that carry a sequence number
            if (this.config.payload.hasSeq) {
                const seq = this.internalBuffer[this.config.header.numStartBytes];
                if (this._lastSeq !== null) {
                    const expectedSeq = (this._lastSeq + 1) & 0xFF;
                    if (seq !== expectedSeq) {
                        this._diagnostics.cntSeqGaps++;
                    }
                }
                this._lastSeq = seq;
            }
        }
        else {
            if (this.config.payload.hasCrc) {
                this._diagnostics.cntCrcFailures++;
                result.status = frame_base_1.FrameMsgStatus.CrcFailure;
            }
            else {
                result.status = frame_base_1.FrameMsgStatus.SyncRecovery;
            }
            this._diagnostics.cntFailedBytes += internalBytes.length;
            this._diagnostics.cntSyncRecoveries++;
        }
        return this.withDiagnostics(result);
    }
    parseBuffer(buffer) {
        if (this.config.payload.hasCrc || this.config.payload.hasLength) {
            return parseFrameWithCrc(this.config, buffer, this.getMessageInfo);
        }
        else {
            if (!this.getMessageInfo) {
                return (0, frame_base_1.createFrameMsgInfo)();
            }
            return parseFrameMinimal(this.config, buffer, this.getMessageInfo);
        }
    }
    // =========================================================================
    // Common API
    // =========================================================================
    /** Check if there might be more data to parse (buffer mode only). */
    hasMore() {
        if (this._state !== AccumulatingReaderState.BUFFER_MODE)
            return false;
        return (this.internalDataLen > 0) || (this.currentBuffer !== null && this.currentOffset < this.currentSize);
    }
    /** Check if there's a partial message waiting for more data. */
    hasPartial() {
        return this.internalDataLen > 0;
    }
    /** Get the size of the partial message data (0 if none). */
    partialSize() {
        return this.internalDataLen;
    }
    /** Get current parser state (for debugging). */
    get state() {
        return this._state;
    }
    /** Reset the reader, clearing any partial message data. */
    reset() {
        this.internalDataLen = 0;
        this.expectedFrameSize = 0;
        this._state = AccumulatingReaderState.IDLE;
        this.currentBuffer = null;
        this.currentSize = 0;
        this.currentOffset = 0;
        this._lastSeq = null;
    }
    /** Get a snapshot of the current diagnostic counters. */
    get diagnostics() {
        return { ...this._diagnostics };
    }
    /** Reset all diagnostic counters to zero. */
    resetDiagnostics() {
        this._diagnostics = { cntCrcFailures: 0, cntSyncRecoveries: 0, cntFailedBytes: 0, cntLenErrors: 0, cntSeqGaps: 0 };
    }
    withDiagnostics(result) {
        result.diagnostics = { ...this._diagnostics };
        return result;
    }
}
exports.AccumulatingReader = AccumulatingReader;
// =============================================================================
// Profile-specific subclasses for standard profiles
// =============================================================================
// -----------------------------------------------------------------------------
// ProfileStandard subclasses
// -----------------------------------------------------------------------------
class ProfileStandardReader extends BufferReader {
    constructor(buffer, getMessageInfo) {
        super(exports.ProfileStandardConfig, buffer, getMessageInfo);
    }
}
exports.ProfileStandardReader = ProfileStandardReader;
class ProfileStandardWriter extends BufferWriter {
    constructor(capacity = 1024) {
        super(exports.ProfileStandardConfig, capacity);
    }
}
exports.ProfileStandardWriter = ProfileStandardWriter;
class ProfileStandardAccumulatingReader extends AccumulatingReader {
    constructor(getMessageInfo, bufferSize = 1024) {
        super(exports.ProfileStandardConfig, getMessageInfo, bufferSize);
    }
}
exports.ProfileStandardAccumulatingReader = ProfileStandardAccumulatingReader;
// -----------------------------------------------------------------------------
// ProfileSensor subclasses
// -----------------------------------------------------------------------------
class ProfileSensorReader extends BufferReader {
    constructor(buffer, getMessageInfo) {
        super(exports.ProfileSensorConfig, buffer, getMessageInfo);
    }
}
exports.ProfileSensorReader = ProfileSensorReader;
class ProfileSensorWriter extends BufferWriter {
    constructor(capacity = 1024) {
        super(exports.ProfileSensorConfig, capacity);
    }
}
exports.ProfileSensorWriter = ProfileSensorWriter;
class ProfileSensorAccumulatingReader extends AccumulatingReader {
    constructor(getMessageInfo, bufferSize = 1024) {
        super(exports.ProfileSensorConfig, getMessageInfo, bufferSize);
    }
}
exports.ProfileSensorAccumulatingReader = ProfileSensorAccumulatingReader;
// -----------------------------------------------------------------------------
// ProfileIPC subclasses
// -----------------------------------------------------------------------------
class ProfileIPCReader extends BufferReader {
    constructor(buffer, getMessageInfo) {
        super(exports.ProfileIPCConfig, buffer, getMessageInfo);
    }
}
exports.ProfileIPCReader = ProfileIPCReader;
class ProfileIPCWriter extends BufferWriter {
    constructor(capacity = 1024) {
        super(exports.ProfileIPCConfig, capacity);
    }
}
exports.ProfileIPCWriter = ProfileIPCWriter;
class ProfileIPCAccumulatingReader extends AccumulatingReader {
    constructor(getMessageInfo, bufferSize = 1024) {
        super(exports.ProfileIPCConfig, getMessageInfo, bufferSize);
    }
}
exports.ProfileIPCAccumulatingReader = ProfileIPCAccumulatingReader;
// -----------------------------------------------------------------------------
// ProfileBulk subclasses
// -----------------------------------------------------------------------------
class ProfileBulkReader extends BufferReader {
    constructor(buffer, getMessageInfo) {
        super(exports.ProfileBulkConfig, buffer, getMessageInfo);
    }
}
exports.ProfileBulkReader = ProfileBulkReader;
class ProfileBulkWriter extends BufferWriter {
    constructor(capacity = 1024) {
        super(exports.ProfileBulkConfig, capacity);
    }
}
exports.ProfileBulkWriter = ProfileBulkWriter;
class ProfileBulkAccumulatingReader extends AccumulatingReader {
    constructor(getMessageInfo, bufferSize = 1024) {
        super(exports.ProfileBulkConfig, getMessageInfo, bufferSize);
    }
}
exports.ProfileBulkAccumulatingReader = ProfileBulkAccumulatingReader;
// -----------------------------------------------------------------------------
// ProfileNetwork subclasses
// -----------------------------------------------------------------------------
class ProfileNetworkReader extends BufferReader {
    constructor(buffer, getMessageInfo) {
        super(exports.ProfileNetworkConfig, buffer, getMessageInfo);
    }
}
exports.ProfileNetworkReader = ProfileNetworkReader;
class ProfileNetworkWriter extends BufferWriter {
    constructor(capacity = 1024) {
        super(exports.ProfileNetworkConfig, capacity);
    }
}
exports.ProfileNetworkWriter = ProfileNetworkWriter;
class ProfileNetworkAccumulatingReader extends AccumulatingReader {
    constructor(getMessageInfo, bufferSize = 1024) {
        super(exports.ProfileNetworkConfig, getMessageInfo, bufferSize);
    }
}
exports.ProfileNetworkAccumulatingReader = ProfileNetworkAccumulatingReader;
