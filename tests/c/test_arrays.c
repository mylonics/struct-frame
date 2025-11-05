#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "comprehensive_arrays.sf.h"
#include "struct_frame_default_frame.h"

#define FLOAT_TOLERANCE 0.0001f

int test_array_operations() {
  printf("Testing Array Operations C Implementation...\n");

  ComprehensiveArraysComprehensiveArrayMessage msg = {0};

  // Test fixed arrays
  msg.fixed_ints[0] = 1;
  msg.fixed_ints[1] = 2;
  msg.fixed_ints[2] = 3;
  msg.fixed_ints[3] = 4;
  msg.fixed_ints[4] = 5;

  msg.fixed_floats[0] = 1.1f;
  msg.fixed_floats[1] = 2.2f;
  msg.fixed_floats[2] = 3.3f;

  msg.fixed_bools[0] = true;
  msg.fixed_bools[1] = false;
  msg.fixed_bools[2] = true;
  msg.fixed_bools[3] = false;
  msg.fixed_bools[4] = true;
  msg.fixed_bools[5] = false;
  msg.fixed_bools[6] = true;
  msg.fixed_bools[7] = false;

  // Test bounded arrays
  msg.bounded_uints.count = 3;
  msg.bounded_uints.data[0] = 100;
  msg.bounded_uints.data[1] = 200;
  msg.bounded_uints.data[2] = 300;

  msg.bounded_doubles.count = 2;
  msg.bounded_doubles.data[0] = 123.456;
  msg.bounded_doubles.data[1] = 789.012;

  // Test fixed string array
  strncpy(msg.fixed_strings[0], "String1", 20);
  strncpy(msg.fixed_strings[1], "String2", 20);
  strncpy(msg.fixed_strings[2], "String3", 20);
  strncpy(msg.fixed_strings[3], "String4", 20);

  // Test bounded string array
  msg.bounded_strings.count = 2;
  strncpy(msg.bounded_strings.data[0], "BoundedStr1", 32);
  strncpy(msg.bounded_strings.data[1], "BoundedStr2", 32);

  // Test enum arrays
  msg.fixed_statuses[0] = COMPREHENSIVE_ARRAYS_STATUS_ACTIVE;
  msg.fixed_statuses[1] = COMPREHENSIVE_ARRAYS_STATUS_ERROR;
  msg.fixed_statuses[2] = COMPREHENSIVE_ARRAYS_STATUS_INACTIVE;

  msg.bounded_statuses.count = 2;
  msg.bounded_statuses.data[0] = COMPREHENSIVE_ARRAYS_STATUS_ACTIVE;
  msg.bounded_statuses.data[1] = COMPREHENSIVE_ARRAYS_STATUS_MAINTENANCE;

  // Test nested message arrays
  msg.fixed_sensors[0].id = 1;
  msg.fixed_sensors[0].value = 25.5f;
  msg.fixed_sensors[0].status = COMPREHENSIVE_ARRAYS_STATUS_ACTIVE;
  strncpy(msg.fixed_sensors[0].name, "Temp1", 16);

  msg.fixed_sensors[1].id = 2;
  msg.fixed_sensors[1].value = 30.0f;
  msg.fixed_sensors[1].status = COMPREHENSIVE_ARRAYS_STATUS_ACTIVE;
  strncpy(msg.fixed_sensors[1].name, "Temp2", 16);

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
  for (int i = 0; i < 5; i++) {
    assert(decoded_msg.fixed_ints[i] == i + 1);
  }

  assert(fabsf(decoded_msg.fixed_floats[0] - 1.1f) < FLOAT_TOLERANCE);
  assert(fabsf(decoded_msg.fixed_floats[1] - 2.2f) < FLOAT_TOLERANCE);
  assert(fabsf(decoded_msg.fixed_floats[2] - 3.3f) < FLOAT_TOLERANCE);

  // Verify bounded arrays
  assert(decoded_msg.bounded_uints.count == 3);
  assert(decoded_msg.bounded_uints.data[0] == 100);
  assert(decoded_msg.bounded_uints.data[1] == 200);
  assert(decoded_msg.bounded_uints.data[2] == 300);

  // Verify string arrays
  assert(strcmp(decoded_msg.fixed_strings[0], "String1") == 0);
  assert(strcmp(decoded_msg.fixed_strings[1], "String2") == 0);

  assert(decoded_msg.bounded_strings.count == 2);
  assert(strcmp(decoded_msg.bounded_strings.data[0], "BoundedStr1") == 0);
  assert(strcmp(decoded_msg.bounded_strings.data[1], "BoundedStr2") == 0);

  // Verify enum arrays
  assert(decoded_msg.fixed_statuses[0] == COMPREHENSIVE_ARRAYS_STATUS_ACTIVE);
  assert(decoded_msg.fixed_statuses[1] == COMPREHENSIVE_ARRAYS_STATUS_ERROR);

  // Verify nested message arrays
  assert(decoded_msg.fixed_sensors[0].id == 1);
  assert(fabsf(decoded_msg.fixed_sensors[0].value - 25.5f) < FLOAT_TOLERANCE);
  assert(strcmp(decoded_msg.fixed_sensors[0].name, "Temp1") == 0);

  assert(decoded_msg.bounded_sensors.count == 1);
  assert(decoded_msg.bounded_sensors.data[0].id == 3);
  assert(fabsf(decoded_msg.bounded_sensors.data[0].value - 15.5f) < FLOAT_TOLERANCE);
  assert(strcmp(decoded_msg.bounded_sensors.data[0].name, "Pressure") == 0);

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