"use strict";
// Struct Frame SDK Client
// High-level interface for sending and receiving framed messages
Object.defineProperty(exports, "__esModule", { value: true });
exports.StructFrameSdk = void 0;
const frame_profiles_1 = require("../frame-profiles");
/**
 * Main SDK Client
 */
class StructFrameSdk {
    constructor(config) {
        this.messageHandlers = new Map();
        this.messageCodecs = new Map();
        this.transport = config.transport;
        this.profile = config.profile;
        this.getMessageInfo = config.getMessageInfo;
        this.reader = new frame_profiles_1.AccumulatingReader(config.profile, config.getMessageInfo);
        this.debug = config.debug ?? false;
        this.transport.onData((data) => this.handleIncomingData(data));
        this.transport.onError((error) => this.handleError(error));
        this.transport.onClose(() => this.handleClose());
    }
    /**
     * Connect to the transport
     */
    async connect() {
        await this.transport.connect();
        this.log('Connected');
    }
    /**
     * Disconnect from the transport
     */
    async disconnect() {
        await this.transport.disconnect();
        this.log('Disconnected');
    }
    /**
     * Register a message codec for automatic deserialization
     */
    registerCodec(codec) {
        this.messageCodecs.set(codec.getMsgId(), codec);
    }
    /**
     * Subscribe to messages with a specific message ID.
     * Returns an unsubscribe function.
     */
    subscribe(msgId, handler) {
        if (!this.messageHandlers.has(msgId)) {
            this.messageHandlers.set(msgId, []);
        }
        this.messageHandlers.get(msgId).push(handler);
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
    async sendRaw(msgId, data) {
        const info = this.getMessageInfo?.(msgId);
        // encodeMessage only reads _buffer (bulk-copied into the frame), so pass the
        // caller's payload through directly instead of allocating a defensive copy.
        const wrapper = {
            _buffer: data,
            getMsgId: () => msgId,
            getMagic1: () => info?.magic1 ?? 0,
            getMagic2: () => info?.magic2 ?? 0,
            isVariable: () => false,
        };
        const framedData = (0, frame_profiles_1.encodeMessage)(this.profile, wrapper);
        const attemptedBytes = framedData.length;
        const bytesWritten = await this.transport.send(framedData);
        this.log(`Sent message ID ${msgId}, ${data.length} bytes`);
        return { success: bytesWritten === attemptedBytes, attemptedBytes, bytesWritten };
    }
    /**
     * Send a generated message object. Calls serialize() and reads the static _msgid
     * from the message's class. Optionally accepts an explicit msgId override.
     */
    async send(message, msgId) {
        const data = message.serialize();
        const id = msgId ?? message.constructor._msgid ?? 0;
        return await this.sendRaw(id, data);
    }
    /**
     * Check if connected
     */
    isConnected() {
        return this.transport.isConnected();
    }
    handleIncomingData(data) {
        this.reader.addData(data);
        let result;
        while ((result = this.reader.next()).valid) {
            this.log(`Received message ID ${result.msgId}, ${result.msgLen} bytes`);
            const handlers = this.messageHandlers.get(result.msgId);
            if (handlers && handlers.length > 0) {
                let message = result.msgData;
                const codec = this.messageCodecs.get(result.msgId);
                if (codec) {
                    try {
                        message = codec.deserialize(result.msgData);
                    }
                    catch (error) {
                        this.log(`Failed to deserialize message ID ${result.msgId}: ${error}`);
                    }
                }
                for (let i = 0; i < handlers.length; i++) {
                    try {
                        handlers[i](message, result.msgId);
                    }
                    catch (error) {
                        this.log(`Handler error for message ID ${result.msgId}: ${error}`);
                    }
                }
            }
        }
    }
    handleError(error) {
        this.log(`Transport error: ${error.message}`);
    }
    handleClose() {
        this.log('Transport closed');
        this.reader = new frame_profiles_1.AccumulatingReader(this.profile, this.getMessageInfo);
    }
    log(message) {
        if (this.debug) {
            console.log(`[StructFrameSdk] ${message}`);
        }
    }
}
exports.StructFrameSdk = StructFrameSdk;
