#pragma once
#include "stdint.h"
#include "struct_frame_gen.h"
#include "struct_frame_types.h"

// https://github.com/serge-sans-paille/frozen

static inline bool parse_default_format_validate(uint8_t *data, msg_id_len_t *msg_id_len) {
  (void)data;
  (void)msg_id_len;
  return true;
}

static inline bool parse_default_format_char_for_len_id(msg_id_len_t *msg_id_len, const uint8_t c) {
  msg_id_len->msg_id = c;
  msg_id_len->len = get_message_length(c);
  return true;
}

parser_functions_t default_parser_functions = {parse_default_format_char_for_len_id, parse_default_format_validate};

static inline parser_functions_t *parse_char_for_start_byte(const struct_frame_config config, const uint8_t c) {
  if (config.start_byte == c) {
    return &default_parser_functions;
  }
  return NULL;
}

static inline bool parse_char(struct_buffer *pb, uint8_t c) {
  parser_functions_t *parse_func_ptr = NULL;
  switch (pb->state) {
    case LOOKING_FOR_START_BYTE:
      parse_func_ptr = parse_char_for_start_byte(pb->config, c);
      if (parse_func_ptr) {
        pb->config.parser_funcs = parse_func_ptr;
        pb->state = GETTING_LENGTH_MSG_AND_ID;
      }
      break;

    case GETTING_LENGTH_MSG_AND_ID:
      if (pb->config.parser_funcs->get_msg_id_len(&pb->msg_id_len, c)) {
        pb->state = GETTING_PAYLOAD;
        pb->size = 0;
      }
      break;

    case GETTING_PAYLOAD:
      pb->data[pb->size++] = c;
      if (pb->size >= pb->msg_id_len.len) {
        pb->state = LOOKING_FOR_START_BYTE;
        return pb->config.parser_funcs->validate_packet(pb->data, &pb->msg_id_len);
      }

      break;

    default:
      break;
  }

  return false;
}

static inline bool parse_buffer(uint8_t *buffer, size_t size, buffer_parser_result_t *parser_result) {
  enum ParserState state = LOOKING_FOR_START_BYTE;
  parser_functions_t *parse_func_ptr;
  for (size_t i = parser_result->r_loc; i < size; i++) {
    switch (state) {
      case LOOKING_FOR_START_BYTE:
        parse_func_ptr = parse_char_for_start_byte(parser_result->config, buffer[i]);
        if (parse_func_ptr) {
          state = GETTING_LENGTH_MSG_AND_ID;
        }
        break;

      case GETTING_LENGTH_MSG_AND_ID:
        if (parse_func_ptr->get_msg_id_len(&parser_result->msg_id_len, buffer[i])) {
          state = GETTING_PAYLOAD;
        }
        break;

      case GETTING_PAYLOAD:
        parser_result->msg_loc = buffer + i;
        parser_result->r_loc = i + parser_result->msg_id_len.len;
        parser_result->found = true;
        if (parse_func_ptr->validate_packet(parser_result->msg_loc, &parser_result->msg_id_len)) {
          parser_result->valid = true;
          return true;
        } else {
          parser_result->valid = false;
          return true;
        }
        break;

      default:
        break;
    }
  }
  return false;
}
