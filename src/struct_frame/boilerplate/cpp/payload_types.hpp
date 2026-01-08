/* Payload Types - Message structure configurations (C++) */
/* Payload types define message structure (length fields, CRC, extra fields) */

#pragma once

#include <cstdint>

namespace FrameParsers {
namespace PayloadTypes {

/* Payload type enumeration */
enum class PayloadType : uint8_t {
  MINIMAL = 0,                     /* [MSG_ID] [PACKET] */
  DEFAULT = 1,                     /* [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
  EXTENDED_MSG_IDS = 2,            /* [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
  EXTENDED_LENGTH = 3,             /* [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2] */
  EXTENDED = 4,                    /* [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
  SYS_COMP = 5,                    /* [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
  SEQ = 6,                         /* [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
  MULTI_SYSTEM_STREAM = 7,         /* [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
  EXTENDED_MULTI_SYSTEM_STREAM = 8 /* [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
};

/* Maximum payload type value (for range checking) */
constexpr uint8_t MAX_PAYLOAD_TYPE_VALUE = 8;

/**
 * Compile-time configuration for a payload type.
 * All members are constexpr for zero runtime overhead.
 */
struct PayloadConfig {
  PayloadType payload_type;
  bool has_crc;
  uint8_t crc_bytes; /* 0 or 2 */
  bool has_length;
  uint8_t length_bytes; /* 0, 1, or 2 */
  bool has_seq;
  bool has_sys_id;
  bool has_comp_id;
  bool has_pkg_id;

  /* Calculate header size (fields before payload, excluding start bytes) */
  constexpr uint8_t header_size() const {
    uint8_t size = 1; /* msg_id always present */
    if (has_length) size += length_bytes;
    if (has_seq) size += 1;
    if (has_sys_id) size += 1;
    if (has_comp_id) size += 1;
    if (has_pkg_id) size += 1;
    return size;
  }

  /* Calculate footer size */
  constexpr uint8_t footer_size() const { return crc_bytes; }

  /* Calculate total overhead (header + footer, excluding start bytes) */
  constexpr uint8_t overhead() const { return header_size() + footer_size(); }

  /* Calculate max payload size based on length field */
  constexpr size_t max_payload() const {
    if (length_bytes == 1) return 255;
    if (length_bytes == 2) return 65535;
    return 0; /* No length field - requires external knowledge */
  }
};

/* Pre-defined payload configurations */
constexpr PayloadConfig PAYLOAD_MINIMAL_CONFIG = {
    PayloadType::MINIMAL,
    false,
    0, /* no CRC */
    false,
    0,     /* no length */
    false, /* no seq */
    false, /* no sys_id */
    false, /* no comp_id */
    false  /* no pkg_id */
};

constexpr PayloadConfig PAYLOAD_DEFAULT_CONFIG = {
    PayloadType::DEFAULT,
    true,
    2, /* has CRC, 2 bytes */
    true,
    1,     /* has length, 1 byte */
    false, /* no seq */
    false, /* no sys_id */
    false, /* no comp_id */
    false  /* no pkg_id */
};

constexpr PayloadConfig PAYLOAD_EXTENDED_MSG_IDS_CONFIG = {
    PayloadType::EXTENDED_MSG_IDS,
    true,
    2, /* has CRC, 2 bytes */
    true,
    1,     /* has length, 1 byte */
    false, /* no seq */
    false, /* no sys_id */
    false, /* no comp_id */
    true   /* has pkg_id */
};

constexpr PayloadConfig PAYLOAD_EXTENDED_LENGTH_CONFIG = {
    PayloadType::EXTENDED_LENGTH,
    true,
    2, /* has CRC, 2 bytes */
    true,
    2,     /* has length, 2 bytes */
    false, /* no seq */
    false, /* no sys_id */
    false, /* no comp_id */
    false  /* no pkg_id */
};

constexpr PayloadConfig PAYLOAD_EXTENDED_CONFIG = {
    PayloadType::EXTENDED,
    true,
    2, /* has CRC, 2 bytes */
    true,
    2,     /* has length, 2 bytes */
    false, /* no seq */
    false, /* no sys_id */
    false, /* no comp_id */
    true   /* has pkg_id */
};

constexpr PayloadConfig PAYLOAD_SYS_COMP_CONFIG = {
    PayloadType::SYS_COMP,
    true,
    2, /* has CRC, 2 bytes */
    true,
    1,     /* has length, 1 byte */
    false, /* no seq */
    true,  /* has sys_id */
    true,  /* has comp_id */
    false  /* no pkg_id */
};

constexpr PayloadConfig PAYLOAD_SEQ_CONFIG = {
    PayloadType::SEQ,
    true,
    2, /* has CRC, 2 bytes */
    true,
    1,     /* has length, 1 byte */
    true,  /* has seq */
    false, /* no sys_id */
    false, /* no comp_id */
    false  /* no pkg_id */
};

constexpr PayloadConfig PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG = {
    PayloadType::MULTI_SYSTEM_STREAM,
    true,
    2, /* has CRC, 2 bytes */
    true,
    1,    /* has length, 1 byte */
    true, /* has seq */
    true, /* has sys_id */
    true, /* has comp_id */
    false /* no pkg_id */
};

constexpr PayloadConfig PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG = {
    PayloadType::EXTENDED_MULTI_SYSTEM_STREAM,
    true,
    2, /* has CRC, 2 bytes */
    true,
    2,    /* has length, 2 bytes */
    true, /* has seq */
    true, /* has sys_id */
    true, /* has comp_id */
    true  /* has pkg_id */
};

}  // namespace PayloadTypes
}  // namespace FrameParsers
