"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SerialTransport = void 0;
// Serial Port Transport implementation using serialport
const serialport_1 = require("serialport");
const transport_1 = require("./transport");
class SerialTransport extends transport_1.BaseTransport {
    constructor(config) {
        super(config);
        this.serialConfig = {
            ...this.config,
            path: config.path,
            baudRate: config.baudRate,
            dataBits: config.dataBits ?? 8,
            stopBits: config.stopBits ?? 1,
            parity: config.parity ?? 'none',
            rtscts: config.rtscts ?? false,
            xon: config.xon ?? false,
            xoff: config.xoff ?? false,
        };
    }
    async connect() {
        return new Promise((resolve, reject) => {
            try {
                this.port = new serialport_1.SerialPort({
                    path: this.serialConfig.path,
                    baudRate: this.serialConfig.baudRate,
                    dataBits: this.serialConfig.dataBits,
                    stopBits: this.serialConfig.stopBits,
                    parity: this.serialConfig.parity,
                    rtscts: this.serialConfig.rtscts,
                    xon: this.serialConfig.xon,
                    xoff: this.serialConfig.xoff,
                });
                this.port.on('open', () => {
                    this.connected = true;
                    resolve();
                });
                this.port.on('data', (data) => {
                    this.handleData(new Uint8Array(data));
                });
                this.port.on('error', (err) => {
                    this.handleError(err);
                    if (!this.connected) {
                        reject(err);
                    }
                });
                this.port.on('close', () => {
                    this.handleClose();
                });
            }
            catch (error) {
                reject(error);
            }
        });
    }
    async disconnect() {
        return new Promise((resolve, reject) => {
            if (this.port && this.port.isOpen) {
                this.port.close((err) => {
                    if (err) {
                        reject(err);
                    }
                    else {
                        this.connected = false;
                        resolve();
                    }
                });
            }
            else {
                resolve();
            }
        });
    }
    async send(data) {
        return new Promise((resolve, reject) => {
            if (!this.port || !this.connected || !this.port.isOpen) {
                reject(new Error('Serial port not connected'));
                return;
            }
            this.port.write(Buffer.from(data), (err) => {
                if (err) {
                    reject(err);
                }
                else {
                    // Wait for drain to ensure data is sent
                    this.port.drain((drainErr) => {
                        if (drainErr) {
                            reject(drainErr);
                        }
                        else {
                            resolve(data.length);
                        }
                    });
                }
            });
        });
    }
}
exports.SerialTransport = SerialTransport;
