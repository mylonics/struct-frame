// Serial Port Transport implementation using serialport
import { SerialPort } from 'serialport';
import { BaseTransport, TransportConfig } from './transport';

export interface SerialTransportConfig extends TransportConfig {
  /** Serial port path (e.g., '/dev/ttyUSB0', 'COM3') */
  path: string;
  /** Baud rate */
  baudRate: number;
  /** Data bits (5, 6, 7, or 8) */
  dataBits?: 5 | 6 | 7 | 8;
  /** Stop bits (1 or 2) */
  stopBits?: 1 | 2;
  /** Parity ('none', 'even', 'odd', 'mark', or 'space') */
  parity?: 'none' | 'even' | 'odd' | 'mark' | 'space';
  /** Flow control */
  rtscts?: boolean;
  /** XON/XOFF flow control */
  xon?: boolean;
  xoff?: boolean;
}

export class SerialTransport extends BaseTransport {
  private port?: SerialPort;
  private serialConfig: Required<SerialTransportConfig>;

  constructor(config: SerialTransportConfig) {
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

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.port = new SerialPort({
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

        this.port.on('data', (data: Buffer) => {
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
      } catch (error) {
        reject(error);
      }
    });
  }

  async disconnect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.port && this.port.isOpen) {
        this.port.close((err) => {
          if (err) {
            reject(err);
          } else {
            this.connected = false;
            resolve();
          }
        });
      } else {
        resolve();
      }
    });
  }

  async send(data: Uint8Array): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.port || !this.connected || !this.port.isOpen) {
        reject(new Error('Serial port not connected'));
        return;
      }

      this.port.write(Buffer.from(data), (err) => {
        if (err) {
          reject(err);
        } else {
          // Wait for drain to ensure data is sent
          this.port!.drain((drainErr) => {
            if (drainErr) {
              reject(drainErr);
            } else {
              resolve();
            }
          });
        }
      });
    });
  }
}
