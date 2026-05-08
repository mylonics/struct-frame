/**
 * Profile runner (header-only) - profile-dispatch encode/decode functions.
 *
 * Provides encode_messages() and decode_messages() which accept a format
 * string and dispatch to the appropriate frame-profile config.
 *
 * Depends on test_config_t from test_harness.h (include test_harness.h instead
 * of this file directly in most cases).
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
 * Encode function
 * ============================================================================ */

static inline bool encode_messages(const test_config_t* config, const char* format, uint8_t* buffer, size_t buffer_size,
                                   size_t* encoded_size) {
  if (!config->supports_format(format)) {
    printf("  Unsupported format: %s\n", format);
    return false;
  }

  if (config->reset_state) {
    config->reset_state();
  }

  *encoded_size = 0;

  const profile_config_t* profile_config = NULL;

  if (strcmp(format, "standard") == 0) {
    profile_config = &PROFILE_STANDARD_CONFIG;
  } else if (strcmp(format, "sensor") == 0) {
    profile_config = &PROFILE_SENSOR_CONFIG;
  } else if (strcmp(format, "ipc") == 0) {
    profile_config = &PROFILE_IPC_CONFIG;
  } else if (strcmp(format, "bulk") == 0) {
    profile_config = &PROFILE_BULK_CONFIG;
  } else if (strcmp(format, "network") == 0) {
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

  const profile_config_t* profile_config = NULL;

  if (strcmp(format, "standard") == 0) {
    profile_config = &PROFILE_STANDARD_CONFIG;
  } else if (strcmp(format, "sensor") == 0) {
    profile_config = &PROFILE_SENSOR_CONFIG;
  } else if (strcmp(format, "ipc") == 0) {
    profile_config = &PROFILE_IPC_CONFIG;
  } else if (strcmp(format, "bulk") == 0) {
    profile_config = &PROFILE_BULK_CONFIG;
  } else if (strcmp(format, "network") == 0) {
    profile_config = &PROFILE_NETWORK_CONFIG;
  } else {
    printf("  Unknown frame format: %s\n", format);
    return false;
  }

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
