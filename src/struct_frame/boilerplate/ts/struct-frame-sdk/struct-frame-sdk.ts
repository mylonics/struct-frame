// Struct Frame SDK Client
// High-level interface for sending and receiving framed messages

import { ITransport } from './transport';
import { FrameMsgInfo } from '../frame-base';

/**
 * Message handler callback type
 */
export type MessageHandler<T = any> = (message: T, msgId: number) => void;

/**
 * Frame parser interface - must be implemented by generated frame parsers
 */
export interface IFrameParser {
  /**
   * Parse incoming data and extract message
   */
  parse(data: Uint8Array): FrameMsgInfo;
  
  /**
   * Frame a message for sending
   */
  frame(msgId: number, data: Uint8Array): Uint8Array;
}

/**
 * Message codec interface - deserializes raw bytes into message objects
 */
export interface IMessageCodec<T = any> {
  /**
   * Get message ID for this codec
   */
  getMsgId(): number;
  
  /**
   * Deserialize bytes into message object
   */
  deserialize(data: Uint8Array): T;
}

/**
 * Struct Frame SDK Configuration
 */
export interface StructFrameSdkConfig {
  /** Transport layer */
  transport: ITransport;
  /** Frame parser */
  frameParser: IFrameParser;
  /** Enable debug logging */
  debug?: boolean;
}

/**
 * Main SDK Client
 */
export class StructFrameSdk {
  private transport: ITransport;
  private frameParser: IFrameParser;
  private debug: boolean;
  private messageHandlers: Map<number, MessageHandler[]> = new Map();
  private messageCodecs: Map<number, IMessageCodec> = new Map();
  private buffer: Uint8Array = new Uint8Array(0);

  constructor(config: StructFrameSdkConfig) {
    this.transport = config.transport;
    this.frameParser = config.frameParser;
    this.debug = config.debug ?? false;

    // Set up transport callbacks
    this.transport.onData((data) => this.handleIncomingData(data));
    this.transport.onError((error) => this.handleError(error));
    this.transport.onClose(() => this.handleClose());
  }

  /**
   * Connect to the transport
   */
  async connect(): Promise<void> {
    await this.transport.connect();
    this.log('Connected');
  }

  /**
   * Disconnect from the transport
   */
  async disconnect(): Promise<void> {
    await this.transport.disconnect();
    this.log('Disconnected');
  }

  /**
   * Register a message codec for automatic deserialization
   */
  registerCodec<T>(codec: IMessageCodec<T>): void {
    this.messageCodecs.set(codec.getMsgId(), codec);
  }

  /**
   * Subscribe to messages with a specific message ID
   */
  subscribe<T = any>(msgId: number, handler: MessageHandler<T>): () => void {
    if (!this.messageHandlers.has(msgId)) {
      this.messageHandlers.set(msgId, []);
    }
    this.messageHandlers.get(msgId)!.push(handler);
    this.log(`Subscribed to message ID ${msgId}`);

    // Return unsubscribe function
    return () => {
      const handlers = this.messageHandlers.get(msgId);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index > -1) {
          handlers.splice(index, 1);
        }
      }
    };
  }

  /**
   * Send a raw message (already serialized)
   */
  async sendRaw(msgId: number, data: Uint8Array): Promise<void> {
    const framedData = this.frameParser.frame(msgId, data);
    await this.transport.send(framedData);
    this.log(`Sent message ID ${msgId}, ${data.length} bytes`);
  }

  /**
   * Send a message object (requires pack() method)
   */
  async send<T extends { pack(): Uint8Array; msg_id: number }>(message: T): Promise<void> {
    const data = message.pack();
    await this.sendRaw(message.msg_id, data);
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.transport.isConnected();
  }

  private handleIncomingData(data: Uint8Array): void {
    // Append to buffer
    const newBuffer = new Uint8Array(this.buffer.length + data.length);
    newBuffer.set(this.buffer);
    newBuffer.set(data, this.buffer.length);
    this.buffer = newBuffer;

    // Try to parse messages from buffer
    this.parseBuffer();
  }

  private parseBuffer(): void {
    while (this.buffer.length > 0) {
      const result = this.frameParser.parse(this.buffer);
      
      if (!result.valid) {
        // No valid frame found, keep buffer as is
        break;
      }

      // Valid message found
      this.log(`Received message ID ${result.msg_id}, ${result.msg_len} bytes`);
      
      // Notify handlers
      const handlers = this.messageHandlers.get(result.msg_id);
      if (handlers && handlers.length > 0) {
        // Try to deserialize with registered codec
        let message: any = result.msg_data;
        const codec = this.messageCodecs.get(result.msg_id);
        if (codec) {
          try {
            message = codec.deserialize(result.msg_data);
          } catch (error) {
            this.log(`Failed to deserialize message ID ${result.msg_id}: ${error}`);
          }
        }

        // Call all handlers
        handlers.forEach(handler => {
          try {
            handler(message, result.msg_id);
          } catch (error) {
            this.log(`Handler error for message ID ${result.msg_id}: ${error}`);
          }
        });
      }

      // Remove parsed data from buffer
      const totalFrameSize = this.calculateFrameSize(result);
      this.buffer = this.buffer.slice(totalFrameSize);
    }
  }

  private calculateFrameSize(result: FrameMsgInfo): number {
    // Calculate total frame size including headers and footers
    // For BasicDefault format: 2 start bytes + 1 length + 1 msg_id + payload + 2 crc = 6 + payload
    // For TinyDefault format: 1 start byte + 1 length + 1 msg_id + payload + 2 crc = 5 + payload
    // Using conservative estimate of 10 bytes overhead to handle various frame formats
    // TODO: Query frame parser for exact overhead to avoid buffering issues
    return result.msg_len + 10;
  }

  private handleError(error: Error): void {
    this.log(`Transport error: ${error.message}`);
  }

  private handleClose(): void {
    this.log('Transport closed');
    this.buffer = new Uint8Array(0);
  }

  private log(message: string): void {
    if (this.debug) {
      console.log(`[StructFrameSdk] ${message}`);
    }
  }
}
