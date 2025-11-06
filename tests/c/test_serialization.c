#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "serialization_test.sf.h"
#include "struct_frame_default_frame.h"

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

  msg.magic_number = 0xDEADBEEF;
  msg.test_string.length = strlen("Hello from C!");
  strncpy(msg.test_string.data, "Hello from C!", msg.test_string.length);
  msg.test_float = 3.14159f;
  msg.test_bool = true;
  msg.test_array.count = 3;
  msg.test_array.data[0] = 100;
  msg.test_array.data[1] = 200;
  msg.test_array.data[2] = 300;

  uint8_t encode_buffer[512];
  msg_encode_buffer buffer = {0};
  buffer.data = encode_buffer;

  packet_format_t* format = &default_frame_format;
  bool encoded = serialization_test_serialization_test_message_encode(&buffer, format, &msg);

  if (!encoded) {
    print_failure_details("Encoding failed", NULL, 0);
    return 0;
  }

  FILE* file = fopen("c_test_data.bin", "wb");
  if (!file) {
    print_failure_details("File creation failed", NULL, 0);
    return 0;
  }

  fwrite(encode_buffer, 1, buffer.size, file);
  fclose(file);

  msg_info_t decode_result = format->validate_packet(encode_buffer, buffer.size);
  if (!decode_result.valid) {
    print_failure_details("Self-validation failed", encode_buffer, buffer.size);
    return 0;
  }

  SerializationTestSerializationTestMessage decoded_msg =
      serialization_test_serialization_test_message_get(decode_result);

  if (decoded_msg.magic_number != 0xDEADBEEF || decoded_msg.test_array.count != 3) {
    print_failure_details("Self-verification failed", encode_buffer, buffer.size);
    return 0;
  }

  return 1;
}

int read_test_data(const char* filename, const char* language) {
  FILE* file = fopen(filename, "rb");
  if (!file) {
    return 1;  // Skip if file not available
  }

  uint8_t buffer[512];
  size_t size = fread(buffer, 1, sizeof(buffer), file);
  fclose(file);

  if (size == 0) {
    print_failure_details("Empty file", buffer, size);
    return 0;
  }

  packet_format_t* format = &default_frame_format;
  msg_info_t decode_result = format->validate_packet(buffer, size);

  if (!decode_result.valid) {
    char label[256];
    snprintf(label, sizeof(label), "Failed to decode %s data", language);
    print_failure_details(label, buffer, size);
    return 0;
  }

  return 1;
}

int main() {
  printf("\n[TEST START] C Cross-Language Serialization\n");
  
  int success = create_test_data();
  if (success) {
    success = success && read_test_data("python_test_data.bin", "Python");
    success = success && read_test_data("typescript_test_data.bin", "TypeScript");
  }
  
  const char* status = success ? "PASS" : "FAIL";
  printf("[TEST END] C Cross-Language Serialization: %s\n\n", status);
  
  return success ? 0 : 1;
}
