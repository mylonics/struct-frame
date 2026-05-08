/**
 * Test harness (header-only) - CLI, file I/O, and run_test_main() for C tests.
 *
 * Includes profile_runner.h and adds the high-level run functions.
 *
 * Usage:
 *   Each *_messages.h file includes this header.
 *   Each test entry point (.c file) includes *_messages.h and calls run_test_main().
 */

#pragma once

#include "profile_runner.h"

/* ============================================================================
 * Utility functions
 * ============================================================================ */

static inline void print_hex(const uint8_t* data, size_t size) {
  printf("  Hex (%zu bytes): ", size);
  for (size_t i = 0; i < size && i < 64; i++) {
    printf("%02x", data[i]);
  }
  if (size > 64) printf("...");
  printf("\n");
}

static inline void print_usage(const char* program_name, const char* formats_help) {
  printf("Usage:\n");
  printf("  %s encode <frame_format> <output_file>\n", program_name);
  printf("  %s decode <frame_format> <input_file>\n", program_name);
  printf("\nFrame formats: %s\n", formats_help);
}

/* ============================================================================
 * Encode runner
 * ============================================================================ */

static inline int run_encode(const test_config_t* config, const char* format, const char* output_file) {
  uint8_t* buffer = (uint8_t*)malloc(config->buffer_size);
  if (!buffer) {
    printf("[ENCODE] FAILED: Cannot allocate buffer\n");
    return 1;
  }

  size_t encoded_size = 0;

  printf("[ENCODE] Format: %s\n", format);

  if (!encode_messages(config, format, buffer, config->buffer_size, &encoded_size)) {
    printf("[ENCODE] FAILED: Encoding error\n");
    free(buffer);
    return 1;
  }

  FILE* file = fopen(output_file, "wb");
  if (!file) {
    printf("[ENCODE] FAILED: Cannot create output file: %s\n", output_file);
    free(buffer);
    return 1;
  }

  fwrite(buffer, 1, encoded_size, file);
  fclose(file);
  free(buffer);

  printf("[ENCODE] SUCCESS: Wrote %zu bytes to %s\n", encoded_size, output_file);
  return 0;
}

/* ============================================================================
 * Decode runner
 * ============================================================================ */

static inline int run_decode(const test_config_t* config, const char* format, const char* input_file) {
  uint8_t* buffer = (uint8_t*)malloc(config->buffer_size);
  if (!buffer) {
    printf("[DECODE] FAILED: Cannot allocate buffer\n");
    return 1;
  }

  printf("[DECODE] Format: %s, File: %s\n", format, input_file);

  FILE* file = fopen(input_file, "rb");
  if (!file) {
    printf("[DECODE] FAILED: Cannot open input file: %s\n", input_file);
    free(buffer);
    return 1;
  }

  size_t size = fread(buffer, 1, config->buffer_size, file);
  fclose(file);

  if (size == 0) {
    printf("[DECODE] FAILED: Empty file\n");
    free(buffer);
    return 1;
  }

  size_t message_count = 0;
  if (!decode_messages(config, format, buffer, size, &message_count)) {
    printf("[DECODE] FAILED: %zu messages validated before error\n", message_count);
    print_hex(buffer, size);
    free(buffer);
    return 1;
  }

  free(buffer);
  printf("[DECODE] SUCCESS: %zu messages validated correctly\n", message_count);
  return 0;
}

/* ============================================================================
 * Main entry point
 * ============================================================================ */

static inline int run_test_main(const test_config_t* config, int argc, char* argv[]) {
  if (argc != 4) {
    print_usage(argv[0], config->formats_help);
    return 1;
  }

  const char* mode = argv[1];
  const char* format = argv[2];
  const char* file = argv[3];

  printf("\n[TEST START] %s %s %s\n", config->test_name, format, mode);

  int result;
  if (strcmp(mode, "encode") == 0) {
    result = run_encode(config, format, file);
  } else if (strcmp(mode, "decode") == 0) {
    result = run_decode(config, format, file);
  } else {
    printf("Unknown mode: %s\n", mode);
    result = 1;
  }

  printf("[TEST END] %s %s %s: %s\n\n", config->test_name, format, mode, result == 0 ? "PASS" : "FAIL");
  return result;
}
