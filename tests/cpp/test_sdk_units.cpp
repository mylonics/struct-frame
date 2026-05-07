/**
 * Unit tests for low-level C++ SDK encoder/parser classes (sections 6.1 and 6.2)
 *
 * Tests:
 * - FrameEncoderWithCrc<Config>::encode()    (section 6.1)
 * - FrameEncoderMinimal<Config>::encode()    (section 6.1)
 * - BufferParserWithCrc<Config>::parse()     (section 6.2)
 * - BufferParserMinimal<Config>::parse()     (section 6.2)
 */

#include <cstdio>
#include <cstring>
#include <vector>

#include "include/standard_messages.hpp"
#include "../../generated/cpp/frame_profiles.hpp"

using namespace structframe;
using namespace structframe::serialization_test;

// Test result tracking
static int tests_run = 0;
static int tests_passed = 0;
static int tests_failed = 0;

// ============================================================================
// FrameEncoderWithCrc tests (section 6.1)
// ============================================================================

/**
 * Test: FrameEncoderWithCrc encodes a valid frame that round-trips through
 *       BufferParserWithCrc (section 6.1 + 6.2 combined round-trip)
 */
bool test_encoder_with_crc_roundtrip() {
  BasicTypesMessage msg = StandardMessages::create_basic_types(
      -10, 300, 70000, 99999LL,
      200u, 50000u, 200000u, 999999ULL,
      1.5f, 2.7182818, true, "dev-01", "encoder-unit-test");

  uint8_t buffer[512];
  size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(
      buffer, sizeof(buffer), msg);

  if (encoded == 0) return false;

  // Verify the frame starts with the expected start bytes
  if (buffer[0] != ProfileStandardConfig::computed_start_byte1()) return false;
  if (buffer[1] != ProfileStandardConfig::computed_start_byte2()) return false;

  // The encoded length must equal header + payload + footer
  size_t expected_size = ProfileStandardConfig::overhead + BasicTypesMessage::MAX_SIZE;
  if (encoded != expected_size) return false;

  return true;
}

/**
 * Test: FrameEncoderWithCrc produces a frame that BufferParserWithCrc accepts
 */
bool test_encoder_with_crc_parser_accepts() {
  BasicTypesMessage msg = StandardMessages::create_basic_types(
      42, 1000, 123456, 9876543210LL,
      255u, 60000u, 3000000u, 12345678901ULL,
      3.14f, 2.71828, false, "unit-test", "parser round-trip");

  uint8_t buffer[512];
  size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(
      buffer, sizeof(buffer), msg);

  if (encoded == 0) return false;

  // Parse the encoded frame
  auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
      buffer, encoded, get_message_info);

  if (!result.valid) return false;
  if (result.msg_id != BasicTypesMessage::MSG_ID) return false;
  if (result.msg_len != BasicTypesMessage::MAX_SIZE) return false;
  if (result.msg_data == nullptr) return false;

  // Deserialize and verify a key field
  BasicTypesMessage decoded{};
  decoded.deserialize(result.msg_data, result.msg_len);
  if (decoded.large_int != 9876543210LL) return false;

  return true;
}

/**
 * Test: FrameEncoderWithCrc with Bulk profile (has pkg_id)
 */
bool test_encoder_with_crc_bulk_profile() {
  BasicTypesMessage msg = StandardMessages::create_basic_types(
      1, 2, 3, 4LL,
      5u, 6u, 7u, 8ULL,
      9.0f, 10.0, true, "bulk", "bulk-test");

  uint8_t buffer[512];
  size_t encoded = FrameEncoderWithCrc<ProfileBulkConfig>::encode(
      buffer, sizeof(buffer), msg);

  if (encoded == 0) return false;

  // Bulk profile overhead is larger (2 start + 2 len + 1 pkg + 1 msg + 2 crc = 9)
  size_t expected_size = ProfileBulkConfig::overhead + BasicTypesMessage::MAX_SIZE;
  if (encoded != expected_size) return false;

  // Parse it back
  auto result = BufferParserWithCrc<ProfileBulkConfig>::parse(
      buffer, encoded, get_message_info);

  if (!result.valid) return false;
  if ((result.msg_id & 0xFF) != (BasicTypesMessage::MSG_ID & 0xFF)) return false;

  return true;
}

/**
 * Test: FrameEncoderWithCrc returns 0 when buffer is too small
 */
bool test_encoder_with_crc_buffer_too_small() {
  BasicTypesMessage msg{};
  uint8_t tiny_buffer[4];  // Way too small

  size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(
      tiny_buffer, sizeof(tiny_buffer), msg);

  // Should return 0 indicating failure
  return encoded == 0;
}

// ============================================================================
// FrameEncoderMinimal tests (section 6.1)
// ============================================================================

/**
 * Test: FrameEncoderMinimal encodes a fixed-size frame (no CRC, no length)
 */
bool test_encoder_minimal_roundtrip() {
  BasicTypesMessage msg = StandardMessages::create_basic_types(
      -5, 200, 55000, 8888LL,
      100u, 40000u, 100000u, 777777ULL,
      0.5f, 1.41421, true, "sensor", "minimal-test");

  uint8_t buffer[512];
  size_t encoded = FrameEncoderMinimal<ProfileSensorConfig>::encode(
      buffer, sizeof(buffer), msg);

  if (encoded == 0) return false;

  // Sensor profile overhead: 1 start byte + 1 msg_id = 2 bytes header, 0 footer
  size_t expected_size = ProfileSensorConfig::overhead + BasicTypesMessage::MAX_SIZE;
  if (encoded != expected_size) return false;

  return true;
}

/**
 * Test: FrameEncoderMinimal produces a frame that BufferParserMinimal accepts
 */
bool test_encoder_minimal_parser_accepts() {
  SerializationTestMessage msg{};
  msg.magic_number = 0xDEADBEEF;
  msg.test_float = 1.618f;
  msg.test_bool = true;
  msg.test_string.length = 4;
  std::strcpy(msg.test_string.data, "test");
  msg.test_array.count = 2;
  msg.test_array.data[0] = 11;
  msg.test_array.data[1] = 22;

  uint8_t buffer[512];
  size_t encoded = FrameEncoderMinimal<ProfileSensorConfig>::encode(
      buffer, sizeof(buffer), msg);

  if (encoded == 0) return false;

  // Parse the minimal frame using BufferParserMinimal
  auto result = BufferParserMinimal<ProfileSensorConfig>::parse(
      buffer, encoded, get_message_info);

  if (!result.valid) return false;
  if (result.msg_id != SerializationTestMessage::MSG_ID) return false;
  if (result.msg_len != SerializationTestMessage::MAX_SIZE) return false;

  return true;
}

/**
 * Test: FrameEncoderMinimal with IPC profile (no start bytes)
 */
bool test_encoder_minimal_ipc_profile() {
  BasicTypesMessage msg{};
  msg.small_int = 99;

  uint8_t buffer[512];
  size_t encoded = FrameEncoderMinimal<ProfileIPCConfig>::encode(
      buffer, sizeof(buffer), msg);

  if (encoded == 0) return false;

  // IPC profile: no start bytes, just msg_id + payload
  size_t expected_size = ProfileIPCConfig::overhead + BasicTypesMessage::MAX_SIZE;
  if (encoded != expected_size) return false;

  return true;
}

/**
 * Test: FrameEncoderMinimal returns 0 when buffer is too small
 */
bool test_encoder_minimal_buffer_too_small() {
  BasicTypesMessage msg{};
  uint8_t tiny_buffer[2];  // Way too small

  size_t encoded = FrameEncoderMinimal<ProfileSensorConfig>::encode(
      tiny_buffer, sizeof(tiny_buffer), msg);

  return encoded == 0;
}

// ============================================================================
// BufferParserWithCrc tests (section 6.2)
// ============================================================================

/**
 * Test: BufferParserWithCrc rejects corrupted CRC
 */
bool test_parser_with_crc_rejects_corrupt_crc() {
  BasicTypesMessage msg{};
  msg.regular_int = 42;

  uint8_t buffer[512];
  size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(
      buffer, sizeof(buffer), msg);

  if (encoded < 4) return false;

  // Corrupt the CRC (last 2 bytes)
  buffer[encoded - 1] ^= 0xFF;
  buffer[encoded - 2] ^= 0xFF;

  auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
      buffer, encoded, get_message_info);

  return !result.valid;  // Should be rejected
}

/**
 * Test: BufferParserWithCrc rejects a truncated frame
 */
bool test_parser_with_crc_rejects_truncated() {
  BasicTypesMessage msg{};

  uint8_t buffer[512];
  size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(
      buffer, sizeof(buffer), msg);

  if (encoded < 10) return false;

  // Try parsing with only half the data
  auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
      buffer, encoded / 2, get_message_info);

  return !result.valid;  // Should be rejected
}

/**
 * Test: BufferParserWithCrc rejects a buffer that is too short for the header
 */
bool test_parser_with_crc_rejects_too_short() {
  uint8_t tiny[1] = {0x90};  // Just the first start byte

  auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
      tiny, sizeof(tiny), get_message_info);

  return !result.valid;
}

/**
 * Test: BufferParserWithCrc rejects wrong start bytes
 */
bool test_parser_with_crc_rejects_wrong_start_bytes() {
  BasicTypesMessage msg{};

  uint8_t buffer[512];
  size_t encoded = FrameEncoderWithCrc<ProfileStandardConfig>::encode(
      buffer, sizeof(buffer), msg);

  // Corrupt the first start byte
  buffer[0] ^= 0xFF;

  auto result = BufferParserWithCrc<ProfileStandardConfig>::parse(
      buffer, encoded, get_message_info);

  return !result.valid;
}

// ============================================================================
// BufferParserMinimal tests (section 6.2)
// ============================================================================

/**
 * Test: BufferParserMinimal accepts a valid minimal frame
 */
bool test_parser_minimal_accepts_valid() {
  BasicTypesMessage msg{};
  msg.medium_int = 12345;

  uint8_t buffer[512];
  size_t encoded = FrameEncoderMinimal<ProfileSensorConfig>::encode(
      buffer, sizeof(buffer), msg);

  if (encoded == 0) return false;

  auto result = BufferParserMinimal<ProfileSensorConfig>::parse(
      buffer, encoded, get_message_info);

  if (!result.valid) return false;
  if (result.msg_id != BasicTypesMessage::MSG_ID) return false;
  if (result.msg_len != BasicTypesMessage::MAX_SIZE) return false;

  return true;
}

/**
 * Test: BufferParserMinimal rejects unknown message ID (get_message_info returns invalid)
 */
bool test_parser_minimal_rejects_unknown_id() {
  // Build a fake minimal frame with an unknown msg_id (0xFF)
  uint8_t fake_frame[256];
  fake_frame[0] = ProfileSensorConfig::computed_start_byte1();
  fake_frame[1] = 0xFF;  // Unknown message ID
  memset(fake_frame + 2, 0, sizeof(fake_frame) - 2);

  auto result = BufferParserMinimal<ProfileSensorConfig>::parse(
      fake_frame, sizeof(fake_frame), get_message_info);

  return !result.valid;  // Should be rejected (unknown ID)
}

/**
 * Test: BufferParserMinimal rejects truncated frame (buffer shorter than header + payload)
 */
bool test_parser_minimal_rejects_truncated() {
  BasicTypesMessage msg{};

  uint8_t buffer[512];
  size_t encoded = FrameEncoderMinimal<ProfileSensorConfig>::encode(
      buffer, sizeof(buffer), msg);

  if (encoded < 10) return false;

  // Provide only the header, not the payload
  auto result = BufferParserMinimal<ProfileSensorConfig>::parse(
      buffer, 2, get_message_info);  // 2 bytes = start + msg_id only

  return !result.valid;
}

// ============================================================================
// Test runner
// ============================================================================

typedef bool (*TestFunc)();

struct TestCase {
  const char* name;
  TestFunc func;
};

static void run_test(const char* name, TestFunc func) {
  tests_run++;
  bool passed = func();
  printf("%-60s %s\n", name, passed ? "PASS" : "FAIL");
  if (passed) tests_passed++;
  else tests_failed++;
}

int main() {
  printf("\n========================================\n");
  printf("SDK UNIT TESTS - C++ Low-Level Classes\n");
  printf("========================================\n\n");
  printf("%-60s %s\n", "Test Name", "Result");
  printf("%-60s %s\n",
    "============================================================", "======");

  // FrameEncoderWithCrc (section 6.1)
  run_test("FrameEncoderWithCrc: round-trip encode size",
           test_encoder_with_crc_roundtrip);
  run_test("FrameEncoderWithCrc: parsed by BufferParserWithCrc",
           test_encoder_with_crc_parser_accepts);
  run_test("FrameEncoderWithCrc: bulk profile (has pkg_id)",
           test_encoder_with_crc_bulk_profile);
  run_test("FrameEncoderWithCrc: returns 0 on buffer overflow",
           test_encoder_with_crc_buffer_too_small);

  // FrameEncoderMinimal (section 6.1)
  run_test("FrameEncoderMinimal: round-trip encode size (sensor)",
           test_encoder_minimal_roundtrip);
  run_test("FrameEncoderMinimal: parsed by BufferParserMinimal",
           test_encoder_minimal_parser_accepts);
  run_test("FrameEncoderMinimal: IPC profile (no start bytes)",
           test_encoder_minimal_ipc_profile);
  run_test("FrameEncoderMinimal: returns 0 on buffer overflow",
           test_encoder_minimal_buffer_too_small);

  // BufferParserWithCrc (section 6.2)
  run_test("BufferParserWithCrc: rejects corrupted CRC",
           test_parser_with_crc_rejects_corrupt_crc);
  run_test("BufferParserWithCrc: rejects truncated frame",
           test_parser_with_crc_rejects_truncated);
  run_test("BufferParserWithCrc: rejects too-short buffer",
           test_parser_with_crc_rejects_too_short);
  run_test("BufferParserWithCrc: rejects wrong start bytes",
           test_parser_with_crc_rejects_wrong_start_bytes);

  // BufferParserMinimal (section 6.2)
  run_test("BufferParserMinimal: accepts valid minimal frame",
           test_parser_minimal_accepts_valid);
  run_test("BufferParserMinimal: rejects unknown message ID",
           test_parser_minimal_rejects_unknown_id);
  run_test("BufferParserMinimal: rejects truncated frame",
           test_parser_minimal_rejects_truncated);

  printf("\n========================================\n");
  printf("Summary: %d/%d tests passed\n", tests_passed, tests_run);
  printf("========================================\n\n");

  return tests_failed > 0 ? 1 : 0;
}
