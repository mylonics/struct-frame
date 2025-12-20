/**
 * Compatibility layer for frame parser functions (JavaScript)
 * Provides encode/decode functions composed from separated header and payload types
 */

const { BASIC_START_BYTE } = require('./frame_headers/base');
const { getTinyStartByte, isTinyStartByte } = require('./frame_headers/header_tiny');
const { getBasicSecondStartByte, isBasicSecondStartByte } = require('./frame_headers/header_basic');
const { fletcher_checksum } = require('./frame_base');

/* Basic + Default */
function basic_default_encode(msgId, msg) {
  const headerSize = 4;
  const footerSize = 2;
  const totalSize = headerSize + msg.length + footerSize;

  if (msg.length > 255) {
    return new Uint8Array(0);
  }

  const buffer = new Uint8Array(totalSize);
  buffer[0] = BASIC_START_BYTE;
  buffer[1] = getBasicSecondStartByte(1);
  buffer[2] = msg.length;
  buffer[3] = msgId;
  buffer.set(msg, headerSize);

  const ck = fletcher_checksum(buffer, 2, headerSize + msg.length);
  buffer[totalSize - 2] = ck[0];
  buffer[totalSize - 1] = ck[1];

  return buffer;
}

function basic_default_validate_packet(buffer) {
  if (
    buffer.length < 6 ||
    buffer[0] !== BASIC_START_BYTE ||
    !isBasicSecondStartByte(buffer[1])
  ) {
    return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
  }

  const msgLen = buffer[2];
  const msgId = buffer[3];
  const totalSize = 4 + msgLen + 2;

  if (buffer.length < totalSize) {
    return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
  }

  const ck = fletcher_checksum(buffer, 2, 4 + msgLen);
  if (ck[0] === buffer[totalSize - 2] && ck[1] === buffer[totalSize - 1]) {
    return {
      valid: true,
      msg_id: msgId,
      msg_len: msgLen,
      msg_data: buffer.slice(4, 4 + msgLen),
    };
  }

  return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
}

/* Tiny + Minimal */
function tiny_minimal_encode(msgId, msg) {
  const headerSize = 2;
  const totalSize = headerSize + msg.length;

  const buffer = new Uint8Array(totalSize);
  buffer[0] = getTinyStartByte(0);
  buffer[1] = msgId;
  buffer.set(msg, headerSize);

  return buffer;
}

function tiny_minimal_validate_packet(buffer) {
  if (buffer.length < 2 || !isTinyStartByte(buffer[0])) {
    return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
  }

  const msgId = buffer[1];
  const msgLen = buffer.length - 2;

  return {
    valid: true,
    msg_id: msgId,
    msg_len: msgLen,
    msg_data: buffer.slice(2),
  };
}

/* Basic + Extended */
function basic_extended_encode(msgId, msg) {
  const headerSize = 6;
  const footerSize = 2;
  const totalSize = headerSize + msg.length + footerSize;

  if (msg.length > 65535) {
    return new Uint8Array(0);
  }

  const buffer = new Uint8Array(totalSize);
  buffer[0] = BASIC_START_BYTE;
  buffer[1] = getBasicSecondStartByte(4);
  buffer[2] = msg.length & 0xff;
  buffer[3] = (msg.length >> 8) & 0xff;
  buffer[4] = 0;
  buffer[5] = msgId;
  buffer.set(msg, headerSize);

  const ck = fletcher_checksum(buffer, 2, headerSize + msg.length);
  buffer[totalSize - 2] = ck[0];
  buffer[totalSize - 1] = ck[1];

  return buffer;
}

function basic_extended_validate_packet(buffer) {
  if (
    buffer.length < 8 ||
    buffer[0] !== BASIC_START_BYTE ||
    !isBasicSecondStartByte(buffer[1])
  ) {
    return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
  }

  const msgLen = buffer[2] | (buffer[3] << 8);
  const msgId = buffer[5];
  const totalSize = 6 + msgLen + 2;

  if (buffer.length < totalSize) {
    return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
  }

  const ck = fletcher_checksum(buffer, 2, 6 + msgLen);
  if (ck[0] === buffer[totalSize - 2] && ck[1] === buffer[totalSize - 1]) {
    return {
      valid: true,
      msg_id: msgId,
      msg_len: msgLen,
      msg_data: buffer.slice(6, 6 + msgLen),
    };
  }

  return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
}

/* Basic + Extended Multi System Stream */
function basic_extended_multi_system_stream_encode(msgId, msg) {
  const headerSize = 9;
  const footerSize = 2;
  const totalSize = headerSize + msg.length + footerSize;

  if (msg.length > 65535) {
    return new Uint8Array(0);
  }

  const buffer = new Uint8Array(totalSize);
  buffer[0] = BASIC_START_BYTE;
  buffer[1] = getBasicSecondStartByte(8);
  buffer[2] = 0;
  buffer[3] = 0;
  buffer[4] = 0;
  buffer[5] = msg.length & 0xff;
  buffer[6] = (msg.length >> 8) & 0xff;
  buffer[7] = 0;
  buffer[8] = msgId;
  buffer.set(msg, headerSize);

  const ck = fletcher_checksum(buffer, 2, headerSize + msg.length);
  buffer[totalSize - 2] = ck[0];
  buffer[totalSize - 1] = ck[1];

  return buffer;
}

function basic_extended_multi_system_stream_validate_packet(buffer) {
  if (
    buffer.length < 11 ||
    buffer[0] !== BASIC_START_BYTE ||
    !isBasicSecondStartByte(buffer[1])
  ) {
    return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
  }

  const msgLen = buffer[5] | (buffer[6] << 8);
  const msgId = buffer[8];
  const totalSize = 9 + msgLen + 2;

  if (buffer.length < totalSize) {
    return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
  }

  const ck = fletcher_checksum(buffer, 2, 9 + msgLen);
  if (ck[0] === buffer[totalSize - 2] && ck[1] === buffer[totalSize - 1]) {
    return {
      valid: true,
      msg_id: msgId,
      msg_len: msgLen,
      msg_data: buffer.slice(9, 9 + msgLen),
    };
  }

  return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
}

/* Basic + Minimal */
function basic_minimal_encode(msgId, msg) {
  const headerSize = 3;
  const totalSize = headerSize + msg.length;

  const buffer = new Uint8Array(totalSize);
  buffer[0] = BASIC_START_BYTE;
  buffer[1] = getBasicSecondStartByte(0);
  buffer[2] = msgId;
  buffer.set(msg, headerSize);

  return buffer;
}

function basic_minimal_validate_packet(buffer) {
  if (
    buffer.length < 3 ||
    buffer[0] !== BASIC_START_BYTE ||
    !isBasicSecondStartByte(buffer[1])
  ) {
    return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
  }

  const msgId = buffer[2];
  const msgLen = buffer.length - 3;

  return {
    valid: true,
    msg_id: msgId,
    msg_len: msgLen,
    msg_data: buffer.slice(3),
  };
}

/* Tiny + Default */
function tiny_default_encode(msgId, msg) {
  const headerSize = 3;
  const footerSize = 2;
  const totalSize = headerSize + msg.length + footerSize;

  if (msg.length > 255) {
    return new Uint8Array(0);
  }

  const buffer = new Uint8Array(totalSize);
  buffer[0] = getTinyStartByte(1);
  buffer[1] = msg.length;
  buffer[2] = msgId;
  buffer.set(msg, headerSize);

  const ck = fletcher_checksum(buffer, 1, headerSize + msg.length);
  buffer[totalSize - 2] = ck[0];
  buffer[totalSize - 1] = ck[1];

  return buffer;
}

function tiny_default_validate_packet(buffer) {
  if (buffer.length < 5 || !isTinyStartByte(buffer[0])) {
    return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
  }

  const msgLen = buffer[1];
  const msgId = buffer[2];
  const totalSize = 3 + msgLen + 2;

  if (buffer.length < totalSize) {
    return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
  }

  const ck = fletcher_checksum(buffer, 1, 3 + msgLen);
  if (ck[0] === buffer[totalSize - 2] && ck[1] === buffer[totalSize - 1]) {
    return {
      valid: true,
      msg_id: msgId,
      msg_len: msgLen,
      msg_data: buffer.slice(3, 3 + msgLen),
    };
  }

  return { valid: false, msg_id: 0, msg_len: 0, msg_data: new Uint8Array(0) };
}

// Export wrapper classes for backward compatibility
const BasicDefault = {
  encode: basic_default_encode,
  validate_packet: basic_default_validate_packet,
};

const TinyMinimal = {
  encode: tiny_minimal_encode,
  validate_packet: tiny_minimal_validate_packet,
};

const BasicExtended = {
  encode: basic_extended_encode,
  validate_packet: basic_extended_validate_packet,
};

const BasicExtendedMultiSystemStream = {
  encode: basic_extended_multi_system_stream_encode,
  validate_packet: basic_extended_multi_system_stream_validate_packet,
};

const BasicMinimal = {
  encode: basic_minimal_encode,
  validate_packet: basic_minimal_validate_packet,
};

const TinyDefault = {
  encode: tiny_default_encode,
  validate_packet: tiny_default_validate_packet,
};

module.exports = {
  basic_default_encode,
  basic_default_validate_packet,
  tiny_minimal_encode,
  tiny_minimal_validate_packet,
  basic_extended_encode,
  basic_extended_validate_packet,
  basic_extended_multi_system_stream_encode,
  basic_extended_multi_system_stream_validate_packet,
  basic_minimal_encode,
  basic_minimal_validate_packet,
  tiny_default_encode,
  tiny_default_validate_packet,
  BasicDefault,
  TinyMinimal,
  BasicExtended,
  BasicExtendedMultiSystemStream,
  BasicMinimal,
  TinyDefault,
};
