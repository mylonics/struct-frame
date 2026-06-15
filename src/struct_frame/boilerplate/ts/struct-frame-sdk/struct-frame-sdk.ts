// Struct Frame SDK Client
// High-level interface for sending and receiving framed messages

import { ITransport, SendResult } from './transport';
import { FrameMsgInfo } from '../frame-base';
import { MessageBase } from '../struct-base';
import {
  FrameProfileConfig,
  GetMessageInfo,
  AccumulatingReader,
  encodeMessage,
} from '../frame-profiles';

/**
 * Message handler callback type
 */
export type MessageHandler<T = any> = (message: T, msgId: number) => void;

/**
 * Message codec interface - deserializes raw bytes into message objects
 */
export interface MessageCodec<T = any> {
  getMsgId(): number;
  deserialize(data: Uint8Array): T;
}

/**
 * Struct Frame SDK Configuration
 */
export interface StructFrameSdkConfig {
  /** Transport layer */
  transport: ITransport;
  /** Frame profile configuration (e.g. ProfileStandardConfig) */
  profile: FrameProfileConfig;
  /** Callback for looking up message metadata by ID */
  getMessageInfo?: GetMessageInfo;
  /** Enable debug logging */
  debug?: boolean;
}

/**
 * Main SDK Client
 */
export class StructFrameSdk {
  private transport: ITransport;
  private profile: FrameProfileConfig;
  private getMessageInfo?: GetMessageInfo;
  private reader: AccumulatingReader;
  private debug: boolean;
  private messageHandlers: Map<number, MessageHandler[]> = new Map();
  private messageCodecs: Map<number, MessageCodec> = new Map();

  constructor(config: StructFrameSdkConfig) {
    this.transport = config.transport;
    this.profile = config.profile;
    this.getMessageInfo = config.getMessageInfo;
    this.reader = new AccumulatingReader(config.profile, config.getMessageInfo);
    this.debug = config.debug ?? false;

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
  registerCodec<T>(codec: MessageCodec<T>): void {
    this.messageCodecs.set(codec.getMsgId(), codec);
  }

  /**
   * Subscribe to messages with a specific message ID.
   * Returns an unsubscribe function.
   */
  subscribe<T = any>(msgId: number, handler: MessageHandler<T>): () => void {
    if (!this.messageHandlers.has(msgId)) {
      this.messageHandlers.set(msgId, []);
    }
    this.messageHandlers.get(msgId)!.push(handler);
    this.log(`Subscribed to message ID ${msgId}`);
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
   * Send a raw pre-serialized payload, framing it with the configured profile.
   */
  async sendRaw(msgId: number, data: Uint8Array): Promise<SendResult> {
    const info = this.getMessageInfo?.(msgId);
    const wrapper = {
      _buffer: Buffer.from(data),
      getMsgId: () => msgId,
      getMagic1: () => info?.magic1 ?? 0,
      getMagic2: () => info?.magic2 ?? 0,
      isVariable: () => false,
    } as unknown as MessageBase;
    const framedData = encodeMessage(this.profile, wrapper);
    const attemptedBytes = framedData.length;
    const bytesWritten = await this.transport.send(framedData);
    this.log(`Sent message ID ${msgId}, ${data.length} bytes`);
    return { success: bytesWritten === attemptedBytes, attemptedBytes, bytesWritten };
  }

  /**
   * Send a generated message object. Calls serialize() and reads the static _msgid
   * from the message's class. Optionally accepts an explicit msgId override.
   */
  async send<T extends { serialize(): Uint8Array }>(message: T, msgId?: number): Promise<SendResult> {
    const data = message.serialize();
    const id = msgId ?? (message.constructor as any)._msgid ?? 0;
    return await this.sendRaw(id, data);
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.transport.isConnected();
  }

  private handleIncomingData(data: Uint8Array): void {
    this.reader.addData(data);
    let result: FrameMsgInfo;
    while ((result = this.reader.next()).valid) {
      this.log(`Received message ID ${result.msgId}, ${result.msgLen} bytes`);
      const handlers = this.messageHandlers.get(result.msgId);
      if (handlers && handlers.length > 0) {
        let message: any = result.msgData;
        const codec = this.messageCodecs.get(result.msgId);
        if (codec) {
          try {
            message = codec.deserialize(result.msgData);
          } catch (error) {
            this.log(`Failed to deserialize message ID ${result.msgId}: ${error}`);
          }
        }
        handlers.forEach(handler => {
          try {
            handler(message, result.msgId);
          } catch (error) {
            this.log(`Handler error for message ID ${result.msgId}: ${error}`);
          }
        });
      }
    }
  }

  private handleError(error: Error): void {
    this.log(`Transport error: ${error.message}`);
  }

  private handleClose(): void {
    this.log('Transport closed');
    this.reader = new AccumulatingReader(this.profile, this.getMessageInfo);
  }

  private log(message: string): void {
    if (this.debug) {
      console.log(`[StructFrameSdk] ${message}`);
    }
  }
}
