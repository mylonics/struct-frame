// Transport interface for struct-frame SDK (JavaScript CommonJS)
// Provides abstraction for various communication channels

/**
 * Abstract base transport.
 * Concrete implementations extend this class and implement connect/disconnect/send.
 */
class BaseTransport {
  constructor(config = {}) {
    this._connected = false;
    this._dataCallback = null;
    this._errorCallback = null;
    this._closeCallback = null;
    this._autoReconnect = config.autoReconnect ?? false;
    this._reconnectDelay = config.reconnectDelay ?? 1000;
    this._maxReconnectAttempts = config.maxReconnectAttempts ?? 0;
    this._reconnectAttempts = 0;
  }

  /** @param {(data: Uint8Array) => void} callback */
  onData(callback) { this._dataCallback = callback; }
  /** @param {(error: Error) => void} callback */
  onError(callback) { this._errorCallback = callback; }
  /** @param {() => void} callback */
  onClose(callback) { this._closeCallback = callback; }

  isConnected() { return this._connected; }

  /** @param {Uint8Array} data */
  _handleData(data) { if (this._dataCallback) this._dataCallback(data); }

  /** @param {Error} error */
  _handleError(error) {
    if (this._errorCallback) this._errorCallback(error);
    if (this._autoReconnect && this._connected) this._attemptReconnect();
  }

  _handleClose() {
    this._connected = false;
    if (this._closeCallback) this._closeCallback();
    if (this._autoReconnect) this._attemptReconnect();
  }

  async _attemptReconnect() {
    if (this._maxReconnectAttempts > 0 && this._reconnectAttempts >= this._maxReconnectAttempts) return;
    this._reconnectAttempts++;
    await new Promise(resolve => setTimeout(resolve, this._reconnectDelay));
    try {
      await this.connect();
      this._reconnectAttempts = 0;
    } catch (err) {
      this._handleError(err);
    }
  }
}

module.exports = { BaseTransport };
