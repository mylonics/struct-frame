// Network transport implementations using ASIO (standalone)
// ASIO headers are included in this directory for convenience

#pragma once

#define ASIO_STANDALONE
#include "asio.hpp"
#include "transport.hpp"
#include <thread>
#include <memory>

namespace StructFrame {

/**
 * UDP Transport configuration
 */
struct UdpTransportConfig : public TransportConfig {
    std::string remoteHost;
    uint16_t remotePort;
    uint16_t localPort = 0;
    size_t bufferSize = 4096;
};

/**
 * UDP Transport using ASIO
 */
class UdpTransport : public BaseTransport {
private:
    asio::io_context io_context_;
    asio::ip::udp::socket socket_;
    asio::ip::udp::endpoint remote_endpoint_;
    std::thread io_thread_;
    std::vector<uint8_t> receive_buffer_;
    UdpTransportConfig udp_config_;

    void startReceive() {
        socket_.async_receive_from(
            asio::buffer(receive_buffer_),
            remote_endpoint_,
            [this](const asio::error_code& error, std::size_t bytes_transferred) {
                if (!error && bytes_transferred > 0) {
                    handleData(receive_buffer_.data(), bytes_transferred);
                } else if (error) {
                    handleError("UDP receive error: " + error.message());
                }
                if (connected_) {
                    startReceive();
                }
            }
        );
    }

public:
    UdpTransport(const UdpTransportConfig& config)
        : BaseTransport(config), 
          socket_(io_context_), 
          receive_buffer_(config.bufferSize),
          udp_config_(config) {}

    ~UdpTransport() {
        if (connected_) {
            disconnect();
        }
    }

    void connect() override {
        try {
            // Resolve remote endpoint
            asio::ip::udp::resolver resolver(io_context_);
            auto endpoints = resolver.resolve(
                asio::ip::udp::v4(),
                udp_config_.remoteHost,
                std::to_string(udp_config_.remotePort)
            );
            remote_endpoint_ = *endpoints.begin();

            // Open and bind socket
            socket_.open(asio::ip::udp::v4());
            socket_.bind(asio::ip::udp::endpoint(asio::ip::udp::v4(), udp_config_.localPort));

            connected_ = true;
            
            // Start receiving
            startReceive();
            
            // Run io_context in separate thread
            io_thread_ = std::thread([this]() {
                io_context_.run();
            });
        } catch (const std::exception& e) {
            handleError("UDP connect error: " + std::string(e.what()));
            throw;
        }
    }

    void disconnect() override {
        connected_ = false;
        io_context_.stop();
        if (socket_.is_open()) {
            socket_.close();
        }
        if (io_thread_.joinable()) {
            io_thread_.join();
        }
        io_context_.restart();
    }

    void send(const uint8_t* data, size_t length) override {
        if (!connected_ || !socket_.is_open()) {
            handleError("UDP socket not connected");
            return;
        }

        try {
            socket_.send_to(asio::buffer(data, length), remote_endpoint_);
        } catch (const std::exception& e) {
            handleError("UDP send error: " + std::string(e.what()));
        }
    }
};

/**
 * TCP Transport configuration
 */
struct TcpTransportConfig : public TransportConfig {
    std::string host;
    uint16_t port;
    size_t bufferSize = 4096;
};

/**
 * TCP Transport using ASIO
 */
class TcpTransport : public BaseTransport {
private:
    asio::io_context io_context_;
    asio::ip::tcp::socket socket_;
    std::thread io_thread_;
    std::vector<uint8_t> receive_buffer_;
    TcpTransportConfig tcp_config_;

    void startReceive() {
        socket_.async_read_some(
            asio::buffer(receive_buffer_),
            [this](const asio::error_code& error, std::size_t bytes_transferred) {
                if (!error && bytes_transferred > 0) {
                    handleData(receive_buffer_.data(), bytes_transferred);
                    if (connected_) {
                        startReceive();
                    }
                } else if (error) {
                    if (error == asio::error::eof) {
                        handleClose();
                    } else {
                        handleError("TCP receive error: " + error.message());
                    }
                }
            }
        );
    }

public:
    TcpTransport(const TcpTransportConfig& config)
        : BaseTransport(config),
          socket_(io_context_),
          receive_buffer_(config.bufferSize),
          tcp_config_(config) {}

    ~TcpTransport() {
        if (connected_) {
            disconnect();
        }
    }

    void connect() override {
        try {
            // Resolve endpoint
            asio::ip::tcp::resolver resolver(io_context_);
            auto endpoints = resolver.resolve(tcp_config_.host, std::to_string(tcp_config_.port));

            // Connect
            asio::connect(socket_, endpoints);
            connected_ = true;

            // Start receiving
            startReceive();

            // Run io_context in separate thread
            io_thread_ = std::thread([this]() {
                io_context_.run();
            });
        } catch (const std::exception& e) {
            handleError("TCP connect error: " + std::string(e.what()));
            throw;
        }
    }

    void disconnect() override {
        connected_ = false;
        io_context_.stop();
        if (socket_.is_open()) {
            asio::error_code ec;
            socket_.shutdown(asio::ip::tcp::socket::shutdown_both, ec);
            socket_.close();
        }
        if (io_thread_.joinable()) {
            io_thread_.join();
        }
        io_context_.restart();
    }

    void send(const uint8_t* data, size_t length) override {
        if (!connected_ || !socket_.is_open()) {
            handleError("TCP socket not connected");
            return;
        }

        try {
            asio::write(socket_, asio::buffer(data, length));
        } catch (const std::exception& e) {
            handleError("TCP send error: " + std::string(e.what()));
        }
    }
};

/**
 * Serial Transport using ASIO serial port
 */
struct SerialTransportConfig : public TransportConfig {
    std::string port;
    uint32_t baudRate = 115200;
    size_t bufferSize = 4096;
};

/**
 * ASIO Serial Port Transport
 */
class AsioSerialTransport : public BaseTransport {
private:
    asio::io_context io_context_;
    asio::serial_port serial_port_;
    std::thread io_thread_;
    std::vector<uint8_t> receive_buffer_;
    SerialTransportConfig serial_config_;

    void startReceive() {
        serial_port_.async_read_some(
            asio::buffer(receive_buffer_),
            [this](const asio::error_code& error, std::size_t bytes_transferred) {
                if (!error && bytes_transferred > 0) {
                    handleData(receive_buffer_.data(), bytes_transferred);
                    if (connected_) {
                        startReceive();
                    }
                } else if (error) {
                    handleError("Serial receive error: " + error.message());
                }
            }
        );
    }

public:
    AsioSerialTransport(const SerialTransportConfig& config)
        : BaseTransport(config),
          serial_port_(io_context_),
          receive_buffer_(config.bufferSize),
          serial_config_(config) {}

    ~AsioSerialTransport() {
        if (connected_) {
            disconnect();
        }
    }

    void connect() override {
        try {
            // Open serial port
            serial_port_.open(serial_config_.port);
            
            // Set baud rate
            serial_port_.set_option(asio::serial_port_base::baud_rate(serial_config_.baudRate));
            serial_port_.set_option(asio::serial_port_base::character_size(8));
            serial_port_.set_option(asio::serial_port_base::parity(asio::serial_port_base::parity::none));
            serial_port_.set_option(asio::serial_port_base::stop_bits(asio::serial_port_base::stop_bits::one));
            serial_port_.set_option(asio::serial_port_base::flow_control(asio::serial_port_base::flow_control::none));

            connected_ = true;

            // Start receiving
            startReceive();

            // Run io_context in separate thread
            io_thread_ = std::thread([this]() {
                io_context_.run();
            });
        } catch (const std::exception& e) {
            handleError("Serial connect error: " + std::string(e.what()));
            throw;
        }
    }

    void disconnect() override {
        connected_ = false;
        io_context_.stop();
        if (serial_port_.is_open()) {
            serial_port_.close();
        }
        if (io_thread_.joinable()) {
            io_thread_.join();
        }
        io_context_.restart();
    }

    void send(const uint8_t* data, size_t length) override {
        if (!connected_ || !serial_port_.is_open()) {
            handleError("Serial port not connected");
            return;
        }

        try {
            asio::write(serial_port_, asio::buffer(data, length));
        } catch (const std::exception& e) {
            handleError("Serial send error: " + std::string(e.what()));
        }
    }
};

} // namespace StructFrame
