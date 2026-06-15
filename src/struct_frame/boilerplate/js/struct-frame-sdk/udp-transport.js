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
exports.UdpTransport = void 0;
// UDP Transport implementation using Node.js dgram
const dgram = __importStar(require("dgram"));
const transport_1 = require("./transport");
class UdpTransport extends transport_1.BaseTransport {
    constructor(config) {
        super(config);
        this.udpConfig = {
            ...this.config,
            localPort: config.localPort ?? 0,
            localAddress: config.localAddress ?? ((config.socketType ?? 'udp4') === 'udp6' ? '::' : '0.0.0.0'),
            remoteHost: config.remoteHost,
            remotePort: config.remotePort,
            socketType: config.socketType ?? 'udp4',
            broadcast: config.broadcast ?? false,
        };
    }
    async connect() {
        return new Promise((resolve, reject) => {
            try {
                this.socket = dgram.createSocket(this.udpConfig.socketType);
                this.socket.on('message', (msg) => {
                    this.handleData(new Uint8Array(msg));
                });
                this.socket.on('error', (err) => {
                    this.handleError(err);
                    reject(err);
                });
                this.socket.on('close', () => {
                    this.handleClose();
                });
                this.socket.bind(this.udpConfig.localPort, this.udpConfig.localAddress, () => {
                    if (this.socket && this.udpConfig.broadcast) {
                        this.socket.setBroadcast(true);
                    }
                    this.connected = true;
                    resolve();
                });
            }
            catch (error) {
                reject(error);
            }
        });
    }
    async disconnect() {
        return new Promise((resolve) => {
            if (this.socket) {
                this.socket.close(() => {
                    this.connected = false;
                    resolve();
                });
            }
            else {
                resolve();
            }
        });
    }
    async send(data) {
        return new Promise((resolve, reject) => {
            if (!this.socket || !this.connected) {
                reject(new Error('UDP socket not connected'));
                return;
            }
            this.socket.send(Buffer.from(data), this.udpConfig.remotePort, this.udpConfig.remoteHost, (err, bytes) => {
                if (err) {
                    reject(err);
                }
                else {
                    resolve(bytes);
                }
            });
        });
    }
}
exports.UdpTransport = UdpTransport;
