// Network transport implementations using ASIO
// NOTE: These require the ASIO library (header-only or standalone)
// Include asio.hpp or boost/asio.hpp in your project

#pragma once

#include "transport.hpp"

namespace StructFrame {

/*
 * UDP Transport using ASIO
 * 
 * To use this transport, you need to:
 * 1. Include ASIO in your project
 * 2. Implement the transport using asio::ip::udp::socket
 * 3. Handle async operations with io_context
 * 
 * Example implementation:
 * 
 * class UdpTransport : public BaseTransport {
 * private:
 *     asio::io_context io_context_;
 *     asio::ip::udp::socket socket_;
 *     asio::ip::udp::endpoint remote_endpoint_;
 *     
 * public:
 *     UdpTransport(const std::string& host, uint16_t port);
 *     void connect() override;
 *     void disconnect() override;
 *     void send(const uint8_t* data, size_t length) override;
 *     void startReceive();
 * };
 */

/*
 * TCP Transport using ASIO
 * 
 * To use this transport, you need to:
 * 1. Include ASIO in your project
 * 2. Implement the transport using asio::ip::tcp::socket
 * 3. Handle async operations with io_context
 * 
 * Example implementation:
 * 
 * class TcpTransport : public BaseTransport {
 * private:
 *     asio::io_context io_context_;
 *     asio::ip::tcp::socket socket_;
 *     asio::ip::tcp::endpoint endpoint_;
 *     
 * public:
 *     TcpTransport(const std::string& host, uint16_t port);
 *     void connect() override;
 *     void disconnect() override;
 *     void send(const uint8_t* data, size_t length) override;
 *     void startReceive();
 * };
 */

/*
 * WebSocket Transport using Simple-WebSocket-Server
 * 
 * To use this transport, you need to:
 * 1. Include Simple-WebSocket-Server in your project
 * 2. Include ASIO (required by Simple-WebSocket-Server)
 * 3. Implement the transport using WsClient or WssClient
 * 
 * Example implementation:
 * 
 * #include "client_ws.hpp"
 * using WsClient = SimpleWeb::SocketClient<SimpleWeb::WS>;
 * 
 * class WebSocketTransport : public BaseTransport {
 * private:
 *     std::shared_ptr<WsClient> client_;
 *     std::shared_ptr<WsClient::Connection> connection_;
 *     
 * public:
 *     WebSocketTransport(const std::string& url);
 *     void connect() override;
 *     void disconnect() override;
 *     void send(const uint8_t* data, size_t length) override;
 * };
 */

/*
 * Serial Transport using ASIO Serial Port
 * 
 * To use this transport, you need to:
 * 1. Include ASIO in your project
 * 2. Implement the transport using asio::serial_port
 * 
 * Example implementation:
 * 
 * class AsioSerialTransport : public BaseTransport {
 * private:
 *     asio::io_context io_context_;
 *     asio::serial_port serial_port_;
 *     
 * public:
 *     AsioSerialTransport(const std::string& port, uint32_t baud_rate);
 *     void connect() override;
 *     void disconnect() override;
 *     void send(const uint8_t* data, size_t length) override;
 *     void startReceive();
 * };
 */

} // namespace StructFrame
