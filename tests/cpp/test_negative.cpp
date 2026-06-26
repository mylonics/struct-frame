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
#include "../../generated/cpp/pkg_test_messages.structframe.hpp"

using namespace structframe;

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
  
  auto msg = StandardMessages::get_message(5);
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
  
  auto msg = StandardMessages::get_message(5);
  std::visit([&writer](auto&& m) { writer.write(m); }, msg);
  
  size_t frame_size = writer.size();
  if (frame_size < 10) return false;
  
  size_t mid = frame_size / 2;
  
  AccumulatingReader<ProfileStandardConfig, 1024, decltype(&get_message_info)> reader(get_message_info);
  
  // Feed first half, then call next() to save partial data to internal buffer
  reader.add_data(buffer.data(), mid);
  auto partial = reader.next();
  if (partial.valid) return false;
  
  // Feed second half - adds to internal buffer completing the frame
  reader.add_data(buffer.data() + mid, frame_size - mid);

  // Drain with try_next(): invalid progress events may be surfaced before valid frame.
  FrameMsgInfo result{};
  bool found_valid = false;
  FrameMsgInfo step{};
  while (reader.try_next(step)) {
    if (step.valid) {
      result = step;
      found_valid = true;
      break;
    }
  }

  if (!found_valid) return false;
  if (result.msg_id != BasicTypesMessage::MSG_ID) return false;
  if (result.msg_data == nullptr) return false;

  BasicTypesMessage decoded;
  decoded.deserialize(result.msg_data, result.msg_len);
  auto expected = std::get<BasicTypesMessage>(msg);
  if (decoded.small_int != expected.small_int) return false;
  if (decoded.flag != expected.flag) return false;

  // No extra complete frame should remain.
  auto trailing = reader.next();
  if (trailing.valid) return false;

  return true;
}

/**
 * Test: Bulk profile rejects corrupted pkg_id byte
 * ProfileBulk layout: [0x90][0x71][LEN][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * Corrupting pkg_id (byte 3) causes CRC failure.
 */
bool test_bulk_corrupted_pkg_id() {
  std::vector<uint8_t> buffer(1024);
  BufferWriter<ProfileBulkConfig> writer(buffer.data(), buffer.size());

  pkg_test_messages::PackageTestMessage msg;
  memset(&msg, 0, sizeof(msg));
  msg.created_at.seconds = 12345;
  msg.created_at.nanoseconds = 67890;
  msg.current_status = common_types::Status::Active;
  strncpy(msg.name, "TestDevice", sizeof(msg.name));

  writer.write(msg);
  size_t frame_size = writer.size();
  if (frame_size < 6) return false;

  // Corrupt pkg_id byte (byte 3 for Bulk: [start1][start2][len][pkg_id][msg_id]...)
  buffer[3] ^= 0xFF;

  BufferReader<ProfileBulkConfig, decltype(&get_message_info)> reader(
      buffer.data(), frame_size, get_message_info);
  auto result = reader.next();
  return !result.valid;  // Expect failure: corrupted pkg_id invalidates CRC
}

/**
 * Test: Network profile rejects corrupted pkg_id byte
 * ProfileNetwork layout: [0x90][0x78][SEQ][SYS_ID][COMP_ID][LEN_LO][LEN_HI][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * Corrupting pkg_id (byte 7) causes CRC failure.
 */
bool test_network_corrupted_pkg_id() {
  std::vector<uint8_t> buffer(1024);
  BufferWriter<ProfileNetworkConfig> writer(buffer.data(), buffer.size());

  pkg_test_messages::PackageTestMessage msg;
  memset(&msg, 0, sizeof(msg));
  msg.created_at.seconds = 12345;
  msg.created_at.nanoseconds = 67890;
  msg.current_status = common_types::Status::Active;
  strncpy(msg.name, "TestDevice", sizeof(msg.name));

  writer.write(msg, 1, 5, 10);
  size_t frame_size = writer.size();
  if (frame_size < 10) return false;

  // Corrupt pkg_id byte (byte 7 for Network)
  buffer[7] ^= 0xFF;

  BufferReader<ProfileNetworkConfig, decltype(&get_message_info)> reader(
      buffer.data(), frame_size, get_message_info);
  auto result = reader.next();
  return !result.valid;  // Expect failure: corrupted pkg_id invalidates CRC
}

/**
 * Test: Cross-package message rejection
 * Encode a pkg_test_a message (pkgid=2) and try to parse it as pkg_test_messages (pkgid=1).
 * The parser should reject it because pkg_id won't match.
 */
bool test_cross_package_rejection() {
  std::vector<uint8_t> buffer(1024);
  BufferWriter<ProfileBulkConfig> writer(buffer.data(), buffer.size());

  // Encode a pkg_test_a message (pkgid=2, msg_id=513)
  pkg_test_a::ActionMessage msg;
  memset(&msg, 0, sizeof(msg));
  msg.action = pkg_test_a::ActionType::Start;
  msg.target_id = 42;
  msg.description.length = 4;
  strncpy(msg.description.data, "test", 4);

  writer.write(msg);
  size_t frame_size = writer.size();
  if (frame_size < 6) return false;

  // Try to parse with get_message_info - the pkg_id (2) won't match pkg_test_messages (1)
  // so the message should be rejected
  BufferReader<ProfileBulkConfig, decltype(&get_message_info)> reader(
      buffer.data(), frame_size, get_message_info);
  auto result = reader.next();

  // The frame may parse as valid at the frame level, but the msg_id should be 513 (pkg_test_a)
  // not a pkg_test_messages ID. Check that the msg_id doesn't belong to pkg_test_messages.
  if (!result.valid) return true;  // If parsing failed, that's good

  // If parsing succeeded, verify it's NOT a pkg_test_messages message
  uint16_t expected_pkg_id = (result.msg_id >> 8) & 0xFF;
  return expected_pkg_id != pkg_test_messages::PACKAGE_ID;
}

/**
 * Test: TryNext drain loop surfaces CRC/resync progress and still delivers
 * the following valid frame.
 */
bool test_try_next_drain_contract() {
  std::vector<uint8_t> buffer(2048);
  BufferWriter<ProfileStandardConfig> writer(buffer.data(), buffer.size());

  auto msg = StandardMessages::get_message(0);
  std::visit([&writer](auto&& m) { writer.write(m); }, msg);
  size_t first_end = writer.size();

  auto msg2 = StandardMessages::get_message(1 % StandardMessages::MESSAGE_COUNT);
  std::visit([&writer](auto&& m) { writer.write(m); }, msg2);
  size_t total = writer.size();

  buffer[first_end - 1] ^= 0xFF;
  buffer[first_end - 2] ^= 0xFF;

  AccumulatingReader<ProfileStandardConfig, 2048, decltype(&get_message_info)> reader(get_message_info);
  reader.add_data(buffer.data(), total);

  int valid_count = 0;
  bool saw_crc_failure = false;
  FrameMsgInfo f;
  while (reader.try_next(f)) {
    if (f.valid) {
      valid_count++;
    } else if (f.status == FrameMsgStatus::CrcFailure) {
      saw_crc_failure = true;
    }
  }

  if (!saw_crc_failure) return false;
  if (valid_count != 1) return false;
  if (reader.has_more()) return false;
  if (reader.has_partial()) return false;
  if (reader.partial_size() != 0) return false;
  return true;
}

/**
 * Test: TryNext partial-pending contract.
 */
bool test_try_next_partial_pending_contract() {
  std::vector<uint8_t> buffer(1024);
  BufferWriter<ProfileStandardConfig> writer(buffer.data(), buffer.size());

  auto msg = StandardMessages::get_message(0);
  std::visit([&writer](auto&& m) { writer.write(m); }, msg);
  size_t frame_size = writer.size();
  if (frame_size < 10) return false;
  size_t mid = frame_size / 2;

  AccumulatingReader<ProfileStandardConfig, 1024, decltype(&get_message_info)> reader(get_message_info);

  reader.add_data(buffer.data(), mid);
  FrameMsgInfo first;
  if (reader.try_next(first)) return false;
  if (!reader.has_partial()) return false;
  if (reader.partial_size() == 0) return false;

  reader.add_data(buffer.data() + mid, frame_size - mid);
  int valid_count = 0;
  FrameMsgInfo f;
  while (reader.try_next(f)) {
    if (f.valid) valid_count++;
  }

  if (valid_count != 1) return false;
  if (reader.has_partial()) return false;
  if (reader.partial_size() != 0) return false;
  return !reader.has_more();
}

/**
 * Test: Bulk profile rejects corrupted msg_id low byte
 * ProfileBulk layout: [0x90][0x71][LEN][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * Corrupting msg_id low byte (byte 4) changes the message type → wrong magic → CRC fails.
 */
bool test_bulk_corrupted_msg_id_low_byte() {
  std::vector<uint8_t> buffer(1024);
  BufferWriter<ProfileBulkConfig> writer(buffer.data(), buffer.size());

  pkg_test_messages::PackageTestMessage msg;
  memset(&msg, 0, sizeof(msg));
  msg.created_at.seconds = 12345;
  msg.created_at.nanoseconds = 67890;
  msg.current_status = common_types::Status::Active;
  strncpy(msg.name, "TestDevice", sizeof(msg.name));

  writer.write(msg);
  size_t frame_size = writer.size();
  if (frame_size < 6) return false;

  // Corrupt msg_id low byte (byte 4 for Bulk)
  buffer[4] ^= 0xFF;

  BufferReader<ProfileBulkConfig, decltype(&get_message_info)> reader(
      buffer.data(), frame_size, get_message_info);
  auto result = reader.next();
  return !result.valid;  // Expect failure: wrong msg_id → wrong magic → CRC fails
}

/**
 * Test: BufferReader advances past a CRC-failed frame and decodes the next valid frame.
 * Catches the A2 stall: BufferReader was not advancing past CRC failures.
 */
bool test_buffer_reader_skips_crc_failure() {
  std::vector<uint8_t> buffer(2048);
  BufferWriter<ProfileStandardConfig> writer(buffer.data(), buffer.size());

  auto msg = StandardMessages::get_message(0);
  std::visit([&writer](auto&& m) { writer.write(m); }, msg);
  size_t first_frame_end = writer.size();

  std::visit([&writer](auto&& m) { writer.write(m); }, msg);
  size_t total = writer.size();

  // Corrupt the CRC of the first frame
  buffer[first_frame_end - 1] ^= 0xFF;
  buffer[first_frame_end - 2] ^= 0xFF;

  BufferReader<ProfileStandardConfig, decltype(&get_message_info)> reader(
      buffer.data(), total, get_message_info);

  auto result1 = reader.next();
  if (result1.valid) return false;  // First frame must fail (CRC corrupted)

  auto result2 = reader.next();
  return result2.valid;  // Second frame must succeed after skipping the bad one
}

/**
 * Test: AccumulatingReader buffer mode recovers after a CRC failure in add_data path.
 * Catches the A3 stall: CRC-bad frames caused a permanent loop in buffer mode.
 */
bool test_buffer_mode_recovers_after_crc_failure() {
  std::vector<uint8_t> bad_buf(1024);
  BufferWriter<ProfileStandardConfig> bad_writer(bad_buf.data(), bad_buf.size());
  auto msg = StandardMessages::get_message(0);
  std::visit([&bad_writer](auto&& m) { bad_writer.write(m); }, msg);
  size_t frame_size = bad_writer.size();

  // Corrupt the CRC
  bad_buf[frame_size - 1] ^= 0xFF;
  bad_buf[frame_size - 2] ^= 0xFF;

  AccumulatingReader<ProfileStandardConfig, 1024, decltype(&get_message_info)> reader(get_message_info);
  reader.add_data(bad_buf.data(), frame_size);
  auto result1 = reader.next();
  if (result1.valid) return false;  // Must fail

  // Feed a valid frame — reader must not be stuck on the bad one
  std::vector<uint8_t> good_buf(1024);
  BufferWriter<ProfileStandardConfig> good_writer(good_buf.data(), good_buf.size());
  std::visit([&good_writer](auto&& m) { good_writer.write(m); }, msg);
  size_t good_size = good_writer.size();

  reader.add_data(good_buf.data(), good_size);
  auto result2 = reader.next();
  return result2.valid;
}

/**
 * Test: Stream mode recovers after garbage prefix and decodes a valid frame.
 */
bool test_stream_recovers_after_garbage() {
  AccumulatingReader<ProfileStandardConfig, 1024, decltype(&get_message_info)> reader(get_message_info);

  uint8_t garbage[] = {0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56};
  for (auto b : garbage) reader.push_byte(b);

  std::vector<uint8_t> frame_buf(1024);
  BufferWriter<ProfileStandardConfig> writer(frame_buf.data(), frame_buf.size());
  auto msg = StandardMessages::get_message(0);
  std::visit([&writer](auto&& m) { writer.write(m); }, msg);
  size_t frame_size = writer.size();

  for (size_t i = 0; i < frame_size; i++) {
    auto r = reader.push_byte(frame_buf[i]);
    if (r.valid) return true;
  }
  return false;
}

/**
 * Test: After a CRC failure the reader continues and decodes the next valid frame,
 * and the buffer-exhausted signal is only raised after ALL frames are consumed.
 */
bool test_crc_error_then_valid_frame() {
  std::vector<uint8_t> buffer(4096);
  BufferWriter<ProfileStandardConfig> writer(buffer.data(), buffer.size());

  auto msg0 = StandardMessages::get_message(0);
  auto msg1 = StandardMessages::get_message(1);
  auto msg2 = StandardMessages::get_message(2);

  // Frame 1: valid
  std::visit([&writer](auto&& m) { writer.write(m); }, msg0);

  // Frame 2: CRC-corrupted
  std::visit([&writer](auto&& m) { writer.write(m); }, msg1);
  size_t frame2_end = writer.size();

  // Frame 3: valid
  std::visit([&writer](auto&& m) { writer.write(m); }, msg2);
  size_t total = writer.size();

  buffer[frame2_end - 1] ^= 0xFF;
  buffer[frame2_end - 2] ^= 0xFF;

  BufferReader<ProfileStandardConfig, decltype(&get_message_info)> reader(
      buffer.data(), total, get_message_info);

  // Frame 1 must decode successfully
  auto result1 = reader.next();
  if (!result1.valid) return false;

  // Frame 2 must report a CRC failure — status MUST be CrcFailure, not None
  auto result2 = reader.next();
  if (result2.valid) return false;
  if (result2.status != FrameMsgStatus::CrcFailure) return false;

  // Reader must continue past the CRC error and decode frame 3
  auto result3 = reader.next();
  if (!result3.valid) return false;

  // Buffer must now be fully consumed
  if (reader.has_more()) return false;

  return true;
}

bool test_split_buffer_crc_error_status() {
  std::vector<uint8_t> buffer(4096);
  BufferWriter<ProfileStandardConfig> writer(buffer.data(), buffer.size());

  auto msg0 = StandardMessages::get_message(0);
  auto msg1 = StandardMessages::get_message(1);
  auto msg2 = StandardMessages::get_message(2);

  // Frame 1: valid
  std::visit([&writer](auto&& m) { writer.write(m); }, msg0);

  // Frame 2: CRC-corrupted
  std::visit([&writer](auto&& m) { writer.write(m); }, msg1);
  size_t frame2_end = writer.size();

  // Frame 3: valid
  std::visit([&writer](auto&& m) { writer.write(m); }, msg2);
  size_t total = writer.size();

  buffer[frame2_end - 1] ^= 0xFF;
  buffer[frame2_end - 2] ^= 0xFF;

  /* Split: frame 2's two CRC bytes go in the second add_data() call */
  size_t split_point = frame2_end - 2;

  AccumulatingReader<ProfileStandardConfig, 1024, decltype(&get_message_info)> reader(get_message_info);

  reader.add_data(buffer.data(), split_point);

  /* Frame 1 must decode from the first chunk */
  auto result1 = reader.next();
  if (!result1.valid) return false;

  /* Frame 2 is incomplete — partial data saved to internal buffer */
  auto partial = reader.next();
  if (partial.valid) return false;

  reader.add_data(buffer.data() + split_point, total - split_point);

  /* CRC bytes of frame 2 arrive — frame 2 is complete but CRC-corrupted.
   * Status MUST be CrcFailure, not None. */
  auto result2 = reader.next();
  if (result2.valid) return false;
  if (result2.status != FrameMsgStatus::CrcFailure) return false;

  /* Frame 3 must still decode from the remainder of the second chunk */
  auto result3 = reader.next();
  if (!result3.valid) return false;

  return true;
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
    {"Buffer mode: recovers after CRC failure", test_buffer_mode_recovers_after_crc_failure},
    {"Buffer reader: skips CRC-failed frame", test_buffer_reader_skips_crc_failure},
    {"Bulk profile: Corrupted CRC", test_bulk_profile_corrupted_crc},
    {"Bulk profile: Corrupted pkg_id", test_bulk_corrupted_pkg_id},
    {"Bulk profile: Corrupted msg_id low byte", test_bulk_corrupted_msg_id_low_byte},
    {"Corrupted CRC detection", test_corrupted_crc},
    {"Corrupted length field detection", test_corrupted_length},
    {"Cross-package message rejection", test_cross_package_rejection},
    {"Invalid message ID rejection", test_invalid_msg_id},
    {"Invalid start bytes detection", test_invalid_start_bytes},
    {"Minimal profile: Truncated frame", test_minimal_profile_truncated_frame},
    {"Multiple frames: CRC error then valid frame", test_crc_error_then_valid_frame},
    {"Multiple frames: Corrupted middle frame", test_multiple_corrupted_frames},
    {"Network profile: Corrupted pkg_id", test_network_corrupted_pkg_id},
    {"Network profile: SysId/CompId corruption", test_network_sysid_compid},
    {"Partial frame across buffer boundary", test_partial_frame_boundary},
    {"Split-buffer: CRC error status preserved", test_split_buffer_crc_error_status},
    {"TryNext drain: CRC/resync + valid", test_try_next_drain_contract},
    {"TryNext partial pending contract", test_try_next_partial_pending_contract},
    {"Stream mode: recovers after garbage prefix", test_stream_recovers_after_garbage},
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
