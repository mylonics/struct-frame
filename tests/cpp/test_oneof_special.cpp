/**
 * Test for oneof special cases: discriminator=none and multi-oneof messages.
 *
 * Mirrors tests/rust/src/main.rs::run_oneof_special_tests().
 */

#include <cstdio>
#include <cstring>

#include "serialization_test.structframe.hpp"

using namespace structframe::serialization_test;

static int g_passed = 0;
static int g_failed = 0;

static void expect(bool condition, const char* name) {
  if (condition) {
    printf("  PASS  %s\n", name);
    g_passed++;
  } else {
    printf("  FAIL  %s\n", name);
    g_failed++;
  }
}

int main() {
  printf("=== C++ oneof special tests ===\n");

  // --- NoneDiscriminatorMessage: no discriminator field, data bytes preserved ---
  NoneDiscriminatorMessage msg1{};
  msg1.header = 0xAB;
  BasicTypesMessage basic{};
  basic.small_int = -42;
  basic.medium_uint = 5000;
  msg1.data.basic = basic;

  uint8_t buf1[NoneDiscriminatorMessage::MAX_SIZE];
  msg1.serialize(buf1);
  NoneDiscriminatorMessage dec1;
  size_t n1 = dec1.deserialize(buf1, sizeof(buf1));
  expect(n1 > 0, "NoneDiscriminator: deserialize succeeds");
  expect(dec1.header == 0xAB, "NoneDiscriminator: header round-trips");
  // Without a discriminator the receiver must know which variant to use.
  expect(dec1.data.basic.small_int == -42, "NoneDiscriminator: basic.small_int round-trips");
  expect(dec1.data.basic.medium_uint == 5000, "NoneDiscriminator: basic.medium_uint round-trips");

  // --- MultiOneofMessage: two independent oneofs ---
  MultiOneofMessage msg2{};
  msg2.selector = 7;
  // first_payload: BasicTypesMessage variant (msgid discriminator)
  BasicTypesMessage basic2{};
  basic2.small_int = 99;
  msg2.first_payload_discriminator = BasicTypesMessage::MSG_ID;
  msg2.first_payload.basic = basic2;
  // second_payload: discriminator=none, use Message variant
  Message msg_payload{};
  msg_payload.severity = MsgSeverity::SevWarn;
  msg2.second_payload.msg_payload = msg_payload;

  uint8_t buf2[MultiOneofMessage::MAX_SIZE];
  msg2.serialize(buf2);
  MultiOneofMessage dec2;
  size_t n2 = dec2.deserialize(buf2, sizeof(buf2));
  expect(n2 > 0, "MultiOneof: deserialize succeeds");
  expect(dec2.selector == 7, "MultiOneof: selector round-trips");
  expect(dec2.first_payload_discriminator == BasicTypesMessage::MSG_ID,
         "MultiOneof: first_payload discriminator is BasicTypesMessage MSG_ID");
  expect(dec2.first_payload.basic.small_int == 99, "MultiOneof: basic.small_int round-trips");
  // second_payload: no discriminator -- caller must know which variant is active
  expect(dec2.second_payload.msg_payload.severity == MsgSeverity::SevWarn,
         "MultiOneof: msg_payload.severity round-trips");

  printf("\nSummary: %d passed, %d failed\n", g_passed, g_failed);
  return g_failed > 0 ? 1 : 0;
}
