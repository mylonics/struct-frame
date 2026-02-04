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
    {"Corrupted CRC detection", test_corrupted_crc},
    {"Truncated frame detection", test_truncated_frame},
    {"Invalid start byte detection", test_invalid_start_byte},
    {"Zero-length buffer handling", test_zero_length_buffer},
    {"Corrupted length field detection", test_corrupted_length},
    {"Streaming: Corrupted CRC detection", test_streaming_corrupted_crc},
    {"Streaming: Garbage data handling", test_streaming_garbage_data},
    {"Multiple frames: Corrupted middle frame", test_multiple_corrupted_frames},
    {"Bulk profile: Corrupted CRC", test_bulk_profile_corrupted_crc}
  };
  
  int num_tests = sizeof(tests) / sizeof(tests[0]);
  
  printf("Testing error handling for invalid frames:\n\n");
  
  // Run all tests from the matrix
  for (int i = 0; i < num_tests; i++) {
    printf("  [TEST] %s... ", tests[i].name);
    tests_run++;
    
    if (tests[i].func()) {
      printf("PASS\n");
      tests_passed++;
    } else {
      printf("FAIL\n");
      tests_failed++;
    }
  }
  
  printf("\n========================================\n");
  printf("RESULTS\n");
  printf("========================================\n");
  printf("Tests run:    %d\n", tests_run);
  printf("Tests passed: %d\n", tests_passed);
  printf("Tests failed: %d\n", tests_failed);
  printf("========================================\n\n");
  
  return tests_failed > 0 ? 1 : 0;
}
