// Generic Serial Interface for embedded systems
// Header-only implementation without external dependencies

#pragma once

#include "transport.hpp"
#include <cstring>

namespace StructFrame {

/**
 * Generic serial interface that can be implemented for any platform
 * This provides a hardware abstraction layer for embedded systems
 */
class ISerialPort {
public:
    virtual ~ISerialPort() = default;

    /**
     * Open the serial port
     * @return true on success
     */
    virtual bool open() = 0;

    /**
     * Close the serial port
     */
    virtual void close() = 0;

    /**
     * Write data to serial port
     * @param data Pointer to data buffer
     * @param length Length of data
     * @return Number of bytes written
     */
    virtual size_t write(const uint8_t* data, size_t length) = 0;

    /**
     * Read data from serial port (non-blocking)
     * @param buffer Buffer to read into
     * @param maxLength Maximum bytes to read
     * @return Number of bytes read
     */
    virtual size_t read(uint8_t* buffer, size_t maxLength) = 0;

    /**
     * Check if serial port is open
     */
    virtual bool isOpen() const = 0;

    /**
     * Get number of bytes available to read
     */
    virtual size_t available() const = 0;
};

/**
 * Serial transport configuration
 */
struct SerialTransportConfig : public TransportConfig {
    size_t bufferSize = 4096;
};

/**
 * Serial transport using generic serial interface
 * Suitable for embedded systems and cross-platform development
 */
class SerialTransport : public BaseTransport {
private:
    ISerialPort* serialPort_;
    SerialTransportConfig serialConfig_;
    std::vector<uint8_t> receiveBuffer_;
    bool running_ = false;

public:
    /**
     * Construct serial transport
     * @param serialPort Platform-specific serial port implementation
     * @param config Transport configuration
     */
    SerialTransport(ISerialPort* serialPort, const SerialTransportConfig& config = SerialTransportConfig())
        : BaseTransport(config), serialPort_(serialPort), serialConfig_(config) {
        receiveBuffer_.resize(config.bufferSize);
    }

    void connect() override {
        if (!serialPort_) {
            handleError("Serial port not initialized");
            return;
        }

        if (!serialPort_->open()) {
            handleError("Failed to open serial port");
            return;
        }

        connected_ = true;
        running_ = true;
    }

    void disconnect() override {
        running_ = false;
        if (serialPort_ && serialPort_->isOpen()) {
            serialPort_->close();
        }
        connected_ = false;
    }

    void send(const uint8_t* data, size_t length) override {
        if (!serialPort_ || !connected_ || !serialPort_->isOpen()) {
            handleError("Serial port not connected");
            return;
        }

        size_t written = serialPort_->write(data, length);
        if (written != length) {
            handleError("Failed to write all data to serial port");
        }
    }

    /**
     * Poll for incoming data (call this regularly in your main loop)
     * This is designed for embedded systems without threading
     */
    void poll() {
        if (!serialPort_ || !connected_ || !serialPort_->isOpen() || !running_) {
            return;
        }

        size_t available = serialPort_->available();
        if (available > 0) {
            size_t toRead = (available < receiveBuffer_.size()) ? available : receiveBuffer_.size();
            size_t bytesRead = serialPort_->read(receiveBuffer_.data(), toRead);
            
            if (bytesRead > 0) {
                handleData(receiveBuffer_.data(), bytesRead);
            }
        }
    }
};

// Example platform-specific implementation stub
// Users would implement this for their specific hardware

#ifdef EXAMPLE_IMPLEMENTATION
/**
 * Example UART implementation for embedded system
 * Replace this with your platform's UART driver
 */
class ExampleUartPort : public ISerialPort {
private:
    // Platform-specific UART handle
    void* uartHandle_;
    bool isOpen_;

public:
    ExampleUartPort() : uartHandle_(nullptr), isOpen_(false) {}

    bool open() override {
        // Platform-specific code to open UART
        // uartHandle_ = HAL_UART_Init(...);
        isOpen_ = true;
        return isOpen_;
    }

    void close() override {
        // Platform-specific code to close UART
        // HAL_UART_DeInit(uartHandle_);
        isOpen_ = false;
    }

    size_t write(const uint8_t* data, size_t length) override {
        if (!isOpen_) return 0;
        // Platform-specific code to write data
        // return HAL_UART_Transmit(uartHandle_, data, length, timeout);
        return length;
    }

    size_t read(uint8_t* buffer, size_t maxLength) override {
        if (!isOpen_) return 0;
        // Platform-specific code to read data
        // return HAL_UART_Receive(uartHandle_, buffer, maxLength, timeout);
        return 0;
    }

    bool isOpen() const override {
        return isOpen_;
    }

    size_t available() const override {
        if (!isOpen_) return 0;
        // Platform-specific code to check available bytes
        // return HAL_UART_GetRxDataCount(uartHandle_);
        return 0;
    }
};
#endif // EXAMPLE_IMPLEMENTATION

} // namespace StructFrame
