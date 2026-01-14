/**
 * Test codec (header-only) - Encode/decode and test runner infrastructure for C.
 *
 * This file provides:
 * 1. Config-based encode/decode functions using function pointers
 * 2. Test runner utilities (file I/O, hex dump, CLI parsing)
 * 3. A unified run_test_main() function for entry points
 *
 * Usage:
 * Each test entry point (.c file) must provide a test_config_t struct with:
 * - message_count: number of messages
 * - buffer_size: buffer size for encode/decode
 * - formats_help: help text for supported formats
 * - test_name: name for logging
 * - get_msg_id_order(): returns array of msg_ids in encode/decode order
 * - encode_message(): function to encode a message by index
 * - validate_message(): function to validate a decoded message
 * - get_message_info(): unified function for message lookup
 * - supports_format(): function to check if format is supported
 */

#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "frame_profiles.h"

/* ============================================================================
 * Test configuration structure
 * ============================================================================ */

typedef struct test_config {
  size_t message_count;
  size_t buffer_size;
  const char* formats_help;
  const char* test_name;

  /* Get message ID order array */
  const uint16_t* (*get_msg_id_order)(void);

  /* Encode message by index, returns bytes written */
  size_t (*encode_message)(buffer_writer_t* writer, size_t index);

  /* Validate decoded message, returns true if valid */
  bool (*validate_message)(uint16_t msg_id, const uint8_t* data, size_t size, size_t* index);

  /* Reset encoder/validator state for new run */
  void (*reset_state)(void);

  /* Get message info (size and magic numbers) for profiles */
  bool (*get_message_info)(uint16_t msg_id, message_info_t* info);

  /* Check if format is supported */
  bool (*supports_format)(const char* format);
} test_config_t;

/* ============================================================================
 * Utility functions
 * ============================================================================ */

/**
 * Print hex dump of data (up to 64 bytes).
 */
static inline void print_hex(const uint8_t* data, size_t size) {
  printf("  Hex (%zu bytes): ", size);
  for (size_t i = 0; i < size && i < 64; i++) {
    printf("%02x", data[i]);
  }
  if (size > 64) printf("...");
  printf("\n");
}

/**
 * Print usage help.
 */
static inline void print_usage(const char* program_name, const char* formats_help) {
  printf("Usage:\n");
  printf("  %s encode <frame_format> <output_file>\n", program_name);
  printf("  %s decode <frame_format> <input_file>\n", program_name);
  printf("\nFrame formats: %s\n", formats_help);
}

/* ============================================================================
 * Encode function
 * ============================================================================ */

static inline bool encode_messages(const test_config_t* config, const char* format, uint8_t* buffer, size_t buffer_size,
                                   size_t* encoded_size) {
  if (!config->supports_format(format)) {
    printf("  Unsupported format: %s\n", format);
    return false;
  }

  /* Reset encoder state */
  if (config->reset_state) {
    config->reset_state();
  }

  *encoded_size = 0;

  /* Get the appropriate profile config */
  const profile_config_t* profile_config = NULL;

  if (strcmp(format, "profile_standard") == 0) {
    profile_config = &PROFILE_STANDARD_CONFIG;
  } else if (strcmp(format, "profile_sensor") == 0) {
    profile_config = &PROFILE_SENSOR_CONFIG;
  } else if (strcmp(format, "profile_ipc") == 0) {
    profile_config = &PROFILE_IPC_CONFIG;
  } else if (strcmp(format, "profile_bulk") == 0) {
    profile_config = &PROFILE_BULK_CONFIG;
  } else if (strcmp(format, "profile_network") == 0) {
    profile_config = &PROFILE_NETWORK_CONFIG;
  } else {
    printf("  Unknown frame format: %s\n", format);
    return false;
  }

  buffer_writer_t writer;
  buffer_writer_init(&writer, profile_config, buffer, buffer_size);

  for (size_t i = 0; i < config->message_count; i++) {
    size_t written = config->encode_message(&writer, i);

    if (written == 0) {
      printf("  Encoding failed for message %zu\n", i);
      return false;
    }
  }

  *encoded_size = buffer_writer_size(&writer);

  if (strstr(config->test_name, "Variable Flag") != NULL) {
    printf("Total: %zu bytes\n", *encoded_size);
  }

  return true;
}

/* ============================================================================
 * Decode function
 * ============================================================================ */

static inline bool decode_messages(const test_config_t* config, const char* format, const uint8_t* buffer,
                                   size_t buffer_size, size_t* message_count) {
  if (!config->supports_format(format)) {
    printf("  Unsupported format: %s\n", format);
    return false;
  }

  /* Reset validator state */
  if (config->reset_state) {
    config->reset_state();
  }

  const uint16_t* msg_order = config->get_msg_id_order();
  *message_count = 0;

  /* Split buffer into 3 chunks to test partial message handling */
  size_t chunk1_size = buffer_size / 3;
  size_t chunk2_size = buffer_size / 3;
  size_t chunk3_size = buffer_size - chunk1_size - chunk2_size;

  const uint8_t* chunk1 = buffer;
  const uint8_t* chunk2 = buffer + chunk1_size;
  const uint8_t* chunk3 = buffer + chunk1_size + chunk2_size;

  /* Get the appropriate profile config */
  const profile_config_t* profile_config = NULL;

  if (strcmp(format, "profile_standard") == 0) {
    profile_config = &PROFILE_STANDARD_CONFIG;
  } else if (strcmp(format, "profile_sensor") == 0) {
    profile_config = &PROFILE_SENSOR_CONFIG;
  } else if (strcmp(format, "profile_ipc") == 0) {
    profile_config = &PROFILE_IPC_CONFIG;
  } else if (strcmp(format, "profile_bulk") == 0) {
    profile_config = &PROFILE_BULK_CONFIG;
  } else if (strcmp(format, "profile_network") == 0) {
    profile_config = &PROFILE_NETWORK_CONFIG;
  } else {
    printf("  Unknown frame format: %s\n", format);
    return false;
  }

  /* Allocate internal buffer for accumulating reader */
  uint8_t* internal_buffer = (uint8_t*)malloc(config->buffer_size);
  if (!internal_buffer) {
    printf("  Failed to allocate internal buffer\n");
    return false;
  }

  accumulating_reader_t reader;
  accumulating_reader_init(&reader, profile_config, internal_buffer, config->buffer_size, config->get_message_info);

  const uint8_t* chunks[] = {chunk1, chunk2, chunk3};
  size_t sizes[] = {chunk1_size, chunk2_size, chunk3_size};

  bool success = true;

  for (int c = 0; c < 3; c++) {
    accumulating_reader_add_data(&reader, chunks[c], sizes[c]);

    frame_msg_info_t result;
    while ((result = accumulating_reader_next(&reader)).valid) {
      if (*message_count >= config->message_count) {
        printf("  Too many messages decoded: %zu\n", *message_count);
        success = false;
        goto cleanup;
      }

      uint16_t expected_msg_id = msg_order[*message_count];
      if (result.msg_id != expected_msg_id) {
        printf("  Message %zu ID mismatch: expected %u, got %u\n", *message_count, expected_msg_id, result.msg_id);
        success = false;
        goto cleanup;
      }

      size_t validate_index = *message_count;
      if (!config->validate_message(result.msg_id, result.msg_data, result.msg_len, &validate_index)) {
        printf("  Message %zu validation failed\n", *message_count);
        success = false;
        goto cleanup;
      }

      (*message_count)++;
    }
  }

  if (*message_count != config->message_count) {
    printf("  Expected %zu messages, decoded %zu\n", config->message_count, *message_count);
    success = false;
    goto cleanup;
  }

  if (accumulating_reader_has_partial(&reader)) {
    printf("  Incomplete partial message: %zu bytes\n", accumulating_reader_partial_size(&reader));
    success = false;
    goto cleanup;
  }

cleanup:
  free(internal_buffer);
  return success;
}

/* ============================================================================
 * Test runner functions
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
