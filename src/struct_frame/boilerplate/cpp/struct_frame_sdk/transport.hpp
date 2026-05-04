// Transport interface for C++ struct-frame SDK
// Header-only implementation

#pragma once

#include <memory>
#include <vector>
#include <cstdint>

namespace structframe {
namespace sdk {

/**
 * Transport configuration base
 */
struct TransportConfig {
    bool auto_reconnect = false;
    int reconnect_delay_ms = 1000;
    int max_reconnect_attempts = 0;  // 0 = infinite
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
class Transport {
public:
    virtual ~Transport() = default;

    /**
     * Connect to the transport endpoint
     */
    virtual void Connect() = 0;

    /**
     * Disconnect from the transport endpoint
     */
    virtual void Disconnect() = 0;

    /**
     * Send data through the transport
     * @param data Pointer to data buffer
     * @param length Length of data
     */
    virtual void Send(const uint8_t* data, size_t length) = 0;

    /**
     * Set callback for receiving data
     * @param callback Function to call when data is received
     * @param user_data User context passed to callback
     */
    virtual void OnData(DataCallbackFn callback, void* user_data) = 0;

    /**
     * Set callback for connection errors
     * @param callback Function to call when error occurs
     * @param user_data User context passed to callback
     */
    virtual void OnError(ErrorCallbackFn callback, void* user_data) = 0;

    /**
     * Set callback for connection close
     * @param callback Function to call when connection closes
     * @param user_data User context passed to callback
     */
    virtual void OnClose(CloseCallbackFn callback, void* user_data) = 0;

    /**
     * Check if transport is connected
     */
    virtual bool IsConnected() const = 0;
};

/**
 * Base transport with common functionality
 */
class BaseTransport : public Transport {
protected:
    bool connected_ = false;
    DataCallbackFn data_callback_ = nullptr;
    void* data_user_data_ = nullptr;
    ErrorCallbackFn error_callback_ = nullptr;
    void* error_user_data_ = nullptr;
    CloseCallbackFn close_callback_ = nullptr;
    void* close_user_data_ = nullptr;
    TransportConfig config_;
    int reconnect_attempts_ = 0;

    void HandleData(const uint8_t* data, size_t length) {
        if (data_callback_) {
            data_callback_(data, length, data_user_data_);
        }
    }

    void HandleError(const char* error) {
        if (error_callback_) {
            error_callback_(error, error_user_data_);
        }
        if (config_.auto_reconnect && connected_) {
            AttemptReconnect();
        }
    }

    void HandleClose() {
        connected_ = false;
        if (close_callback_) {
            close_callback_(close_user_data_);
        }
        if (config_.auto_reconnect) {
            AttemptReconnect();
        }
    }

    virtual void AttemptReconnect() {
        if (config_.max_reconnect_attempts > 0 &&
            reconnect_attempts_ >= config_.max_reconnect_attempts) {
            return;
        }

        reconnect_attempts_++;
        // Reconnect logic would go here
        // In practice, this would use a timer/thread to delay reconnection
    }

public:
    BaseTransport(const TransportConfig& config = TransportConfig())
        : config_(config) {}

    void OnData(DataCallbackFn callback, void* user_data) override {
        data_callback_ = callback;
        data_user_data_ = user_data;
    }

    void OnError(ErrorCallbackFn callback, void* user_data) override {
        error_callback_ = callback;
        error_user_data_ = user_data;
    }

    void OnClose(CloseCallbackFn callback, void* user_data) override {
        close_callback_ = callback;
        close_user_data_ = user_data;
    }

    bool IsConnected() const override {
        return connected_;
    }
};

} // namespace sdk
} // namespace structframe
