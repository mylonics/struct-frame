#pragma once
#include "stdint.h"
#include "struct_frame_types.h"

// https://github.com/serge-sans-paille/frozen

static inline msg_info_t parse_buffer(packet_state_t *packet_state) {
  packet_state->state = LOOKING_FOR_START_BYTE;
  packet_state->finished = false;
  for (size_t i = packet_state->r_loc; i < packet_state->buffer_size; i++) {
    uint8_t c = packet_state->buffer[i];
    switch (packet_state->state) {
      case LOOKING_FOR_START_BYTE:
        packet_state->format = packet_state->defines->get_packet_formats(c);
        if (packet_state->format) {
          packet_state->packet_start_index = i;
          if (packet_state->format->process_header_byte(c, true)) {
            packet_state->state = GETTING_PAYLOAD;
          } else {
            packet_state->state = GETTING_HEADER;
          }
        }
        break;

      case GETTING_HEADER:
        if (packet_state->format->process_header_byte(c, false)) {
          size_t msg_id = packet_state->format->get_msg_id(packet_state->buffer + packet_state->packet_start_index);
          size_t length = 0;
          if (packet_state->defines->get_message_length(msg_id, &length)) {
            packet_state->packet_size = packet_state->format->get_full_packet_length(length);
            packet_state->state = GETTING_PAYLOAD;
          } else {
            packet_state->state = LOOKING_FOR_START_BYTE;
          }
        }
        break;

      case GETTING_PAYLOAD:
        if ((packet_state->packet_start_index + packet_state->packet_size) > packet_state->buffer_size) {
          packet_state->state = LOOKING_FOR_START_BYTE;
          msg_info_t info = packet_state->format->validate_packet(
              packet_state->buffer + packet_state->packet_start_index, packet_state->packet_size);
          packet_state->r_loc += i;
          return info;
        } else {
          packet_state->state = LOOKING_FOR_START_BYTE;
        }

        break;

      default:
        break;
    }
  }
  packet_state->finished = true;
  packet_state->r_loc = 0;

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
        return info;
      }
      break;

    default:
      break;
  }

  msg_info_t info = {0, 0, 0, 0};
  return info;
}
