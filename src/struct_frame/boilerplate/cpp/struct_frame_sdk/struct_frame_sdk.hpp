// Struct Frame SDK Client for C++
// Header-only implementation

#pragma once

#include "transport.hpp"
#include "observer.hpp"
#include <map>
#include <vector>
#include <cstdint>
#include <cstring>

namespace structframe {
namespace sdk {

/**
 * Frame parser interface - must be implemented by generated frame parsers
 */
class frame_parser {
public:
    virtual ~frame_parser() = default;

    /**
     * Parse incoming data and extract message
     * Returns frame message info with valid flag
     */
    virtual structframe::FrameMsgInfo parse(const uint8_t* data, size_t length) = 0;

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
class MessageCodec {
public:
    virtual ~MessageCodec() = default;

    /**
     * Get message ID for this codec
     */
    virtual uint8_t GetMsgId() const = 0;

    /**
     * Deserialize bytes into message object
     */
    virtual bool deserialize(const uint8_t* data, size_t length, TMessage& message) = 0;
};

/**
 * Struct Frame SDK Configuration
 */
struct StructFrameSdkConfig {
    Transport* transport;
    frame_parser* parser;
    bool debug = false;
    size_t max_buffer_size = 8192;
};

/**
 * Main SDK Client
 */
class StructFrameSdk {
private:
    Transport* transport_;
    frame_parser* frame_parser_;
    bool debug_;
    std::vector<uint8_t> buffer_;
    size_t max_buffer_size_;

    // Type-erased observable map for different message types
    std::map<uint8_t, void*> observables_;

    void HandleIncomingData(const uint8_t* data, size_t length) {
        // Append to buffer
        if (buffer_.size() + length > max_buffer_size_) {
            log("Buffer overflow, clearing buffer");
            buffer_.clear();
        }

        buffer_.insert(buffer_.end(), data, data + length);

        // Try to parse messages from buffer
        ParseBuffer();
    }

    void ParseBuffer() {
        while (!buffer_.empty()) {
            auto result = frame_parser_->parse(buffer_.data(), buffer_.size());

            if (!result.valid) {
                // No valid frame found
                break;
            }

            // Valid message found
            log("Received message ID " + std::to_string(result.msg_id) +
                ", " + std::to_string(result.msg_len) + " bytes");

            // Notify observers (user must call NotifyObservers with proper type)
            // This is handled by the typed NotifyObservers method

            // Remove parsed data from buffer
            size_t frameSize = CalculateFrameSize(result);
            if (frameSize == 0 || frameSize > buffer_.size()) {
                // Safety guard: if CalculateFrameSize returns more than the buffer
                // holds (e.g. conservative estimate exceeded actual data), consume
                // the whole buffer to avoid an infinite loop.
                buffer_.clear();
                break;
            }
            buffer_.erase(buffer_.begin(), buffer_.begin() + frameSize);
        }
    }

    size_t CalculateFrameSize(const structframe::FrameMsgInfo& result) const {
        // Prefer the exact total frame size reported by the parser when available.
        if (result.frame_size > 0) {
            return result.frame_size;
        }
        // Fallback: conservative estimate of 10 bytes overhead to handle all
        // frame formats when the parser does not populate frame_size.
        // TODO: Query frame parser for exact overhead to avoid buffering issues
        return result.msg_len + 10;
    }

    void HandleError(const std::string& error) {
        log("Transport error: ");
        log(error);
    }

    void HandleClose() {
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
    static void DataCallbackWrapper(const uint8_t* data, size_t length, void* user_data) {
        auto* self = static_cast<StructFrameSdk*>(user_data);
        self->HandleIncomingData(data, length);
    }

    static void ErrorCallbackWrapper(const char* error, void* user_data) {
        auto* self = static_cast<StructFrameSdk*>(user_data);
        self->HandleError(error);
    }

    static void CloseCallbackWrapper(void* user_data) {
        auto* self = static_cast<StructFrameSdk*>(user_data);
        self->HandleClose();
    }

public:
    StructFrameSdk(const StructFrameSdkConfig& config)
        : transport_(config.transport),
          frame_parser_(config.parser),
          debug_(config.debug),
          max_buffer_size_(config.max_buffer_size) {

        buffer_.reserve(max_buffer_size_);

        // Set up transport callbacks using static wrappers
        transport_->OnData(DataCallbackWrapper, this);
        transport_->OnError(ErrorCallbackWrapper, this);
        transport_->OnClose(CloseCallbackWrapper, this);
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
    void Connect() {
        transport_->Connect();
        log("Connected");
    }

    /**
     * Disconnect from the transport
     */
    void Disconnect() {
        transport_->Disconnect();
        log("Disconnected");
    }

    /**
     * Get or create observable for a specific message type
     * @tparam TMessage The message type
     * @tparam MaxObservers Maximum number of observers (default 16)
     * @param msgId The message ID
     */
    template<typename TMessage, size_t MaxObservers = 16>
    Observable<TMessage, MaxObservers>* GetObservable(uint8_t msgId) {
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
        auto* observable = GetObservable<TMessage, MaxObservers>(msgId);
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
        auto* observable = GetObservable<TMessage, MaxObservers>(msgId);
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
    void NotifyObservers(uint8_t msgId, const TMessage& message) {
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
    void SendRaw(uint8_t msgId, const uint8_t* data, size_t dataLen) {
        // Frame the message
        std::vector<uint8_t> framedData(dataLen + 20);  // Extra space for framing
        size_t framedLen = frame_parser_->frame(msgId, data, dataLen,
                                              framedData.data(), framedData.size());

        transport_->Send(framedData.data(), framedLen);
        log("Sent message ID " + std::to_string(msgId) + ", " +
            std::to_string(dataLen) + " bytes");
    }

    /**
     * Send a message object (requires pack() method and msg_id member)
     * @tparam TMessage Message type
     * @param message The message to send
     */
    template<typename TMessage>
    void Send(const TMessage& message) {
        // Assuming message has pack method and msg_id member
        std::vector<uint8_t> packed(message.msg_size);
        // User would call message.pack(packed.data()) or similar
        // This is placeholder - actual implementation depends on generated code
        SendRaw(message.msg_id, packed.data(), packed.size());
    }

    /**
     * Check if connected
     */
    bool IsConnected() const {
        return transport_->IsConnected();
    }
};

} // namespace sdk
} // namespace structframe
