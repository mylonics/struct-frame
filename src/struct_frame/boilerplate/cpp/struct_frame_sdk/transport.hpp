// Transport interface for C++ struct-frame SDK
// Header-only implementation

#pragma once

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
 * Callback types using function pointers (no std::function)
 */
using DataCallbackFn = void (*)(const uint8_t*, size_t, void*);
using ErrorCallbackFn = void (*)(const char*, void*);
using CloseCallbackFn = void (*)(void*);

/**
 * Transport interface for sending and receiving data
 * Uses function pointers with user_data for callback context
 */
class ITransport {
public:
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
     * @param user_data User context passed to callback
     */
    virtual void onData(DataCallbackFn callback, void* user_data) = 0;

    /**
     * Set callback for connection errors
     * @param callback Function to call when error occurs
     * @param user_data User context passed to callback
     */
    virtual void onError(ErrorCallbackFn callback, void* user_data) = 0;

    /**
     * Set callback for connection close
     * @param callback Function to call when connection closes
     * @param user_data User context passed to callback
     */
    virtual void onClose(CloseCallbackFn callback, void* user_data) = 0;

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
    DataCallbackFn dataCallback_ = nullptr;
    void* dataUserData_ = nullptr;
    ErrorCallbackFn errorCallback_ = nullptr;
    void* errorUserData_ = nullptr;
    CloseCallbackFn closeCallback_ = nullptr;
    void* closeUserData_ = nullptr;
    TransportConfig config_;
    int reconnectAttempts_ = 0;

    void handleData(const uint8_t* data, size_t length) {
        if (dataCallback_) {
            dataCallback_(data, length, dataUserData_);
        }
    }

    void handleError(const char* error) {
        if (errorCallback_) {
            errorCallback_(error, errorUserData_);
        }
        if (config_.autoReconnect && connected_) {
            attemptReconnect();
        }
    }

    void handleClose() {
        connected_ = false;
        if (closeCallback_) {
            closeCallback_(closeUserData_);
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

    void onData(DataCallbackFn callback, void* user_data) override {
        dataCallback_ = callback;
        dataUserData_ = user_data;
    }

    void onError(ErrorCallbackFn callback, void* user_data) override {
        errorCallback_ = callback;
        errorUserData_ = user_data;
    }

    void onClose(CloseCallbackFn callback, void* user_data) override {
        closeCallback_ = callback;
        closeUserData_ = user_data;
    }

    bool isConnected() const override {
        return connected_;
    }
};

} // namespace StructFrame
