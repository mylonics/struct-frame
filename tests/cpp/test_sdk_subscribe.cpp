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
    // frame() is only called by SendRaw(). SendRaw is not exercised by any
    // test in this file, so this mock returns 0 (unsupported).
    (void)msgId; (void)data; (void)dataLen; (void)output; (void)outputMaxLen;
    return 0;
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

template <typename MessageT>
static bool inject_encoded_message(MockTransport& transport, const MessageT& msg) {
  uint8_t encoded[512];
  size_t frame_len =
      FrameEncoderWithCrc<ProfileStandardConfig>::encode(encoded, sizeof(encoded), msg);
  if (frame_len == 0) return false;
  transport.inject_data(encoded, frame_len);
  return true;
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

  // Build a test message and inject a real frame through the transport.
  BasicTypesMessage sent{};
  sent.regular_int = 42;
  sent.flag = true;

  if (!inject_encoded_message(transport, sent)) return false;

  if (call_count != 1) return false;
  if (received.regular_int != 42) return false;
  if (!received.flag) return false;
  if (parser.parse_calls == 0) return false;

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
  msg.regular_int = 99;
  if (!inject_encoded_message(transport, msg)) return false;

  return count_a == 1 && count_b == 1 && parser.parse_calls > 0;
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
    msg.regular_int = 123;
    if (!inject_encoded_message(transport, msg)) return false;
    if (count != 1) return false;  // handler should fire once while active
  }
  // sub destroyed → auto-unsubscribed

  BasicTypesMessage msg{};
  msg.regular_int = 456;
  if (!inject_encoded_message(transport, msg)) return false;
  // count should still be 1 (second notify has no subscriber)
  return count == 1 && parser.parse_calls >= 2;
}

/**
 * Test: NotifyObservers for an unregistered message ID is a no-op (no crash)
 *       and does not invoke any registered handlers.
 */
bool test_notify_unregistered_id_is_noop() {
  MockTransport transport;
  MockFrameParser parser;

  StructFrameSdkConfig config;
  config.transport = &transport;
  config.parser = &parser;

  StructFrameSdk sdk(config);

  // Register a handler for a known ID to verify it's NOT called for unregistered IDs
  int call_count = 0;
  auto sub = sdk.subscribe<BasicTypesMessage>(
      BasicTypesMessage::MSG_ID,
      [&](const BasicTypesMessage&, uint8_t) { call_count++; });

  // Inject a valid frame for a different message type that has no subscriber.
  SerializationTestMessage other_msg{};
  other_msg.magic_number = 0x12345678;
  other_msg.test_float = 1.5f;
  other_msg.test_bool = true;
  if (!inject_encoded_message(transport, other_msg)) return false;
  if (call_count != 0) return false;  // handler must not fire for unregistered ID

  // Verify the handler DOES fire for the registered ID
  BasicTypesMessage msg{};
  sdk.NotifyObservers<BasicTypesMessage>(BasicTypesMessage::MSG_ID, msg);
  if (call_count != 1) return false;  // handler must fire once for registered ID

  return parser.parse_calls > 0;
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
 * Test: Incoming data from transport triggers frame_parser->parse() and
 *       auto-dispatches to a registered subscriber.
 */
bool test_incoming_data_triggers_parse() {
  MockTransport transport;
  MockFrameParser parser;

  StructFrameSdkConfig config;
  config.transport = &transport;
  config.parser = &parser;

  StructFrameSdk sdk(config);

  int dispatch_count = 0;
  auto sub = sdk.subscribe<BasicTypesMessage>(
      BasicTypesMessage::MSG_ID,
      [&](const BasicTypesMessage&, uint8_t) { dispatch_count++; });

  // Encode a real frame and inject it so parse() is called
  BasicTypesMessage msg{};
  msg.regular_int = 55;
  uint8_t encoded[512];
  size_t frame_len =
      FrameEncoderWithCrc<ProfileStandardConfig>::encode(encoded, sizeof(encoded), msg);
  if (frame_len == 0) return false;

  transport.inject_data(encoded, frame_len);

  // parse() was called and auto-dispatch fired
  return parser.parse_calls > 0 && dispatch_count == 1;
}

/**
 * Test: Full end-to-end — encode a frame, inject via transport, SDK
 *       auto-dispatches to the registered subscriber with the correct data.
 */
bool test_end_to_end_parse_pipeline() {
  MockTransport transport;
  MockFrameParser parser;

  StructFrameSdkConfig config;
  config.transport = &transport;
  config.parser = &parser;

  StructFrameSdk sdk(config);

  int dispatch_count = 0;
  BasicTypesMessage dispatched{};
  auto sub = sdk.subscribe<BasicTypesMessage>(
      BasicTypesMessage::MSG_ID,
      [&](const BasicTypesMessage& m, uint8_t) {
          dispatch_count++;
          dispatched = m;
      });

  // Encode a real frame
  BasicTypesMessage msg{};
  msg.regular_int = 777;
  msg.flag = false;

  uint8_t encoded[512];
  size_t frame_len =
      FrameEncoderWithCrc<ProfileStandardConfig>::encode(encoded, sizeof(encoded), msg);
  if (frame_len == 0) return false;

  // Inject the complete frame via the transport
  transport.inject_data(encoded, frame_len);

  // Subscriber must have been called with the correct decoded values
  if (dispatch_count != 1) return false;
  if (dispatched.regular_int != 777) return false;
  if (dispatched.flag != false) return false;

  return true;
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
  run_test("Incoming transport data triggers parse() + dispatch",
           test_incoming_data_triggers_parse);
  run_test("Full encode -> inject -> subscriber receives message",
           test_end_to_end_parse_pipeline);

  printf("\n========================================\n");
  printf("Summary: %d/%d tests passed\n", tests_passed, tests_run);
  printf("========================================\n\n");

  return tests_failed > 0 ? 1 : 0;
}
