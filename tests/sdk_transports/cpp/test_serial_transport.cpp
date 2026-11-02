// Tests for the C++ SDK's embedded SerialTransport (struct_frame_sdk/serial_transport.hpp).
// The transport drives a user-supplied ISerialPort, so an in-memory port stands in for the UART.
//
//   g++ -std=c++20 -I src/struct_frame/boilerplate/cpp tests/sdk_transports/cpp/test_serial_transport.cpp
#include <cstdio>
#include <deque>
#include <string>
#include <vector>

#include "struct_frame_sdk/serial_transport.hpp"

using namespace structframe::sdk;

static int g_run = 0, g_failed = 0;

static void check(const char* name, bool ok) {
  g_run++;
  if (!ok) g_failed++;
  std::printf("  %s  %s\n", ok ? "PASS" : "FAIL", name);
}

class FakePort : public ISerialPort {
 public:
  bool open_ok = true;
  bool is_open = false;
  size_t write_limit = SIZE_MAX;  // bytes accepted per write() call
  std::vector<uint8_t> written;
  std::deque<uint8_t> incoming;
  int read_calls = 0;

  bool open() override { is_open = open_ok; incoming.clear(); return open_ok; }
  void close() override { is_open = false; incoming.clear(); }  // a closed port keeps no input
  size_t write(const uint8_t* data, size_t length) override {
    size_t n = length < write_limit ? length : write_limit;
    written.insert(written.end(), data, data + n);
    return n;
  }
  size_t read(uint8_t* buffer, size_t max_length) override {
    read_calls++;
    size_t n = 0;
    while (n < max_length && !incoming.empty()) {
      buffer[n++] = incoming.front();
      incoming.pop_front();
    }
    return n;
  }
  bool isOpen() const override { return is_open; }
  size_t available() const override { return incoming.size(); }
};

struct Events {
  std::vector<uint8_t> data;
  std::vector<std::string> errors;
};

static void on_data(const uint8_t* d, size_t n, void* u) {
  auto* e = static_cast<Events*>(u);
  e->data.insert(e->data.end(), d, d + n);
}
static void on_error(const char* msg, void* u) { static_cast<Events*>(u)->errors.emplace_back(msg); }

int main() {
  std::printf("Serial transport (ISerialPort)\n");

  {
    Events ev;
    SerialTransport t(nullptr);
    t.OnError(on_error, &ev);
    t.Connect();
    check("Connect without a port reports an error", !t.IsConnected() && ev.errors.size() == 1);
  }

  {
    FakePort port;
    port.open_ok = false;
    Events ev;
    SerialTransport t(&port);
    t.OnError(on_error, &ev);
    t.Connect();
    check("Connect reports a port that fails to open", !t.IsConnected() && ev.errors.size() == 1);
  }

  {
    FakePort port;
    Events ev;
    SerialTransportConfig cfg;
    cfg.bufferSize = 8;
    SerialTransport t(&port, cfg);
    t.OnData(on_data, &ev);
    t.OnError(on_error, &ev);

    const uint8_t frame[] = {0x90, 0x71, 0x02, 0x01, 0xAA, 0xBB, 0x12, 0x34};
    check("Send before Connect returns 0 and reports an error", t.Send(frame, sizeof frame) == 0 && ev.errors.size() == 1);

    t.Connect();
    check("Connect opens the port", t.IsConnected() && port.is_open);
    check("Send writes every byte", t.Send(frame, sizeof frame) == sizeof frame &&
                                        port.written == std::vector<uint8_t>(frame, frame + sizeof frame));

    port.write_limit = 3;
    size_t errors_before = ev.errors.size();
    check("a short write is returned and reported", t.Send(frame, sizeof frame) == 3 && ev.errors.size() == errors_before + 1);
    port.write_limit = SIZE_MAX;

    t.poll();
    check("poll with nothing available delivers nothing and does not read", ev.data.empty() && port.read_calls == 0);

    for (int i = 0; i < 20; i++) port.incoming.push_back(static_cast<uint8_t>(i));
    t.poll();
    check("poll reads at most bufferSize bytes per call", ev.data.size() == 8);
    t.poll();
    t.poll();
    bool in_order = ev.data.size() == 20;
    for (size_t i = 0; in_order && i < ev.data.size(); i++) in_order = ev.data[i] == i;
    check("repeated polls deliver everything, in order", in_order);

    t.Disconnect();
    check("Disconnect closes the port", !t.IsConnected() && !port.is_open);
    port.incoming.push_back(0x55);
    t.poll();
    check("poll after Disconnect delivers nothing", ev.data.size() == 20);

    t.Connect();
    port.incoming.push_back(0x66);
    t.poll();
    check("the transport works again after reconnecting", t.IsConnected() && ev.data.size() == 21 && ev.data.back() == 0x66);
  }

  std::printf("\n%d/%d transport checks passed\n", g_run - g_failed, g_run);
  return g_failed == 0 ? 0 : 1;
}
