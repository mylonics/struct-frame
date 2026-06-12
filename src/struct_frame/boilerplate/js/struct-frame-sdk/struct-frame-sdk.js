// Struct Frame SDK Client (JavaScript CommonJS)
// High-level interface for sending and receiving framed messages

'use strict';

/**
 * Main SDK Client.
 *
 * Usage:
 *   const { StructFrameSdk } = require('./struct-frame-sdk');
 *   const sdk = new StructFrameSdk({ transport, frameParser });
 *   const unsub = sdk.subscribe(msgId, (payload, msgId) => { ... });
 *   await sdk.connect();
 *   await sdk.sendRaw(msgId, data);
 *   unsub(); // unsubscribe
 */
class StructFrameSdk {
  /**
   * @param {{ transport: BaseTransport, frameParser: object, debug?: boolean }} config
   */
  constructor(config) {
    this._transport = config.transport;
    this._frameParser = config.frameParser;
    this._minFrameSize = this._estimateMinFrameSize();
    this._debug = config.debug ?? false;

    /** @type {Map<number, Function[]>} */
    this._handlers = new Map();
    /** @type {Map<number, object>} */
    this._codecs = new Map();
    /** @type {Uint8Array} */
    this._buffer = new Uint8Array(0);

    // Wire transport callbacks
    this._transport.onData((data) => this._handleIncomingData(data));
    this._transport.onError((err) => this._log(`Transport error: ${err.message}`));
    this._transport.onClose(() => {
      this._log('Transport closed');
      this._buffer = new Uint8Array(0);
    });
  }

  /** Connect to the underlying transport. */
  async connect() {
    await this._transport.connect();
    this._log('Connected');
  }

  /** Disconnect from the underlying transport. */
  async disconnect() {
    await this._transport.disconnect();
    this._log('Disconnected');
  }

  /**
   * Register a message codec for automatic deserialization.
   * The codec must expose `getMsgId()` and `deserialize(data)`.
   * @param {object} codec
   */
  registerCodec(codec) {
    this._codecs.set(codec.getMsgId(), codec);
  }

  /**
   * Subscribe to frames with the given message ID.
   *
   * @param {number} msgId
   * @param {(payload: Uint8Array|object, msgId: number) => void} handler
   * @returns {() => void} unsubscribe function
   */
  subscribe(msgId, handler) {
    if (!this._handlers.has(msgId)) this._handlers.set(msgId, []);
    this._handlers.get(msgId).push(handler);
    this._log(`Subscribed to message ID ${msgId}`);
    return () => {
      const list = this._handlers.get(msgId);
      if (!list) return;
      const idx = list.indexOf(handler);
      if (idx > -1) list.splice(idx, 1);
    };
  }

  /**
   * Send raw (already-serialized) payload for the given message ID.
   * @param {number} msgId
   * @param {Uint8Array} data
   * @returns {Promise<{success: boolean, attemptedBytes: number, bytesWritten: number}>}
   */
  async sendRaw(msgId, data) {
    const framed = this._frameParser.frame(msgId, data);
    const attemptedBytes = framed.length;
    const bytesWritten = await this._transport.send(framed);
    this._log(`Sent message ID ${msgId}, ${data.length} bytes`);
    return {
      success: bytesWritten === attemptedBytes,
      attemptedBytes,
      bytesWritten,
    };
  }

  /**
   * Send a message object (requires pack() and msgId).
   * @param {{ pack: () => Uint8Array, msgId: number }} message
   * @returns {Promise<{success: boolean, attemptedBytes: number, bytesWritten: number}>}
   */
  async send(message) {
    const data = message.pack();
    return this.sendRaw(message.msgId, data);
  }

  /** @returns {boolean} */
  isConnected() { return this._transport.isConnected(); }

  // ---- private ----

  /** @param {Uint8Array} data */
  _handleIncomingData(data) {
    const merged = new Uint8Array(this._buffer.length + data.length);
    merged.set(this._buffer);
    merged.set(data, this._buffer.length);
    this._buffer = merged;
    this._parseBuffer();
  }

  _parseBuffer() {
    while (this._buffer.length > 0) {
      const result = this._frameParser.parse(this._buffer);
      if (!result.valid) {
        // If we already have enough bytes for at least one frame attempt, drop one byte
        // and continue scanning to recover from corrupted leading data.
        if (this._buffer.length >= this._minFrameSize) {
          this._log('Parser desync detected, discarding 1 byte for resync');
          this._buffer = this._buffer.subarray(1);
          continue;
        }
        break;
      }

      this._log(`Received message ID ${result.msgId}, ${result.msgLen} bytes`);

      const handlers = this._handlers.get(result.msgId);
      if (handlers && handlers.length > 0) {
        let message = result.msgData;
        const codec = this._codecs.get(result.msgId);
        if (codec) {
          try { message = codec.deserialize(result.msgData); }
          catch (e) { this._log(`Deserialize error for ${result.msgId}: ${e}`); }
        }
        handlers.forEach(h => {
          try { h(message, result.msgId); }
          catch (e) { this._log(`Handler error for ${result.msgId}: ${e}`); }
        });
      }

      // Advance buffer past consumed frame. Use parser-reported frame size when available,
      // otherwise re-frame the parsed payload to obtain exact encoded length.
      const frameSize = this._calculateFrameSize(result);
      this._buffer = this._buffer.subarray(frameSize);
    }
  }

  _calculateFrameSize(result) {
    if (typeof result.frameSize === 'number' && result.frameSize > 0) {
      return result.frameSize;
    }
    return this._frameParser.frame(result.msgId, result.msgData).length;
  }

  _estimateMinFrameSize() {
    try {
      const probe = this._frameParser.frame(0, new Uint8Array(0));
      return probe.length > 0 ? probe.length : 1;
    } catch (_e) {
      return 1;
    }
  }

  /** @param {string} msg */
  _log(msg) { if (this._debug) console.log(`[StructFrameSdk] ${msg}`); }
}

module.exports = { StructFrameSdk };
