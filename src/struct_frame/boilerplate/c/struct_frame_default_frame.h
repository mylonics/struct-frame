#pragma once
#include "stdint.h"
#include "struct_frame.h"
#include "struct_frame_parser.h"
#include "struct_frame_types.h"

#define BASIC_FRAME_HEADER_LENGTH 2
#define BASIC_FRAME_FOOTER_LENGTH 2

bool basic_frame_check_start_bytes(uint8_t c) { return c == 0x90; }

bool basic_frame_process_header_byte(uint8_t c, size_t length) { return length >= BASIC_FRAME_HEADER_LENGTH; }

size_t basic_frame_get_msg_id(uint8_t* data) { return data[1]; }

size_t basic_frame_get_full_packet_length(size_t msg_length) {
  return msg_length + BASIC_FRAME_HEADER_LENGTH + BASIC_FRAME_FOOTER_LENGTH;
}

msg_info_t basic_frame_validate_packet(uint8_t* data, size_t packet_length) {
  size_t msg_size = packet_length - BASIC_FRAME_HEADER_LENGTH - BASIC_FRAME_FOOTER_LENGTH;
  checksum_t ck = fletcher_checksum_calculation(data + 1, msg_size + 1);

  msg_info_t info = {false, (uint8_t)msg_size, data[1], data + 2};
  if (ck.byte1 == data[packet_length - 2] && ck.byte2 == data[packet_length - 1]) {
    info.valid = true;
  }
  return info;
};

uint8_t basic_frame_finish(uint8_t* buffer, uint8_t msg_size) {
  checksum_t ck = fletcher_checksum_calculation(buffer + 1, msg_size + 1);

  buffer[msg_size + BASIC_FRAME_HEADER_LENGTH] = ck.byte1;
  buffer[msg_size + BASIC_FRAME_HEADER_LENGTH + 1] = ck.byte2;
  return msg_size + BASIC_FRAME_HEADER_LENGTH + BASIC_FRAME_FOOTER_LENGTH;
}

size_t basic_frame_encode(uint8_t* buffer, uint8_t msg_id, uint8_t* msg, uint8_t msg_size) {
  buffer[0] = 0x90;
  buffer[1] = msg_id;
  memcpy(buffer + 2, msg, msg_size);
  return basic_frame_finish(buffer, msg_size);
}

uint8_t* basic_frame_reserve(uint8_t* buffer, uint8_t msg_id, uint8_t msg_size) {
  buffer[0] = 0x90;
  buffer[1] = msg_id;
  return buffer + 2;
}

static packet_format_t default_frame_format = {.check_start_bytes = basic_frame_check_start_bytes,
                                               .process_header_byte = basic_frame_process_header_byte,
                                               .get_msg_id = basic_frame_get_msg_id,
                                               .get_full_packet_length = basic_frame_get_full_packet_length,
                                               .validate_packet = basic_frame_validate_packet,
                                               .encode = basic_frame_encode,
                                               .encode_reserve = basic_frame_reserve,
                                               .encode_finsish = basic_frame_finish};
