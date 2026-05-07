/**
 * Subscribe/dispatch tests for the C++ StructFrameSdk (section 6.3)
 *
 * Tests the observer pattern provided by StructFrameSdk:
 * - subscribe() with callable callbacks
 * - NotifyObservers() dispatches to registered observers
 * - RAII Subscription handle auto-unsubscribes on destruction
 * - Multiple observers for the same message ID
 * - Transport integration: incoming data triggers ParseBuffer
 */

#include <cstdio>
#include <cstring>
#include <vector>

// Generated frame profiles and message types
#include "include/standard_messages.hpp"
#include "../../generated/cpp/frame_profiles.hpp"

// StructFrameSdk (header-only)
#include "../../src/struct_frame/boilerplate/cpp/struct_frame_sdk/struct_frame_sdk.hpp"

using namespace structframe;
using namespace structframe::serialization_test;
using namespace structframe::sdk;

// ============================================================================
// Mock transport
// ============================================================================

/**
 * MockTransport - records all calls and allows manual data injection.
 */
class MockTransport : public BaseTransport {
 public:
  int connect_calls = 0;
  int disconnect_calls = 0;
  std::vector<std::vector<uint8_t>> sent_data;

  void Connect() override { connect_calls++; connected_ = true; }
  void Disconnect() override { disconnect_calls++; connected_ = false; }
  void Send(const uint8_t* data, size_t length) override {
    sent_data.push_back(std::vector<uint8_t>(data, data + length));
  }

  // Simulate incoming data from the peer
  void inject_data(const uint8_t* data, size_t length) {
    HandleData(data, length);
  }
};

// ============================================================================
// Mock frame_parser
// ============================================================================

/**
 * MockFrameParser - wraps AccumulatingReader<ProfileStandardConfig> so that
 * StructFrameSdk can parse real encoded frames in tests.
 */
class MockFrameParser : public frame_parser {
 public:
  int parse_calls = 0;

  FrameMsgInfo parse(const uint8_t* data, size_t length) override {
    parse_calls++;
    return BufferParserWithCrc<ProfileStandardConfig>::parse(data, length,
                                                             get_message_info);
  }

  size_t frame(uint8_t msgId, const uint8_t* data, size_t dataLen,
               uint8_t* output, size_t outputMaxLen) override {
    // Minimal passthrough: copy payload with a trivial header for test purposes.
    // Full framing is not needed for send tests in this file.
    if (outputMaxLen < dataLen + 6) return 0;
    // Build a standard frame manually using BufferWriter
    std::vector<uint8_t> tmp(512);
    BufferWriter<ProfileStandardConfig> writer(tmp.data(), tmp.size());
    // We don't have a typed message here — copy raw via encode_with_crc
    // For send tests, just mirror the raw bytes into output.
    if (dataLen + 6 > outputMaxLen) return 0;
    output[0] = ProfileStandardConfig::computed_start_byte1();
    output[1] = ProfileStandardConfig::computed_start_byte2();
    output[2] = static_cast<uint8_t>(dataLen);
    output[3] = msgId;
    memcpy(output + 4, data, dataLen);
    // CRC omitted for this mock framer – sufficient for dispatch tests
    output[4 + dataLen] = 0x00;
    output[5 + dataLen] = 0x00;
    return dataLen + 6;
  }
};

// ============================================================================
// Test helpers
// ============================================================================

static int tests_run = 0;
static int tests_passed = 0;
static int tests_failed = 0;

static void run_test(const char* name, bool (*func)()) {
  tests_run++;
  bool passed = func();
  printf("%-65s %s\n", name, passed ? "PASS" : "FAIL");
  if (passed) tests_passed++;
  else tests_failed++;
}

// ============================================================================
// Tests
// ============================================================================

/**
 * Test: subscribe + NotifyObservers dispatches to a registered lambda callback
 */
bool test_subscribe_dispatch_lambda() {
  MockTransport transport;
  MockFrameParser parser;

  StructFrameSdkConfig config;
  config.transport = &transport;
  config.parser = &parser;

  StructFrameSdk sdk(config);

  int call_count = 0;
  BasicTypesMessage received{};

  auto sub = sdk.subscribe<BasicTypesMessage>(
      BasicTypesMessage::MSG_ID,
      [&](const BasicTypesMessage& msg, uint8_t) {
        call_count++;
        received = msg;
      });

  // Build a test message and dispatch manually
  BasicTypesMessage sent{};
  sent.regular_int = 42;
  sent.flag = true;

  sdk.NotifyObservers<BasicTypesMessage>(BasicTypesMessage::MSG_ID, sent);

  if (call_count != 1) return false;
  if (received.regular_int != 42) return false;
  if (!received.flag) return false;

  return true;
}

/**
 * Test: multiple observers for the same message ID all receive the notification
 */
bool test_subscribe_multiple_observers() {
  MockTransport transport;
  MockFrameParser parser;

  StructFrameSdkConfig config;
  config.transport = &transport;
  config.parser = &parser;

  StructFrameSdk sdk(config);

  int count_a = 0, count_b = 0;

  auto sub_a = sdk.subscribe<BasicTypesMessage>(
      BasicTypesMessage::MSG_ID,
      [&](const BasicTypesMessage&, uint8_t) { count_a++; });

  auto sub_b = sdk.subscribe<BasicTypesMessage>(
      BasicTypesMessage::MSG_ID,
      [&](const BasicTypesMessage&, uint8_t) { count_b++; });

  BasicTypesMessage msg{};
  sdk.NotifyObservers<BasicTypesMessage>(BasicTypesMessage::MSG_ID, msg);

  return count_a == 1 && count_b == 1;
}

/**
 * Test: RAII Subscription auto-unsubscribes on destruction
 */
bool test_subscription_raii_unsubscribe() {
  MockTransport transport;
  MockFrameParser parser;

  StructFrameSdkConfig config;
  config.transport = &transport;
  config.parser = &parser;

  StructFrameSdk sdk(config);

  int count = 0;

  {
    // Subscription is scoped — it unsubscribes when it goes out of scope
    auto sub = sdk.subscribe<BasicTypesMessage>(
        BasicTypesMessage::MSG_ID,
        [&](const BasicTypesMessage&, uint8_t) { count++; });

    BasicTypesMessage msg{};
    sdk.NotifyObservers<BasicTypesMessage>(BasicTypesMessage::MSG_ID, msg);
    if (count != 1) return false;  // handler should fire once while active
  }
  // sub destroyed → auto-unsubscribed

  BasicTypesMessage msg{};
  sdk.NotifyObservers<BasicTypesMessage>(BasicTypesMessage::MSG_ID, msg);
  // count should still be 1 (second notify has no subscriber)
  return count == 1;
}

/**
 * Test: NotifyObservers for an unregistered message ID is a no-op (no crash)
 */
bool test_notify_unregistered_id_is_noop() {
  MockTransport transport;
  MockFrameParser parser;

  StructFrameSdkConfig config;
  config.transport = &transport;
  config.parser = &parser;

  StructFrameSdk sdk(config);

  BasicTypesMessage msg{};
  // MSG_ID 0xFF is not subscribed — should not crash
  sdk.NotifyObservers<BasicTypesMessage>(0xFF, msg);
  return true;
}

/**
 * Test: Transport Connect() is called through sdk.Connect()
 */
bool test_sdk_connect_delegates_to_transport() {
  MockTransport transport;
  MockFrameParser parser;

  StructFrameSdkConfig config;
  config.transport = &transport;
  config.parser = &parser;

  StructFrameSdk sdk(config);
  sdk.Connect();

  return transport.connect_calls == 1 && sdk.IsConnected();
}

/**
 * Test: Incoming data from transport triggers frame_parser->parse()
 */
bool test_incoming_data_triggers_parse() {
  MockTransport transport;
  MockFrameParser parser;

  StructFrameSdkConfig config;
  config.transport = &transport;
  config.parser = &parser;

  StructFrameSdk sdk(config);

  // Inject some bytes (even if not a valid frame)
  uint8_t dummy[8] = {0x90, 0x71, 0x02, 0x01, 0xAA, 0xBB, 0x00, 0x00};
  transport.inject_data(dummy, sizeof(dummy));

  // The parser's parse() should have been called at least once
  return parser.parse_calls > 0;
}

/**
 * Test: Full end-to-end — encode a frame, inject via transport, ParseBuffer
 *       calls parse(), and the parsed result is available for NotifyObservers.
 *
 * Since StructFrameSdk::ParseBuffer() does not auto-dispatch (by design —
 * typed dispatch requires explicit NotifyObservers), this test verifies that
 * the pipeline up to ParseBuffer works correctly.
 */
bool test_end_to_end_parse_pipeline() {
  MockTransport transport;
  MockFrameParser parser;

  StructFrameSdkConfig config;
  config.transport = &transport;
  config.parser = &parser;

  StructFrameSdk sdk(config);

  // Encode a real frame
  BasicTypesMessage msg{};
  msg.regular_int = 777;
  msg.flag = false;

  uint8_t encoded[512];
  size_t frame_len =
      FrameEncoderWithCrc<ProfileStandardConfig>::encode(encoded, sizeof(encoded), msg);

  if (frame_len == 0) return false;

  int parse_calls_before = parser.parse_calls;

  // Inject the complete frame
  transport.inject_data(encoded, frame_len);

  // parse() must have been invoked at least once
  return parser.parse_calls > parse_calls_before;
}

// ============================================================================
// Main
// ============================================================================

int main() {
  printf("\n========================================\n");
  printf("SDK SUBSCRIBE/DISPATCH TESTS - C++\n");
  printf("========================================\n\n");
  printf("%-65s %s\n", "Test Name", "Result");
  printf("%-65s %s\n",
    "=================================================================", "======");

  run_test("subscribe + NotifyObservers dispatches to lambda",
           test_subscribe_dispatch_lambda);
  run_test("multiple observers all receive notification",
           test_subscribe_multiple_observers);
  run_test("RAII Subscription auto-unsubscribes on destruction",
           test_subscription_raii_unsubscribe);
  run_test("NotifyObservers for unregistered ID is no-op",
           test_notify_unregistered_id_is_noop);
  run_test("Connect() delegates to transport",
           test_sdk_connect_delegates_to_transport);
  run_test("Incoming transport data triggers parse()",
           test_incoming_data_triggers_parse);
  run_test("Full encode -> inject -> ParseBuffer pipeline",
           test_end_to_end_parse_pipeline);

  printf("\n========================================\n");
  printf("Summary: %d/%d tests passed\n", tests_passed, tests_run);
  printf("========================================\n\n");

  return tests_failed > 0 ? 1 : 0;
}
