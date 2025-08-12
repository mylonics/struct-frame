
export class msg_id_len_t {
  valid = false;
  len = 0;
  msg_id = 0;
}

export type GetMsgIdLenType = (c: number, msg_id_len: msg_id_len_t) => boolean;
export type ValidatePacketType = (buffer: Uint8Array, msg_id_len: msg_id_len_t) => boolean;

export interface parser_functions_t {
  get_msg_id_len: GetMsgIdLenType;
  validate_packet: ValidatePacketType;
}

export interface struct_frame_config {
  has_crc: number;
  has_len: number;
  start_byte: number;
  parser_funcs?: parser_functions_t;
}

export enum ParserState {
  LOOKING_FOR_START_BYTE = 0,
  GETTING_LENGTH_MSG_AND_ID = 1,
  GETTING_PAYLOAD = 2
};

export const basic_frame_config: struct_frame_config = { has_crc: 0, has_len: 0, start_byte: 0x90 };

export class struct_frame_buffer {
  // Used for framing and parsing
  config: struct_frame_config = basic_frame_config;
  data: Uint8Array;
  size = 0;
  in_progress = false;

  // Used for framing
  crc_start_loc = 0;

  // Used for parsing
  state: ParserState = ParserState.LOOKING_FOR_START_BYTE;
  payload_len = 0;
  msg_id_len: msg_id_len_t = new msg_id_len_t();
  msg_data: Buffer = Buffer.allocUnsafe(0);

  constructor(public max_size: number, buffer?: Uint8Array) {
    if (buffer) {
      this.data = buffer;
    } else {
      this.data = new Uint8Array(max_size);
    }
  }
}

export class buffer_parser_result_t {
  config: struct_frame_config = basic_frame_config;
  found = false;
  valid = false;
  msg_data: Buffer = Buffer.allocUnsafe(0);
  r_loc = 0;
  finished = false;
  msg_id_len: msg_id_len_t = new msg_id_len_t();
}

// https://github.com/serge-sans-paille/frozen
// https://www.npmjs.com/package/typed-struct

//#define default_parser { 0, 0, 0x90 }
//
//#define zero_initialized_parser_result { default_parser, false, false, 0, 0, false, { 0, 0} };
//
//#define CREATE_DEFAULT_STRUCT_BUFFER(name, size) \
//  uint8_t name##_buffer[size]; \
//  struct_buffer name = { default_parser, name##_buffer, size, 0, 0, false, 0, 0, 0, 0, NULL }

export interface checksum_t {
  byte1: number;
  byte2: number;
}
