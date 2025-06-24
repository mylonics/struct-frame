#pragma once
#include "stdint.h"
#include "struct_frame_types.h"

// https://github.com/serge-sans-paille/frozen

static inline msg_info_t parse_buffer(uint8_t *buffer, size_t size, buffer_parser_result_t *parser_result) {
  enum ParserState state = LOOKING_FOR_START_BYTE;
  parser_result->finished = false;
  for (size_t i = parser_result->r_loc; i < size; i++) {
    uint8_t c = buffer[i];
    switch (state) {
      case LOOKING_FOR_START_BYTE:
        parser_result->format = parser_result->defines->get_packet_formats(c);
        if (parser_result->format) {
          parser_result->packet_start_index = i;
          if (parser_result->format->process_header_byte(c, true)) {
            parser_result->state = GETTING_PAYLOAD;
          } else {
            parser_result->state = GETTING_HEADER;
          }
        }
        break;

      case GETTING_HEADER:
        if (parser_result->format->process_header_byte(c, false)) {
          size_t msg_id = parser_result->format->get_msg_id(buffer + parser_result->packet_start_index);
          size_t length = 0;
          if (parser_result->defines->get_message_length(msg_id, &length)) {
            parser_result->packet_size = parser_result->format->get_full_packet_length(length);
            parser_result->state = GETTING_PAYLOAD;
          } else {
            parser_result->state = LOOKING_FOR_START_BYTE;
          }
        }
        break;

      case GETTING_PAYLOAD:
        if ((parser_result->packet_start_index + parser_result->packet_size) > size) {
          parser_result->state = LOOKING_FOR_START_BYTE;
          msg_info_t info = parser_result->format->validate_packet(buffer + parser_result->packet_start_index,
                                                                   parser_result->packet_size);
          return info;
        } else {
          parser_result->state = LOOKING_FOR_START_BYTE;
        }

        break;

      default:
        break;
    }
  }
  parser_result->finished = true;
  parser_result->r_loc = 0;

  msg_info_t info = {0, 0, 0, 0};
  return info;
}

msg_info_t parse_char(packet_state_t *state, const uint8_t c) {
  state->buffer[state->buffer_size] = c;
  state->buffer_size = (state->buffer_size + 1) % state->buffer_max_size;

  switch (state->state) {
    case LOOKING_FOR_START_BYTE:;
      state->format = state->defines->get_packet_formats(c);
      if (state->format) {
        state->buffer[0] = state->buffer[state->buffer_size];
        state->buffer_size = 0;
        if (state->format->process_header_byte(c, true)) {
          state->state = GETTING_PAYLOAD;
        } else {
          state->state = GETTING_HEADER;
        }
      }
      break;

    case GETTING_HEADER:
      if (state->format->process_header_byte(c, false)) {
        size_t msg_id = state->format->get_msg_id(state->buffer);
        size_t length = 0;
        if (state->defines->get_message_length(msg_id, &length)) {
          state->packet_size = state->format->get_full_packet_length(length);
          state->state = GETTING_PAYLOAD;
        } else {
          state->state = LOOKING_FOR_START_BYTE;
        }
      }
      break;

    case GETTING_PAYLOAD:
      if (state->buffer_size >= state->packet_size) {
        state->state = LOOKING_FOR_START_BYTE;
        msg_info_t info = state->format->validate_packet(state->buffer, state->buffer_size);
        return;
      }
      break;

    default:
      break;
  }

  msg_info_t info = {0, 0, 0, 0};
  return info;
}

msg_info_t parse_buffer(packet_state_t *state, const uint8_t c) {
  state->buffer[state->buffer_size] = c;
  state->buffer_size = (state->buffer_size + 1) % state->buffer_max_size;

  switch (state->state) {
    case LOOKING_FOR_START_BYTE:;
      state->format = state->defines->get_packet_formats(c);
      if (state->format) {
        state->buffer[0] = state->buffer[state->buffer_size];
        state->buffer_size = 0;
        if (state->format->process_header_byte(c, true)) {
          state->state = GETTING_PAYLOAD;
        } else {
          state->state = GETTING_HEADER;
        }
      }
      break;

    case GETTING_HEADER:
      if (state->format->process_header_byte(c, false)) {
        size_t msg_id = state->format->get_msg_id();
        size_t length = 0;
        if (state->defines->get_message_length(msg_id, &length)) {
          state->packet_size = state->format->get_full_packet_length(length);
          state->state = GETTING_PAYLOAD;
        } else {
          state->state = LOOKING_FOR_START_BYTE;
        }
      }
      break;

    case GETTING_PAYLOAD:
      if (state->buffer_size >= state->packet_size) {
        state->state = LOOKING_FOR_START_BYTE;
        msg_info_t info = state->format->validate_packet(state->buffer, state->packet_size);
        return info;
      }
      break;

    default:
      break;
  }

  msg_info_t info = {0, 0, 0, 0};
  return info;
}
