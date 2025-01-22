#pragma once

#include "stdint.h"
#include "stdbool.h"

typedef struct _msg_id_len_t
{
  bool valid;
  uint8_t len;
  uint8_t msg_id;
} msg_id_len_t;

typedef struct _parser_functions_t
{
  bool (*get_msg_id_len)(msg_id_len_t *, uint8_t);
  bool (*validate_packet)(uint8_t *, msg_id_len_t *);
} parser_functions_t;

typedef struct _struct_frame_config
{
  uint8_t has_crc;
  uint8_t has_len;
  uint8_t start_byte;
  parser_functions_t *parser_funcs;
} struct_frame_config;

enum ParserState
{
  LOOKING_FOR_START_BYTE = 0,
  GETTING_LENGTH_MSG_AND_ID = 1,
  GETTING_PAYLOAD = 2
};

typedef struct _struct_frame_buffer
{
  // Used for framing and parsing
  struct_frame_config config;
  uint8_t *data;
  size_t max_size;
  size_t size;
  bool in_progress;

  // Used for framing
  size_t crc_start_loc;

  // Used for parsing
  enum ParserState state;
  size_t payload_len;
  msg_id_len_t msg_id_len;

} struct_buffer;

typedef struct _buffer_parser_result_t
{
  struct_frame_config config;
  bool found;
  bool valid;
  uint8_t *msg_loc;
  size_t r_loc;
  bool finished;
  msg_id_len_t msg_id_len;
} buffer_parser_result_t;

// https://github.com/serge-sans-paille/frozen
// https://www.npmjs.com/package/typed-struct

#define default_parser {0, 0, 0x90}

#define zero_initialized_parser_result {default_parser, false, false, 0, 0, false, {0, 0}};

#define CREATE_DEFAULT_STRUCT_BUFFER(name, size) \
  uint8_t name##_buffer[size];                   \
  struct_buffer name = {default_parser, name##_buffer, size, 0, 0, false, 0, 0, 0, 0, NULL}

typedef struct checksum_t
{
  uint8_t byte1;
  uint8_t byte2;
} checksum_t;