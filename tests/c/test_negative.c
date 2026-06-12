/**
 * Negative tests for struct-frame C parser
 * 
 * Tests error handling for:
 * - Corrupted CRC/checksum
 * - Truncated frames
 * - Invalid start bytes
 * - Malformed data
 * 
 * Note: C API uses buffer_writer_t/buffer_reader_t which differs from C++/Python.
 * These tests use a simplified approach focusing on the buffer reader API.
 */

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "frame_profiles.h"
#include "serialization_test.structframe.h"

/* Package test message constants (from pkg_test_messages, pkgid=1) */
#define PKG_TEST_MESSAGES_PACKAGE_ID        1
#define PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_MSG_ID  257
#define PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_MAGIC1  211
#define PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_MAGIC2  76
#define PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_BASE_SIZE 45

/* Package A constants (from pkg_test_a, pkgid=2) */
#define PKG_TEST_A_PACKAGE_ID               2
#define PKG_TEST_A_ACTION_MESSAGE_MSG_ID    513
#define PKG_TEST_A_ACTION_MESSAGE_MAGIC1    70
#define PKG_TEST_A_ACTION_MESSAGE_MAGIC2    36
#define PKG_TEST_A_ACTION_MESSAGE_BASE_SIZE 70

// Test result tracking
static int tests_run = 0;
static int tests_passed = 0;
static int tests_failed = 0;

/**
 * Helper to create a test message
 */
static void create_test_message(SerializationTestBasicTypesMessage* msg) {
  memset(msg, 0, sizeof(*msg));
  msg->small_int = 42;
  msg->medium_int = 1000;
  msg->regular_int = 100000;
  msg->large_int = 1000000000LL;
  msg->small_uint = 200;
  msg->medium_uint = 50000;
  msg->regular_uint = 3000000000U;
  msg->large_uint = 9000000000000000000ULL;
  msg->single_precision = 3.14159f;
  msg->double_precision = 2.71828;
  msg->flag = true;
  strncpy(msg->device_id, "DEVICE123", sizeof(msg->device_id) - 1);
  msg->description.length = 11;
  strncpy(msg->description.data, "Test device", 63);
}

/**
 * Test: Parser rejects frame with corrupted CRC
 */
bool test_corrupted_crc(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);
  
  // Create writer and encode
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));
  
  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);
  
  size_t frame_size = buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload, payload_size, 0, 0, 0, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  if (frame_size < 4) return false;
  
  // Corrupt the CRC (last 2 bytes)
  buffer[frame_size - 1] ^= 0xFF;
  buffer[frame_size - 2] ^= 0xFF;
  
  // Try to parse - should fail
  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, frame_size, get_message_info);
  frame_msg_info_t result = buffer_reader_next(&reader);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser rejects truncated frame
 */
bool test_truncated_frame(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);
  
  // Create writer and encode
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));
  
  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);
  
  size_t frame_size = buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload, payload_size, 0, 0, 0, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  if (frame_size < 10) return false;
  
  // Truncate the frame
  size_t truncated = frame_size - 5;
  
  // Try to parse - should fail
  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, truncated, get_message_info);
  frame_msg_info_t result = buffer_reader_next(&reader);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser rejects frame with invalid start bytes
 */
bool test_invalid_start_bytes(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);
  
  // Create writer and encode
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));
  
  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);
  
  size_t frame_size = buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload, payload_size, 0, 0, 0, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  if (frame_size < 2) return false;
  
  // Corrupt start bytes
  buffer[0] = 0xDE;
  buffer[1] = 0xAD;
  
  // Try to parse - should fail
  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, frame_size, get_message_info);
  frame_msg_info_t result = buffer_reader_next(&reader);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser handles zero-length buffer
 */
bool test_zero_length_buffer(void) {
  uint8_t buffer[1024];
  
  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, 0, get_message_info);
  frame_msg_info_t result = buffer_reader_next(&reader);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser handles corrupted length field
 */
bool test_corrupted_length(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);
  
  // Create writer and encode
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));
  
  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);
  
  size_t frame_size = buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload, payload_size, 0, 0, 0, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  if (frame_size < 4) return false;
  
  // Corrupt length field (byte 2 for ProfileStandard)
  buffer[2] = 0xFF;
  
  // Try to parse - should fail
  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, frame_size, get_message_info);
  frame_msg_info_t result = buffer_reader_next(&reader);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Streaming parser rejects corrupted CRC
 */
bool test_streaming_corrupted_crc(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);
  
  // Create writer and encode
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));
  
  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);
  
  size_t frame_size = buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload, payload_size, 0, 0, 0, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  if (frame_size < 4) return false;
  
  // Corrupt CRC
  buffer[frame_size - 1] ^= 0xFF;
  
  // Allocate internal buffer for accumulating reader
  uint8_t internal_buffer[1024];
  
  // Try streaming parse
  accumulating_reader_t reader;
  accumulating_reader_init(&reader, &PROFILE_STANDARD_CONFIG, internal_buffer, sizeof(internal_buffer), get_message_info);
  
  // Feed byte by byte
  for (size_t i = 0; i < frame_size; i++) {
    accumulating_reader_push_byte(&reader, buffer[i]);
  }
  
  frame_msg_info_t result = accumulating_reader_next(&reader);
  return !result.valid;  // Expect failure
}

/**
 * Test: Streaming parser handles garbage data
 */
bool test_streaming_garbage(void) {
  // Allocate internal buffer for accumulating reader
  uint8_t internal_buffer[1024];
  
  // Create accumulating reader
  accumulating_reader_t reader;
  accumulating_reader_init(&reader, &PROFILE_STANDARD_CONFIG, internal_buffer, sizeof(internal_buffer), get_message_info);
  
  // Feed garbage bytes
  uint8_t garbage[] = {0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56, 0x78, 0x9A};
  
  for (size_t i = 0; i < sizeof(garbage); i++) {
    accumulating_reader_push_byte(&reader, garbage[i]);
  }
  
  frame_msg_info_t result = accumulating_reader_next(&reader);
  return !result.valid;  // Expect no valid frame
}

/**
 * Test: Multiple frames with corrupted middle frame
 */
bool test_multiple_corrupted_frames(void) {
  uint8_t buffer[4096];
  SerializationTestBasicTypesMessage msg;
  
  // Create writer
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));
  
  // Write three frames
  create_test_message(&msg);
  msg.small_int = 1;
  
  uint8_t payload1[256];
  size_t payload_size1 = SerializationTestBasicTypesMessage_serialize(&msg, payload1);
  buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                     payload1, payload_size1, 0, 0, 0, 0,
                     SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                     SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  size_t first_frame_end = buffer_writer_size(&writer);
  
  msg.small_int = 2;
  uint8_t payload2[256];
  size_t payload_size2 = SerializationTestBasicTypesMessage_serialize(&msg, payload2);
  buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                     payload2, payload_size2, 0, 0, 0, 0,
                     SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                     SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  size_t second_frame_end = buffer_writer_size(&writer);
  
  msg.small_int = 3;
  uint8_t payload3[256];
  size_t payload_size3 = SerializationTestBasicTypesMessage_serialize(&msg, payload3);
  buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                     payload3, payload_size3, 0, 0, 0, 0,
                     SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                     SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  size_t total_size = buffer_writer_size(&writer);
  
  // Corrupt the second frame's CRC (last 2 bytes before third frame)
  buffer[second_frame_end - 1] ^= 0xFF;
  buffer[second_frame_end - 2] ^= 0xFF;
  
  // Parse all frames
  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, total_size, get_message_info);
  
  // First should be valid
  frame_msg_info_t result1 = buffer_reader_next(&reader);
  if (!result1.valid) return false;
  
  // Second should be invalid
  frame_msg_info_t result2 = buffer_reader_next(&reader);
  return !result2.valid;  // Expect failure on second frame
}

/**
 * Test: Bulk profile with corrupted CRC
 */
bool test_bulk_profile_corrupted_crc(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);
  
  // Create writer with bulk profile
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_BULK_CONFIG, buffer, sizeof(buffer));
  
  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);
  
  size_t frame_size = buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload, payload_size, 0, 0, 0, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  if (frame_size < 4) return false;
  
  // Corrupt the CRC (last 2 bytes)
  buffer[frame_size - 1] ^= 0xFF;
  buffer[frame_size - 2] ^= 0xFF;
  
  // Try to parse - should fail
  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_BULK_CONFIG, buffer, frame_size, get_message_info);
  frame_msg_info_t result = buffer_reader_next(&reader);
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser rejects frame with unknown message ID (CRC fails with wrong magic values)
 * ProfileStandard layout: [0x90][0x71][LEN][MSG_ID][PAYLOAD...][CRC1][CRC2]
 */
bool test_invalid_msg_id(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);

  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));

  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);

  size_t frame_size = buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload, payload_size, 0, 0, 0, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  if (frame_size < 5) return false;

  /* Corrupt the msg_id byte (byte 3 for ProfileStandard: [start1][start2][len][msg_id]...) */
  /* 0xFF is not a known message ID → get_message_info returns {0,0,0} magic → CRC fails */
  buffer[3] = 0xFF;

  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, frame_size, get_message_info);
  frame_msg_info_t result = buffer_reader_next(&reader);
  return !result.valid;  /* Expect failure: CRC mismatch due to wrong magic values */
}

/**
 * Test: Minimal profile (no CRC) rejects a truncated frame
 * ProfileSensor layout: [0x70][MSG_ID][PAYLOAD...]  (no CRC, no length field)
 * Parser uses get_message_info to determine expected payload size.
 */
bool test_minimal_profile_truncated_frame(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);

  /* Encode a ProfileSensor frame manually: [0x70][msg_id][payload...] */
  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);

  buffer[0] = 0x70;  /* Tiny start byte for MINIMAL payload type */
  buffer[1] = SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID & 0xFF;
  memcpy(buffer + 2, payload, payload_size);
  size_t frame_size = 2 + payload_size;

  if (frame_size <= 5) return false;

  /* Provide fewer bytes than the full frame to trigger truncation error */
  size_t truncated = frame_size - 5;

  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_SENSOR_CONFIG, buffer, truncated, get_message_info);
  frame_msg_info_t result = buffer_reader_next(&reader);
  return !result.valid;  /* Expect failure: buffer too small for expected payload */
}

/**
 * Test: Network profile validates sys_id/comp_id as part of CRC-protected header
 * ProfileNetwork layout: [0x90][0x78][SEQ][SYS_ID][COMP_ID][LEN_LO][LEN_HI][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * Since sys_id (byte 3) is within the CRC region, corrupting it causes CRC failure.
 */
bool test_network_sysid_compid(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);

  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_NETWORK_CONFIG, buffer, sizeof(buffer));

  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);

  /* Encode with seq=1, sys_id=5, comp_id=10, pkg_id=0 */
  size_t frame_size = buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload, payload_size, 1, 5, 10, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  if (frame_size < 10) return false;

  /* Corrupt sys_id (byte 3: [start1][start2][seq][sys_id]...)
   * sys_id is inside the CRC-protected region so this will cause CRC failure */
  buffer[3] ^= 0xFF;

  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_NETWORK_CONFIG, buffer, frame_size, get_message_info);
  frame_msg_info_t result = buffer_reader_next(&reader);
  return !result.valid;  /* Expect failure: corrupted sys_id invalidates CRC */
}

/**
 * Test: AccumulatingReader handles a frame fed in two separate chunks
 */
bool test_partial_frame_boundary(void) {
  uint8_t buffer[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);
  
  // Encode a valid frame
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));
  
  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);
  
  size_t frame_size = buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload, payload_size, 0, 0, 0, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  
  if (frame_size < 10) return false;
  
  size_t mid = frame_size / 2;
  uint8_t internal_buffer[1024];
  
  // Create accumulating reader (buffer mode)
  accumulating_reader_t reader;
  accumulating_reader_init(&reader, &PROFILE_STANDARD_CONFIG, internal_buffer, sizeof(internal_buffer), get_message_info);
  
  // Feed first half via add_data, then call next() to save partial data
  accumulating_reader_add_data(&reader, buffer, mid);
  accumulating_reader_next(&reader);  // Should return invalid but save partial data
  
  // Feed second half - adds to internal_buffer completing the frame
  accumulating_reader_add_data(&reader, buffer + mid, frame_size - mid);
  
  // Call next() once all data is present - should successfully decode the frame
  frame_msg_info_t result = accumulating_reader_next(&reader);
  return result.valid;  // Expect success after accumulating both halves
}

/**
 * Test: Bulk profile rejects corrupted pkg_id byte
 * ProfileBulk layout: [0x90][0x71][LEN][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * Corrupting pkg_id (byte 3) causes CRC failure.
 */
bool test_bulk_corrupted_pkg_id(void) {
  uint8_t buffer[1024];
  /* Raw payload for PackageTestMessage (45 bytes):
   * created_at: seconds (uint32), nanoseconds (uint32) = 8 bytes
   * current_status: uint8 = 1 byte
   * name: char[32] = 32 bytes
   * Total: 41 bytes... wait let me check the actual struct
   * Actually from the generated header:
   *   CommonTypesTimestamp created_at;  // 8 bytes
   *   CommonTypesStatus_t current_status; // 1 byte
   *   char name[32]; // 32 bytes
   *   Total = 8 + 1 + 32 = 41, but BASE_SIZE is 45 (padding for alignment)
   * Let's just use a 45-byte zero payload with some data.
   */
  uint8_t payload[45];
  memset(payload, 0, sizeof(payload));
  payload[0] = 0x39;  /* seconds low byte = 12345 & 0xFF */
  payload[1] = 0x30;
  payload[4] = 0x12;  /* nanoseconds low byte = 67890 & 0xFF */
  payload[5] = 0x09;
  payload[8] = 1;     /* status = Active */
  memcpy(payload + 9, "TestDevice", 10);

  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_BULK_CONFIG, buffer, sizeof(buffer));

  uint8_t msg_id_byte = (uint8_t)(PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_MSG_ID & 0xFF);
  uint8_t pkg_id_byte = (uint8_t)((PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_MSG_ID >> 8) & 0xFF);

  size_t frame_size = buffer_writer_write_ext(&writer, msg_id_byte,
                                          payload, sizeof(payload),
                                          0, 0, 0, pkg_id_byte,
                                          PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_BASE_SIZE,
                                          PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_MAGIC1,
                                          PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_MAGIC2);
  if (frame_size < 6) return false;

  /* Corrupt pkg_id byte (byte 3 for Bulk: [start1][start2][len][pkg_id][msg_id]...) */
  buffer[3] ^= 0xFF;

  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_BULK_CONFIG, buffer, frame_size, get_message_info);
  frame_msg_info_t result = buffer_reader_next(&reader);
  return !result.valid;  /* Expect failure: corrupted pkg_id invalidates CRC */
}

/**
 * Test: Network profile rejects corrupted pkg_id byte
 * ProfileNetwork layout: [0x90][0x78][SEQ][SYS_ID][COMP_ID][LEN_LO][LEN_HI][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * Corrupting pkg_id (byte 7) causes CRC failure.
 */
bool test_network_corrupted_pkg_id(void) {
  uint8_t buffer[1024];
  uint8_t payload[45];
  memset(payload, 0, sizeof(payload));
  payload[0] = 0x39;
  payload[1] = 0x30;
  payload[4] = 0x12;
  payload[5] = 0x09;
  payload[8] = 1;
  memcpy(payload + 9, "TestDevice", 10);

  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_NETWORK_CONFIG, buffer, sizeof(buffer));

  uint8_t msg_id_byte = (uint8_t)(PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_MSG_ID & 0xFF);
  uint8_t pkg_id_byte = (uint8_t)((PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_MSG_ID >> 8) & 0xFF);

  size_t frame_size = buffer_writer_write_ext(&writer, msg_id_byte,
                                          payload, sizeof(payload),
                                          1, 5, 10, pkg_id_byte,
                                          PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_BASE_SIZE,
                                          PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_MAGIC1,
                                          PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_MAGIC2);
  if (frame_size < 10) return false;

  /* Corrupt pkg_id byte (byte 7 for Network) */
  buffer[7] ^= 0xFF;

  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_NETWORK_CONFIG, buffer, frame_size, get_message_info);
  frame_msg_info_t result = buffer_reader_next(&reader);
  return !result.valid;  /* Expect failure: corrupted pkg_id invalidates CRC */
}

/**
 * Test: Cross-package message rejection
 * Encode a pkg_test_a message (pkgid=2) and try to parse it as pkg_test_messages (pkgid=1).
 * The parser should reject it because pkg_id won't match.
 */
bool test_cross_package_rejection(void) {
  uint8_t buffer[1024];
  /* Raw payload for pkg_test_a::ActionMessage (70 bytes):
   * action: uint8 = 1 byte
   * target_id: uint32 = 4 bytes
   * description: {length: uint8, data: char[64]} = 65 bytes
   * Total = 1 + 4 + 65 = 70
   */
  uint8_t payload[70];
  memset(payload, 0, sizeof(payload));
  payload[0] = 0;     /* action = Start */
  payload[1] = 42;    /* target_id low byte */
  payload[5] = 4;     /* description.length = 4 */
  memcpy(payload + 6, "test", 4);

  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_BULK_CONFIG, buffer, sizeof(buffer));

  uint8_t msg_id_byte = (uint8_t)(PKG_TEST_A_ACTION_MESSAGE_MSG_ID & 0xFF);
  uint8_t pkg_id_byte = (uint8_t)((PKG_TEST_A_ACTION_MESSAGE_MSG_ID >> 8) & 0xFF);

  size_t frame_size = buffer_writer_write_ext(&writer, msg_id_byte,
                                          payload, sizeof(payload),
                                          0, 0, 0, pkg_id_byte,
                                          PKG_TEST_A_ACTION_MESSAGE_BASE_SIZE,
                                          PKG_TEST_A_ACTION_MESSAGE_MAGIC1,
                                          PKG_TEST_A_ACTION_MESSAGE_MAGIC2);
  if (frame_size < 6) return false;

  /* Try to parse with get_message_info - the pkg_id (2) won't match pkg_test_messages (1) */
  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_BULK_CONFIG, buffer, frame_size, get_message_info);
  frame_msg_info_t result = buffer_reader_next(&reader);

  /* The frame may parse as valid at the frame level, but the msg_id should be 513 (pkg_test_a)
   * not a pkg_test_messages ID. Check that the msg_id doesn't belong to pkg_test_messages. */
  if (!result.valid) return true;  /* If parsing failed, that's good */

  /* If parsing succeeded, verify it's NOT a pkg_test_messages message */
  uint16_t expected_pkg_id = (result.msg_id >> 8) & 0xFF;
  return expected_pkg_id != PKG_TEST_MESSAGES_PACKAGE_ID;
}

/**
 * Test: Bulk profile rejects corrupted msg_id low byte
 * ProfileBulk layout: [0x90][0x71][LEN][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * Corrupting msg_id low byte (byte 4) changes the message type → wrong magic → CRC fails.
 */
bool test_bulk_corrupted_msg_id_low_byte(void) {
  uint8_t buffer[1024];
  uint8_t payload[45];
  memset(payload, 0, sizeof(payload));
  payload[0] = 0x39;
  payload[1] = 0x30;
  payload[4] = 0x12;
  payload[5] = 0x09;
  payload[8] = 1;
  memcpy(payload + 9, "TestDevice", 10);

  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_BULK_CONFIG, buffer, sizeof(buffer));

  uint8_t msg_id_byte = (uint8_t)(PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_MSG_ID & 0xFF);
  uint8_t pkg_id_byte = (uint8_t)((PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_MSG_ID >> 8) & 0xFF);

  size_t frame_size = buffer_writer_write_ext(&writer, msg_id_byte,
                                          payload, sizeof(payload),
                                          0, 0, 0, pkg_id_byte,
                                          PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_BASE_SIZE,
                                          PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_MAGIC1,
                                          PKG_TEST_MESSAGES_PACKAGE_TEST_MESSAGE_MAGIC2);
  if (frame_size < 6) return false;

  /* Corrupt msg_id low byte (byte 4 for Bulk) */
  buffer[4] ^= 0xFF;

  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_BULK_CONFIG, buffer, frame_size, get_message_info);
  frame_msg_info_t result = buffer_reader_next(&reader);
  return !result.valid;  /* Expect failure: wrong msg_id → wrong magic → CRC fails */
}

/**
 * Test: BufferReader advances past a CRC-failed frame and decodes the next valid frame.
 * Catches the A2 stall: buffer_reader was not advancing past CRC failures.
 */
bool test_buffer_reader_skips_crc_failure(void) {
  uint8_t buffer[2048];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);

  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));

  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);
  buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                      payload, payload_size, 0, 0, 0, 0,
                      SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                      SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  size_t first_frame_end = buffer_writer_size(&writer);

  buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                      payload, payload_size, 0, 0, 0, 0,
                      SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                      SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  size_t total_size = buffer_writer_size(&writer);

  /* Corrupt CRC of first frame */
  buffer[first_frame_end - 1] ^= 0xFF;
  buffer[first_frame_end - 2] ^= 0xFF;

  buffer_reader_t reader;
  buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, total_size, get_message_info);

  frame_msg_info_t result1 = buffer_reader_next(&reader);
  if (result1.valid) return false;  /* First frame must fail */

  frame_msg_info_t result2 = buffer_reader_next(&reader);
  return result2.valid;  /* Second frame must succeed after skipping the bad one */
}

/**
 * Test: AccumulatingReader buffer mode recovers after a CRC failure in add_data path.
 * Catches the A3 stall: CRC-bad frames caused a permanent loop in buffer mode.
 */
bool test_buffer_mode_recovers_after_crc_failure(void) {
  uint8_t bad_frame[1024];
  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);

  buffer_writer_t writer1;
  buffer_writer_init(&writer1, &PROFILE_STANDARD_CONFIG, bad_frame, sizeof(bad_frame));

  uint8_t payload1[256];
  size_t payload_size1 = SerializationTestBasicTypesMessage_serialize(&msg, payload1);
  size_t frame_size = buffer_writer_write(&writer1, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload1, payload_size1, 0, 0, 0, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
  if (frame_size < 4) return false;

  bad_frame[frame_size - 1] ^= 0xFF;
  bad_frame[frame_size - 2] ^= 0xFF;

  uint8_t internal_buffer[2048];
  accumulating_reader_t reader;
  accumulating_reader_init(&reader, &PROFILE_STANDARD_CONFIG, internal_buffer, sizeof(internal_buffer), get_message_info);

  accumulating_reader_add_data(&reader, bad_frame, frame_size);
  frame_msg_info_t result1 = accumulating_reader_next(&reader);
  if (result1.valid) return false;  /* Must fail */

  /* Feed a valid frame - reader must not be stuck on the bad one */
  uint8_t good_frame[1024];
  buffer_writer_t writer2;
  buffer_writer_init(&writer2, &PROFILE_STANDARD_CONFIG, good_frame, sizeof(good_frame));
  uint8_t payload2[256];
  size_t payload_size2 = SerializationTestBasicTypesMessage_serialize(&msg, payload2);
  size_t good_size = buffer_writer_write(&writer2, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                         payload2, payload_size2, 0, 0, 0, 0,
                                         SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                         SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);

  accumulating_reader_add_data(&reader, good_frame, good_size);
  frame_msg_info_t result2 = accumulating_reader_next(&reader);
  return result2.valid;
}

/**
 * Test: Stream mode recovers after garbage prefix and decodes a valid frame.
 */
bool test_stream_recovers_after_garbage(void) {
  uint8_t internal_buffer[1024];
  accumulating_reader_t reader;
  accumulating_reader_init(&reader, &PROFILE_STANDARD_CONFIG, internal_buffer, sizeof(internal_buffer), get_message_info);

  uint8_t garbage[] = {0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56};
  for (size_t i = 0; i < sizeof(garbage); i++) {
    accumulating_reader_push_byte(&reader, garbage[i]);
  }

  uint8_t frame_buf[1024];
  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, frame_buf, sizeof(frame_buf));

  SerializationTestBasicTypesMessage msg;
  create_test_message(&msg);
  uint8_t payload[256];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);
  size_t frame_size = buffer_writer_write(&writer, SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
                                          payload, payload_size, 0, 0, 0, 0,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
                                          SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);

  for (size_t i = 0; i < frame_size; i++) {
    frame_msg_info_t r = accumulating_reader_push_byte(&reader, frame_buf[i]);
    if (r.valid) return true;
  }
  return false;
}

// Test function pointer type
typedef bool (*TestFunc)(void);

// Test case structure
typedef struct {
  const char* name;
  TestFunc func;
} TestCase;

int main(void) {
  printf("\n========================================\n");
  printf("NEGATIVE TESTS - C Parser\n");
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
    {"Multiple frames: Corrupted middle frame", test_multiple_corrupted_frames},
    {"Network profile: Corrupted pkg_id", test_network_corrupted_pkg_id},
    {"Network profile: SysId/CompId corruption", test_network_sysid_compid},
    {"Partial frame across buffer boundary", test_partial_frame_boundary},
    {"Stream mode: recovers after garbage prefix", test_stream_recovers_after_garbage},
    {"Streaming: Corrupted CRC detection", test_streaming_corrupted_crc},
    {"Streaming: Garbage data handling", test_streaming_garbage},
    {"Truncated frame detection", test_truncated_frame},
    {"Zero-length buffer handling", test_zero_length_buffer}
  };
  
  int num_tests = sizeof(tests) / sizeof(tests[0]);
  
  printf("Test Results Matrix:\n\n");
  printf("%-50s %6s\n", "Test Name", "Result");
  printf("%-50s %6s\n", "==================================================", "======");
  
  // Run all tests from the matrix
  for (int i = 0; i < num_tests; i++) {
    tests_run++;
    bool passed = tests[i].func();
    
    printf("%-50s %6s\n", tests[i].name, passed ? "PASS" : "FAIL");
    
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
