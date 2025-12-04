/**
 * Frame format deserialization test for C.
 * 
 * This test reads binary files and deserializes using different frame formats.
 * Usage: test_frame_format_deserialization <frame_format> <binary_file>
 */

#include <math.h>
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

typedef frame_msg_info_t (*validate_func_t)(const uint8_t* buffer, size_t length);

typedef struct {
  const char* name;
  validate_func_t validate;
} frame_format_entry_t;

// Frame format registry
static const frame_format_entry_t frame_formats[] = {
  {"basic_default", basic_default_validate_packet},
  {"basic_minimal", basic_minimal_validate_packet},
  {"basic_seq", basic_seq_validate_packet},
  {"basic_sys_comp", basic_sys_comp_validate_packet},
  {"basic_extended_msg_ids", basic_extended_msg_ids_validate_packet},
  {"basic_extended_length", basic_extended_length_validate_packet},
  {"basic_extended", basic_extended_validate_packet},
  {"basic_multi_system_stream", basic_multi_system_stream_validate_packet},
  {"basic_extended_multi_system_stream", basic_extended_multi_system_stream_validate_packet},
  {"tiny_default", tiny_default_validate_packet},
  {"tiny_minimal", tiny_minimal_validate_packet},
  {"tiny_seq", tiny_seq_validate_packet},
  {"tiny_sys_comp", tiny_sys_comp_validate_packet},
  {"tiny_extended_msg_ids", tiny_extended_msg_ids_validate_packet},
  {"tiny_extended_length", tiny_extended_length_validate_packet},
  {"tiny_extended", tiny_extended_validate_packet},
  {"tiny_multi_system_stream", tiny_multi_system_stream_validate_packet},
  {"tiny_extended_multi_system_stream", tiny_extended_multi_system_stream_validate_packet},
  {NULL, NULL}
};

const frame_format_entry_t* find_frame_format(const char* name) {
  for (int i = 0; frame_formats[i].name != NULL; i++) {
    if (strcmp(frame_formats[i].name, name) == 0) {
      return &frame_formats[i];
    }
  }
  return NULL;
}

int read_and_validate_test_data(const char* frame_format, const char* filename) {
  const frame_format_entry_t* ff = find_frame_format(frame_format);
  if (ff == NULL) {
    printf("  Unknown frame format: %s\n", frame_format);
    return 0;
  }

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

  frame_msg_info_t decode_result = ff->validate(buffer, size);

  if (!decode_result.valid) {
    print_failure_details("Failed to decode data", buffer, size);
    return 0;
  }

  SerializationTestSerializationTestMessage* decoded_msg =
      (SerializationTestSerializationTestMessage*)decode_result.msg_data;

  if (!validate_message(decoded_msg)) {
    printf("  Validation failed\n");
    return 0;
  }

  printf("  [OK] Data validated successfully with %s format\n", frame_format);
  return 1;
}

int main(int argc, char* argv[]) {
  printf("\n[TEST START] C Frame Format Deserialization\n");

  if (argc != 3) {
    printf("  Usage: %s <frame_format> <binary_file>\n", argv[0]);
    printf("  Supported formats:\n");
    for (int i = 0; frame_formats[i].name != NULL; i++) {
      printf("    %s\n", frame_formats[i].name);
    }
    printf("[TEST END] C Frame Format Deserialization: FAIL\n\n");
    return 1;
  }

  int success = read_and_validate_test_data(argv[1], argv[2]);

  const char* status = success ? "PASS" : "FAIL";
  printf("[TEST END] C Frame Format Deserialization: %s\n\n", status);

  return success ? 0 : 1;
}
