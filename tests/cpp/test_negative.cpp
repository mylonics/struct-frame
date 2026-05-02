/**
 * Negative tests for struct-frame C++ parser
 * 
 * Tests error handling for:
 * - Corrupted CRC/checksum
 * - Truncated frames
 * - Invalid start bytes
 * - Invalid message IDs
 * - Malformed data
 */

#include <cstdio>
#include <cstring>
#include <vector>

#include "include/standard_messages.hpp"
#include "../../generated/cpp/frame_profiles.hpp"

using namespace FrameParsers;

// Test result tracking
static int tests_run = 0;
static int tests_passed = 0;
static int tests_failed = 0;

/**
 * Test: Parser rejects frame with corrupted CRC
 */
bool test_corrupted_crc() {
  // Encode a valid message
  std::vector<uint8_t> buffer(1024);
  BufferWriter<ProfileStandardConfig> writer(buffer.data(), buffer.size());
  
  auto msg = StandardMessages::get_message(0);
  std::visit([&writer](auto&& m) { writer.write(m); }, msg);
  
  size_t frame_size = writer.size();
  if (frame_size < 4) return false;
  
  // Corrupt the CRC bytes (last 2 bytes)
  buffer[frame_size - 1] ^= 0xFF;
  buffer[frame_size - 2] ^= 0xFF;
  
  // Try to parse - should fail (need to provide get_message_info for CRC validation)
  BufferReader<ProfileStandardConfig, decltype(&get_message_info)> reader(
    buffer.data(), frame_size, get_message_info);
  auto result = reader.next();
  
  return !result.valid;  // Expect parsing to fail
}

/**
 * Test: Parser rejects truncated frame
 */
bool test_truncated_frame() {
  // Encode a valid message
  std::vector<uint8_t> buffer(1024);
  BufferWriter<ProfileStandardConfig> writer(buffer.data(), buffer.size());
  
  auto msg = StandardMessages::get_message(0);
  std::visit([&writer](auto&& m) { writer.write(m); }, msg);
  
  size_t frame_size = writer.size();
  if (frame_size < 10) return false;
  
  // Truncate the frame (cut off last 5 bytes)
  size_t truncated_size = frame_size - 5;
  
  // Try to parse - should fail
  BufferReader<ProfileStandardConfig, decltype(&get_message_info)> reader(
    buffer.data(), truncated_size, get_message_info);
  auto result = reader.next();
  
  return !result.valid;  // Expect parsing to fail
}

/**
 * Test: Parser rejects frame with invalid start byte
 */
bool test_invalid_start_byte() {
  // Encode a valid message
  std::vector<uint8_t> buffer(1024);
  BufferWriter<ProfileStandardConfig> writer(buffer.data(), buffer.size());
  
  auto msg = StandardMessages::get_message(0);
  std::visit([&writer](auto&& m) { writer.write(m); }, msg);
  
  size_t frame_size = writer.size();
  if (frame_size < 2) return false;
  
  // Corrupt the start bytes
  buffer[0] = 0xDE;
  buffer[1] = 0xAD;
  
  // Try to parse - should fail
  BufferReader<ProfileStandardConfig, decltype(&get_message_info)> reader(
    buffer.data(), frame_size, get_message_info);
  auto result = reader.next();
  
  return !result.valid;  // Expect parsing to fail
}

// Alias for consistency with other languages
bool test_invalid_start_bytes() {
  return test_invalid_start_byte();
}

/**
 * Test: Parser handles zero-length buffer
 */
bool test_zero_length_buffer() {
  std::vector<uint8_t> buffer(1024);
  
  BufferReader<ProfileStandardConfig, decltype(&get_message_info)> reader(
    buffer.data(), 0, get_message_info);
  auto result = reader.next();
  
  return !result.valid;  // Expect parsing to fail
}

/**
 * Test: Parser handles corrupted length field
 */
bool test_corrupted_length() {
  // Encode a valid message
  std::vector<uint8_t> buffer(1024);
  BufferWriter<ProfileStandardConfig> writer(buffer.data(), buffer.size());
  
  auto msg = StandardMessages::get_message(0);
  std::visit([&writer](auto&& m) { writer.write(m); }, msg);
  
  size_t frame_size = writer.size();
  if (frame_size < 4) return false;
  
  // Corrupt the length field (byte 2 for ProfileStandard)
  // Set it to a very large value
  buffer[2] = 0xFF;
  
  // Try to parse - should fail due to buffer too small for claimed length
  BufferReader<ProfileStandardConfig, decltype(&get_message_info)> reader(
    buffer.data(), frame_size, get_message_info);
  auto result = reader.next();
  
  return !result.valid;  // Expect parsing to fail
}

/**
 * Test: AccumulatingReader rejects corrupted CRC in streaming mode
 */
bool test_streaming_corrupted_crc() {
  // Encode a valid message
  std::vector<uint8_t> buffer(1024);
  BufferWriter<ProfileStandardConfig> writer(buffer.data(), buffer.size());
  
  auto msg = StandardMessages::get_message(0);
  std::visit([&writer](auto&& m) { writer.write(m); }, msg);
  
  size_t frame_size = writer.size();
  if (frame_size < 4) return false;
  
  // Corrupt the CRC
  buffer[frame_size - 1] ^= 0xFF;
  
  // Try to parse with AccumulatingReader
  AccumulatingReader<ProfileStandardConfig, 1024, decltype(&get_message_info)> reader(get_message_info);
  
  // Feed byte by byte
  for (size_t i = 0; i < frame_size; i++) {
    reader.push_byte(buffer[i]);
  }
  
  auto result = reader.next();
  return !result.valid;  // Expect parsing to fail
}

/**
 * Test: AccumulatingReader handles garbage data
 */
bool test_streaming_garbage_data() {
  AccumulatingReader<ProfileStandardConfig, 1024, decltype(&get_message_info)> reader(get_message_info);
  
  // Feed random garbage bytes
  uint8_t garbage[] = {0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56, 0x78, 0x9A};
  
  for (size_t i = 0; i < sizeof(garbage); i++) {
    reader.push_byte(garbage[i]);
  }
  
  auto result = reader.next();
  return !result.valid;  // Expect no valid frame found
}

/**
 * Test: Multiple corrupted frames in buffer
 */
bool test_multiple_corrupted_frames() {
  // Create buffer with 3 messages
  std::vector<uint8_t> buffer(4096);
  BufferWriter<ProfileStandardConfig> writer(buffer.data(), buffer.size());
  
  for (size_t i = 0; i < 3; i++) {
    auto msg = StandardMessages::get_message(i % StandardMessages::MESSAGE_COUNT);
    std::visit([&writer](auto&& m) { writer.write(m); }, msg);
  }
  
  size_t total_size = writer.size();
  
  // Corrupt the second frame (find its start and corrupt its CRC)
  // First, find where second frame starts
  BufferReader<ProfileStandardConfig, decltype(&get_message_info)> reader(
    buffer.data(), total_size, get_message_info);
  auto first = reader.next();
  size_t second_start = reader.offset();
  
  // Get second frame
  auto second = reader.next();
  if (!second.valid) return false;
  
  // Corrupt second frame's CRC
  size_t second_end = reader.offset();
  buffer[second_end - 1] ^= 0xFF;
  
  // Now parse all frames - should get first one valid, second invalid
  BufferReader<ProfileStandardConfig, decltype(&get_message_info)> reader2(
    buffer.data(), total_size, get_message_info);
  
  auto result1 = reader2.next();
  if (!result1.valid) return false;  // First should be valid
  
  auto result2 = reader2.next();
  return !result2.valid;  // Second should be invalid
}

/**
 * Test: Bulk profile with corrupted CRC
 */
bool test_bulk_profile_corrupted_crc() {
  // Encode a valid message with bulk profile (has CRC)
  std::vector<uint8_t> buffer(1024);
  BufferWriter<ProfileBulkConfig> writer(buffer.data(), buffer.size());
  
  auto msg = StandardMessages::get_message(0);
  std::visit([&writer](auto&& m) { writer.write(m); }, msg);
  
  size_t frame_size = writer.size();
  if (frame_size < 4) return false;
  
  // Corrupt the CRC (last 2 bytes)
  buffer[frame_size - 1] ^= 0xFF;
  buffer[frame_size - 2] ^= 0xFF;
  
  // Try to parse - should fail
  BufferReader<ProfileBulkConfig, decltype(&get_message_info)> reader(
    buffer.data(), frame_size, get_message_info);
  auto result = reader.next();
  
  return !result.valid;  // Expect parsing to fail
}

/**
 * Test: Parser rejects frame with unknown message ID (CRC fails with wrong magic values)
 * ProfileStandard layout: [0x90][0x71][LEN][MSG_ID][PAYLOAD...][CRC1][CRC2]
 */
bool test_invalid_msg_id() {
  std::vector<uint8_t> buffer(1024);
  BufferWriter<ProfileStandardConfig> writer(buffer.data(), buffer.size());

  auto msg = StandardMessages::get_message(0);
  std::visit([&writer](auto&& m) { writer.write(m); }, msg);

  size_t frame_size = writer.size();
  if (frame_size < 5) return false;

  // Corrupt the msg_id byte (byte 3 for ProfileStandard: [start1][start2][len][msg_id]...)
  // 0xFF is not a known message ID so get_message_info returns {0,0,0} magic → CRC fails
  buffer[3] = 0xFF;

  BufferReader<ProfileStandardConfig, decltype(&get_message_info)> reader(
      buffer.data(), frame_size, get_message_info);
  auto result = reader.next();
  return !result.valid;  // Expect parsing to fail (CRC mismatch due to wrong magic values)
}

/**
 * Test: Minimal profile (no CRC) rejects a truncated frame
 * ProfileSensor layout: [0x70][MSG_ID][PAYLOAD...]  (no CRC, no length field)
 * Parser uses get_message_info to determine expected payload size.
 */
bool test_minimal_profile_truncated_frame() {
  uint8_t raw[1024];

  // Encode a valid ProfileSensor frame manually (no CRC, no length)
  auto msg = StandardMessages::get_message(0);
  size_t frame_size = 0;
  std::visit([&raw, &frame_size](auto&& m) {
    // ProfileSensor: [tiny_start] [msg_id] [payload...]
    uint8_t payload[512];
    std::memcpy(payload, m.data(), std::decay_t<decltype(m)>::MAX_SIZE);
    size_t plen = std::decay_t<decltype(m)>::MAX_SIZE;
    raw[0] = 0x70;  // Tiny start byte for MINIMAL payload type
    raw[1] = static_cast<uint8_t>(std::decay_t<decltype(m)>::MSG_ID & 0xFF);
    std::memcpy(raw + 2, payload, plen);
    frame_size = 2 + plen;
  }, msg);

  if (frame_size <= 5) return false;

  // Truncate: provide fewer bytes than the full frame
  size_t truncated = frame_size - 5;

  BufferReader<ProfileSensorConfig, decltype(&get_message_info)> reader(
      raw, truncated, get_message_info);
  auto result = reader.next();
  return !result.valid;  // Expect failure: buffer too small for expected payload
}

/**
 * Test: Network profile validates sys_id/comp_id as part of CRC-protected header
 * ProfileNetwork layout: [0x90][0x78][SEQ][SYS_ID][COMP_ID][LEN_LO][LEN_HI][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * Since sys_id (byte 3) is within the CRC region, corrupting it causes CRC failure.
 */
bool test_network_sysid_compid() {
  std::vector<uint8_t> buffer(1024);
  BufferWriter<ProfileNetworkConfig> writer(buffer.data(), buffer.size());

  // Encode with specific sys_id=5, comp_id=10
  auto msg = StandardMessages::get_message(0);
  std::visit([&writer](auto&& m) { writer.write(m, 1, 5, 10); }, msg);

  size_t frame_size = writer.size();
  if (frame_size < 10) return false;

  // Corrupt sys_id byte (byte 3: [start1][start2][seq][sys_id]...)
  // This is inside the CRC-protected region, so CRC will fail
  buffer[3] ^= 0xFF;

  BufferReader<ProfileNetworkConfig, decltype(&get_message_info)> reader(
      buffer.data(), frame_size, get_message_info);
  auto result = reader.next();
  return !result.valid;  // Expect failure: corrupted sys_id invalidates CRC
}

/**
 * Test: AccumulatingReader handles a frame fed in two separate add_data chunks
 */
bool test_partial_frame_boundary() {
  // Encode a valid message
  std::vector<uint8_t> buffer(1024);
  BufferWriter<ProfileStandardConfig> writer(buffer.data(), buffer.size());
  
  auto msg = StandardMessages::get_message(0);
  std::visit([&writer](auto&& m) { writer.write(m); }, msg);
  
  size_t frame_size = writer.size();
  if (frame_size < 10) return false;
  
  size_t mid = frame_size / 2;
  
  AccumulatingReader<ProfileStandardConfig, 1024, decltype(&get_message_info)> reader(get_message_info);
  
  // Feed first half, then call next() to save partial data to internal buffer
  reader.add_data(buffer.data(), mid);
  reader.next();  // Should return invalid but save partial data internally
  
  // Feed second half - adds to internal buffer completing the frame
  reader.add_data(buffer.data() + mid, frame_size - mid);
  
  // Call next() once all data is present - should successfully decode the frame
  auto result = reader.next();
  return result.valid;  // Expect success after accumulating both halves
}

// Test function pointer type
typedef bool (*TestFunc)();

// Test case structure
struct TestCase {
  const char* name;
  TestFunc func;
};

int main() {
  printf("\n========================================\n");
  printf("NEGATIVE TESTS - C++ Parser\n");
  printf("========================================\n\n");
  
  // Define test matrix
  TestCase tests[] = {
    {"Bulk profile: Corrupted CRC", test_bulk_profile_corrupted_crc},
    {"Corrupted CRC detection", test_corrupted_crc},
    {"Corrupted length field detection", test_corrupted_length},
    {"Invalid message ID rejection", test_invalid_msg_id},
    {"Invalid start byte detection", test_invalid_start_byte},
    {"Invalid start bytes detection", test_invalid_start_bytes},
    {"Minimal profile: Truncated frame", test_minimal_profile_truncated_frame},
    {"Multiple frames: Corrupted middle frame", test_multiple_corrupted_frames},
    {"Network profile: SysId/CompId corruption", test_network_sysid_compid},
    {"Partial frame across buffer boundary", test_partial_frame_boundary},
    {"Streaming: Corrupted CRC detection", test_streaming_corrupted_crc},
    {"Streaming: Garbage data handling", test_streaming_garbage_data},
    {"Truncated frame detection", test_truncated_frame},
    {"Zero-length buffer handling", test_zero_length_buffer}
  };
  
  int num_tests = sizeof(tests) / sizeof(tests[0]);
  
  printf("Test Results Matrix:\n\n");
  printf("%-50s %s\n", "Test Name", "Result");
  printf("%-50s %s\n", "==================================================", "======");
  
  // Run all tests from the matrix
  for (int i = 0; i < num_tests; i++) {
    tests_run++;
    bool passed = tests[i].func();
    
    printf("%-50s %s\n", tests[i].name, passed ? "PASS" : "FAIL");
    
    if (passed) {
      tests_passed++;
    } else {
      tests_failed++;
    }
  }
  
  printf("\n========================================\n");
  printf("Summary: %d/%d tests passed\n", tests_passed, tests_run);
  printf("========================================\n\n");
  
  return tests_failed > 0 ? 1 : 0;
}
