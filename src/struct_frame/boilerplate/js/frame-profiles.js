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
 * This module builds on frame_headers and payload_types, composing profiles from
 * header + payload configurations (mirroring the C++ FrameProfiles.hpp structure).
 */

const {
  HEADER_NONE_CONFIG,
  HEADER_TINY_CONFIG,
  HEADER_BASIC_CONFIG,
  PAYLOAD_TYPE_BASE,
} = require('./frame-headers');
const {
  PAYLOAD_MINIMAL_CONFIG,
  PAYLOAD_DEFAULT_CONFIG,
  PAYLOAD_EXTENDED_CONFIG,
  PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG,
  payloadHeaderSize,
  payloadFooterSize,
} = require('./payload-types');
const { fletcherChecksum, createFrameMsgInfo } = require('./frame-base');

/**
 * @typedef {Object} MessageInfo
 * @property {number} size - Message size in bytes
 * @property {number} magic1 - First magic number for CRC
 * @property {number} magic2 - Second magic number for CRC
 */

/**
 * @callback GetMessageInfo
 * @param {number} msgId - Message ID to lookup
 * @returns {MessageInfo|undefined} Message info or undefined if not found
 */

// =============================================================================
// Profile Helper Functions
// =============================================================================

/** Get the total header size for a profile (start bytes + payload header fields) */
function profileHeaderSize(config) {
  return config.header.numStartBytes + payloadHeaderSize(config.payload);
}

/** Get the footer size for a profile */
function profileFooterSize(config) {
  return payloadFooterSize(config.payload);
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
const ProfileStandardConfig = createProfileConfig(
  'ProfileStandard',
  HEADER_BASIC_CONFIG,
  PAYLOAD_DEFAULT_CONFIG
);

/**
 * Profile Sensor: Tiny + Minimal
 * Frame: [0x70] [MSG_ID] [PAYLOAD]
 * 2 bytes overhead, no length field (requires get_msg_length callback)
 */
const ProfileSensorConfig = createProfileConfig(
  'ProfileSensor',
  HEADER_TINY_CONFIG,
  PAYLOAD_MINIMAL_CONFIG
);

/**
 * Profile IPC: None + Minimal
 * Frame: [MSG_ID] [PAYLOAD]
 * 1 byte overhead, no start bytes (requires get_msg_length callback)
 */
const ProfileIPCConfig = createProfileConfig(
  'ProfileIPC',
  HEADER_NONE_CONFIG,
  PAYLOAD_MINIMAL_CONFIG
);

/**
 * Profile Bulk: Basic + Extended
 * Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * 8 bytes overhead, 64KB max payload
 */
const ProfileBulkConfig = createProfileConfig(
  'ProfileBulk',
  HEADER_BASIC_CONFIG,
  PAYLOAD_EXTENDED_CONFIG
);

/**
 * Profile Network: Basic + ExtendedMultiSystemStream
 * Frame: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * 11 bytes overhead, 64KB max payload
 */
const ProfileNetworkConfig = createProfileConfig(
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
function encodeMessage(config, msg, options = {}) {
  const msgId = msg.getMsgId();

  if (msgId === undefined) {
    throw new Error('Message struct must have _msgid static property');
  }

  // Check if this is a variable message
  const isVariable = typeof msg.isVariable === 'function' ? msg.isVariable() : false;
  
  // Get payload - use serialize() for all messages
  // serialize() returns variable-length data for variable messages,
  // and MAX_SIZE data for non-variable messages
  // Note: Minimal profiles (no length field) use MAX_SIZE even for variable messages
  let payload;
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
 * @param {Object} config - Profile configuration
 * @param {Uint8Array} buffer - Buffer to parse
 * @param {GetMessageInfo} [getMessageInfo] - Callback to get message info (size, magic1, magic2)
 */
function parseFrameWithCrc(config, buffer, getMessageInfo) {
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
 * @param {Object} config - Profile configuration
 * @param {Uint8Array} buffer - Buffer to parse
 * @param {GetMessageInfo} getMessageInfo - Callback to get message info (size field used)
 */
function parseFrameMinimal(config, buffer, getMessageInfo) {
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
  const msgInfo = getMessageInfo(msgId);
  if (!msgInfo) {
    return result;
  }
  const msgLen = msgInfo.size;

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
 * For minimal profiles that need getMessageInfo:
 *   const reader = new BufferReader(ProfileSensorConfig, buffer, getMessageInfo);
 */
class BufferReader {
  /**
   * @param {Object} config - Profile configuration
   * @param {Uint8Array} buffer - Buffer to parse
   * @param {GetMessageInfo} [getMessageInfo] - Callback to get message info (size, magic1, magic2)
   */
  constructor(config, buffer, getMessageInfo = undefined) {
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
      return createFrameMsgInfo();
    }

    const remaining = this.buffer.slice(this._offset);
    let result;

    if (this.config.payload.hasCrc || this.config.payload.hasLength) {
      result = parseFrameWithCrc(this.config, remaining, this.getMessageInfo);
    } else {
      if (!this.getMessageInfo) {
        // No more valid data to parse without getMessageInfo callback
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
   * @param {MessageBase} msg - The message to write
   * @param {Object} options - Optional encode options
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

// =============================================================================
// AccumulatingReader - Unified parser for buffer and byte-by-byte streaming
// =============================================================================

/** Parser state for streaming mode */
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
 *   const reader = new AccumulatingReader(ProfileSensorConfig, getMessageInfo);
 */
class AccumulatingReader {
  /**
   * @param {Object} config - Profile configuration
   * @param {GetMessageInfo} [getMessageInfo] - Callback to get message info (size, magic1, magic2)
   * @param {number} [bufferSize=1024] - Internal buffer size
   */
  constructor(config, getMessageInfo = undefined, bufferSize = 1024) {
    this.config = config;
    this.getMessageInfo = getMessageInfo;
    this.bufferSize = bufferSize;

    // Internal buffer for partial messages
    this.internalBuffer = new Uint8Array(bufferSize);
    this.internalDataLen = 0;
    this.expectedFrameSize = 0;
    this._state = AccumulatingReaderState.IDLE;

    // Buffer mode state
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
  addData(buffer) {
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
  next() {
    if (this._state !== AccumulatingReaderState.BUFFER_MODE) {
      return createFrameMsgInfo();
    }

    // First, try to complete a partial message from the internal buffer
    if (this.internalDataLen > 0 && this.currentOffset === 0) {
      const internalBytes = this.internalBuffer.slice(0, this.internalDataLen);
      const result = this._parseBuffer(internalBytes);

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
    const result = this._parseBuffer(remaining);

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
  pushByte(byte) {
    // Initialize state on first byte if idle
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
    if (this.config.header.numStartBytes === 0) {
      this.internalBuffer[0] = byte;
      this.internalDataLen = 1;

      if (!this.config.payload.hasLength && !this.config.payload.hasCrc) {
        return this._handleMinimalMsgId(byte);
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
    const headerSize = profileHeaderSize(this.config);
    const footerSize = profileFooterSize(this.config);

    if (this.internalDataLen >= headerSize) {
      if (!this.config.payload.hasLength && !this.config.payload.hasCrc) {
        const msgId = this.internalBuffer[headerSize - 1];
        if (this.getMessageInfo) {
          const msgInfo = this.getMessageInfo(msgId);
          if (msgInfo) {
            const msgLen = msgInfo.size;
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
    if (this.getMessageInfo) {
      const msgInfo = this.getMessageInfo(msgId);
      if (msgInfo) {
        const msgLen = msgInfo.size;
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

  _validateAndReturn() {
    const internalBytes = this.internalBuffer.slice(0, this.internalDataLen);
    const result = this._parseBuffer(internalBytes);

    this._state = AccumulatingReaderState.LOOKING_FOR_START1;
    this.internalDataLen = 0;
    this.expectedFrameSize = 0;

    return result;
  }

  _parseBuffer(buffer) {
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
  hasMore() {
    if (this._state !== AccumulatingReaderState.BUFFER_MODE) return false;
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
  }
}

// =============================================================================
// Profile-specific subclasses for standard profiles
// =============================================================================

// -----------------------------------------------------------------------------
// ProfileStandard subclasses
// -----------------------------------------------------------------------------

class ProfileStandardReader extends BufferReader {
  constructor(buffer, getMessageInfo = undefined) {
    super(ProfileStandardConfig, buffer, getMessageInfo);
  }
}

class ProfileStandardWriter extends BufferWriter {
  constructor(capacity = 1024) {
    super(ProfileStandardConfig, capacity);
  }
}

class ProfileStandardAccumulatingReader extends AccumulatingReader {
  constructor(getMessageInfo = undefined, bufferSize = 1024) {
    super(ProfileStandardConfig, getMessageInfo, bufferSize);
  }
}

// -----------------------------------------------------------------------------
// ProfileSensor subclasses
// -----------------------------------------------------------------------------

class ProfileSensorReader extends BufferReader {
  constructor(buffer, getMessageInfo) {
    super(ProfileSensorConfig, buffer, getMessageInfo);
  }
}

class ProfileSensorWriter extends BufferWriter {
  constructor(capacity = 1024) {
    super(ProfileSensorConfig, capacity);
  }
}

class ProfileSensorAccumulatingReader extends AccumulatingReader {
  constructor(getMessageInfo, bufferSize = 1024) {
    super(ProfileSensorConfig, getMessageInfo, bufferSize);
  }
}

// -----------------------------------------------------------------------------
// ProfileIPC subclasses
// -----------------------------------------------------------------------------

class ProfileIPCReader extends BufferReader {
  constructor(buffer, getMessageInfo) {
    super(ProfileIPCConfig, buffer, getMessageInfo);
  }
}

class ProfileIPCWriter extends BufferWriter {
  constructor(capacity = 1024) {
    super(ProfileIPCConfig, capacity);
  }
}

class ProfileIPCAccumulatingReader extends AccumulatingReader {
  constructor(getMessageInfo, bufferSize = 1024) {
    super(ProfileIPCConfig, getMessageInfo, bufferSize);
  }
}

// -----------------------------------------------------------------------------
// ProfileBulk subclasses
// -----------------------------------------------------------------------------

class ProfileBulkReader extends BufferReader {
  constructor(buffer, getMessageInfo = undefined) {
    super(ProfileBulkConfig, buffer, getMessageInfo);
  }
}

class ProfileBulkWriter extends BufferWriter {
  constructor(capacity = 1024) {
    super(ProfileBulkConfig, capacity);
  }
}

class ProfileBulkAccumulatingReader extends AccumulatingReader {
  constructor(getMessageInfo = undefined, bufferSize = 1024) {
    super(ProfileBulkConfig, getMessageInfo, bufferSize);
  }
}

// -----------------------------------------------------------------------------
// ProfileNetwork subclasses
// -----------------------------------------------------------------------------

class ProfileNetworkReader extends BufferReader {
  constructor(buffer, getMessageInfo = undefined) {
    super(ProfileNetworkConfig, buffer, getMessageInfo);
  }
}

class ProfileNetworkWriter extends BufferWriter {
  constructor(capacity = 1024) {
    super(ProfileNetworkConfig, capacity);
  }
}

class ProfileNetworkAccumulatingReader extends AccumulatingReader {
  constructor(getMessageInfo = undefined, bufferSize = 1024) {
    super(ProfileNetworkConfig, getMessageInfo, bufferSize);
  }
}

module.exports = {
  // Profile helper functions
  profileHeaderSize,
  profileFooterSize,
  profileOverhead,

  // Profile configurations
  ProfileStandardConfig,
  ProfileSensorConfig,
  ProfileIPCConfig,
  ProfileBulkConfig,
  ProfileNetworkConfig,

  // Generic encode/parse functions
  encodeMessage,
  parseFrameWithCrc,
  parseFrameMinimal,

  // BufferReader/BufferWriter/AccumulatingReader base classes
  BufferReader,
  BufferWriter,
  AccumulatingReader,
  AccumulatingReaderState,

  // Profile-specific subclasses
  ProfileStandardReader,
  ProfileStandardWriter,
  ProfileStandardAccumulatingReader,
  ProfileSensorReader,
  ProfileSensorWriter,
  ProfileSensorAccumulatingReader,
  ProfileIPCReader,
  ProfileIPCWriter,
  ProfileIPCAccumulatingReader,
  ProfileBulkReader,
  ProfileBulkWriter,
  ProfileBulkAccumulatingReader,
  ProfileNetworkReader,
  ProfileNetworkWriter,
  ProfileNetworkAccumulatingReader,
};
