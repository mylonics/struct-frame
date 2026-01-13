/**
 * Payload Types - Message structure configurations (JavaScript)
 * Payload types define message structure (length fields, CRC, extra fields)
 *
 * This file mirrors the C++ payload_types.hpp structure.
 */

/** Payload type enumeration */
const PayloadType = {
  MINIMAL: 0,                      // [MSG_ID] [PACKET]
  DEFAULT: 1,                      // [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
  EXTENDED_MSG_IDS: 2,             // [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
  EXTENDED_LENGTH: 3,              // [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2]
  EXTENDED: 4,                     // [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
  SYS_COMP: 5,                     // [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
  SEQ: 6,                          // [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
  MULTI_SYSTEM_STREAM: 7,          // [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
  EXTENDED_MULTI_SYSTEM_STREAM: 8  // [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
};

/** Maximum payload type value (for range checking) */
const MAX_PAYLOAD_TYPE_VALUE = 8;

/** Calculate header size (fields before payload, excluding start bytes) */
function payloadHeaderSize(config) {
  let size = 1;  // msg_id always present
  if (config.hasLength) size += config.lengthBytes;
  if (config.hasSeq) size += 1;
  if (config.hasSysId) size += 1;
  if (config.hasCompId) size += 1;
  if (config.hasPkgId) size += 1;
  return size;
}

/** Calculate footer size */
function payloadFooterSize(config) {
  return config.crcBytes;
}

/** Calculate total overhead (header + footer, excluding start bytes) */
function payloadOverhead(config) {
  return payloadHeaderSize(config) + payloadFooterSize(config);
}

/** Calculate max payload size based on length field */
function payloadMaxPayload(config) {
  if (config.lengthBytes === 1) return 255;
  if (config.lengthBytes === 2) return 65535;
  return 0;  // No length field - requires external knowledge
}

/** Pre-defined payload configurations */
const PAYLOAD_MINIMAL_CONFIG = {
  payloadType: PayloadType.MINIMAL,
  hasCrc: false,
  crcBytes: 0,
  hasLength: false,
  lengthBytes: 0,
  hasSeq: false,
  hasSysId: false,
  hasCompId: false,
  hasPkgId: false,
};

const PAYLOAD_DEFAULT_CONFIG = {
  payloadType: PayloadType.DEFAULT,
  hasCrc: true,
  crcBytes: 2,
  hasLength: true,
  lengthBytes: 1,
  hasSeq: false,
  hasSysId: false,
  hasCompId: false,
  hasPkgId: false,
};

const PAYLOAD_EXTENDED_MSG_IDS_CONFIG = {
  payloadType: PayloadType.EXTENDED_MSG_IDS,
  hasCrc: true,
  crcBytes: 2,
  hasLength: true,
  lengthBytes: 1,
  hasSeq: false,
  hasSysId: false,
  hasCompId: false,
  hasPkgId: true,
};

const PAYLOAD_EXTENDED_LENGTH_CONFIG = {
  payloadType: PayloadType.EXTENDED_LENGTH,
  hasCrc: true,
  crcBytes: 2,
  hasLength: true,
  lengthBytes: 2,
  hasSeq: false,
  hasSysId: false,
  hasCompId: false,
  hasPkgId: false,
};

const PAYLOAD_EXTENDED_CONFIG = {
  payloadType: PayloadType.EXTENDED,
  hasCrc: true,
  crcBytes: 2,
  hasLength: true,
  lengthBytes: 2,
  hasSeq: false,
  hasSysId: false,
  hasCompId: false,
  hasPkgId: true,
};

const PAYLOAD_SYS_COMP_CONFIG = {
  payloadType: PayloadType.SYS_COMP,
  hasCrc: true,
  crcBytes: 2,
  hasLength: true,
  lengthBytes: 1,
  hasSeq: false,
  hasSysId: true,
  hasCompId: true,
  hasPkgId: false,
};

const PAYLOAD_SEQ_CONFIG = {
  payloadType: PayloadType.SEQ,
  hasCrc: true,
  crcBytes: 2,
  hasLength: true,
  lengthBytes: 1,
  hasSeq: true,
  hasSysId: false,
  hasCompId: false,
  hasPkgId: false,
};

const PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG = {
  payloadType: PayloadType.MULTI_SYSTEM_STREAM,
  hasCrc: true,
  crcBytes: 2,
  hasLength: true,
  lengthBytes: 1,
  hasSeq: true,
  hasSysId: true,
  hasCompId: true,
  hasPkgId: false,
};

const PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG = {
  payloadType: PayloadType.EXTENDED_MULTI_SYSTEM_STREAM,
  hasCrc: true,
  crcBytes: 2,
  hasLength: true,
  lengthBytes: 2,
  hasSeq: true,
  hasSysId: true,
  hasCompId: true,
  hasPkgId: true,
};

module.exports = {
  PayloadType,
  MAX_PAYLOAD_TYPE_VALUE,
  payloadHeaderSize,
  payloadFooterSize,
  payloadOverhead,
  payloadMaxPayload,
  PAYLOAD_MINIMAL_CONFIG,
  PAYLOAD_DEFAULT_CONFIG,
  PAYLOAD_EXTENDED_MSG_IDS_CONFIG,
  PAYLOAD_EXTENDED_LENGTH_CONFIG,
  PAYLOAD_EXTENDED_CONFIG,
  PAYLOAD_SYS_COMP_CONFIG,
  PAYLOAD_SEQ_CONFIG,
  PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG,
  PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG,
};
