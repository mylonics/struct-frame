"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.TcpTransport = void 0;
// TCP Transport implementation using Node.js net
const net = __importStar(require("net"));
const transport_1 = require("./transport");
class TcpTransport extends transport_1.BaseTransport {
    constructor(config) {
        super(config);
        this.tcpConfig = {
            ...this.config,
            host: config.host,
            port: config.port,
            timeout: config.timeout ?? 5000,
        };
    }
    async connect() {
        return new Promise((resolve, reject) => {
            try {
                this.socket = new net.Socket();
                this.socket.setTimeout(this.tcpConfig.timeout);
                this.socket.on('connect', () => {
                    this.socket?.setTimeout(0); // clear connect-phase timeout; keep socket alive indefinitely
                    this.connected = true;
                    resolve();
                });
                this.socket.on('data', (data) => {
                    this.handleData(new Uint8Array(data));
                });
                this.socket.on('error', (err) => {
                    this.handleError(err);
                    if (!this.connected) {
                        reject(err);
                    }
                });
                this.socket.on('close', () => {
                    this.handleClose();
                });
                this.socket.on('timeout', () => {
                    this.handleError(new Error('TCP connection timeout'));
                    this.socket?.destroy();
                });
                this.socket.connect(this.tcpConfig.port, this.tcpConfig.host);
            }
            catch (error) {
                reject(error);
            }
        });
    }
    async disconnect() {
        this._intentionalClose = true;
        return new Promise((resolve) => {
            if (this.socket) {
                this.socket.end(() => {
                    this.connected = false;
                    resolve();
                });
            }
            else {
                this._intentionalClose = false;
                resolve();
            }
        });
    }
    async send(data) {
        return new Promise((resolve, reject) => {
            if (!this.socket || !this.connected) {
                reject(new Error('TCP socket not connected'));
                return;
            }
            this.socket.write(this.toBuffer(data), (err) => {
                if (err) {
                    reject(err);
                }
                else {
                    resolve(data.length);
                }
            });
        });
    }
}
exports.TcpTransport = TcpTransport;
