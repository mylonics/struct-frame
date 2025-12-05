/**
 * Test runner entry point for C.
 *
 * Usage:
 *   test_runner encode <frame_format> <output_file>
 *   test_runner decode <frame_format> <input_file>
 *
 * Frame formats: basic_default, basic_minimal, tiny_default, tiny_minimal
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "test_codec.h"

#define MAX_BUFFER_SIZE 512

static void print_usage(const char* program_name) {
  printf("Usage:\n");
  printf("  %s encode <frame_format> <output_file>\n", program_name);
  printf("  %s decode <frame_format> <input_file>\n", program_name);
  printf("\nFrame formats: basic_default, basic_minimal, tiny_default, tiny_minimal\n");
}

static void print_hex(const uint8_t* data, size_t size) {
  printf("  Hex (%zu bytes): ", size);
  for (size_t i = 0; i < size && i < 64; i++) {
    printf("%02x", data[i]);
  }
  if (size > 64) printf("...");
  printf("\n");
}

static int run_encode(const char* format, const char* output_file) {
  uint8_t buffer[MAX_BUFFER_SIZE];
  size_t encoded_size = 0;

  printf("[ENCODE] Format: %s\n", format);

  if (!encode_test_message(format, buffer, sizeof(buffer), &encoded_size)) {
    printf("[ENCODE] FAILED: Encoding error\n");
    return 1;
  }

  FILE* file = fopen(output_file, "wb");
  if (!file) {
    printf("[ENCODE] FAILED: Cannot create output file: %s\n", output_file);
    return 1;
  }

  fwrite(buffer, 1, encoded_size, file);
  fclose(file);

  printf("[ENCODE] SUCCESS: Wrote %zu bytes to %s\n", encoded_size, output_file);
  return 0;
}

static int run_decode(const char* format, const char* input_file) {
  uint8_t buffer[MAX_BUFFER_SIZE];
  SerializationTestSerializationTestMessage msg;

  printf("[DECODE] Format: %s, File: %s\n", format, input_file);

  FILE* file = fopen(input_file, "rb");
  if (!file) {
    printf("[DECODE] FAILED: Cannot open input file: %s\n", input_file);
    return 1;
  }

  size_t size = fread(buffer, 1, sizeof(buffer), file);
  fclose(file);

  if (size == 0) {
    printf("[DECODE] FAILED: Empty file\n");
    return 1;
  }

  if (!decode_test_message(format, buffer, size, &msg)) {
    printf("[DECODE] FAILED: Decoding error\n");
    print_hex(buffer, size);
    return 1;
  }

  if (!validate_test_message(&msg)) {
    printf("[DECODE] FAILED: Validation error\n");
    return 1;
  }

  printf("[DECODE] SUCCESS: Message validated correctly\n");
  return 0;
}

int main(int argc, char* argv[]) {
  if (argc != 4) {
    print_usage(argv[0]);
    return 1;
  }

  const char* mode = argv[1];
  const char* format = argv[2];
  const char* file = argv[3];

  printf("\n[TEST START] C %s %s\n", format, mode);

  int result;
  if (strcmp(mode, "encode") == 0) {
    result = run_encode(format, file);
  } else if (strcmp(mode, "decode") == 0) {
    result = run_decode(format, file);
  } else {
    printf("Unknown mode: %s\n", mode);
    print_usage(argv[0]);
    result = 1;
  }

  printf("[TEST END] C %s %s: %s\n\n", format, mode, result == 0 ? "PASS" : "FAIL");
  return result;
}
