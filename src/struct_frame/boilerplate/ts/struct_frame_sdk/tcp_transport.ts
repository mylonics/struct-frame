// TCP Transport implementation using Node.js net
import * as net from 'net';
import { BaseTransport, TransportConfig } from './transport';

export interface TcpTransportConfig extends TransportConfig {
  /** Remote host to connect to */
  host: string;
  /** Remote port to connect to */
  port: number;
  /** Connection timeout in milliseconds */
  timeout?: number;
}

export class TcpTransport extends BaseTransport {
  private socket?: net.Socket;
  private tcpConfig: Required<TcpTransportConfig>;

  constructor(config: TcpTransportConfig) {
    super(config);
    this.tcpConfig = {
      ...this.config,
      host: config.host,
      port: config.port,
      timeout: config.timeout ?? 5000,
    };
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.socket = new net.Socket();
        this.socket.setTimeout(this.tcpConfig.timeout);

        this.socket.on('connect', () => {
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
      } catch (error) {
        reject(error);
      }
    });
  }

  async disconnect(): Promise<void> {
    return new Promise((resolve) => {
      if (this.socket) {
        this.socket.end(() => {
          this.connected = false;
          resolve();
        });
      } else {
        resolve();
      }
    });
  }

  async send(data: Uint8Array): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.socket || !this.connected) {
        reject(new Error('TCP socket not connected'));
        return;
      }

      this.socket.write(Buffer.from(data), (err) => {
        if (err) {
          reject(err);
        } else {
          resolve();
        }
      });
    });
  }
}
