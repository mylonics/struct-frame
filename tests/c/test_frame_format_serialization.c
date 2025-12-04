/**
 * Frame format serialization test for C.
 * 
 * This test serializes data using different frame formats and saves to binary files.
 * Usage: test_frame_format_serialization <frame_format>
 * 
 * Supported frame formats:
 *   basic_default, basic_minimal, basic_seq, basic_sys_comp, basic_extended_msg_ids,
 *   basic_extended_length, basic_extended, basic_multi_system_stream,
 *   basic_extended_multi_system_stream, tiny_default, tiny_minimal, tiny_seq,
 *   tiny_sys_comp, tiny_extended_msg_ids, tiny_extended_length, tiny_extended,
 *   tiny_multi_system_stream, tiny_extended_multi_system_stream
 */

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

void init_test_message(SerializationTestSerializationTestMessage* msg) {
  memset(msg, 0, sizeof(*msg));
  
  // Use values from expected_values.json
  msg->magic_number = 3735928559;  // 0xDEADBEEF
  msg->test_string.length = strlen("Cross-platform test!");
  strncpy(msg->test_string.data, "Cross-platform test!", msg->test_string.length);
  msg->test_float = 3.14159f;
  msg->test_bool = true;
  msg->test_array.count = 3;
  msg->test_array.data[0] = 100;
  msg->test_array.data[1] = 200;
  msg->test_array.data[2] = 300;
}

typedef size_t (*encode_func_t)(uint8_t* buffer, size_t buffer_size, uint8_t msg_id,
                                 const uint8_t* msg, size_t msg_size);
typedef frame_msg_info_t (*validate_func_t)(const uint8_t* buffer, size_t length);

typedef struct {
  const char* name;
  encode_func_t encode;
  validate_func_t validate;
} frame_format_entry_t;

// Frame format registry
static const frame_format_entry_t frame_formats[] = {
  {"basic_default", basic_default_encode, basic_default_validate_packet},
  {"basic_minimal", basic_minimal_encode, basic_minimal_validate_packet},
  {"basic_seq", basic_seq_encode, basic_seq_validate_packet},
  {"basic_sys_comp", basic_sys_comp_encode, basic_sys_comp_validate_packet},
  {"basic_extended_msg_ids", basic_extended_msg_ids_encode, basic_extended_msg_ids_validate_packet},
  {"basic_extended_length", basic_extended_length_encode, basic_extended_length_validate_packet},
  {"basic_extended", basic_extended_encode, basic_extended_validate_packet},
  {"basic_multi_system_stream", basic_multi_system_stream_encode, basic_multi_system_stream_validate_packet},
  {"basic_extended_multi_system_stream", basic_extended_multi_system_stream_encode, basic_extended_multi_system_stream_validate_packet},
  {"tiny_default", tiny_default_encode, tiny_default_validate_packet},
  {"tiny_minimal", tiny_minimal_encode, tiny_minimal_validate_packet},
  {"tiny_seq", tiny_seq_encode, tiny_seq_validate_packet},
  {"tiny_sys_comp", tiny_sys_comp_encode, tiny_sys_comp_validate_packet},
  {"tiny_extended_msg_ids", tiny_extended_msg_ids_encode, tiny_extended_msg_ids_validate_packet},
  {"tiny_extended_length", tiny_extended_length_encode, tiny_extended_length_validate_packet},
  {"tiny_extended", tiny_extended_encode, tiny_extended_validate_packet},
  {"tiny_multi_system_stream", tiny_multi_system_stream_encode, tiny_multi_system_stream_validate_packet},
  {"tiny_extended_multi_system_stream", tiny_extended_multi_system_stream_encode, tiny_extended_multi_system_stream_validate_packet},
  {NULL, NULL, NULL}
};

const frame_format_entry_t* find_frame_format(const char* name) {
  for (int i = 0; frame_formats[i].name != NULL; i++) {
    if (strcmp(frame_formats[i].name, name) == 0) {
      return &frame_formats[i];
    }
  }
  return NULL;
}

int create_test_data(const char* frame_format) {
  const frame_format_entry_t* ff = find_frame_format(frame_format);
  if (ff == NULL) {
    printf("  Unknown frame format: %s\n", frame_format);
    return 0;
  }

  SerializationTestSerializationTestMessage msg;
  init_test_message(&msg);

  uint8_t encode_buffer[512];
  size_t encoded_size = ff->encode(encode_buffer, sizeof(encode_buffer),
                                   SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MSG_ID,
                                   (const uint8_t*)&msg, SERIALIZATION_TEST_SERIALIZATION_TEST_MESSAGE_MAX_SIZE);

  if (encoded_size == 0) {
    print_failure_details("Encoding failed", NULL, 0);
    return 0;
  }

  // Create output filename
  char filename[256];
  snprintf(filename, sizeof(filename), "c_%s_test_data.bin", frame_format);

  FILE* file = fopen(filename, "wb");
  if (!file) {
    print_failure_details("File creation failed", NULL, 0);
    return 0;
  }

  fwrite(encode_buffer, 1, encoded_size, file);
  fclose(file);

  // Self-validate
  frame_msg_info_t decode_result = ff->validate(encode_buffer, encoded_size);
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

  printf("  [OK] Encoded with %s format (%zu bytes) -> %s\n", frame_format, encoded_size, filename);
  return 1;
}

int main(int argc, char* argv[]) {
  printf("\n[TEST START] C Frame Format Serialization\n");
  
  if (argc != 2) {
    printf("  Usage: %s <frame_format>\n", argv[0]);
    printf("  Supported formats:\n");
    for (int i = 0; frame_formats[i].name != NULL; i++) {
      printf("    %s\n", frame_formats[i].name);
    }
    printf("[TEST END] C Frame Format Serialization: FAIL\n\n");
    return 1;
  }

  int success = create_test_data(argv[1]);
  
  const char* status = success ? "PASS" : "FAIL";
  printf("[TEST END] C Frame Format Serialization: %s\n\n", status);
  
  return success ? 0 : 1;
}
