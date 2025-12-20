/**
 * Compatibility layer for frame parser functions (TypeScript)
 * Provides encode/decode functions composed from separated header and payload types
 */

import { BASIC_START_BYTE } from './frame_headers/base';
import { getTinyStartByte, isTinyStartByte } from './frame_headers/header_tiny';
import { getBasicSecondStartByte, isBasicSecondStartByte } from './frame_headers/header_basic';
import { fletcher_checksum, FrameMsgInfo } from './frame_base';

/* Basic + Default */
export function basic_default_encode(
  msgId: number,
  msg: Uint8Array
): Uint8Array {
  const headerSize = 4; /* [0x90] [0x71] [LEN] [MSG_ID] */
  const footerSize = 2; /* [CRC1] [CRC2] */
  const totalSize = headerSize + msg.length + footerSize;

  if (msg.length > 255) {
    return new Uint8Array(0);
  }

  const buffer = new Uint8Array(totalSize);
  buffer[0] = BASIC_START_BYTE;
  buffer[1] = getBasicSecondStartByte(1); // PayloadType.DEFAULT = 1
  buffer[2] = msg.length;
  buffer[3] = msgId;
  buffer.set(msg, headerSize);

  const ck = fletcher_checksum(buffer, 2, headerSize + msg.length);
  buffer[totalSize - 2] = ck[0];
  buffer[totalSize - 1] = ck[1];

  return buffer;
}

export function basic_default_validate_packet(
  buffer: Uint8Array
): FrameMsgInfo {
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
export function tiny_minimal_encode(
  msgId: number,
  msg: Uint8Array
): Uint8Array {
  const headerSize = 2; /* [0x70] [MSG_ID] */
  const totalSize = headerSize + msg.length;

  const buffer = new Uint8Array(totalSize);
  buffer[0] = getTinyStartByte(0); // PayloadType.MINIMAL = 0
  buffer[1] = msgId;
  buffer.set(msg, headerSize);

  return buffer;
}

export function tiny_minimal_validate_packet(buffer: Uint8Array): FrameMsgInfo {
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
export function basic_extended_encode(
  msgId: number,
  msg: Uint8Array
): Uint8Array {
  const headerSize = 6; /* [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] */
  const footerSize = 2; /* [CRC1] [CRC2] */
  const totalSize = headerSize + msg.length + footerSize;

  if (msg.length > 65535) {
    return new Uint8Array(0);
  }

  const buffer = new Uint8Array(totalSize);
  buffer[0] = BASIC_START_BYTE;
  buffer[1] = getBasicSecondStartByte(4); // PayloadType.EXTENDED = 4
  buffer[2] = msg.length & 0xff;
  buffer[3] = (msg.length >> 8) & 0xff;
  buffer[4] = 0; // PKG_ID = 0
  buffer[5] = msgId;
  buffer.set(msg, headerSize);

  const ck = fletcher_checksum(buffer, 2, headerSize + msg.length);
  buffer[totalSize - 2] = ck[0];
  buffer[totalSize - 1] = ck[1];

  return buffer;
}

export function basic_extended_validate_packet(buffer: Uint8Array): FrameMsgInfo {
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
export function basic_extended_multi_system_stream_encode(
  msgId: number,
  msg: Uint8Array
): Uint8Array {
  const headerSize = 9; /* [0x90] [0x78] [SEQ] [SYS] [COMP] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] */
  const footerSize = 2; /* [CRC1] [CRC2] */
  const totalSize = headerSize + msg.length + footerSize;

  if (msg.length > 65535) {
    return new Uint8Array(0);
  }

  const buffer = new Uint8Array(totalSize);
  buffer[0] = BASIC_START_BYTE;
  buffer[1] = getBasicSecondStartByte(8); // PayloadType.EXTENDED_MULTI_SYSTEM_STREAM = 8
  buffer[2] = 0; // SEQ = 0
  buffer[3] = 0; // SYS_ID = 0
  buffer[4] = 0; // COMP_ID = 0
  buffer[5] = msg.length & 0xff;
  buffer[6] = (msg.length >> 8) & 0xff;
  buffer[7] = 0; // PKG_ID = 0
  buffer[8] = msgId;
  buffer.set(msg, headerSize);

  const ck = fletcher_checksum(buffer, 2, headerSize + msg.length);
  buffer[totalSize - 2] = ck[0];
  buffer[totalSize - 1] = ck[1];

  return buffer;
}

export function basic_extended_multi_system_stream_validate_packet(
  buffer: Uint8Array
): FrameMsgInfo {
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
export function basic_minimal_encode(
  msgId: number,
  msg: Uint8Array
): Uint8Array {
  const headerSize = 3; /* [0x90] [0x70] [MSG_ID] */
  const totalSize = headerSize + msg.length;

  const buffer = new Uint8Array(totalSize);
  buffer[0] = BASIC_START_BYTE;
  buffer[1] = getBasicSecondStartByte(0); // PayloadType.MINIMAL = 0
  buffer[2] = msgId;
  buffer.set(msg, headerSize);

  return buffer;
}

export function basic_minimal_validate_packet(buffer: Uint8Array): FrameMsgInfo {
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
export function tiny_default_encode(
  msgId: number,
  msg: Uint8Array
): Uint8Array {
  const headerSize = 3; /* [0x71] [LEN] [MSG_ID] */
  const footerSize = 2; /* [CRC1] [CRC2] */
  const totalSize = headerSize + msg.length + footerSize;

  if (msg.length > 255) {
    return new Uint8Array(0);
  }

  const buffer = new Uint8Array(totalSize);
  buffer[0] = getTinyStartByte(1); // PayloadType.DEFAULT = 1
  buffer[1] = msg.length;
  buffer[2] = msgId;
  buffer.set(msg, headerSize);

  const ck = fletcher_checksum(buffer, 1, headerSize + msg.length);
  buffer[totalSize - 2] = ck[0];
  buffer[totalSize - 1] = ck[1];

  return buffer;
}

export function tiny_default_validate_packet(buffer: Uint8Array): FrameMsgInfo {
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

// Create wrapper classes for backward compatibility
export class BasicDefault {
  static encodeMsg = basic_default_encode;
  static validatePacket = basic_default_validate_packet;
}

export class TinyMinimal {
  static encodeMsg = tiny_minimal_encode;
  static validatePacket = tiny_minimal_validate_packet;
}

export class BasicExtended {
  static encodeMsg = basic_extended_encode;
  static validatePacket = basic_extended_validate_packet;
}

export class BasicExtendedMultiSystemStream {
  static encodeMsg = basic_extended_multi_system_stream_encode;
  static validatePacket = basic_extended_multi_system_stream_validate_packet;
}

export class BasicMinimal {
  static encodeMsg = basic_minimal_encode;
  static validatePacket = basic_minimal_validate_packet;
}

export class TinyDefault {
  static encodeMsg = tiny_default_encode;
  static validatePacket = tiny_default_validate_packet;
}
