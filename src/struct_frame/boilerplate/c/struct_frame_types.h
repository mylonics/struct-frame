#pragma once

#include "stdbool.h"
#include "stdint.h"

// https://github.com/serge-sans-paille/frozen
// https://www.npmjs.com/package/typed-struct

// #define default_parser {1, 0, 0x90}
//
// #define zero_initialized_parser_result {default_parser, false, 0, 0, false, {0, 0}}
//
// #d efine CREATE_DEFAULT_STRUCT_BUFFER(name, size) \
//  uint8_t name##_buffer[size];                   \
//  struct_buffer name = {default_parser, name##_buffer, size, 0, false, 0, LOOKING_FOR_START_BYTE, 0, {false, 0, 0}};

typedef struct checksum_t {
  uint8_t byte1;
  uint8_t byte2;
} checksum_t;

typedef struct msg_info_t {
  bool valid;
  uint8_t len;
  uint8_t msg_id;
  uint8_t *msg_loc;
} msg_info_t;

typedef struct _packet_format {
  bool (*check_start_bytes)(uint8_t);
  bool (*process_header_byte)(uint8_t, size_t);
  size_t (*get_msg_id)(uint8_t *data);
  size_t (*get_full_packet_length)(size_t);
  struct msg_info_t (*validate_packet)(uint8_t *, size_t);
  size_t (*encode)(uint8_t *buffer, uint8_t msg_id, uint8_t *msg, uint8_t msg_size);
  uint8_t *(*encode_reserve)(uint8_t *buffer, uint8_t msg_id, uint8_t msg_size);
  uint8_t (*encode_finsish)(uint8_t *buffer, uint8_t msg_size);

} packet_format_t;

enum parser_state_enum { LOOKING_FOR_START_BYTE = 0, GETTING_HEADER = 1, GETTING_PAYLOAD = 2 };

typedef struct _definitions {
  bool (*get_message_length)(size_t, size_t *);
  bool (*get_packet_formats)(uint8_t);
} packet_definitions_t;

typedef struct packet_state_t {
  enum parser_state_enum state;
  size_t packet_size;
  packet_format_t *format;
  uint8_t *buffer;
  size_t buffer_size;
  size_t buffer_max_size;
  packet_definitions_t *defines;
} packet_state_t;

typedef struct buffer_parser_result_t {
  enum parser_state_enum state;
  size_t packet_size;
  packet_format_t *format;
  uint8_t *buffer;
  size_t packet_start_index;
  size_t buffer_size;
  size_t buffer_max_size;
  packet_definitions_t *defines;
  bool finished;
  size_t r_loc;

} buffer_parser_result_t;

typedef struct _msg_encode_buffer {
  uint8_t *data;
  size_t size;
  bool in_progress;
} msg_encode_buffer;

typedef struct _struct_frame_parse_char_impl {
  // Used for framing and parsing
  packet_format_t packet_format;
  packet_state_t parser_state;

} struct_frame_parse_char_impl;

// typedef struct _buffer_parser_result_t {
//   struct_frame_config config;
//   bool valid;
//   uint8_t *msg_loc;
//   size_t r_loc;
//   bool finished;
//   msg_id_len_t msg_id_len;
// } buffer_parser_result_t;
