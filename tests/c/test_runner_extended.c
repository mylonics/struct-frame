/**
 * Test runner entry point for C - Extended message ID and payload tests.
 *
 * Usage:
 *   test_runner_extended encode <frame_format> <output_file>
 *   test_runner_extended decode <frame_format> <input_file>
 *
 * Frame formats (extended profiles only): profile_bulk, profile_network
 */

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "test_codec_extended.h"

#define MAX_BUFFER_SIZE 8192  /* Larger for extended payloads */

static void print_usage(const char* program_name) {
  printf("Usage:\n");
  printf("  %s encode <frame_format> <output_file>\n", program_name);
  printf("  %s decode <frame_format> <input_file>\n", program_name);
  printf("\nFrame formats (extended profiles): profile_bulk, profile_network\n");
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
  
  if (!encode_extended_messages(format, buffer, sizeof(buffer), &encoded_size)) {
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
  
  size_t message_count = 0;
  if (!decode_extended_messages(format, buffer, size, &message_count)) {
    printf("[DECODE] FAILED: Decoding error\n");
    print_hex(buffer, size);
    return 1;
  }
  
  printf("[DECODE] SUCCESS: %zu messages validated correctly\n", message_count);
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
  
  /* Validate format */
  if (strcmp(format, "profile_bulk") != 0 && strcmp(format, "profile_network") != 0) {
    printf("Error: Invalid frame format '%s'. Extended tests only support profile_bulk and profile_network.\n", format);
    return 1;
  }
  
  if (strcmp(mode, "encode") == 0) {
    return run_encode(format, file);
  } else if (strcmp(mode, "decode") == 0) {
    return run_decode(format, file);
  } else {
    printf("Error: Unknown mode '%s'\n", mode);
    print_usage(argv[0]);
    return 1;
  }
}
