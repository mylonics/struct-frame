#pragma once

#include "struct_frame_parser.h"
#include "struct_frame_types.h"

class StructFrameDevice : public struct_buffer {
 public:
  StructFrameDevice(struct_frame_config config)
      : struct_buffer{config, nullptr, 0, 0, false, 0, LOOKING_FOR_START_BYTE, 0, {false, 0, 0}},
        parser_result_{config, false, 0, 0, false, {0, 0}} {}

  void RunRx() {
    uint8_t *buffer;
    size_t buffer_size;
    GetArray(buffer, buffer_size);
    if (buffer && buffer_size) {
      while (!parser_result_.finished) {
        if (parse_buffer(buffer, buffer_size, &parser_result_)) {
          if (parser_result_.valid) {
            HandleResult();
          }
        }
      }
    }
  }

  void RunTx() { PutArray(struct_buffer::data, struct_buffer::max_size, struct_buffer::size); }

 protected:
  void Init() {
    size_t dummy = 0;
    PutArray(struct_buffer::data, struct_buffer::max_size, dummy);
  }

  // Put Array must accept the full buffer of data and returns a pointer to either a new buffer or the same buffer
  // that is free
  virtual void PutArray(uint8_t *&buffer, size_t &max_length, size_t &length) = 0;

  // Get array, a pointer to an array and refernce to the array length is pased and mutated by this function
  virtual void GetArray(uint8_t *&buffer, size_t &length) = 0;

  virtual void HandleResult() = 0;
  buffer_parser_result_t parser_result_;
};
