// Transport interface for C++ struct-frame SDK
// Header-only implementation

#pragma once

#include <functional>
#include <memory>
#include <vector>
#include <cstdint>

namespace StructFrame {

/**
 * Transport configuration base
 */
struct TransportConfig {
    bool autoReconnect = false;
    int reconnectDelayMs = 1000;
    int maxReconnectAttempts = 0;  // 0 = infinite
};

/**
 * Transport interface for sending and receiving data
 */
class ITransport {
public:
    using DataCallback = std::function<void(const uint8_t*, size_t)>;
    using ErrorCallback = std::function<void(const std::string&)>;
    using CloseCallback = std::function<void()>;

    virtual ~ITransport() = default;

    /**
     * Connect to the transport endpoint
     */
    virtual void connect() = 0;

    /**
     * Disconnect from the transport endpoint
     */
    virtual void disconnect() = 0;

    /**
     * Send data through the transport
     * @param data Pointer to data buffer
     * @param length Length of data
     */
    virtual void send(const uint8_t* data, size_t length) = 0;

    /**
     * Set callback for receiving data
     * @param callback Function to call when data is received
     */
    virtual void onData(DataCallback callback) = 0;

    /**
     * Set callback for connection errors
     * @param callback Function to call when error occurs
     */
    virtual void onError(ErrorCallback callback) = 0;

    /**
     * Set callback for connection close
     * @param callback Function to call when connection closes
     */
    virtual void onClose(CloseCallback callback) = 0;

    /**
     * Check if transport is connected
     */
    virtual bool isConnected() const = 0;
};

/**
 * Base transport with common functionality
 */
class BaseTransport : public ITransport {
protected:
    bool connected_ = false;
    DataCallback dataCallback_;
    ErrorCallback errorCallback_;
    CloseCallback closeCallback_;
    TransportConfig config_;
    int reconnectAttempts_ = 0;

    void handleData(const uint8_t* data, size_t length) {
        if (dataCallback_) {
            dataCallback_(data, length);
        }
    }

    void handleError(const std::string& error) {
        if (errorCallback_) {
            errorCallback_(error);
        }
        if (config_.autoReconnect && connected_) {
            attemptReconnect();
        }
    }

    void handleClose() {
        connected_ = false;
        if (closeCallback_) {
            closeCallback_();
        }
        if (config_.autoReconnect) {
            attemptReconnect();
        }
    }

    virtual void attemptReconnect() {
        if (config_.maxReconnectAttempts > 0 &&
            reconnectAttempts_ >= config_.maxReconnectAttempts) {
            return;
        }

        reconnectAttempts_++;
        // Reconnect logic would go here
        // In practice, this would use a timer/thread to delay reconnection
    }

public:
    BaseTransport(const TransportConfig& config = TransportConfig())
        : config_(config) {}

    void onData(DataCallback callback) override {
        dataCallback_ = std::move(callback);
    }

    void onError(ErrorCallback callback) override {
        errorCallback_ = std::move(callback);
    }

    void onClose(CloseCallback callback) override {
        closeCallback_ = std::move(callback);
    }

    bool isConnected() const override {
        return connected_;
    }
};

} // namespace StructFrame
