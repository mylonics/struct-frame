// Transport primitives for C++ struct-frame SDK
// Header-only implementation

#pragma once

#include <cstddef>
#include <cstdint>

namespace structframe {
namespace sdk {

/**
 * Transport configuration base.
 *
 * auto_reconnect, reconnect_delay_ms, and max_reconnect_attempts are
 * configuration knobs inherited by concrete transports (SerialTransport,
 * TcpTransport, etc.). Reconnect logic is NOT implemented in BaseTransport
 * itself — concrete transports must implement AttemptReconnect() for these
 * fields to have any effect.
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
 * Base transport with common functionality
 */
class BaseTransport {
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

    /**
     * Attempt to reconnect after an error or close event.
     * BaseTransport provides no implementation — concrete transports must
     * override this method to support auto-reconnect.
     */
    void AttemptReconnect() {}

public:
    BaseTransport(const TransportConfig& config = TransportConfig())
        : config_(config) {}

    ~BaseTransport() = default;

    void OnData(DataCallbackFn callback, void* user_data) {
        data_callback_ = callback;
        data_user_data_ = user_data;
    }

    void OnError(ErrorCallbackFn callback, void* user_data) {
        error_callback_ = callback;
        error_user_data_ = user_data;
    }

    void OnClose(CloseCallbackFn callback, void* user_data) {
        close_callback_ = callback;
        close_user_data_ = user_data;
    }

    bool IsConnected() const {
        return connected_;
    }

    /**
     * Establish a connection. Concrete transports can hide this method to
     * provide actual connection logic. Default implementation is a no-op.
     */
    void Connect() {}

    /**
     * Close the connection. Concrete transports can hide this method to
     * provide actual disconnection logic. Default implementation is a no-op.
     */
    void Disconnect() {}

    /**
     * Send data through the transport. Concrete transports can hide this
     * method to provide actual send logic. Default implementation returns 0.
     * @return Number of bytes sent.
     */
    size_t Send(const uint8_t*, size_t) { return 0; }
};

} // namespace sdk
} // namespace structframe
