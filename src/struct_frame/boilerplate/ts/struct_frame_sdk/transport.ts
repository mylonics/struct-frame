// Transport interface for struct-frame SDK
// Provides abstraction for various communication channels

export interface ITransport {
  /**
   * Connect to the transport endpoint
   */
  connect(): Promise<void>;

  /**
   * Disconnect from the transport endpoint
   */
  disconnect(): Promise<void>;

  /**
   * Send data through the transport
   * @param data - Data to send
   */
  send(data: Uint8Array): Promise<void>;

  /**
   * Set callback for receiving data
   * @param callback - Function to call when data is received
   */
  onData(callback: (data: Uint8Array) => void): void;

  /**
   * Set callback for connection errors
   * @param callback - Function to call when error occurs
   */
  onError(callback: (error: Error) => void): void;

  /**
   * Set callback for connection close
   * @param callback - Function to call when connection closes
   */
  onClose(callback: () => void): void;

  /**
   * Check if transport is connected
   */
  isConnected(): boolean;
}

export interface TransportConfig {
  /** Auto-reconnect on connection loss */
  autoReconnect?: boolean;
  /** Reconnection delay in milliseconds */
  reconnectDelay?: number;
  /** Maximum reconnection attempts (0 = infinite) */
  maxReconnectAttempts?: number;
}

export abstract class BaseTransport implements ITransport {
  protected connected: boolean = false;
  protected dataCallback?: (data: Uint8Array) => void;
  protected errorCallback?: (error: Error) => void;
  protected closeCallback?: () => void;
  protected config: Required<TransportConfig>;
  protected reconnectAttempts: number = 0;

  constructor(config?: TransportConfig) {
    this.config = {
      autoReconnect: config?.autoReconnect ?? false,
      reconnectDelay: config?.reconnectDelay ?? 1000,
      maxReconnectAttempts: config?.maxReconnectAttempts ?? 0,
    };
  }

  abstract connect(): Promise<void>;
  abstract disconnect(): Promise<void>;
  abstract send(data: Uint8Array): Promise<void>;

  onData(callback: (data: Uint8Array) => void): void {
    this.dataCallback = callback;
  }

  onError(callback: (error: Error) => void): void {
    this.errorCallback = callback;
  }

  onClose(callback: () => void): void {
    this.closeCallback = callback;
  }

  isConnected(): boolean {
    return this.connected;
  }

  protected handleData(data: Uint8Array): void {
    if (this.dataCallback) {
      this.dataCallback(data);
    }
  }

  protected handleError(error: Error): void {
    if (this.errorCallback) {
      this.errorCallback(error);
    }
    if (this.config.autoReconnect && this.connected) {
      this.attemptReconnect();
    }
  }

  protected handleClose(): void {
    this.connected = false;
    if (this.closeCallback) {
      this.closeCallback();
    }
    if (this.config.autoReconnect) {
      this.attemptReconnect();
    }
  }

  protected async attemptReconnect(): Promise<void> {
    if (this.config.maxReconnectAttempts > 0 && 
        this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      return;
    }

    this.reconnectAttempts++;
    await new Promise(resolve => setTimeout(resolve, this.config.reconnectDelay));
    
    try {
      await this.connect();
      this.reconnectAttempts = 0;
    } catch (error) {
      this.handleError(error as Error);
    }
  }
}
