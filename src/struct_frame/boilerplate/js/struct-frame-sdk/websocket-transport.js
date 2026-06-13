"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.WebSocketTransport = void 0;
// WebSocket Transport implementation using WebSocket API
const transport_1 = require("./transport");
class WebSocketTransport extends transport_1.BaseTransport {
    constructor(config) {
        super(config);
        this.wsConfig = {
            ...this.config,
            url: config.url,
            protocols: config.protocols ?? [],
        };
    }
    async connect() {
        return new Promise((resolve, reject) => {
            try {
                // Use global WebSocket (works in both browser and Node.js with ws package)
                this.ws = new WebSocket(this.wsConfig.url, this.wsConfig.protocols);
                this.ws.binaryType = 'arraybuffer';
                this.ws.onopen = () => {
                    this.connected = true;
                    resolve();
                };
                this.ws.onmessage = (event) => {
                    let data;
                    if (event.data instanceof ArrayBuffer) {
                        data = new Uint8Array(event.data);
                    }
                    else if (event.data instanceof Blob) {
                        event.data.arrayBuffer().then(buffer => this.handleData(new Uint8Array(buffer)), err => this.handleError(err instanceof Error ? err : new Error(String(err))));
                        return;
                    }
                    else {
                        // String data - convert to bytes
                        const encoder = new TextEncoder();
                        data = encoder.encode(event.data);
                    }
                    this.handleData(data);
                };
                this.ws.onerror = (_event) => {
                    const error = new Error('WebSocket error');
                    this.handleError(error);
                    if (!this.connected) {
                        reject(error);
                    }
                };
                this.ws.onclose = () => {
                    this.handleClose();
                };
            }
            catch (error) {
                reject(error);
            }
        });
    }
    async disconnect() {
        return new Promise((resolve) => {
            if (this.ws) {
                if (this.ws.readyState === WebSocket.OPEN) {
                    this.ws.close();
                }
                this.connected = false;
                resolve();
            }
            else {
                resolve();
            }
        });
    }
    async send(data) {
        return new Promise((resolve, reject) => {
            if (!this.ws || !this.connected || this.ws.readyState !== WebSocket.OPEN) {
                reject(new Error('WebSocket not connected'));
                return;
            }
            try {
                this.ws.send(data);
                resolve(data.length);
            }
            catch (error) {
                reject(error);
            }
        });
    }
}
exports.WebSocketTransport = WebSocketTransport;
