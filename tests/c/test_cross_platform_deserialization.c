#include <math.h>
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

int validate_message(SerializationTestSerializationTestMessage* msg) {
  // Expected values from expected_values.json
  uint32_t expected_magic = 3735928559;  // 0xDEADBEEF
  const char* expected_string = "Cross-platform test!";
  float expected_float = 3.14159f;
  bool expected_bool = true;
  int expected_array[3] = {100, 200, 300};

  if (msg->magic_number != expected_magic) {
    printf("  Value mismatch: magic_number (expected %u, got %u)\n", expected_magic, msg->magic_number);
    return 0;
  }

  if (strncmp(msg->test_string.data, expected_string, msg->test_string.length) != 0) {
    printf("  Value mismatch: test_string\n");
    return 0;
  }

  if (fabs(msg->test_float - expected_float) > 0.0001f) {
    printf("  Value mismatch: test_float (expected %f, got %f)\n", expected_float, msg->test_float);
    return 0;
  }

  if (msg->test_bool != expected_bool) {
    printf("  Value mismatch: test_bool\n");
    return 0;
  }

  if (msg->test_array.count != 3) {
    printf("  Value mismatch: test_array.count (expected 3, got %u)\n", msg->test_array.count);
    return 0;
  }

  for (int i = 0; i < 3; i++) {
    if (msg->test_array.data[i] != expected_array[i]) {
      printf("  Value mismatch: test_array[%d] (expected %d, got %d)\n", i, expected_array[i], msg->test_array.data[i]);
      return 0;
    }
  }

  return 1;
}

// Return values: 1 = validated successfully, 0 = validation failed, -1 = skipped (file not found)
int read_and_validate_test_data(const char* filename, const char* language) {
  FILE* file = fopen(filename, "rb");
  if (!file) {
    printf("  Skipping %s - file not found: %s\n", language, filename);
    return -1;  // Skip if file not available
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

  SerializationTestSerializationTestMessage decoded_msg =
      serialization_test_serialization_test_message_get(decode_result);

  if (!validate_message(&decoded_msg)) {
    printf("  Validation failed for %s data\n", language);
    return 0;
  }

  printf("  [OK] %s data validated successfully\n", language);
  return 1;
}

int main() {
  printf("\n[TEST START] C Cross-Platform Deserialization\n");

  int any_failed = 0;
  int validated_count = 0;
  int result;

  result = read_and_validate_test_data("python_test_data.bin", "Python");
  if (result == 0) any_failed = 1;
  if (result == 1) validated_count++;

  result = read_and_validate_test_data("c_test_data.bin", "C");
  if (result == 0) any_failed = 1;
  if (result == 1) validated_count++;

  result = read_and_validate_test_data("cpp_test_data.bin", "C++");
  if (result == 0) any_failed = 1;
  if (result == 1) validated_count++;

  result = read_and_validate_test_data("typescript_test_data.bin", "TypeScript");
  if (result == 0) any_failed = 1;
  if (result == 1) validated_count++;

  int success = !any_failed && (validated_count > 0);

  if (validated_count == 0) {
    printf("  [WARN] No files were validated - at least one input file is required\n");
  } else {
    printf("  Validated %d file(s) successfully\n", validated_count);
  }

  const char* status = success ? "PASS" : "FAIL";
  printf("[TEST END] C Cross-Platform Deserialization: %s\n\n", status);

  return success ? 0 : 1;
}
