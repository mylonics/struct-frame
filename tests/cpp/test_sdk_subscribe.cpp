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
// SDK type alias for ProfileStandard
// ============================================================================

using TestSdk = StructFrameSdkT<ProfileStandardConfig>;
using TestBulkSdk = StructFrameSdkT<ProfileBulkConfig>;

struct ExtendedDummyMessage {
  static constexpr uint16_t MSG_ID = 300;
  static constexpr size_t MAX_SIZE = 1;
  static constexpr uint8_t MAGIC_1 = 0;
  static constexpr uint8_t MAGIC_2 = 0;

  uint8_t value = 0;

  void deserialize(const uint8_t* data, size_t len) {
    value = (data != nullptr && len > 0) ? data[0] : 0;
  }
};

static MessageInfo get_extended_dummy_message_info(uint16_t msg_id) {
  if (msg_id == ExtendedDummyMessage::MSG_ID) {
    return MessageInfo(ExtendedDummyMessage::MAX_SIZE,
                       ExtendedDummyMessage::MAGIC_1,
                       ExtendedDummyMessage::MAGIC_2);
  }
  return MessageInfo();
}

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

/**
 * LoopbackTransport - anything sent is immediately fed back as incoming data.
 * Useful for verifying end-to-end forwarding into another SDK instance.
 */
class LoopbackTransport : public BaseTransport {
 public:
  std::vector<std::vector<uint8_t>> sent_data;

  void Connect() override { connected_ = true; }
  void Disconnect() override { connected_ = false; }
  void Send(const uint8_t* data, size_t length) override {
    sent_data.push_back(std::vector<uint8_t>(data, data + length));
    HandleData(data, length);
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
 * Test: subscribe + incoming frame dispatches to a registered lambda callback
 */
bool test_subscribe_dispatch_lambda() {
  MockTransport transport;
  TestSdk sdk(&transport, &get_message_info);

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

  return true;
}

/**
 * Test: multiple observers for the same message ID all receive the notification
 */
bool test_subscribe_multiple_observers() {
  MockTransport transport;
  TestSdk sdk(&transport, &get_message_info);

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

  return count_a == 1 && count_b == 1;
}

/**
 * Test: RAII Subscription auto-unsubscribes on destruction
 */
bool test_subscription_raii_unsubscribe() {
  MockTransport transport;
  TestSdk sdk(&transport, &get_message_info);

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
  return count == 1;
}

/**
 * Test: NotifyObservers for an unregistered message ID is a no-op (no crash)
 *       and does not invoke any registered handlers.
 */
bool test_notify_unregistered_id_is_noop() {
  MockTransport transport;
  TestSdk sdk(&transport, &get_message_info);

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

  return true;
}

/**
 * Test: Transport Connect() is called through sdk.Connect()
 */
bool test_sdk_connect_delegates_to_transport() {
  MockTransport transport;
  TestSdk sdk(&transport, &get_message_info);
  sdk.Connect();

  return transport.connect_calls == 1 && sdk.IsConnected();
}

/**
 * Test: Incoming data from transport triggers parse and
 *       auto-dispatches to a registered subscriber.
 */
bool test_incoming_data_triggers_parse() {
  MockTransport transport;
  TestSdk sdk(&transport, &get_message_info);

  int dispatch_count = 0;
  auto sub = sdk.subscribe<BasicTypesMessage>(
      BasicTypesMessage::MSG_ID,
      [&](const BasicTypesMessage&, uint8_t) { dispatch_count++; });

  // Encode a real frame and inject it
  BasicTypesMessage msg{};
  msg.regular_int = 55;
  uint8_t encoded[512];
  size_t frame_len =
      FrameEncoderWithCrc<ProfileStandardConfig>::encode(encoded, sizeof(encoded), msg);
  if (frame_len == 0) return false;

  transport.inject_data(encoded, frame_len);

  // auto-dispatch fired
  return dispatch_count == 1;
}

/**
 * Test: Full end-to-end — encode a frame, inject via transport, SDK
 *       auto-dispatches to the registered subscriber with the correct data.
 */
bool test_end_to_end_parse_pipeline() {
  MockTransport transport;
  TestSdk sdk(&transport, &get_message_info);

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

/**
 * Test: subscribeFrameInfo receives each valid parsed frame.
 */
bool test_subscribe_frame_info_receives_valid_frames() {
  MockTransport transport;
  TestSdk sdk(&transport, &get_message_info);

  int frame_count = 0;
  uint16_t last_msg_id = 0;
  size_t last_msg_len = 0;

  auto sub = sdk.subscribeFrameInfo(
      [&](const FrameMsgInfo& frame) {
        frame_count++;
        last_msg_id = frame.msg_id;
        last_msg_len = frame.msg_len;
      });

  BasicTypesMessage msg{};
  msg.regular_int = 314;
  if (!inject_encoded_message(transport, msg)) return false;

  return frame_count == 1 &&
         last_msg_id == BasicTypesMessage::MSG_ID &&
         last_msg_len == BasicTypesMessage::MAX_SIZE;
}

/**
 * Test: forwarding FrameMsgInfo between two SDK instances via Send(frame_info).
 */
bool test_forward_frame_info_between_two_sdks() {
  MockTransport source_transport;
  LoopbackTransport target_transport;

  TestSdk source_sdk(&source_transport, &get_message_info);
  TestSdk target_sdk(&target_transport, &get_message_info);

  int target_dispatch_count = 0;
  int forwarded_from_source = 0;
  BasicTypesMessage target_received{};

  auto target_sub = target_sdk.subscribe<BasicTypesMessage>(
      BasicTypesMessage::MSG_ID,
      [&](const BasicTypesMessage& msg, uint8_t) {
        target_dispatch_count++;
        target_received = msg;
      });

  auto forward_sub = source_sdk.subscribeFrameInfo(
      [&](const FrameMsgInfo& frame) {
        if (target_sdk.Send(frame)) {
          forwarded_from_source++;
        }
      });

  BasicTypesMessage msg{};
  msg.regular_int = 909;
  msg.flag = true;
  if (!inject_encoded_message(source_transport, msg)) return false;

  if (forwarded_from_source != 1) return false;
  if (target_dispatch_count != 1) return false;
  if (target_received.regular_int != 909) return false;
  if (!target_received.flag) return false;

  return true;
}

/**
 * Test: extended message IDs (>255) are preserved through SendRaw + dispatch.
 */
bool test_extended_msg_id_sendraw_roundtrip() {
  LoopbackTransport transport;
  TestBulkSdk sdk(&transport, &get_extended_dummy_message_info);

  int dispatch_count = 0;
  uint16_t observed_msg_id = 0;
  uint8_t observed_value = 0;

  auto sub = sdk.subscribe<ExtendedDummyMessage>(
      ExtendedDummyMessage::MSG_ID,
      [&](const ExtendedDummyMessage& msg, uint16_t msg_id) {
        dispatch_count++;
        observed_msg_id = msg_id;
        observed_value = msg.value;
      });

  uint8_t payload[ExtendedDummyMessage::MAX_SIZE] = {0xAB};
  if (!sdk.SendRaw(ExtendedDummyMessage::MSG_ID, payload, sizeof(payload))) return false;

  return dispatch_count == 1 &&
         observed_msg_id == ExtendedDummyMessage::MSG_ID &&
         observed_value == payload[0];
}

/**
 * Test: forwarding FrameMsgInfo preserves extended message IDs (>255).
 */
bool test_forward_extended_msg_id_between_two_sdks() {
  LoopbackTransport source_transport;
  LoopbackTransport target_transport;
  TestBulkSdk source_sdk(&source_transport, &get_extended_dummy_message_info);
  TestBulkSdk target_sdk(&target_transport, &get_extended_dummy_message_info);

  int target_dispatch_count = 0;
  int forwarded_from_source = 0;
  uint16_t observed_msg_id = 0;
  uint8_t observed_value = 0;

  auto target_sub = target_sdk.subscribe<ExtendedDummyMessage>(
      ExtendedDummyMessage::MSG_ID,
      [&](const ExtendedDummyMessage& msg, uint16_t msg_id) {
        target_dispatch_count++;
        observed_msg_id = msg_id;
        observed_value = msg.value;
      });

  auto forward_sub = source_sdk.subscribeFrameInfo(
      [&](const FrameMsgInfo& frame) {
        if (target_sdk.Send(frame)) {
          forwarded_from_source++;
        }
      });

  uint8_t payload[ExtendedDummyMessage::MAX_SIZE] = {0x6C};
  if (!source_sdk.SendRaw(ExtendedDummyMessage::MSG_ID, payload, sizeof(payload))) return false;

  return forwarded_from_source == 1 &&
         target_dispatch_count == 1 &&
         observed_msg_id == ExtendedDummyMessage::MSG_ID &&
         observed_value == payload[0];
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

  run_test("subscribe + incoming frame dispatches to lambda",
           test_subscribe_dispatch_lambda);
  run_test("multiple observers all receive notification",
           test_subscribe_multiple_observers);
  run_test("RAII Subscription auto-unsubscribes on destruction",
           test_subscription_raii_unsubscribe);
  run_test("NotifyObservers for unregistered ID is no-op",
           test_notify_unregistered_id_is_noop);
  run_test("Connect() delegates to transport",
           test_sdk_connect_delegates_to_transport);
  run_test("Incoming transport data triggers parse + dispatch",
           test_incoming_data_triggers_parse);
  run_test("Full encode -> inject -> subscriber receives message",
           test_end_to_end_parse_pipeline);
  run_test("subscribeFrameInfo receives valid parsed frames",
           test_subscribe_frame_info_receives_valid_frames);
  run_test("FrameMsgInfo forwarding works across two SDK instances",
           test_forward_frame_info_between_two_sdks);
  run_test("SendRaw preserves extended msg_id (>255) during dispatch",
           test_extended_msg_id_sendraw_roundtrip);
  run_test("FrameMsgInfo forwarding preserves extended msg_id (>255)",
           test_forward_extended_msg_id_between_two_sdks);

  printf("\n========================================\n");
  printf("Summary: %d/%d tests passed\n", tests_passed, tests_run);
  printf("========================================\n\n");

  return tests_failed > 0 ? 1 : 0;
}
