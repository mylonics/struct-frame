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

import {
    HeaderConfig,
    HEADER_NONE_CONFIG,
    HEADER_TINY_CONFIG,
    HEADER_BASIC_CONFIG,
    PAYLOAD_TYPE_BASE,
} from './frame-headers';
import {
    PayloadConfig,
    PAYLOAD_MINIMAL_CONFIG,
    PAYLOAD_DEFAULT_CONFIG,
    PAYLOAD_EXTENDED_CONFIG,
    PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG,
    payloadHeaderSize,
    payloadFooterSize,
} from './payload-types';
import { fletcherChecksum, createFrameMsgInfo, FrameMsgInfo } from './frame-base';
import { MessageBase } from './struct-base';

// =============================================================================
// Profile Configuration Interface
// =============================================================================

/**
 * Profile configuration - combines a HeaderConfig with a PayloadConfig.
 * Mirrors the C++ ProfileConfig template structure.
 */
export interface FrameProfileConfig {
    readonly name: string;
    readonly header: HeaderConfig;
    readonly payload: PayloadConfig;
    /** Computed start byte 1 (handles dynamic payload type encoding) */
    readonly startByte1: number;
    /** Computed start byte 2 (handles dynamic payload type encoding) */
    readonly startByte2: number;
}

export interface EncodeOptions {
    seq?: number;
    sysId?: number;
    compId?: number;
    pkgId?: number;
    magic1?: number;
    magic2?: number;
}

// =============================================================================
// Message Info Interface - Unified lookup for parsing
// =============================================================================

/**
 * Message info returned by the getMessageInfo callback.
 * Contains all information needed to parse a message by ID.
 */
export interface MessageInfo {
    /** Message size in bytes */
    size: number;
    /** Magic number 1 (added at end of CRC checksum calculation) */
    magic1: number;
    /** Magic number 2 (added at end of CRC checksum calculation) */
    magic2: number;
}

/**
 * Callback type for looking up message info by ID.
 * Returns MessageInfo if the message ID is known, undefined otherwise.
 */
export type GetMessageInfo = (msgId: number) => MessageInfo | undefined;

// =============================================================================
// Profile Helper Functions
// =============================================================================

/** Get the total header size for a profile (start bytes + payload header fields) */
export function profileHeaderSize(config: FrameProfileConfig): number {
    return config.header.numStartBytes + payloadHeaderSize(config.payload);
}

/** Get the footer size for a profile */
export function profileFooterSize(config: FrameProfileConfig): number {
    return payloadFooterSize(config.payload);
}

/** Get the total overhead for a profile (header + footer) */
export function profileOverhead(config: FrameProfileConfig): number {
    return profileHeaderSize(config) + profileFooterSize(config);
}

// =============================================================================
// Profile Configuration Factory
// =============================================================================

/**
 * Create a profile configuration from header and payload configs.
 */
function createProfileConfig(
    name: string,
    header: HeaderConfig,
    payload: PayloadConfig
): FrameProfileConfig {
    // Compute start byte1 dynamically for Tiny header (single byte encodes payload type)
    const computedStartByte1 = header.encodesPayloadType && header.numStartBytes === 1
        ? PAYLOAD_TYPE_BASE + payload.payloadType
        : header.startByte1;

    // Compute start byte2 dynamically for headers that encode payload type
    const computedStartByte2 = header.encodesPayloadType && header.numStartBytes === 2
        ? PAYLOAD_TYPE_BASE + payload.payloadType
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
export const ProfileStandardConfig: FrameProfileConfig = createProfileConfig(
    'ProfileStandard',
    HEADER_BASIC_CONFIG,
    PAYLOAD_DEFAULT_CONFIG
);

/**
 * Profile Sensor: Tiny + Minimal
 * Frame: [0x70] [MSG_ID] [PAYLOAD]
 * 2 bytes overhead, no length field (requires get_msg_length callback)
 */
export const ProfileSensorConfig: FrameProfileConfig = createProfileConfig(
    'ProfileSensor',
    HEADER_TINY_CONFIG,
    PAYLOAD_MINIMAL_CONFIG
);

/**
 * Profile IPC: None + Minimal
 * Frame: [MSG_ID] [PAYLOAD]
 * 1 byte overhead, no start bytes (requires get_msg_length callback)
 */
export const ProfileIPCConfig: FrameProfileConfig = createProfileConfig(
    'ProfileIPC',
    HEADER_NONE_CONFIG,
    PAYLOAD_MINIMAL_CONFIG
);

/**
 * Profile Bulk: Basic + Extended
 * Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * 8 bytes overhead, 64KB max payload
 */
export const ProfileBulkConfig: FrameProfileConfig = createProfileConfig(
    'ProfileBulk',
    HEADER_BASIC_CONFIG,
    PAYLOAD_EXTENDED_CONFIG
);

/**
 * Profile Network: Basic + ExtendedMultiSystemStream
 * Frame: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * 11 bytes overhead, 64KB max payload
 */
export const ProfileNetworkConfig: FrameProfileConfig = createProfileConfig(
    'ProfileNetwork',
    HEADER_BASIC_CONFIG,
    PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG
);

// =============================================================================
// Generic Encode/Parse Functions
// =============================================================================

/**
 * Encode a message object.
 * Automatically extracts msgId, payload, and magic numbers from the message.
 */
export function encodeMessage(
    config: FrameProfileConfig,
    msg: MessageBase,
    options: EncodeOptions = {}
): Uint8Array {
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
    let payload: Uint8Array;
    if (isVariable && config.payload.hasLength && typeof msg.serialize === 'function') {
        // Variable message with length field - serialize() returns only used bytes
        payload = new Uint8Array(msg.serialize());
    } else {
        // Non-variable message OR minimal profile - use full buffer
        payload = new Uint8Array(msg._buffer);
    }
    
    const magic1 = msg.getMagic1();
    const magic2 = msg.getMagic2();
    const { seq = 0, sysId = 0, compId = 0 } = options;
    
    // For extended profiles with pkg_id, split the 16-bit msgId into pkg_id and msg_id
    // unless pkgId is explicitly provided in options
    let pkgIdValue = options.pkgId;
    let msgIdValue = msgId;
    if (config.payload.hasPkgId && pkgIdValue === undefined) {
        pkgIdValue = (msgId >> 8) & 0xFF;  // high byte
        msgIdValue = msgId & 0xFF;          // low byte
    } else {
        pkgIdValue = pkgIdValue ?? 0;
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
        } else {
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

    // Calculate and write CRC
    const crcLen = idx - crcStart;
    const ck = fletcherChecksum(buffer, crcStart, crcStart + crcLen, magic1, magic2);
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
export function parseFrameWithCrc(
    config: FrameProfileConfig,
    buffer: Uint8Array,
    getMessageInfo?: GetMessageInfo
): FrameMsgInfo {
    const result = createFrameMsgInfo();
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
    if (config.payload.hasSeq) idx++;
    if (config.payload.hasSysId) idx++;
    if (config.payload.hasCompId) idx++;

    // Read length field
    let msgLen = 0;
    if (config.payload.hasLength) {
        if (config.payload.lengthBytes === 1) {
            msgLen = buffer[idx++];
        } else {
            msgLen = buffer[idx] | (buffer[idx + 1] << 8);
            idx += 2;
        }
    }

    // Read message ID (16-bit: high byte is pkg_id when hasPkgId, low byte is msg_id)
    let msgId = 0;
    if (config.payload.hasPkgId) {
        msgId = buffer[idx++] << 8;  // pkg_id (high byte)
    }
    msgId |= buffer[idx++];  // msg_id (low byte)

    // Verify total size
    const totalSize = headerSize + msgLen + footerSize;
    if (length < totalSize) {
        return result;
    }

    // Verify CRC
    const crcLen = totalSize - crcStart - footerSize;
    
    // Get magic numbers for this message type
    let magic1 = 0, magic2 = 0;
    if (getMessageInfo) {
        const info = getMessageInfo(msgId);
        if (info) {
            magic1 = info.magic1;
            magic2 = info.magic2;
        }
    }
    
    const ck = fletcherChecksum(buffer, crcStart, crcStart + crcLen, magic1, magic2);
    if (ck[0] !== buffer[totalSize - 2] || ck[1] !== buffer[totalSize - 1]) {
        return result;
    }

    // Extract message data
    result.valid = true;
    result.msg_id = msgId;
    result.msg_len = msgLen;
    result.msg_data = buffer.slice(headerSize, headerSize + msgLen);

    return result;
}

/**
 * Generic parse function for minimal frames (requires getMessageInfo callback for size).
 * @param config Profile configuration
 * @param buffer Buffer containing frame data
 * @param getMessageInfo Callback to get message info (size is required, magic numbers ignored for minimal frames)
 */
export function parseFrameMinimal(
    config: FrameProfileConfig,
    buffer: Uint8Array,
    getMessageInfo: GetMessageInfo
): FrameMsgInfo {
    const result = createFrameMsgInfo();
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
    result.msg_id = msgId;
    result.msg_len = msgLen;
    result.msg_data = buffer.slice(headerSize, headerSize + msgLen);

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
 *       // Process result.msg_id, result.msg_data, result.msg_len
 *       result = reader.next();
 *   }
 */
export class BufferReader {
    private config: FrameProfileConfig;
    private buffer: Uint8Array;
    private size: number;
    private _offset: number;
    private getMessageInfo?: GetMessageInfo;

    constructor(
        config: FrameProfileConfig,
        buffer: Uint8Array,
        getMessageInfo?: GetMessageInfo
    ) {
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
    next(): FrameMsgInfo {
        if (this._offset >= this.size) {
            return createFrameMsgInfo();
        }

        const remaining = this.buffer.slice(this._offset);
        let result: FrameMsgInfo;

        if (this.config.payload.hasCrc || this.config.payload.hasLength) {
            result = parseFrameWithCrc(this.config, remaining, this.getMessageInfo);
        } else {
            if (!this.getMessageInfo) {
                // No more valid data to parse without message info callback
                this._offset = this.size;
                return createFrameMsgInfo();
            }
            result = parseFrameMinimal(this.config, remaining, this.getMessageInfo);
        }

        if (result.valid) {
            const frameSize = profileHeaderSize(this.config) + result.msg_len + profileFooterSize(this.config);
            this._offset += frameSize;
        } else {
            // No more valid frames - stop parsing
            this._offset = this.size;
        }

        return result;
    }

    /** Reset the reader to the beginning of the buffer. */
    reset(): void {
        this._offset = 0;
    }

    /** Get the current offset in the buffer. */
    get offset(): number {
        return this._offset;
    }

    /** Get the remaining bytes in the buffer. */
    get remaining(): number {
        return Math.max(0, this.size - this._offset);
    }

    /** Check if there are more bytes to parse. */
    hasMore(): boolean {
        return this._offset < this.size;
    }
}

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
export class BufferWriter {
    private config: FrameProfileConfig;
    private capacity: number;
    private buffer: Uint8Array;
    private _offset: number;

    constructor(config: FrameProfileConfig, capacity: number) {
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
    write(msg: MessageBase, options: EncodeOptions = {}): number {
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
    reset(): void {
        this._offset = 0;
    }

    /** Get the total number of bytes written. */
    get size(): number {
        return this._offset;
    }

    /** Get the remaining capacity in the buffer. */
    get remaining(): number {
        return Math.max(0, this.capacity - this._offset);
    }

    /** Get the written data as a new Uint8Array. */
    data(): Uint8Array {
        return this.buffer.slice(0, this._offset);
    }
}

// =============================================================================
// AccumulatingReader - Unified parser for buffer and byte-by-byte streaming
// =============================================================================

/** Parser state for streaming mode */
export enum AccumulatingReaderState {
    IDLE = 0,
    LOOKING_FOR_START1 = 1,
    LOOKING_FOR_START2 = 2,
    COLLECTING_HEADER = 3,
    COLLECTING_PAYLOAD = 4,
    BUFFER_MODE = 5
}

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
export class AccumulatingReader {
    private config: FrameProfileConfig;
    private getMessageInfo?: GetMessageInfo;
    private bufferSize: number;

    // Internal buffer for partial messages
    private internalBuffer: Uint8Array;
    private internalDataLen: number;
    private expectedFrameSize: number;
    private _state: AccumulatingReaderState;

    // Buffer mode state
    private currentBuffer: Uint8Array | null;
    private currentSize: number;
    private currentOffset: number;

    constructor(
        config: FrameProfileConfig,
        getMessageInfo?: GetMessageInfo,
        bufferSize: number = 1024
    ) {
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
    }

    // =========================================================================
    // Buffer Mode API
    // =========================================================================

    /**
     * Add a new buffer of data to process.
     */
    addData(buffer: Uint8Array): void {
        this.currentBuffer = buffer;
        this.currentSize = buffer.length;
        this.currentOffset = 0;
        this._state = AccumulatingReaderState.BUFFER_MODE;

        // If we have partial data in internal buffer, try to complete it
        if (this.internalDataLen > 0) {
            const spaceAvailable = this.bufferSize - this.internalDataLen;
            const bytesToCopy = Math.min(buffer.length, spaceAvailable);
            this.internalBuffer.set(buffer.slice(0, bytesToCopy), this.internalDataLen);
            this.internalDataLen += bytesToCopy;
        }
    }

    /**
     * Parse the next frame (buffer mode).
     */
    next(): FrameMsgInfo {
        if (this._state !== AccumulatingReaderState.BUFFER_MODE) {
            return createFrameMsgInfo();
        }

        // First, try to complete a partial message from the internal buffer
        if (this.internalDataLen > 0 && this.currentOffset === 0) {
            const internalBytes = this.internalBuffer.slice(0, this.internalDataLen);
            const result = this.parseBuffer(internalBytes);

            if (result.valid) {
                const frameSize = profileHeaderSize(this.config) + result.msg_len + profileFooterSize(this.config);
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

        // Parse from current buffer
        if (this.currentBuffer === null || this.currentOffset >= this.currentSize) {
            return createFrameMsgInfo();
        }

        const remaining = this.currentBuffer.slice(this.currentOffset);
        const result = this.parseBuffer(remaining);

        if (result.valid) {
            const frameSize = profileHeaderSize(this.config) + result.msg_len + profileFooterSize(this.config);
            this.currentOffset += frameSize;
            return result;
        }

        // Parse failed - might be partial message at end of buffer
        const remainingLen = this.currentSize - this.currentOffset;
        if (remainingLen > 0 && remainingLen < this.bufferSize) {
            this.internalBuffer.set(remaining, 0);
            this.internalDataLen = remainingLen;
            this.currentOffset = this.currentSize;
        }

        return createFrameMsgInfo();
    }

    // =========================================================================
    // Stream Mode API
    // =========================================================================

    /**
     * Push a single byte for parsing (stream mode).
     */
    pushByte(byte: number): FrameMsgInfo {
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
                return createFrameMsgInfo();
        }
    }

    private handleLookingForStart1(byte: number): FrameMsgInfo {
        if (this.config.header.numStartBytes === 0) {
            this.internalBuffer[0] = byte;
            this.internalDataLen = 1;

            if (!this.config.payload.hasLength && !this.config.payload.hasCrc) {
                return this.handleMinimalMsgId(byte);
            } else {
                this._state = AccumulatingReaderState.COLLECTING_HEADER;
            }
        } else {
            if (byte === this.config.startByte1) {
                this.internalBuffer[0] = byte;
                this.internalDataLen = 1;

                if (this.config.header.numStartBytes === 1) {
                    this._state = AccumulatingReaderState.COLLECTING_HEADER;
                } else {
                    this._state = AccumulatingReaderState.LOOKING_FOR_START2;
                }
            }
        }
        return createFrameMsgInfo();
    }

    private handleLookingForStart2(byte: number): FrameMsgInfo {
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

    private handleCollectingHeader(byte: number): FrameMsgInfo {
        if (this.internalDataLen >= this.bufferSize) {
            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
            this.internalDataLen = 0;
            return createFrameMsgInfo();
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
                let lenOffset = this.config.header.numStartBytes;
                if (this.config.payload.hasSeq) lenOffset++;
                if (this.config.payload.hasSysId) lenOffset++;
                if (this.config.payload.hasCompId) lenOffset++;

                let payloadLen = 0;
                if (this.config.payload.hasLength) {
                    if (this.config.payload.lengthBytes === 1) {
                        payloadLen = this.internalBuffer[lenOffset];
                    } else {
                        payloadLen = this.internalBuffer[lenOffset] | (this.internalBuffer[lenOffset + 1] << 8);
                    }
                }

                this.expectedFrameSize = headerSize + payloadLen + footerSize;

                if (this.expectedFrameSize > this.bufferSize) {
                    this._state = AccumulatingReaderState.LOOKING_FOR_START1;
                    this.internalDataLen = 0;
                    return createFrameMsgInfo();
                }

                if (this.internalDataLen >= this.expectedFrameSize) {
                    return this.validateAndReturn();
                }

                this._state = AccumulatingReaderState.COLLECTING_PAYLOAD;
            }
        }

        return createFrameMsgInfo();
    }

    private handleCollectingPayload(byte: number): FrameMsgInfo {
        if (this.internalDataLen >= this.bufferSize) {
            this._state = AccumulatingReaderState.LOOKING_FOR_START1;
            this.internalDataLen = 0;
            return createFrameMsgInfo();
        }

        this.internalBuffer[this.internalDataLen++] = byte;

        if (this.internalDataLen >= this.expectedFrameSize) {
            return this.validateAndReturn();
        }

        return createFrameMsgInfo();
    }

    private handleMinimalMsgId(msgId: number): FrameMsgInfo {
        if (this.getMessageInfo) {
            const info = this.getMessageInfo(msgId);
            if (info !== undefined) {
                const msgLen = info.size;
                const headerSize = profileHeaderSize(this.config);
                this.expectedFrameSize = headerSize + msgLen;

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

    private validateAndReturn(): FrameMsgInfo {
        const internalBytes = this.internalBuffer.slice(0, this.internalDataLen);
        const result = this.parseBuffer(internalBytes);

        this._state = AccumulatingReaderState.LOOKING_FOR_START1;
        this.internalDataLen = 0;
        this.expectedFrameSize = 0;

        return result;
    }

    private parseBuffer(buffer: Uint8Array): FrameMsgInfo {
        if (this.config.payload.hasCrc || this.config.payload.hasLength) {
            return parseFrameWithCrc(this.config, buffer, this.getMessageInfo);
        } else {
            if (!this.getMessageInfo) {
                return createFrameMsgInfo();
            }
            return parseFrameMinimal(this.config, buffer, this.getMessageInfo);
        }
    }

    // =========================================================================
    // Common API
    // =========================================================================

    /** Check if there might be more data to parse (buffer mode only). */
    hasMore(): boolean {
        if (this._state !== AccumulatingReaderState.BUFFER_MODE) return false;
        return (this.internalDataLen > 0) || (this.currentBuffer !== null && this.currentOffset < this.currentSize);
    }

    /** Check if there's a partial message waiting for more data. */
    hasPartial(): boolean {
        return this.internalDataLen > 0;
    }

    /** Get the size of the partial message data (0 if none). */
    partialSize(): number {
        return this.internalDataLen;
    }

    /** Get current parser state (for debugging). */
    get state(): AccumulatingReaderState {
        return this._state;
    }

    /** Reset the reader, clearing any partial message data. */
    reset(): void {
        this.internalDataLen = 0;
        this.expectedFrameSize = 0;
        this._state = AccumulatingReaderState.IDLE;
        this.currentBuffer = null;
        this.currentSize = 0;
        this.currentOffset = 0;
    }
}

// =============================================================================
// Profile-specific subclasses for standard profiles
// =============================================================================

// -----------------------------------------------------------------------------
// ProfileStandard subclasses
// -----------------------------------------------------------------------------

export class ProfileStandardReader extends BufferReader {
    constructor(buffer: Uint8Array, getMessageInfo?: GetMessageInfo) {
        super(ProfileStandardConfig, buffer, getMessageInfo);
    }
}

export class ProfileStandardWriter extends BufferWriter {
    constructor(capacity: number = 1024) {
        super(ProfileStandardConfig, capacity);
    }
}

export class ProfileStandardAccumulatingReader extends AccumulatingReader {
    constructor(getMessageInfo?: GetMessageInfo, bufferSize: number = 1024) {
        super(ProfileStandardConfig, getMessageInfo, bufferSize);
    }
}

// -----------------------------------------------------------------------------
// ProfileSensor subclasses
// -----------------------------------------------------------------------------

export class ProfileSensorReader extends BufferReader {
    constructor(buffer: Uint8Array, getMessageInfo: GetMessageInfo) {
        super(ProfileSensorConfig, buffer, getMessageInfo);
    }
}

export class ProfileSensorWriter extends BufferWriter {
    constructor(capacity: number = 1024) {
        super(ProfileSensorConfig, capacity);
    }
}

export class ProfileSensorAccumulatingReader extends AccumulatingReader {
    constructor(getMessageInfo: GetMessageInfo, bufferSize: number = 1024) {
        super(ProfileSensorConfig, getMessageInfo, bufferSize);
    }
}

// -----------------------------------------------------------------------------
// ProfileIPC subclasses
// -----------------------------------------------------------------------------

export class ProfileIPCReader extends BufferReader {
    constructor(buffer: Uint8Array, getMessageInfo: GetMessageInfo) {
        super(ProfileIPCConfig, buffer, getMessageInfo);
    }
}

export class ProfileIPCWriter extends BufferWriter {
    constructor(capacity: number = 1024) {
        super(ProfileIPCConfig, capacity);
    }
}

export class ProfileIPCAccumulatingReader extends AccumulatingReader {
    constructor(getMessageInfo: GetMessageInfo, bufferSize: number = 1024) {
        super(ProfileIPCConfig, getMessageInfo, bufferSize);
    }
}

// -----------------------------------------------------------------------------
// ProfileBulk subclasses
// -----------------------------------------------------------------------------

export class ProfileBulkReader extends BufferReader {
    constructor(buffer: Uint8Array, getMessageInfo?: GetMessageInfo) {
        super(ProfileBulkConfig, buffer, getMessageInfo);
    }
}

export class ProfileBulkWriter extends BufferWriter {
    constructor(capacity: number = 1024) {
        super(ProfileBulkConfig, capacity);
    }
}

export class ProfileBulkAccumulatingReader extends AccumulatingReader {
    constructor(getMessageInfo?: GetMessageInfo, bufferSize: number = 1024) {
        super(ProfileBulkConfig, getMessageInfo, bufferSize);
    }
}

// -----------------------------------------------------------------------------
// ProfileNetwork subclasses
// -----------------------------------------------------------------------------

export class ProfileNetworkReader extends BufferReader {
    constructor(buffer: Uint8Array, getMessageInfo?: GetMessageInfo) {
        super(ProfileNetworkConfig, buffer, getMessageInfo);
    }
}

export class ProfileNetworkWriter extends BufferWriter {
    constructor(capacity: number = 1024) {
        super(ProfileNetworkConfig, capacity);
    }
}

export class ProfileNetworkAccumulatingReader extends AccumulatingReader {
    constructor(getMessageInfo?: GetMessageInfo, bufferSize: number = 1024) {
        super(ProfileNetworkConfig, getMessageInfo, bufferSize);
    }
}
