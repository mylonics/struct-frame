/* Payload Types - Message structure configurations (C) */
/* Payload types define message structure (length fields, CRC, extra fields) */

#pragma once

#include <stdbool.h>
#include <stdint.h>

/*===========================================================================
 * Payload Type Enumeration
 *===========================================================================*/

typedef enum payload_type {
  PAYLOAD_MINIMAL = 0,             /* [MSG_ID] [PACKET] */
  PAYLOAD_DEFAULT = 1,             /* [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
  PAYLOAD_EXTENDED_MSG_IDS = 2,    /* [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
  PAYLOAD_EXTENDED_LENGTH = 3,     /* [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2] */
  PAYLOAD_EXTENDED = 4,            /* [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
  PAYLOAD_SYS_COMP = 5,            /* [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
  PAYLOAD_SEQ = 6,                 /* [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
  PAYLOAD_MULTI_SYSTEM_STREAM = 7, /* [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
  PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM =
      8 /* [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
} payload_type_t;

/* Maximum payload type value (for range checking) */
#define MAX_PAYLOAD_TYPE_VALUE 8

/*===========================================================================
 * Payload Configuration Structure
 *===========================================================================*/

typedef struct payload_config {
  payload_type_t payload_type;
  bool has_crc;
  uint8_t crc_bytes; /* 0 or 2 */
  bool has_length;
  uint8_t length_bytes; /* 0, 1, or 2 */
  bool has_seq;
  bool has_sys_id;
  bool has_comp_id;
  bool has_pkg_id;
} payload_config_t;

/*===========================================================================
 * Helper Functions
 *===========================================================================*/

/* Calculate header size (fields before payload, excluding start bytes) */
static inline uint8_t payload_config_header_size(const payload_config_t* config) {
  uint8_t size = 1; /* msg_id always present */
  if (config->has_length) size += config->length_bytes;
  if (config->has_seq) size += 1;
  if (config->has_sys_id) size += 1;
  if (config->has_comp_id) size += 1;
  if (config->has_pkg_id) size += 1;
  return size;
}

/* Calculate footer size */
static inline uint8_t payload_config_footer_size(const payload_config_t* config) { return config->crc_bytes; }

/* Calculate total overhead (header + footer, excluding start bytes) */
static inline uint8_t payload_config_overhead(const payload_config_t* config) {
  return payload_config_header_size(config) + payload_config_footer_size(config);
}

/*===========================================================================
 * Pre-defined Payload Configurations
 *===========================================================================*/

/* Minimal: [MSG_ID] [PACKET] */
static const payload_config_t PAYLOAD_MINIMAL_CONFIG = {.payload_type = PAYLOAD_MINIMAL,
                                                        .has_crc = false,
                                                        .crc_bytes = 0,
                                                        .has_length = false,
                                                        .length_bytes = 0,
                                                        .has_seq = false,
                                                        .has_sys_id = false,
                                                        .has_comp_id = false,
                                                        .has_pkg_id = false};

/* Default: [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
static const payload_config_t PAYLOAD_DEFAULT_CONFIG = {.payload_type = PAYLOAD_DEFAULT,
                                                        .has_crc = true,
                                                        .crc_bytes = 2,
                                                        .has_length = true,
                                                        .length_bytes = 1,
                                                        .has_seq = false,
                                                        .has_sys_id = false,
                                                        .has_comp_id = false,
                                                        .has_pkg_id = false};

/* Extended Msg IDs: [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
static const payload_config_t PAYLOAD_EXTENDED_MSG_IDS_CONFIG = {.payload_type = PAYLOAD_EXTENDED_MSG_IDS,
                                                                 .has_crc = true,
                                                                 .crc_bytes = 2,
                                                                 .has_length = true,
                                                                 .length_bytes = 1,
                                                                 .has_seq = false,
                                                                 .has_sys_id = false,
                                                                 .has_comp_id = false,
                                                                 .has_pkg_id = true};

/* Extended Length: [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2] */
static const payload_config_t PAYLOAD_EXTENDED_LENGTH_CONFIG = {.payload_type = PAYLOAD_EXTENDED_LENGTH,
                                                                .has_crc = true,
                                                                .crc_bytes = 2,
                                                                .has_length = true,
                                                                .length_bytes = 2,
                                                                .has_seq = false,
                                                                .has_sys_id = false,
                                                                .has_comp_id = false,
                                                                .has_pkg_id = false};

/* Extended: [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
static const payload_config_t PAYLOAD_EXTENDED_CONFIG = {.payload_type = PAYLOAD_EXTENDED,
                                                         .has_crc = true,
                                                         .crc_bytes = 2,
                                                         .has_length = true,
                                                         .length_bytes = 2,
                                                         .has_seq = false,
                                                         .has_sys_id = false,
                                                         .has_comp_id = false,
                                                         .has_pkg_id = true};

/* SysComp: [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
static const payload_config_t PAYLOAD_SYS_COMP_CONFIG = {.payload_type = PAYLOAD_SYS_COMP,
                                                         .has_crc = true,
                                                         .crc_bytes = 2,
                                                         .has_length = true,
                                                         .length_bytes = 1,
                                                         .has_seq = false,
                                                         .has_sys_id = true,
                                                         .has_comp_id = true,
                                                         .has_pkg_id = false};

/* Seq: [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
static const payload_config_t PAYLOAD_SEQ_CONFIG = {.payload_type = PAYLOAD_SEQ,
                                                    .has_crc = true,
                                                    .crc_bytes = 2,
                                                    .has_length = true,
                                                    .length_bytes = 1,
                                                    .has_seq = true,
                                                    .has_sys_id = false,
                                                    .has_comp_id = false,
                                                    .has_pkg_id = false};

/* Multi System Stream: [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
static const payload_config_t PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG = {.payload_type = PAYLOAD_MULTI_SYSTEM_STREAM,
                                                                    .has_crc = true,
                                                                    .crc_bytes = 2,
                                                                    .has_length = true,
                                                                    .length_bytes = 1,
                                                                    .has_seq = true,
                                                                    .has_sys_id = true,
                                                                    .has_comp_id = true,
                                                                    .has_pkg_id = false};

/* Extended Multi System Stream: [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
static const payload_config_t PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG = {
    .payload_type = PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM,
    .has_crc = true,
    .crc_bytes = 2,
    .has_length = true,
    .length_bytes = 2,
    .has_seq = true,
    .has_sys_id = true,
    .has_comp_id = true,
    .has_pkg_id = true};
