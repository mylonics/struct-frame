// WebSocket Transport implementation using WebSocket API
import { BaseTransport, TransportConfig } from './transport';

export interface WebSocketTransportConfig extends TransportConfig {
  /** WebSocket URL (ws:// or wss://) */
  url: string;
  /** WebSocket protocols */
  protocols?: string | string[];
}

export class WebSocketTransport extends BaseTransport {
  private ws?: WebSocket;
  private wsConfig: Required<WebSocketTransportConfig>;

  constructor(config: WebSocketTransportConfig) {
    super(config);
    this.wsConfig = {
      ...this.config,
      url: config.url,
      protocols: config.protocols ?? [],
    };
  }

  async connect(): Promise<void> {
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
          let data: Uint8Array;
          if (event.data instanceof ArrayBuffer) {
            data = new Uint8Array(event.data);
          } else if (event.data instanceof Blob) {
            // Handle blob asynchronously
            event.data.arrayBuffer().then(buffer => {
              this.handleData(new Uint8Array(buffer));
            });
            return;
          } else {
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
      } catch (error) {
        reject(error);
      }
    });
  }

  async disconnect(): Promise<void> {
    return new Promise((resolve) => {
      if (this.ws) {
        if (this.ws.readyState === WebSocket.OPEN) {
          this.ws.close();
        }
        this.connected = false;
        resolve();
      } else {
        resolve();
      }
    });
  }

  async send(data: Uint8Array): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.ws || !this.connected || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket not connected'));
        return;
      }

      try {
        this.ws.send(data);
        resolve();
      } catch (error) {
        reject(error);
      }
    });
  }
}
