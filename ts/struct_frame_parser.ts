import { get_message_length } from './struct_frame_gen';
import * as sf_types from './struct_frame_types';

function parse_default_format_validate(buffer: Uint8Array, msg_id_len: sf_types.msg_id_len_t): boolean {
  return true;
}

function parse_default_format_char_for_len_id(c: number, msg_id_len: sf_types.msg_id_len_t): boolean {
  msg_id_len.msg_id = c;
  msg_id_len.len = get_message_length(c);
  return true;
}

const default_parser_functions: sf_types.parser_functions_t = { get_msg_id_len: parse_default_format_char_for_len_id, validate_packet: parse_default_format_validate };

function parse_char_for_start_byte(config: sf_types.struct_frame_config, c: number): sf_types.parser_functions_t | undefined {
  if (config.start_byte == c) {
    return default_parser_functions;
  }
  return;
}

export function parse_char(pb: sf_types.struct_frame_buffer, c: number): boolean {
  let parse_func_ptr: sf_types.parser_functions_t | undefined = undefined;
  switch (pb.state) {
    case sf_types.ParserState.LOOKING_FOR_START_BYTE:
      parse_func_ptr = parse_char_for_start_byte(pb.config, c);
      if (parse_func_ptr) {
        pb.config.parser_funcs = parse_func_ptr;
        pb.state = sf_types.ParserState.GETTING_LENGTH_MSG_AND_ID;
      }
      break;

    case sf_types.ParserState.GETTING_LENGTH_MSG_AND_ID:
      if (pb.config.parser_funcs && pb.config.parser_funcs.get_msg_id_len(c, pb.msg_id_len)) {
        pb.state = sf_types.ParserState.GETTING_PAYLOAD;
        pb.size = 0;
      }
      break;

    case sf_types.ParserState.GETTING_PAYLOAD:
      pb.data[pb.size] = c;
      pb.size++;
      if (pb.size >= pb.msg_id_len.len) {
        pb.msg_data = Buffer.from(pb.data, 0, pb.size)
        pb.state = sf_types.ParserState.LOOKING_FOR_START_BYTE;
        if (pb.config.parser_funcs) {
          return pb.config.parser_funcs.validate_packet(pb.data, pb.msg_id_len);
        }
        return false;
      }
      break;

    default:
      break;
  }

  return false;
}

export function parse_buffer(buffer: Uint8Array, size: number, parser_result: sf_types.buffer_parser_result_t): boolean {
  let state: sf_types.ParserState = sf_types.ParserState.LOOKING_FOR_START_BYTE;
  let parse_func_ptr: sf_types.parser_functions_t | undefined;
  for (let i = parser_result.r_loc; i < size; i++) {
    switch (state) {
      case sf_types.ParserState.LOOKING_FOR_START_BYTE:
        parse_func_ptr = parse_char_for_start_byte(parser_result.config, buffer[i]);
        if (parse_func_ptr) {
          state = sf_types.ParserState.GETTING_LENGTH_MSG_AND_ID;
        }
        break;

      case sf_types.ParserState.GETTING_LENGTH_MSG_AND_ID:
        if (parse_func_ptr && parse_func_ptr.get_msg_id_len(buffer[i], parser_result.msg_id_len)) {
          state = sf_types.ParserState.GETTING_PAYLOAD;
        }
        break;

      case sf_types.ParserState.GETTING_PAYLOAD:
        parser_result.msg_data = Buffer.from(buffer, i, (i + parser_result.msg_id_len.len));
        parser_result.r_loc = i + parser_result.msg_id_len.len;
        parser_result.found = true;
        if (parse_func_ptr && parse_func_ptr.validate_packet(parser_result.msg_data, parser_result.msg_id_len)) {
          parser_result.valid = true;
          return true;
        }
        else {
          parser_result.valid = false;
          return true;
        }
        break;

      default:
        break;
    }
  }
  return false;
}
