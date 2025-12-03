#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "comprehensive_arrays.sf.h"
#include "frame_parsers.h"

void print_failure_details(const char* label, const void* raw_data, size_t raw_data_size) {
  printf("\n");
  printf("============================================================\n");
  printf("FAILURE DETAILS: %s\n", label);
  printf("============================================================\n");
  
  if (raw_data && raw_data_size > 0) {
    printf("\nRaw Data (%zu bytes):\n  Hex: ", raw_data_size);
    for (size_t i = 0; i < raw_data_size && i < 64; i++) {
      printf("%02x", ((const uint8_t*)raw_data)[i]);
    }
    if (raw_data_size > 64) printf("...");
    printf("\n");
  }
  
  printf("============================================================\n\n");
}

int test_array_operations() {
  ComprehensiveArraysComprehensiveArrayMessage msg = {0};

  msg.fixed_ints[0] = 1;
  msg.fixed_ints[1] = 2;
  msg.fixed_ints[2] = 3;

  msg.fixed_floats[0] = 1.1f;
  msg.fixed_floats[1] = 2.2f;

  msg.fixed_bools[0] = true;
  msg.fixed_bools[1] = false;
  msg.fixed_bools[2] = true;
  msg.fixed_bools[3] = false;

  msg.bounded_uints.count = 3;
  msg.bounded_uints.data[0] = 100;
  msg.bounded_uints.data[1] = 200;
  msg.bounded_uints.data[2] = 300;

  msg.bounded_doubles.count = 2;
  msg.bounded_doubles.data[0] = 123.456;
  msg.bounded_doubles.data[1] = 789.012;

  strncpy(msg.fixed_strings[0], "String1", sizeof(msg.fixed_strings[0]));
  strncpy(msg.fixed_strings[1], "String2", sizeof(msg.fixed_strings[1]));

  msg.bounded_strings.count = 2;
  strncpy(msg.bounded_strings.data[0], "BoundedStr1", sizeof(msg.bounded_strings.data[0]));
  strncpy(msg.bounded_strings.data[1], "BoundedStr2", sizeof(msg.bounded_strings.data[1]));

  msg.fixed_statuses[0] = 1;
  msg.fixed_statuses[1] = 2;

  msg.bounded_statuses.count = 2;
  msg.bounded_statuses.data[0] = 1;
  msg.bounded_statuses.data[1] = 3;

  msg.fixed_sensors[0].id = 1;
  msg.fixed_sensors[0].value = 25.5;
  msg.fixed_sensors[0].status = 1;
  strncpy(msg.fixed_sensors[0].name, "Temp1", 16);

  msg.bounded_sensors.count = 1;
  msg.bounded_sensors.data[0].id = 3;
  msg.bounded_sensors.data[0].value = 15.5;
  msg.bounded_sensors.data[0].status = 2;
  strncpy(msg.bounded_sensors.data[0].name, "Pressure", 16);

  // Encode message into BasicFrame format
  uint8_t encode_buffer[1024];
  size_t encoded_size = basic_frame_encode(encode_buffer, sizeof(encode_buffer),
                                           COMPREHENSIVE_ARRAYS_COMPREHENSIVE_ARRAY_MESSAGE_MSG_ID,
                                           (const uint8_t*)&msg, COMPREHENSIVE_ARRAYS_COMPREHENSIVE_ARRAY_MESSAGE_MAX_SIZE);

  if (encoded_size == 0) {
    print_failure_details("Encoding failed", NULL, 0);
    return 0;
  }

  // Validate and decode the BasicFrame
  frame_msg_info_t decode_result = basic_frame_validate_packet(encode_buffer, encoded_size);
  if (!decode_result.valid) {
    print_failure_details("Validation failed", encode_buffer, encoded_size);
    return 0;
  }

  ComprehensiveArraysComprehensiveArrayMessage* decoded_msg = 
      (ComprehensiveArraysComprehensiveArrayMessage*)decode_result.msg_data;

  // Compare original and decoded messages
  if (decoded_msg->fixed_ints[0] != msg.fixed_ints[0]) {
    print_failure_details("Value mismatch: fixed_ints[0]", encode_buffer, encoded_size);
    return 0;
  }

  if (decoded_msg->bounded_uints.count != msg.bounded_uints.count) {
    print_failure_details("Value mismatch: bounded_uints.count", encode_buffer, encoded_size);
    return 0;
  }

  if (decoded_msg->bounded_uints.data[0] != msg.bounded_uints.data[0]) {
    print_failure_details("Value mismatch: bounded_uints.data[0]", encode_buffer, encoded_size);
    return 0;
  }

  if (decoded_msg->fixed_sensors[0].id != msg.fixed_sensors[0].id) {
    print_failure_details("Value mismatch: fixed_sensors[0].id", encode_buffer, encoded_size);
    return 0;
  }

  return 1;
}

int main() {
  printf("\n[TEST START] C Array Operations\n");
  
  int success = test_array_operations();
  
  const char* status = success ? "PASS" : "FAIL";
  printf("[TEST END] C Array Operations: %s\n\n", status);
  
  return success ? 0 : 1;
}
