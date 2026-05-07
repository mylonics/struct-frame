/**
 * Byte-by-byte streaming mode tests for the C AccumulatingReader (section 6.2)
 *
 * Validates accumulating_reader_push_byte() in the positive (successful decode) case:
 * - Standard profile: push bytes one by one and decode a complete frame
 * - Sensor profile: same for a minimal (no-CRC) profile
 * - Multiple frames: push two frames sequentially, decode both
 * - Interleaved start-byte search: garbage bytes before a valid frame are skipped
 */

#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include "frame_profiles.h"
#include "serialization_test.structframe.h"

/* ------------------------------------------------------------------
 * Shared test tracking
 * ------------------------------------------------------------------ */
static int tests_run = 0;
static int tests_passed = 0;
static int tests_failed = 0;

static bool run_test(const char* name, bool result) {
  tests_run++;
  printf("%-65s %s\n", name, result ? "PASS" : "FAIL");
  if (result) tests_passed++;
  else tests_failed++;
  return result;
}

/* ------------------------------------------------------------------
 * Helper: build a standard-profile frame for BasicTypesMessage
 *   Returns the number of bytes written into 'out'.
 * ------------------------------------------------------------------ */
static size_t encode_basic_types_standard(uint8_t* out, size_t out_size,
                                          int32_t regular_int_val) {
  SerializationTestBasicTypesMessage msg;
  memset(&msg, 0, sizeof(msg));
  msg.regular_int = regular_int_val;

  uint8_t payload[SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAX_SIZE];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);

  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, out, out_size);

  return buffer_writer_write(
      &writer,
      SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
      payload, payload_size,
      0, 0, 0, 0,  /* seq, sys_id, comp_id, pkg_id */
      SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
      SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
}

/* ------------------------------------------------------------------
 * Helper: build a sensor-profile frame for BasicTypesMessage
 *   Sensor = Tiny header + Minimal payload (no CRC, no length).
 * ------------------------------------------------------------------ */
static size_t encode_basic_types_sensor(uint8_t* out, size_t out_size) {
  SerializationTestBasicTypesMessage msg;
  memset(&msg, 0, sizeof(msg));
  msg.small_int = 7;

  uint8_t payload[SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAX_SIZE];
  size_t payload_size = SerializationTestBasicTypesMessage_serialize(&msg, payload);

  buffer_writer_t writer;
  buffer_writer_init(&writer, &PROFILE_SENSOR_CONFIG, out, out_size);

  return buffer_writer_write(
      &writer,
      SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID,
      payload, payload_size,
      0, 0, 0, 0,
      SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC1,
      SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MAGIC2);
}

/* ------------------------------------------------------------------
 * Test 1: Standard profile – push bytes one-by-one, last byte completes frame
 * ------------------------------------------------------------------ */
static bool test_streaming_standard_positive(void) {
  uint8_t frame_buf[512];
  size_t frame_size = encode_basic_types_standard(frame_buf, sizeof(frame_buf), 9876);
  if (frame_size == 0) return false;

  uint8_t internal_buf[512];
  accumulating_reader_t reader;
  accumulating_reader_init(&reader, &PROFILE_STANDARD_CONFIG,
                           internal_buf, sizeof(internal_buf), get_message_info);

  frame_msg_info_t result = {false, 0, 0, NULL};

  for (size_t i = 0; i < frame_size; i++) {
    result = accumulating_reader_push_byte(&reader, frame_buf[i]);
    if (i < frame_size - 1) {
      /* Intermediate bytes must not yet produce a complete frame */
      if (result.valid) return false;
    }
  }

  /* The final push_byte should yield a valid frame */
  if (!result.valid) return false;
  if (result.msg_id != SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID) return false;
  if (result.msg_len == 0) return false;

  /* Deserialise and verify the payload field */
  SerializationTestBasicTypesMessage decoded;
  memset(&decoded, 0, sizeof(decoded));
  SerializationTestBasicTypesMessage_deserialize(result.msg_data, result.msg_len, &decoded);
  return decoded.regular_int == 9876;
}

/* ------------------------------------------------------------------
 * Test 2: Sensor profile (minimal, no CRC) – push bytes one-by-one
 * ------------------------------------------------------------------ */
static bool test_streaming_sensor_positive(void) {
  uint8_t frame_buf[512];
  size_t frame_size = encode_basic_types_sensor(frame_buf, sizeof(frame_buf));
  if (frame_size == 0) return false;

  uint8_t internal_buf[512];
  accumulating_reader_t reader;
  accumulating_reader_init(&reader, &PROFILE_SENSOR_CONFIG,
                           internal_buf, sizeof(internal_buf), get_message_info);

  frame_msg_info_t result = {false, 0, 0, NULL};
  for (size_t i = 0; i < frame_size; i++) {
    result = accumulating_reader_push_byte(&reader, frame_buf[i]);
  }

  if (!result.valid) return false;
  if (result.msg_id != SERIALIZATION_TEST_BASIC_TYPES_MESSAGE_MSG_ID) return false;

  return true;
}

/* ------------------------------------------------------------------
 * Test 3: Two consecutive frames decoded from a single push_byte stream
 * ------------------------------------------------------------------ */
static bool test_streaming_two_consecutive_frames(void) {
  uint8_t frame1[512], frame2[512];
  size_t sz1 = encode_basic_types_standard(frame1, sizeof(frame1), 1111);
  size_t sz2 = encode_basic_types_standard(frame2, sizeof(frame2), 2222);
  if (sz1 == 0 || sz2 == 0) return false;

  uint8_t internal_buf[512];
  accumulating_reader_t reader;
  accumulating_reader_init(&reader, &PROFILE_STANDARD_CONFIG,
                           internal_buf, sizeof(internal_buf), get_message_info);

  /* Feed first frame, capturing the result on the last byte */
  frame_msg_info_t r1 = {false, 0, 0, NULL};
  for (size_t i = 0; i < sz1; i++) {
    r1 = accumulating_reader_push_byte(&reader, frame1[i]);
  }
  if (!r1.valid) return false;

  SerializationTestBasicTypesMessage d1;
  memset(&d1, 0, sizeof(d1));
  SerializationTestBasicTypesMessage_deserialize(r1.msg_data, r1.msg_len, &d1);
  if (d1.regular_int != 1111) return false;

  /* Feed second frame */
  frame_msg_info_t r2 = {false, 0, 0, NULL};
  for (size_t i = 0; i < sz2; i++) {
    r2 = accumulating_reader_push_byte(&reader, frame2[i]);
  }
  if (!r2.valid) return false;

  SerializationTestBasicTypesMessage d2;
  memset(&d2, 0, sizeof(d2));
  SerializationTestBasicTypesMessage_deserialize(r2.msg_data, r2.msg_len, &d2);
  return d2.regular_int == 2222;
}

/* ------------------------------------------------------------------
 * Test 4: Garbage bytes before a valid frame are silently discarded
 * ------------------------------------------------------------------ */
static bool test_streaming_skips_garbage_prefix(void) {
  uint8_t frame_buf[512];
  size_t frame_size = encode_basic_types_standard(frame_buf, sizeof(frame_buf), 5555);
  if (frame_size == 0) return false;

  uint8_t internal_buf[512];
  accumulating_reader_t reader;
  accumulating_reader_init(&reader, &PROFILE_STANDARD_CONFIG,
                           internal_buf, sizeof(internal_buf), get_message_info);

  /* Push garbage that doesn't contain a valid start byte sequence */
  uint8_t garbage[] = {0x00, 0x11, 0x22, 0x33, 0x44, 0x55};
  for (size_t i = 0; i < sizeof(garbage); i++) {
    frame_msg_info_t r = accumulating_reader_push_byte(&reader, garbage[i]);
    if (r.valid) return false; /* garbage must not produce a frame */
  }

  /* Now push the real frame */
  frame_msg_info_t result = {false, 0, 0, NULL};
  for (size_t i = 0; i < frame_size; i++) {
    result = accumulating_reader_push_byte(&reader, frame_buf[i]);
  }

  if (!result.valid) return false;

  SerializationTestBasicTypesMessage decoded;
  memset(&decoded, 0, sizeof(decoded));
  SerializationTestBasicTypesMessage_deserialize(result.msg_data, result.msg_len, &decoded);
  return decoded.regular_int == 5555;
}

/* ------------------------------------------------------------------
 * Main
 * ------------------------------------------------------------------ */
int main(void) {
  printf("\n========================================\n");
  printf("STREAMING TESTS - C AccumulatingReader (push_byte)\n");
  printf("========================================\n\n");
  printf("%-65s %s\n", "Test Name", "Result");
  printf("%-65s %s\n",
    "=================================================================", "======");

  run_test("Standard profile: push_byte decodes complete frame",
           test_streaming_standard_positive());
  run_test("Sensor profile: push_byte decodes minimal frame",
           test_streaming_sensor_positive());
  run_test("Two consecutive frames decoded via push_byte",
           test_streaming_two_consecutive_frames());
  run_test("Garbage bytes before frame are silently skipped",
           test_streaming_skips_garbage_prefix());

  printf("\n========================================\n");
  printf("Summary: %d/%d tests passed\n", tests_passed, tests_run);
  printf("========================================\n\n");

  return tests_failed > 0 ? 1 : 0;
}
