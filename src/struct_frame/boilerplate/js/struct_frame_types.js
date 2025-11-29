/**
 * Struct frame types for JavaScript.
 * Human-readable JavaScript version of the TypeScript boilerplate.
 */
"use strict";

class msg_id_len_t {
  constructor() {
    this.valid = false;
    this.len = 0;
    this.msg_id = 0;
  }
}
module.exports.msg_id_len_t = msg_id_len_t;

const ParserState = Object.freeze({
  LOOKING_FOR_START_BYTE: 0,
  GETTING_LENGTH_MSG_AND_ID: 1,
  GETTING_PAYLOAD: 2
});
module.exports.ParserState = ParserState;

const basic_frame_config = { has_crc: 0, has_len: 0, start_byte: 0x90 };
module.exports.basic_frame_config = basic_frame_config;

class struct_frame_buffer {
  constructor(max_size, buffer) {
    this.max_size = max_size;
    // Used for framing and parsing
    this.config = basic_frame_config;
    if (buffer) {
      this.data = buffer;
    } else {
      this.data = new Uint8Array(max_size);
    }
    this.size = 0;
    this.in_progress = false;

    // Used for framing
    this.crc_start_loc = 0;

    // Used for parsing
    this.state = ParserState.LOOKING_FOR_START_BYTE;
    this.payload_len = 0;
    this.msg_id_len = new msg_id_len_t();
    this.msg_data = Buffer.allocUnsafe(0);
  }
}
module.exports.struct_frame_buffer = struct_frame_buffer;

class buffer_parser_result_t {
  constructor() {
    this.config = basic_frame_config;
    this.found = false;
    this.valid = false;
    this.msg_data = Buffer.allocUnsafe(0);
    this.r_loc = 0;
    this.finished = false;
    this.msg_id_len = new msg_id_len_t();
  }
}
module.exports.buffer_parser_result_t = buffer_parser_result_t;
