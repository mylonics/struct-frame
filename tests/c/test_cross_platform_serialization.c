#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "serialization_test.sf.h"
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

int create_test_data() {
  SerializationTestSerializationTestMessage msg = {0};

  // Use values from expected_values.json
  msg.magic_number = 3735928559;  // 0xDEADBEEF
  msg.test_string.length = strlen("Cross-platform test!");
  strncpy(msg.test_string.data, "Cross-platform test!", msg.test_string.length);
  msg.test_float = 3.14159f;
  msg.test_bool = true;
  msg.test_array.count = 3;
  msg.test_array.data[0] = 100;
  msg.test_array.data[1] = 200;
  msg.test_array.data[2] = 300;

  uint8_t encode_buffer[512];
  size_t encoded_size = basic_frame_encode(encode_buffer, sizeof(encode_buffer),
                                           SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                           (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);

  if (encoded_size == 0) {
    print_failure_details("Encoding failed", NULL, 0);
    return 0;
  }

  FILE* file = fopen("c_test_data.bin", "wb");
  if (!file) {
    print_failure_details("File creation failed", NULL, 0);
    return 0;
  }

  fwrite(encode_buffer, 1, encoded_size, file);
  fclose(file);

  // Self-validate
  frame_msg_info_t decode_result = basic_frame_validate_packet(encode_buffer, encoded_size);
  if (!decode_result.valid) {
    print_failure_details("Self-validation failed", encode_buffer, encoded_size);
    return 0;
  }

  SerializationTestSerializationTestMessage* decoded_msg =
      (SerializationTestSerializationTestMessage*)decode_result.msg_data;

  if (decoded_msg->magic_number != 3735928559 || decoded_msg->test_array.count != 3) {
    print_failure_details("Self-verification failed", encode_buffer, encoded_size);
    return 0;
  }

  return 1;
}

int main() {
  printf("\n[TEST START] C Cross-Platform Serialization\n");
  
  int success = create_test_data();
  
  const char* status = success ? "PASS" : "FAIL";
  printf("[TEST END] C Cross-Platform Serialization: %s\n\n", status);
  
  return success ? 0 : 1;
}
