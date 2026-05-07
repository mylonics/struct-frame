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
   */
  async sendRaw(msgId, data) {
    const framed = this._frameParser.frame(msgId, data);
    await this._transport.send(framed);
    this._log(`Sent message ID ${msgId}, ${data.length} bytes`);
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
      if (!result.valid) break;

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

      // Advance buffer past consumed frame.
      // prefer the parser-reported frameSize (total bytes including header+payload+footer);
      // fall back to payload + a conservative 10-byte estimate of framing overhead if the
      // parser does not report a frame size (the TS SDK uses the same fallback).
      const FRAME_OVERHEAD_ESTIMATE = 10;
      const frameSize = result.frameSize > 0 ? result.frameSize : result.msgLen + FRAME_OVERHEAD_ESTIMATE;
      this._buffer = this._buffer.slice(frameSize);
    }
  }

  /** @param {string} msg */
  _log(msg) { if (this._debug) console.log(`[StructFrameSdk] ${msg}`); }
}

module.exports = { StructFrameSdk };
