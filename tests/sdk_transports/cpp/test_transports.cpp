// Loopback tests for the concrete C++ SDK TcpTransport and UdpTransport (ASIO). A small blocking
// ASIO peer plays the other side. Every wait is bounded, so a stuck socket fails instead of hanging.
//
//   g++ -std=c++20 -I <asio include> -I src/struct_frame/boilerplate/cpp \
//       tests/sdk_transports/cpp/test_transports.cpp -o test_transports -pthread
#include <atomic>
#include <chrono>
#include <cstdio>
#include <functional>
#include <mutex>
#include <thread>
#include <vector>

#include "struct_frame_sdk/network_transports.hpp"

using namespace structframe::sdk;
using namespace std::chrono_literals;

static int g_run = 0, g_failed = 0;

static void check(const char* name, bool ok) {
  g_run++;
  if (!ok) g_failed++;
  std::printf("  %s  %s\n", ok ? "PASS" : "FAIL", name);
}

static bool until(const std::function<bool()>& pred, int timeout_ms = 2000) {
  auto end = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeout_ms);
  while (std::chrono::steady_clock::now() < end) {
    if (pred()) return true;
    std::this_thread::sleep_for(5ms);
  }
  return pred();
}

struct Sink {
  std::mutex m;
  std::vector<uint8_t> data;
  std::atomic<int> closed{0};
  std::atomic<int> errors{0};
  size_t size() { std::lock_guard<std::mutex> l(m); return data.size(); }
  bool equals(std::initializer_list<uint8_t> v) {
    std::lock_guard<std::mutex> l(m);
    return data == std::vector<uint8_t>(v);
  }
};

static void on_data(const uint8_t* d, size_t n, void* u) {
  auto* s = static_cast<Sink*>(u);
  std::lock_guard<std::mutex> l(s->m);
  s->data.insert(s->data.end(), d, d + n);
}
static void on_close(void* u) { static_cast<Sink*>(u)->closed++; }
static void on_error(const char*, void* u) { static_cast<Sink*>(u)->errors++; }

static void test_tcp() {
  std::printf("TCP transport\n");
  asio::io_context peer_ctx;
  asio::ip::tcp::acceptor acceptor(peer_ctx, asio::ip::tcp::endpoint(asio::ip::make_address("127.0.0.1"), 0));
  uint16_t port = acceptor.local_endpoint().port();

  std::unique_ptr<asio::ip::tcp::socket> peer;
  std::atomic<bool> accepted{false};
  Sink peer_got;
  std::thread accept_thread([&] {
    peer = std::make_unique<asio::ip::tcp::socket>(peer_ctx);
    asio::error_code ec;
    acceptor.accept(*peer, ec);
    accepted = !ec;
    uint8_t buf[256];
    while (!ec) {
      size_t n = peer->read_some(asio::buffer(buf), ec);
      if (!ec) on_data(buf, n, &peer_got);
    }
  });

  TcpTransportConfig cfg;
  cfg.host = "127.0.0.1";
  cfg.port = port;
  Sink got;
  {
    TcpTransport t(cfg);
    t.OnData(on_data, &got);
    t.OnClose(on_close, &got);
    t.OnError(on_error, &got);

    check("IsConnected false before Connect", !t.IsConnected());
    t.Connect();
    check("IsConnected true after Connect", t.IsConnected());

    const uint8_t out[] = {1, 2, 3, 4};
    check("Send returns the byte count", t.Send(out, 4) == 4);
    check("peer receives the bytes sent", until([&] { return peer_got.size() == 4; }) && peer_got.equals({1, 2, 3, 4}));

    until([&] { return accepted.load(); });
    const uint8_t in[] = {9, 8, 7};
    asio::write(*peer, asio::buffer(in));
    check("OnData delivers bytes sent by the peer", until([&] { return got.size() == 3; }) && got.equals({9, 8, 7}));

    asio::error_code ec;
    peer->shutdown(asio::ip::tcp::socket::shutdown_both, ec);
    peer->close(ec);
    check("peer close fires OnClose", until([&] { return got.closed == 1; }));
    check("IsConnected false after peer close", !t.IsConnected());
    size_t sent = t.Send(out, 4);
    check("Send on a closed transport returns 0 and reports an error", sent == 0 && got.errors > 0);
    t.Disconnect();
  }
  accept_thread.join();

  // Connection refused: take a port, then free it again.
  uint16_t dead_port;
  {
    asio::io_context c;
    asio::ip::tcp::acceptor a(c, asio::ip::tcp::endpoint(asio::ip::make_address("127.0.0.1"), 0));
    dead_port = a.local_endpoint().port();
  }
  TcpTransportConfig bad;
  bad.host = "127.0.0.1";
  bad.port = dead_port;
  Sink bad_sink;
  TcpTransport t2(bad);
  t2.OnError(on_error, &bad_sink);
  bool threw = false;
  try { t2.Connect(); } catch (const std::exception&) { threw = true; }
  check("Connect to a closed port throws", threw);
  check("the failure is also reported through OnError", bad_sink.errors > 0);
  check("IsConnected stays false after a failed connect", !t2.IsConnected());

  // Disconnect is idempotent and clears the state.
  asio::io_context c3;
  asio::ip::tcp::acceptor a3(c3, asio::ip::tcp::endpoint(asio::ip::make_address("127.0.0.1"), 0));
  TcpTransportConfig cfg3;
  cfg3.host = "127.0.0.1";
  cfg3.port = a3.local_endpoint().port();
  std::thread acc3([&] { asio::ip::tcp::socket s(c3); asio::error_code e; a3.accept(s, e); });
  TcpTransport t3(cfg3);
  t3.Connect();
  t3.Disconnect();
  t3.Disconnect();
  check("Disconnect clears IsConnected (and is idempotent)", !t3.IsConnected());
  acc3.join();
}

static void test_udp() {
  std::printf("UDP transport\n");
  asio::io_context ctx;
  asio::ip::udp::socket peer(ctx, asio::ip::udp::endpoint(asio::ip::make_address("127.0.0.1"), 0));
  uint16_t peer_port = peer.local_endpoint().port();

  UdpTransportConfig cfg;
  cfg.remoteHost = "127.0.0.1";
  cfg.remotePort = peer_port;
  Sink got;
  UdpTransport t(cfg);
  t.OnData(on_data, &got);
  t.Connect();
  check("IsConnected true after Connect", t.IsConnected());

  const uint8_t out[] = {5, 6, 7};
  check("Send returns the byte count", t.Send(out, 3) == 3);

  uint8_t buf[64];
  asio::ip::udp::endpoint from;
  peer.non_blocking(true);
  size_t n = 0;
  bool received = until([&] {
    asio::error_code ec;
    n = peer.receive_from(asio::buffer(buf), from, 0, ec);
    return !ec && n > 0;
  });
  check("peer receives the datagram", received && n == 3 && buf[0] == 5 && buf[2] == 7);

  if (received) {
    const uint8_t in[] = {40, 41};
    peer.send_to(asio::buffer(in), from);
    check("OnData delivers a datagram from the peer", until([&] { return got.size() == 2; }) && got.equals({40, 41}));
  }
  t.Disconnect();
  check("Disconnect clears IsConnected", !t.IsConnected());
}

int main() {
  std::thread watchdog([] {
    std::this_thread::sleep_for(60s);
    std::printf("FAIL  transport tests timed out\n");
    std::_Exit(2);
  });
  watchdog.detach();
  test_tcp();
  test_udp();
  std::printf("\n%d/%d transport checks passed\n", g_run - g_failed, g_run);
  return g_failed == 0 ? 0 : 1;
}
