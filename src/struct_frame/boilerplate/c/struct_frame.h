#pragma once
#include "stdbool.h"
#include "stdint.h"
#include "string.h"
#include "struct_frame_types.h"

static inline struct checksum_t fletcher_checksum_calculation(uint8_t *buffer, uint8_t data_length) {
  checksum_t checksum{};

  for (int i = 0; i < data_length; i++) {
    checksum.byte1 += buffer[i];
    checksum.byte2 += checksum.byte1;
  }
  return checksum;
}

static inline bool msg_encode(msg_encode_buffer *buffer, packet_format_t *format, void *msg, uint8_t msg_id,
                              uint8_t msg_size) {
  if (buffer->in_progress) {
    return false;
  }
  buffer->in_progress = true;
  buffer->size += format->encode(buffer, msg_id, msg, msg_size);
  buffer->in_progress = false;
  return true;
}

static inline bool *msg_reserve(msg_encode_buffer *buffer, packet_format_t *format, uint8_t msg_id, uint8_t msg_size) {
  if (buffer->in_progress) {
    return false;
  }
  buffer->in_progress = true;
  void *out = format->encode_reserve(buffer, msg_id, msg_size);
  return out;
}

static inline bool msg_finish(msg_encode_buffer *buffer, packet_format_t *format, uint8_t msg_size) {
  if (buffer->in_progress == false) {
    return false;
  }

  buffer->size += format->encode_finsish(buffer, msg_size);
  buffer->in_progress = false;
  return true;
}

#define MESSAGE_HELPER(funcname, name, msg_size, msg_id)                                     \
  static inline bool funcname##_encode(struct_buffer *buffer, name *name##_obj) {            \
    return msg_encode(buffer, name##_obj, msg_id, msg_size);                                 \
  }                                                                                          \
  static inline bool funcname##_reserve(struct_buffer *buffer, name **msg) {                 \
    void *ptr = msg_reserve(buffer, msg_id, msg_size);                                       \
    if (ptr) {                                                                               \
      *msg = (name *)ptr;                                                                    \
      return true;                                                                           \
    }                                                                                        \
    return false;                                                                            \
  }                                                                                          \
  static inline bool funcname##_finish(struct_buffer *buffer) { return msg_finish(buffer); } \
  static inline name funcname##_get(uint8_t *buffer) {                                       \
    name msg = *(name *)(buffer);                                                            \
    return msg;                                                                              \
  }                                                                                          \
  static inline name funcname##_get(msg_info_t result) {                                     \
    name msg = *(name *)(result.msg_loc);                                                    \
    return msg;                                                                              \
  }                                                                                          \
  static inline name *funcname##_get_ref(uint8_t *buffer) { return (name *)(buffer); }       \
  static inline name *funcname##_get_ref(msg_info_t result) { return (name *)(result.msg_loc); }
