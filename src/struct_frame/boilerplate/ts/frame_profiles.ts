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
} from './frame_headers';
import {
    PayloadConfig,
    PAYLOAD_MINIMAL_CONFIG,
    PAYLOAD_DEFAULT_CONFIG,
    PAYLOAD_EXTENDED_CONFIG,
    PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG,
    payloadHeaderSize,
    payloadFooterSize,
} from './payload_types';
import { fletcher_checksum, createFrameMsgInfo, FrameMsgInfo } from './frame_base';

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
}

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
 * Generic encode function for frames with CRC.
 */
export function encodeFrameWithCrc(
    config: FrameProfileConfig,
    msgId: number,
    payload: Uint8Array,
    options: EncodeOptions = {}
): Uint8Array {
    const { seq = 0, sysId = 0, compId = 0, pkgId = 0 } = options;
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
 */
export function encodeFrameMinimal(
    config: FrameProfileConfig,
    msgId: number,
    payload: Uint8Array
): Uint8Array {
    const headerSize = profileHeaderSize(config);
    const totalSize = headerSize + payload.length;
    const buffer = new Uint8Array(totalSize);
    let idx = 0;

    // Write start bytes
    if (config.header.numStartBytes >= 1) {
        buffer[idx++] = config.startByte1;
    }
    if (config.header.numStartBytes >= 2) {
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
 */
export function parseFrameWithCrc(
    config: FrameProfileConfig,
    buffer: Uint8Array
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

    // Skip package ID
    if (config.payload.hasPkgId) idx++;

    // Read message ID
    const msgId = buffer[idx++];

    // Verify total size
    const totalSize = headerSize + msgLen + footerSize;
    if (length < totalSize) {
        return result;
    }

    // Verify CRC
    const crcLen = totalSize - crcStart - footerSize;
    const ck = fletcher_checksum(buffer, crcStart, crcStart + crcLen);
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
 * Generic parse function for minimal frames (requires get_msg_length callback).
 */
export function parseFrameMinimal(
    config: FrameProfileConfig,
    buffer: Uint8Array,
    getMsgLength: (msgId: number) => number | undefined
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
    const msgLen = getMsgLength(msgId);
    if (msgLen === undefined || msgLen === null) {
        return result;
    }

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
 *   const reader = new BufferReader(ProfileStandardConfig, buffer);
 *   let result = reader.next();
 *   while (result.valid) {
 *       // Process result.msg_id, result.msg_data, result.msg_len
 *       result = reader.next();
 *   }
 *
 * For minimal profiles that need getMsgLength:
 *   const reader = new BufferReader(ProfileSensorConfig, buffer, getMsgLength);
 */
export class BufferReader {
    private config: FrameProfileConfig;
    private buffer: Uint8Array;
    private size: number;
    private _offset: number;
    private getMsgLength?: (msgId: number) => number | undefined;

    constructor(
        config: FrameProfileConfig,
        buffer: Uint8Array,
        getMsgLength?: (msgId: number) => number | undefined
    ) {
        this.config = config;
        this.buffer = buffer;
        this.size = buffer.length;
        this._offset = 0;
        this.getMsgLength = getMsgLength;
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
     * The message must be a struct instance with a constructor that has _msgid static property
     * and the instance must have _buffer property.
     * Returns the number of bytes written, or 0 on failure.
     */
    write(msg: { _buffer: Buffer; constructor: { _msgid?: number; _size?: number } }, options: EncodeOptions = {}): number {
        const msgId = (msg.constructor as any)._msgid;
        const payload = new Uint8Array(msg._buffer);

        if (msgId === undefined) {
            throw new Error('Message struct must have _msgid static property');
        }

        let encoded: Uint8Array;

        if (this.config.payload.hasCrc || this.config.payload.hasLength) {
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
 *   const reader = new AccumulatingReader(ProfileStandardConfig);
 *   reader.addData(chunk1);
 *   let result = reader.next();
 *   while (result.valid) {
 *       // Process complete messages
 *       result = reader.next();
 *   }
 *
 * Stream mode usage:
 *   const reader = new AccumulatingReader(ProfileStandardConfig);
 *   while (receiving) {
 *       const byte = readByte();
 *       const result = reader.pushByte(byte);
 *       if (result.valid) {
 *           // Process complete message
 *       }
 *   }
 *
 * For minimal profiles:
 *   const reader = new AccumulatingReader(ProfileSensorConfig, getMsgLength);
 */
export class AccumulatingReader {
    private config: FrameProfileConfig;
    private getMsgLength?: (msgId: number) => number | undefined;
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
        getMsgLength?: (msgId: number) => number | undefined,
        bufferSize: number = 1024
    ) {
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
                if (this.getMsgLength) {
                    const msgLen = this.getMsgLength(msgId);
                    if (msgLen !== undefined) {
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
        if (this.getMsgLength) {
            const msgLen = this.getMsgLength(msgId);
            if (msgLen !== undefined) {
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
            return parseFrameWithCrc(this.config, buffer);
        } else {
            if (!this.getMsgLength) {
                return createFrameMsgInfo();
            }
            return parseFrameMinimal(this.config, buffer, this.getMsgLength);
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
    constructor(buffer: Uint8Array) {
        super(ProfileStandardConfig, buffer);
    }
}

export class ProfileStandardWriter extends BufferWriter {
    constructor(capacity: number = 1024) {
        super(ProfileStandardConfig, capacity);
    }
}

export class ProfileStandardAccumulatingReader extends AccumulatingReader {
    constructor(bufferSize: number = 1024) {
        super(ProfileStandardConfig, undefined, bufferSize);
    }
}

// -----------------------------------------------------------------------------
// ProfileSensor subclasses
// -----------------------------------------------------------------------------

export class ProfileSensorReader extends BufferReader {
    constructor(buffer: Uint8Array, getMsgLength: (msgId: number) => number | undefined) {
        super(ProfileSensorConfig, buffer, getMsgLength);
    }
}

export class ProfileSensorWriter extends BufferWriter {
    constructor(capacity: number = 1024) {
        super(ProfileSensorConfig, capacity);
    }
}

export class ProfileSensorAccumulatingReader extends AccumulatingReader {
    constructor(getMsgLength: (msgId: number) => number | undefined, bufferSize: number = 1024) {
        super(ProfileSensorConfig, getMsgLength, bufferSize);
    }
}

// -----------------------------------------------------------------------------
// ProfileIPC subclasses
// -----------------------------------------------------------------------------

export class ProfileIPCReader extends BufferReader {
    constructor(buffer: Uint8Array, getMsgLength: (msgId: number) => number | undefined) {
        super(ProfileIPCConfig, buffer, getMsgLength);
    }
}

export class ProfileIPCWriter extends BufferWriter {
    constructor(capacity: number = 1024) {
        super(ProfileIPCConfig, capacity);
    }
}

export class ProfileIPCAccumulatingReader extends AccumulatingReader {
    constructor(getMsgLength: (msgId: number) => number | undefined, bufferSize: number = 1024) {
        super(ProfileIPCConfig, getMsgLength, bufferSize);
    }
}

// -----------------------------------------------------------------------------
// ProfileBulk subclasses
// -----------------------------------------------------------------------------

export class ProfileBulkReader extends BufferReader {
    constructor(buffer: Uint8Array) {
        super(ProfileBulkConfig, buffer);
    }
}

export class ProfileBulkWriter extends BufferWriter {
    constructor(capacity: number = 1024) {
        super(ProfileBulkConfig, capacity);
    }
}

export class ProfileBulkAccumulatingReader extends AccumulatingReader {
    constructor(bufferSize: number = 1024) {
        super(ProfileBulkConfig, undefined, bufferSize);
    }
}

// -----------------------------------------------------------------------------
// ProfileNetwork subclasses
// -----------------------------------------------------------------------------

export class ProfileNetworkReader extends BufferReader {
    constructor(buffer: Uint8Array) {
        super(ProfileNetworkConfig, buffer);
    }
}

export class ProfileNetworkWriter extends BufferWriter {
    constructor(capacity: number = 1024) {
        super(ProfileNetworkConfig, capacity);
    }
}

export class ProfileNetworkAccumulatingReader extends AccumulatingReader {
    constructor(bufferSize: number = 1024) {
        super(ProfileNetworkConfig, undefined, bufferSize);
    }
}
