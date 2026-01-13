// UDP Transport implementation using Node.js dgram
import * as dgram from 'dgram';
import { BaseTransport, TransportConfig } from './transport';

export interface UdpTransportConfig extends TransportConfig {
  /** Local port to bind to */
  localPort?: number;
  /** Local address to bind to */
  localAddress?: string;
  /** Remote host to send to */
  remoteHost: string;
  /** Remote port to send to */
  remotePort: number;
  /** Socket type: 'udp4' or 'udp6' */
  socketType?: 'udp4' | 'udp6';
  /** Enable broadcast */
  broadcast?: boolean;
}

export class UdpTransport extends BaseTransport {
  private socket?: dgram.Socket;
  private udpConfig: Required<UdpTransportConfig>;

  constructor(config: UdpTransportConfig) {
    super(config);
    this.udpConfig = {
      ...this.config,
      localPort: config.localPort ?? 0,
      localAddress: config.localAddress ?? '0.0.0.0',
      remoteHost: config.remoteHost,
      remotePort: config.remotePort,
      socketType: config.socketType ?? 'udp4',
      broadcast: config.broadcast ?? false,
    };
  }

  async connect(): Promise<void> {
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
      } catch (error) {
        reject(error);
      }
    });
  }

  async disconnect(): Promise<void> {
    return new Promise((resolve) => {
      if (this.socket) {
        this.socket.close(() => {
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
        reject(new Error('UDP socket not connected'));
        return;
      }

      this.socket.send(
        Buffer.from(data),
        this.udpConfig.remotePort,
        this.udpConfig.remoteHost,
        (err) => {
          if (err) {
            reject(err);
          } else {
            resolve();
          }
        }
      );
    });
  }
}
