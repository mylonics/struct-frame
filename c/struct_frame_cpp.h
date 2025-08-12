#pragma once

#include "struct_frame_parser.h"
#include "struct_frame_types.h"

class StructFrameDevice : public msg_encode_buffer {
 public:
  StructFrameDevice(packet_format_t formats[], packet_definitions_t defines[])
      : msg_encode_buffer{0, 0, 0},
        packet_state_{LOOKING_FOR_START_BYTE, 0, formats, defines, nullptr, 0, 0, 0, false, 0} {}

  void RunRx() {
    GetArray(packet_state_.buffer, packet_state_.buffer_size);
    if (packet_state_.buffer && packet_state_.buffer_size) {
      while (!packet_state_.finished) {
        msg_info_t info = parse_buffer(&packet_state_);
        if (info.valid) {
          HandleResult(info);
        }
      }
    }
  }

  void RunTx() { PutArray(msg_encode_buffer::data, msg_encode_buffer::max_size, msg_encode_buffer::size); }

 protected:
  void Init() {
    size_t dummy = 0;
    PutArray(msg_encode_buffer::data, msg_encode_buffer::max_size, dummy);
  }

  // Put Array must accept the full buffer of data and returns a pointer to either a new buffer or the same buffer
  // that is free
  virtual void PutArray(uint8_t *&buffer, size_t &max_length, size_t &length) = 0;

  // Get array, a pointer to an array and refernce to the array length is pased and mutated by this function
  virtual void GetArray(uint8_t *&buffer, size_t &length) = 0;

  virtual void HandleResult(msg_info_t info) = 0;
  packet_state_t packet_state_;
};
