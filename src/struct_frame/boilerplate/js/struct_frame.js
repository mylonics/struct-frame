/**
 * Struct frame framing functions for JavaScript.
 * Human-readable JavaScript version of the TypeScript boilerplate.
 */
"use strict";

const { Struct } = require('./struct_base');

function fletcher_checksum_calculation(buffer, data_length) {
  const checksum = { byte1: 0, byte2: 0 };

  for (let i = 0; i < data_length; i++) {
    checksum.byte1 += buffer[i];
    checksum.byte2 += checksum.byte1;
  }
  return checksum;
}

function msg_encode(buffer, msg, msgid) {
  buffer.data[buffer.size++] = buffer.config.start_byte;
  buffer.crc_start_loc = buffer.size;
  buffer.data[buffer.size++] = msgid;

  if (buffer.config.has_len) {
    buffer.data[buffer.size++] = msg.getSize();
  }
  const rawData = Struct.raw(msg);
  for (let i = 0; i < rawData.length; i++) {
    buffer.data[buffer.size++] = rawData[i];
  }

  if (buffer.config.has_crc) {
    const crc = fletcher_checksum_calculation(buffer.data.slice(buffer.crc_start_loc), buffer.crc_start_loc + rawData.length);
    buffer.data[buffer.size++] = crc.byte1;
    buffer.data[buffer.size++] = crc.byte2;
  }
}
module.exports.msg_encode = msg_encode;

function msg_reserve(buffer, msg_id, msg_size) {
  throw new Error('Function Unimplemented');

  if (buffer.in_progress) {
    return;
  }
  buffer.in_progress = true;
  buffer.data[buffer.size++] = buffer.config.start_byte;

  buffer.data[buffer.size++] = msg_id;
  if (buffer.config.has_len) {
    buffer.data[buffer.size++] = msg_size;
  }

  const ret = Buffer.from(buffer.data.slice(buffer.size, buffer.size + msg_size));
  buffer.size += msg_size;
  return ret;
}
module.exports.msg_reserve = msg_reserve;

function msg_finish(buffer) {
  throw new Error('Function Unimplemented');

  if (buffer.config.has_crc) {
    const crc = fletcher_checksum_calculation(buffer.data.slice(buffer.crc_start_loc), buffer.crc_start_loc - buffer.size);
    buffer.data[buffer.size++] = crc.byte1;
    buffer.data[buffer.size++] = crc.byte2;
    buffer.size += 2;
  }
  buffer.in_progress = false;
}
module.exports.msg_finish = msg_finish;
