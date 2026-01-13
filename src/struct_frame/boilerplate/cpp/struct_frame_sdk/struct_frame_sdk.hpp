// Struct Frame SDK Client for C++
// Header-only implementation

#pragma once

#include "transport.hpp"
#include "observer.hpp"
#include <map>
#include <vector>
#include <cstdint>
#include <cstring>

namespace StructFrame {

/**
 * Frame parser interface - must be implemented by generated frame parsers
 */
class IFrameParser {
public:
    virtual ~IFrameParser() = default;

    /**
     * Parse incoming data and extract message
     * Returns frame message info with valid flag
     */
    virtual FrameParsers::FrameMsgInfo parse(const uint8_t* data, size_t length) = 0;

    /**
     * Frame a message for sending
     * @param msgId Message ID
     * @param data Message payload
     * @param dataLen Payload length
     * @param output Output buffer for framed message
     * @param outputMaxLen Maximum output buffer size
     * @return Actual framed message length
     */
    virtual size_t frame(uint8_t msgId, const uint8_t* data, size_t dataLen,
                        uint8_t* output, size_t outputMaxLen) = 0;
};

/**
 * Message codec interface - deserializes raw bytes into message objects
 */
template<typename TMessage>
class IMessageCodec {
public:
    virtual ~IMessageCodec() = default;

    /**
     * Get message ID for this codec
     */
    virtual uint8_t getMsgId() const = 0;

    /**
     * Deserialize bytes into message object
     */
    virtual bool deserialize(const uint8_t* data, size_t length, TMessage& message) = 0;
};

/**
 * Struct Frame SDK Configuration
 */
struct StructFrameSdkConfig {
    ITransport* transport;
    IFrameParser* frameParser;
    bool debug = false;
    size_t maxBufferSize = 8192;
};

/**
 * Main SDK Client
 */
class StructFrameSdk {
private:
    ITransport* transport_;
    IFrameParser* frameParser_;
    bool debug_;
    std::vector<uint8_t> buffer_;
    size_t maxBufferSize_;

    // Type-erased observable map for different message types
    std::map<uint8_t, void*> observables_;

    void handleIncomingData(const uint8_t* data, size_t length) {
        // Append to buffer
        if (buffer_.size() + length > maxBufferSize_) {
            log("Buffer overflow, clearing buffer");
            buffer_.clear();
        }

        buffer_.insert(buffer_.end(), data, data + length);

        // Try to parse messages from buffer
        parseBuffer();
    }

    void parseBuffer() {
        while (!buffer_.empty()) {
            auto result = frameParser_->parse(buffer_.data(), buffer_.size());

            if (!result.valid) {
                // No valid frame found
                break;
            }

            // Valid message found
            log("Received message ID " + std::to_string(result.msg_id) +
                ", " + std::to_string(result.msg_len) + " bytes");

            // Notify observers (user must call notifyObservers with proper type)
            // This is handled by the typed notifyObservers method

            // Remove parsed data from buffer
            size_t frameSize = calculateFrameSize(result);
            buffer_.erase(buffer_.begin(), buffer_.begin() + frameSize);
        }
    }

    size_t calculateFrameSize(const FrameParsers::FrameMsgInfo& result) const {
        // Calculate total frame size including headers and footers
        // Frame overhead by format:
        // - BasicDefault: 2 start + 1 length + 1 msg_id + payload + 2 crc = 6 + payload
        // - TinyDefault: 1 start + 1 length + 1 msg_id + payload + 2 crc = 5 + payload
        // Using conservative estimate of 10 bytes to handle all frame formats
        // TODO: Query frame parser for exact overhead to avoid buffering issues
        return result.msg_len + 10;
    }

    void handleError(const std::string& error) {
        log("Transport error: ");
        log(error);
    }

    void handleClose() {
        log("Transport closed");
        buffer_.clear();
    }

    void log(const std::string& message) {
        if (debug_) {
            // In a real implementation, this would use platform-specific logging
            // printf("[StructFrameSdk] %s\n", message.c_str());
        }
    }

    void log(const char* message) {
        if (debug_) {
            // In a real implementation, this would use platform-specific logging
            // printf("[StructFrameSdk] %s\n", message);
        }
    }

    // Static callback wrappers for transport
    static void dataCallbackWrapper(const uint8_t* data, size_t length, void* user_data) {
        auto* self = static_cast<StructFrameSdk*>(user_data);
        self->handleIncomingData(data, length);
    }

    static void errorCallbackWrapper(const char* error, void* user_data) {
        auto* self = static_cast<StructFrameSdk*>(user_data);
        self->handleError(error);
    }

    static void closeCallbackWrapper(void* user_data) {
        auto* self = static_cast<StructFrameSdk*>(user_data);
        self->handleClose();
    }

public:
    StructFrameSdk(const StructFrameSdkConfig& config)
        : transport_(config.transport),
          frameParser_(config.frameParser),
          debug_(config.debug),
          maxBufferSize_(config.maxBufferSize) {

        buffer_.reserve(maxBufferSize_);

        // Set up transport callbacks using static wrappers
        transport_->onData(dataCallbackWrapper, this);
        transport_->onError(errorCallbackWrapper, this);
        transport_->onClose(closeCallbackWrapper, this);
    }

    ~StructFrameSdk() {
        // Clean up observables
        for (auto& pair : observables_) {
            // Type-erased, would need proper cleanup in real implementation
        }
    }

    /**
     * Connect to the transport
     */
    void connect() {
        transport_->connect();
        log("Connected");
    }

    /**
     * Disconnect from the transport
     */
    void disconnect() {
        transport_->disconnect();
        log("Disconnected");
    }

    /**
     * Get or create observable for a specific message type
     * @tparam TMessage The message type
     * @tparam MaxObservers Maximum number of observers (default 16)
     * @param msgId The message ID
     */
    template<typename TMessage, size_t MaxObservers = 16>
    Observable<TMessage, MaxObservers>* getObservable(uint8_t msgId) {
        auto it = observables_.find(msgId);
        if (it == observables_.end()) {
            auto* observable = new Observable<TMessage, MaxObservers>();
            observables_[msgId] = static_cast<void*>(observable);
            return observable;
        }
        return static_cast<Observable<TMessage, MaxObservers>*>(it->second);
    }

    /**
     * Subscribe to messages with a specific message ID
     * @tparam TMessage The message type
     * @tparam MaxObservers Maximum number of observers (default 16)
     * @param msgId The message ID
     * @param observer The observer to subscribe
     * @return Subscription handle (RAII)
     */
    template<typename TMessage, size_t MaxObservers = 16>
    Subscription<TMessage, MaxObservers> subscribe(uint8_t msgId, IObserver<TMessage>* observer) {
        auto* observable = getObservable<TMessage, MaxObservers>(msgId);
        observable->subscribe(observer);
        log("Subscribed to message ID " + std::to_string(msgId));
        return Subscription<TMessage, MaxObservers>(observable, observer);
    }

    /**
     * Subscribe with a callable (lambda, functor, etc.)
     * @tparam TMessage The message type
     * @tparam Callable The callable type
     * @tparam MaxObservers Maximum number of observers (default 16)
     * @param msgId The message ID
     * @param callback Callable to invoke when message is received
     * @return Subscription handle (RAII) - keep alive as long as subscription is needed
     */
    template<typename TMessage, typename Callable, size_t MaxObservers = 16>
    Subscription<TMessage, MaxObservers> subscribe(uint8_t msgId, Callable callback) {
        auto* observer = new CallableObserver<TMessage, Callable>(callback);
        auto* observable = getObservable<TMessage, MaxObservers>(msgId);
        observable->subscribe(observer);
        log("Subscribed to message ID " + std::to_string(msgId));
        return Subscription<TMessage, MaxObservers>(observable, observer);
    }

    /**
     * Notify observers of a parsed message (internal use)
     * @tparam TMessage The message type
     * @tparam MaxObservers Maximum number of observers (default 16)
     * @param msgId The message ID
     * @param message The parsed message
     */
    template<typename TMessage, size_t MaxObservers = 16>
    void notifyObservers(uint8_t msgId, const TMessage& message) {
        auto it = observables_.find(msgId);
        if (it != observables_.end()) {
            auto* observable = static_cast<Observable<TMessage, MaxObservers>*>(it->second);
            observable->notify(message, msgId);
        }
    }

    /**
     * Send a raw message (already serialized)
     * @param msgId Message ID
     * @param data Message payload
     * @param dataLen Payload length
     */
    void sendRaw(uint8_t msgId, const uint8_t* data, size_t dataLen) {
        // Frame the message
        std::vector<uint8_t> framedData(dataLen + 20);  // Extra space for framing
        size_t framedLen = frameParser_->frame(msgId, data, dataLen,
                                              framedData.data(), framedData.size());

        transport_->send(framedData.data(), framedLen);
        log("Sent message ID " + std::to_string(msgId) + ", " +
            std::to_string(dataLen) + " bytes");
    }

    /**
     * Send a message object (requires pack() method and msg_id member)
     * @tparam TMessage Message type
     * @param message The message to send
     */
    template<typename TMessage>
    void send(const TMessage& message) {
        // Assuming message has pack method and msg_id member
        std::vector<uint8_t> packed(message.msg_size);
        // User would call message.pack(packed.data()) or similar
        // This is placeholder - actual implementation depends on generated code
        sendRaw(message.msg_id, packed.data(), packed.size());
    }

    /**
     * Check if connected
     */
    bool isConnected() const {
        return transport_->isConnected();
    }
};

} // namespace StructFrame
