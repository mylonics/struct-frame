#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "comprehensive_arrays.sf.h"
#include "struct_frame_default_frame.h"

#define FLOAT_TOLERANCE 0.0001f

// Debug printing function for ComprehensiveArrayMessage
void print_arrays_message(const char* label, const ComprehensiveArraysComprehensiveArrayMessage* msg) {
  printf("=== %s ===\n", label);

  printf("Fixed arrays:\n");
  printf("  fixed_ints: [");
  for (int i = 0; i < 3; i++) {
    printf("%d", msg->fixed_ints[i]);
    if (i < 2) printf(", ");
  }
  printf("]\n");

  printf("  fixed_floats: [");
  for (int i = 0; i < 2; i++) {
    printf("%.6f", msg->fixed_floats[i]);
    if (i < 1) printf(", ");
  }
  printf("]\n");

  printf("  fixed_bools: [");
  for (int i = 0; i < 4; i++) {
    printf("%s", msg->fixed_bools[i] ? "true" : "false");
    if (i < 3) printf(", ");
  }
  printf("]\n");

  printf("Bounded arrays:\n");
  printf("  bounded_uints: count=%d, data=[", msg->bounded_uints.count);
  for (int i = 0; i < msg->bounded_uints.count; i++) {
    printf("%u", msg->bounded_uints.data[i]);
    if (i < msg->bounded_uints.count - 1) printf(", ");
  }
  printf("]\n");

  printf("  bounded_doubles: count=%d, data=[", msg->bounded_doubles.count);
  for (int i = 0; i < msg->bounded_doubles.count; i++) {
    printf("%.6f", msg->bounded_doubles.data[i]);
    if (i < msg->bounded_doubles.count - 1) printf(", ");
  }
  printf("]\n");

  printf("String arrays:\n");
  printf("  fixed_strings: [");
  for (int i = 0; i < 2; i++) {
    printf("'%s'", msg->fixed_strings[i]);
    if (i < 1) printf(", ");
  }
  printf("]\n");

  printf("  bounded_strings: count=%d, data=[", msg->bounded_strings.count);
  for (int i = 0; i < msg->bounded_strings.count; i++) {
    printf("'%s'", msg->bounded_strings.data[i]);
    if (i < msg->bounded_strings.count - 1) printf(", ");
  }
  printf("]\n");

  printf("Enum arrays:\n");
  printf("  fixed_statuses: [%d, %d]\n", msg->fixed_statuses[0], msg->fixed_statuses[1]);
  printf("  bounded_statuses: count=%d, data=[", msg->bounded_statuses.count);
  for (int i = 0; i < msg->bounded_statuses.count; i++) {
    printf("%d", msg->bounded_statuses.data[i]);
    if (i < msg->bounded_statuses.count - 1) printf(", ");
  }
  printf("]\n");

  printf("Sensor arrays:\n");
  printf("  fixed_sensors[0]: id=%d, value=%.2f, status=%d, name='%s'\n", msg->fixed_sensors[0].id,
         msg->fixed_sensors[0].value, msg->fixed_sensors[0].status, msg->fixed_sensors[0].name);

  printf("  bounded_sensors: count=%d\n", msg->bounded_sensors.count);
  for (int i = 0; i < msg->bounded_sensors.count; i++) {
    printf("    [%d]: id=%d, value=%.2f, status=%d, name='%s'\n", i, msg->bounded_sensors.data[i].id,
           msg->bounded_sensors.data[i].value, msg->bounded_sensors.data[i].status, msg->bounded_sensors.data[i].name);
  }
  printf("\n");
}

#define ASSERT_ARRAYS_WITH_DEBUG(condition, msg1, msg2) \
  do {                                                  \
    if (!(condition)) {                                 \
      printf("❌ ASSERTION FAILED: %s\n", #condition);  \
      print_arrays_message("ORIGINAL MESSAGE", msg1);   \
      print_arrays_message("DECODED MESSAGE", msg2);    \
      assert(condition);                                \
    }                                                   \
  } while (0)

int test_array_operations() {
  printf("Testing Array Operations C Implementation...\n");

  ComprehensiveArraysComprehensiveArrayMessage msg = {0};

  // Test fixed arrays
  msg.fixed_ints[0] = 1;
  msg.fixed_ints[1] = 2;
  msg.fixed_ints[2] = 3;

  msg.fixed_floats[0] = 1.1f;
  msg.fixed_floats[1] = 2.2f;

  msg.fixed_bools[0] = true;
  msg.fixed_bools[1] = false;
  msg.fixed_bools[2] = true;
  msg.fixed_bools[3] = false;

  // Test bounded arrays
  msg.bounded_uints.count = 2;
  msg.bounded_uints.data[0] = 100;
  msg.bounded_uints.data[1] = 200;

  msg.bounded_doubles.count = 1;
  msg.bounded_doubles.data[0] = 123.456;

  // Test fixed string array
  strncpy(msg.fixed_strings[0], "String1", 8);
  strncpy(msg.fixed_strings[1], "String2", 8);

  // Test bounded string array
  msg.bounded_strings.count = 1;
  strncpy(msg.bounded_strings.data[0], "BoundedStr1", 12);

  // Test enum arrays
  msg.fixed_statuses[0] = COMPREHENSIVE_ARRAYS_STATUS_ACTIVE;
  msg.fixed_statuses[1] = COMPREHENSIVE_ARRAYS_STATUS_ERROR;

  msg.bounded_statuses.count = 1;
  msg.bounded_statuses.data[0] = COMPREHENSIVE_ARRAYS_STATUS_ACTIVE;

  // Test nested message arrays
  msg.fixed_sensors[0].id = 1;
  msg.fixed_sensors[0].value = 25.5f;
  msg.fixed_sensors[0].status = COMPREHENSIVE_ARRAYS_STATUS_ACTIVE;
  strncpy(msg.fixed_sensors[0].name, "Temp1", 16);

  msg.bounded_sensors.count = 1;
  msg.bounded_sensors.data[0].id = 3;
  msg.bounded_sensors.data[0].value = 15.5f;
  msg.bounded_sensors.data[0].status = COMPREHENSIVE_ARRAYS_STATUS_ERROR;
  strncpy(msg.bounded_sensors.data[0].name, "Pressure", 16);

  // Create encoding buffer
  uint8_t encode_buffer[2048];  // Larger buffer for arrays
  msg_encode_buffer buffer = {0};
  buffer.data = encode_buffer;

  // Encode the message
  packet_format_t* format = &default_frame_format;
  bool encoded = comprehensive_arrays_comprehensive_array_message_encode(&buffer, format, &msg);

  if (!encoded) {
    printf("❌ Failed to encode array message\n");
    return 0;
  }

  printf("✅ Array message encoded successfully, size: %d bytes\n", buffer.size);

  // Decode the message
  msg_info_t decode_result = format->validate_packet(encode_buffer, buffer.size);

  if (!decode_result.valid) {
    printf("❌ Failed to validate array packet\n");
    return 0;
  }

  // Get decoded message
  ComprehensiveArraysComprehensiveArrayMessage decoded_msg =
      comprehensive_arrays_comprehensive_array_message_get(decode_result);

  // Verify fixed arrays
  for (int i = 0; i < 3; i++) {
    ASSERT_ARRAYS_WITH_DEBUG(decoded_msg.fixed_ints[i] == i + 1, &msg, &decoded_msg);
  }

  ASSERT_ARRAYS_WITH_DEBUG(fabsf(decoded_msg.fixed_floats[0] - 1.1f) < FLOAT_TOLERANCE, &msg, &decoded_msg);
  ASSERT_ARRAYS_WITH_DEBUG(fabsf(decoded_msg.fixed_floats[1] - 2.2f) < FLOAT_TOLERANCE, &msg, &decoded_msg);

  // Verify bounded arrays
  ASSERT_ARRAYS_WITH_DEBUG(decoded_msg.bounded_uints.count == 2, &msg, &decoded_msg);
  ASSERT_ARRAYS_WITH_DEBUG(decoded_msg.bounded_uints.data[0] == 100, &msg, &decoded_msg);
  ASSERT_ARRAYS_WITH_DEBUG(decoded_msg.bounded_uints.data[1] == 200, &msg, &decoded_msg);

  // Verify string arrays
  ASSERT_ARRAYS_WITH_DEBUG(strcmp(decoded_msg.fixed_strings[0], "String1") == 0, &msg, &decoded_msg);
  ASSERT_ARRAYS_WITH_DEBUG(strcmp(decoded_msg.fixed_strings[1], "String2") == 0, &msg, &decoded_msg);

  ASSERT_ARRAYS_WITH_DEBUG(decoded_msg.bounded_strings.count == 1, &msg, &decoded_msg);
  ASSERT_ARRAYS_WITH_DEBUG(strcmp(decoded_msg.bounded_strings.data[0], "BoundedStr1") == 0, &msg, &decoded_msg);

  // Verify enum arrays
  ASSERT_ARRAYS_WITH_DEBUG(decoded_msg.fixed_statuses[0] == COMPREHENSIVE_ARRAYS_STATUS_ACTIVE, &msg, &decoded_msg);
  ASSERT_ARRAYS_WITH_DEBUG(decoded_msg.fixed_statuses[1] == COMPREHENSIVE_ARRAYS_STATUS_ERROR, &msg, &decoded_msg);

  // Verify nested message arrays
  ASSERT_ARRAYS_WITH_DEBUG(decoded_msg.fixed_sensors[0].id == 1, &msg, &decoded_msg);
  ASSERT_ARRAYS_WITH_DEBUG(fabsf(decoded_msg.fixed_sensors[0].value - 25.5f) < FLOAT_TOLERANCE, &msg, &decoded_msg);
  ASSERT_ARRAYS_WITH_DEBUG(strcmp(decoded_msg.fixed_sensors[0].name, "Temp1") == 0, &msg, &decoded_msg);

  ASSERT_ARRAYS_WITH_DEBUG(decoded_msg.bounded_sensors.count == 1, &msg, &decoded_msg);
  ASSERT_ARRAYS_WITH_DEBUG(decoded_msg.bounded_sensors.data[0].id == 3, &msg, &decoded_msg);
  ASSERT_ARRAYS_WITH_DEBUG(fabsf(decoded_msg.bounded_sensors.data[0].value - 15.5f) < FLOAT_TOLERANCE, &msg,
                           &decoded_msg);
  ASSERT_ARRAYS_WITH_DEBUG(strcmp(decoded_msg.bounded_sensors.data[0].name, "Pressure") == 0, &msg, &decoded_msg);

  printf("✅ All array serialization/deserialization tests passed!\n");
  return 1;
}

int main() {
  printf("=== C Array Operations Test ===\n");

  if (!test_array_operations()) {
    printf("❌ Array tests failed\n");
    return 1;
  }

  printf("🎉 All C array tests completed successfully!\n");
  return 0;
}