#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "basic_types.sf.h"
#include "frame_parsers.h"

void print_failure_details(const char* label, const BasicTypesBasicTypesMessage* expected, 
                          const BasicTypesBasicTypesMessage* actual, 
                          const uint8_t* raw_data, size_t raw_data_size) {
  printf("\n");
  printf("============================================================\n");
  printf("FAILURE DETAILS: %s\n", label);
  printf("============================================================\n");
  
  if (expected && actual) {
    printf("\nExpected Values:\n");
    printf("  small_int: %d\n", expected->small_int);
    printf("  medium_int: %d\n", expected->medium_int);
    printf("  regular_int: %d\n", expected->regular_int);
    printf("  large_int: %lld\n", (long long)expected->large_int);
    printf("  flag: %s\n", expected->flag ? "true" : "false");
    
    printf("\nActual Values:\n");
    printf("  small_int: %d\n", actual->small_int);
    printf("  medium_int: %d\n", actual->medium_int);
    printf("  regular_int: %d\n", actual->regular_int);
    printf("  large_int: %lld\n", (long long)actual->large_int);
    printf("  flag: %s\n", actual->flag ? "true" : "false");
  }
  
  if (raw_data && raw_data_size > 0) {
    printf("\nRaw Data (%zu bytes):\n  Hex: ", raw_data_size);
    for (size_t i = 0; i < raw_data_size && i < 64; i++) {
      printf("%02x", raw_data[i]);
    }
    if (raw_data_size > 64) printf("...");
    printf("\n");
  }
  
  printf("============================================================\n\n");
}

int test_basic_types() {
  BasicTypesBasicTypesMessage msg = {0};

  msg.small_int = -42;
  msg.medium_int = -1000;
  msg.regular_int = -100000;
  msg.large_int = -1000000000LL;
  msg.small_uint = 255;
  msg.medium_uint = 65535;
  msg.regular_uint = 4294967295U;
  msg.large_uint = 18446744073709551615ULL;
  msg.single_precision = 3.14159f;
  msg.double_precision = 2.718281828459045;
  msg.flag = true;
  strncpy(msg.device_id, "TEST_DEVICE_12345678901234567890", 32);
  msg.description.length = strlen("Test description for basic types");
  strncpy(msg.description.data, "Test description for basic types", msg.description.length);

  // Encode message into BasicFrame format
  uint8_t encode_buffer[1024];
  size_t encoded_size = basic_frame_encode(encode_buffer, sizeof(encode_buffer),
                                           BASIC_TYPES_BASIC_TYPES_MESSAGE_MSG_ID,
                                           (const uint8_t*)&msg, BASIC_TYPES_BASIC_TYPES_MESSAGE_MAX_SIZE);

  if (encoded_size == 0) {
    print_failure_details("Encoding failed", &msg, NULL, NULL, 0);
    return 0;
  }

  // Validate and decode the BasicFrame
  frame_msg_info_t decode_result = basic_frame_validate_packet(encode_buffer, encoded_size);
  if (!decode_result.valid) {
    print_failure_details("Validation failed", &msg, NULL, encode_buffer, encoded_size);
    return 0;
  }

  BasicTypesBasicTypesMessage* decoded_msg = (BasicTypesBasicTypesMessage*)decode_result.msg_data;

  // Compare original and decoded messages
  if (decoded_msg->small_int != msg.small_int) {
    print_failure_details("Value mismatch: small_int", &msg, decoded_msg, encode_buffer, encoded_size);
    return 0;
  }

  if (decoded_msg->medium_int != msg.medium_int) {
    print_failure_details("Value mismatch: medium_int", &msg, decoded_msg, encode_buffer, encoded_size);
    return 0;
  }
  
  if (decoded_msg->flag != msg.flag) {
    print_failure_details("Value mismatch: flag", &msg, decoded_msg, encode_buffer, encoded_size);
    return 0;
  }

  if (decoded_msg->single_precision != msg.single_precision) {
    print_failure_details("Value mismatch: single_precision", &msg, decoded_msg, encode_buffer, encoded_size);
    return 0;
  }

  return 1;
}

int main() {
  printf("\n[TEST START] C Basic Types\n");
  
  int success = test_basic_types();
  
  const char* status = success ? "PASS" : "FAIL";
  printf("[TEST END] C Basic Types: %s\n\n", status);
  
  return success ? 0 : 1;
}
