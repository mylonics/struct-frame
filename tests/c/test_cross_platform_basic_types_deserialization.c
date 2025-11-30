#include <math.h>
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

int validate_message(BasicTypesBasicTypesMessage* msg) {
  // Expected values from expected_values.json
  if (msg->small_int != -42) {
    printf("  Value mismatch: small_int (expected -42, got %d)\n", msg->small_int);
    return 0;
  }

  if (msg->medium_int != -1000) {
    printf("  Value mismatch: medium_int (expected -1000, got %d)\n", msg->medium_int);
    return 0;
  }

  if (msg->regular_int != -100000) {
    printf("  Value mismatch: regular_int (expected -100000, got %d)\n", msg->regular_int);
    return 0;
  }

  if (msg->large_int != -1000000000LL) {
    printf("  Value mismatch: large_int (expected -1000000000, got %lld)\n", (long long)msg->large_int);
    return 0;
  }

  if (msg->small_uint != 255) {
    printf("  Value mismatch: small_uint (expected 255, got %u)\n", msg->small_uint);
    return 0;
  }

  if (msg->medium_uint != 65535) {
    printf("  Value mismatch: medium_uint (expected 65535, got %u)\n", msg->medium_uint);
    return 0;
  }

  if (fabs(msg->single_precision - 3.14159f) > 0.0001f) {
    printf("  Value mismatch: single_precision (expected 3.14159, got %f)\n", msg->single_precision);
    return 0;
  }

  if (msg->flag != true) {
    printf("  Value mismatch: flag (expected true, got false)\n");
    return 0;
  }

  return 1;
}

int read_and_validate_test_data(const char* filename) {
  FILE* file = fopen(filename, "rb");
  if (!file) {
    printf("  Error: file not found: %s\n", filename);
    return 0;
  }

  uint8_t buffer[512];
  size_t size = fread(buffer, 1, sizeof(buffer), file);
  fclose(file);

  if (size == 0) {
    print_failure_details("Empty file", buffer, size);
    return 0;
  }

  basic_frame_msg_info_t decode_result = basic_frame_validate_packet(buffer, size);

  if (!decode_result.valid) {
    print_failure_details("Failed to decode data", buffer, size);
    return 0;
  }

  BasicTypesBasicTypesMessage* decoded_msg =
      (BasicTypesBasicTypesMessage*)decode_result.msg_data;

  if (!validate_message(decoded_msg)) {
    printf("  Validation failed\n");
    return 0;
  }

  printf("  [OK] Data validated successfully\n");
  return 1;
}

int main(int argc, char* argv[]) {
  printf("\n[TEST START] C Cross-Platform Basic Types Deserialization\n");

  if (argc != 2) {
    printf("  Usage: %s <binary_file>\n", argv[0]);
    printf("[TEST END] C Cross-Platform Basic Types Deserialization: FAIL\n\n");
    return 1;
  }

  int success = read_and_validate_test_data(argv[1]);

  const char* status = success ? "PASS" : "FAIL";
  printf("[TEST END] C Cross-Platform Basic Types Deserialization: %s\n\n", status);

  return success ? 0 : 1;
}
