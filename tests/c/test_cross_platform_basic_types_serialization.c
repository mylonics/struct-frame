#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "basic_types.sf.h"
#include "basic_frame.h"

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

int create_test_data() {
  BasicTypesBasicTypesMessage msg = {0};

  // Use values from expected_values.json
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

  uint8_t encode_buffer[512];
  basic_frame_encode_buffer_t buffer;
  basic_frame_encode_init(&buffer, encode_buffer, sizeof(encode_buffer));

  bool encoded = basic_frame_encode_msg(&buffer, BASIC_TYPES_BASIC_TYPES_MESSAGE_MSG_ID,
                                         &msg, BASIC_TYPES_BASIC_TYPES_MESSAGE_MAX_SIZE);

  if (!encoded) {
    print_failure_details("Encoding failed", NULL, 0);
    return 0;
  }

  FILE* file = fopen("c_basic_types_test_data.bin", "wb");
  if (!file) {
    print_failure_details("File creation failed", NULL, 0);
    return 0;
  }

  fwrite(encode_buffer, 1, buffer.size, file);
  fclose(file);

  // Self-validate
  basic_frame_msg_info_t decode_result = basic_frame_validate_packet(encode_buffer, buffer.size);
  if (!decode_result.valid) {
    print_failure_details("Self-validation failed", encode_buffer, buffer.size);
    return 0;
  }

  BasicTypesBasicTypesMessage* decoded_msg =
      (BasicTypesBasicTypesMessage*)decode_result.msg_data;

  if (decoded_msg->small_int != -42 || decoded_msg->medium_int != -1000) {
    print_failure_details("Self-verification failed", encode_buffer, buffer.size);
    return 0;
  }

  return 1;
}

int main() {
  printf("\n[TEST START] C Cross-Platform Basic Types Serialization\n");
  
  int success = create_test_data();
  
  const char* status = success ? "PASS" : "FAIL";
  printf("[TEST END] C Cross-Platform Basic Types Serialization: %s\n\n", status);
  
  return success ? 0 : 1;
}
