"use strict";
// Transport interface for struct-frame SDK
// Provides abstraction for various communication channels
Object.defineProperty(exports, "__esModule", { value: true });
exports.BaseTransport = void 0;
class BaseTransport {
    constructor(config) {
        this.connected = false;
        this.reconnectAttempts = 0;
        this._intentionalClose = false;
        this.config = {
            autoReconnect: config?.autoReconnect ?? false,
            reconnectDelay: config?.reconnectDelay ?? 1000,
            maxReconnectAttempts: config?.maxReconnectAttempts ?? 0,
        };
    }
    onData(callback) {
        this.dataCallback = callback;
    }
    onError(callback) {
        this.errorCallback = callback;
    }
    onClose(callback) {
        this.closeCallback = callback;
    }
    isConnected() {
        return this.connected;
    }
    handleData(data) {
        if (this.dataCallback) {
            this.dataCallback(data);
        }
    }
    /**
     * Wrap a Uint8Array as a Node Buffer without copying when possible.
     * Encoded frames are freshly-allocated, non-reused buffers, so a view over the
     * backing ArrayBuffer is safe to hand to the socket (it stays alive until the write
     * completes). Avoids the per-send copy that `Buffer.from(uint8array)` would incur.
     */
    toBuffer(data) {
        return Buffer.isBuffer(data)
            ? data
            : Buffer.from(data.buffer, data.byteOffset, data.byteLength);
    }
    handleError(error) {
        if (this.errorCallback) {
            this.errorCallback(error);
        }
        if (this.config.autoReconnect && this.connected) {
            this.attemptReconnect();
        }
    }
    handleClose() {
        this.connected = false;
        if (this.closeCallback) {
            this.closeCallback();
        }
        if (this.config.autoReconnect && !this._intentionalClose) {
            this.attemptReconnect();
        }
        this._intentionalClose = false;
    }
    async attemptReconnect() {
        if (this.config.maxReconnectAttempts > 0 &&
            this.reconnectAttempts >= this.config.maxReconnectAttempts) {
            return;
        }
        this.reconnectAttempts++;
        await new Promise(resolve => setTimeout(resolve, this.config.reconnectDelay));
        try {
            await this.connect();
            this.reconnectAttempts = 0;
        }
        catch (error) {
            this.handleError(error);
        }
    }
}
exports.BaseTransport = BaseTransport;
