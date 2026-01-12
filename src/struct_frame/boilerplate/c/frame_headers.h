/* Frame Headers - Start byte patterns and header configurations (C) */
/* Header types define start byte patterns and header-specific parsing */

#pragma once

#include <stdbool.h>
#include <stdint.h>

/*===========================================================================
 * Header Type Enumeration
 *===========================================================================*/

typedef enum header_type {
  HEADER_NONE = 0,       /* No start bytes */
  HEADER_TINY = 1,       /* 1 start byte [0x70+PayloadType] */
  HEADER_BASIC = 2,      /* 2 start bytes [0x90] [0x70+PayloadType] */
  HEADER_UBX = 3,        /* 2 start bytes [0xB5] [0x62] */
  HEADER_MAVLINK_V1 = 4, /* 1 start byte [0xFE] */
  HEADER_MAVLINK_V2 = 5  /* 1 start byte [0xFD] */
} header_type_t;

/*===========================================================================
 * Constants
 *===========================================================================*/

#define BASIC_START_BYTE 0x90
#define PAYLOAD_TYPE_BASE 0x70 /* Payload type encoded as 0x70 + payload_type */
#define UBX_SYNC1 0xB5
#define UBX_SYNC2 0x62
#define MAVLINK_V1_STX 0xFE
#define MAVLINK_V2_STX 0xFD
#define MAX_PAYLOAD_TYPE 8

/*===========================================================================
 * Header Configuration Structure
 *===========================================================================*/

typedef struct header_config {
  header_type_t header_type;
  uint8_t start_byte1;       /* First start byte (0 if none or dynamic) */
  uint8_t start_byte2;       /* Second start byte (0 if none or dynamic) */
  uint8_t num_start_bytes;   /* Number of start bytes (0, 1, or 2) */
  bool encodes_payload_type; /* True if start byte encodes payload type */
} header_config_t;

/*===========================================================================
 * Pre-defined Header Configurations
 *===========================================================================*/

/* None header - no start bytes */
static const header_config_t HEADER_NONE_CONFIG = {.header_type = HEADER_NONE,
                                                   .start_byte1 = 0,
                                                   .start_byte2 = 0,
                                                   .num_start_bytes = 0,
                                                   .encodes_payload_type = false};

/* Tiny header - 1 start byte [0x70+PayloadType] */
static const header_config_t HEADER_TINY_CONFIG = {.header_type = HEADER_TINY,
                                                   .start_byte1 = 0, /* Dynamic - depends on payload type */
                                                   .start_byte2 = 0,
                                                   .num_start_bytes = 1,
                                                   .encodes_payload_type = true};

/* Basic header - 2 start bytes [0x90] [0x70+PayloadType] */
static const header_config_t HEADER_BASIC_CONFIG = {.header_type = HEADER_BASIC,
                                                    .start_byte1 = BASIC_START_BYTE,
                                                    .start_byte2 = 0, /* Dynamic - depends on payload type */
                                                    .num_start_bytes = 2,
                                                    .encodes_payload_type = true};

/* UBX header - 2 start bytes [0xB5] [0x62] */
static const header_config_t HEADER_UBX_CONFIG = {.header_type = HEADER_UBX,
                                                  .start_byte1 = UBX_SYNC1,
                                                  .start_byte2 = UBX_SYNC2,
                                                  .num_start_bytes = 2,
                                                  .encodes_payload_type = false};

/* Mavlink V1 header - 1 start byte [0xFE] */
static const header_config_t HEADER_MAVLINK_V1_CONFIG = {.header_type = HEADER_MAVLINK_V1,
                                                         .start_byte1 = MAVLINK_V1_STX,
                                                         .start_byte2 = 0,
                                                         .num_start_bytes = 1,
                                                         .encodes_payload_type = false};

/* Mavlink V2 header - 1 start byte [0xFD] */
static const header_config_t HEADER_MAVLINK_V2_CONFIG = {.header_type = HEADER_MAVLINK_V2,
                                                         .start_byte1 = MAVLINK_V2_STX,
                                                         .start_byte2 = 0,
                                                         .num_start_bytes = 1,
                                                         .encodes_payload_type = false};

/*===========================================================================
 * Helper Functions
 *===========================================================================*/

/* Get the start byte for a Tiny frame with given payload type */
static inline uint8_t get_tiny_start_byte(uint8_t payload_type_value) { return PAYLOAD_TYPE_BASE + payload_type_value; }

/* Check if byte is a valid Tiny frame start byte */
static inline bool is_tiny_start_byte(uint8_t byte) {
  return byte >= PAYLOAD_TYPE_BASE && byte <= (PAYLOAD_TYPE_BASE + MAX_PAYLOAD_TYPE);
}

/* Extract payload type value from Tiny start byte */
static inline uint8_t get_payload_type_from_tiny(uint8_t byte) { return byte - PAYLOAD_TYPE_BASE; }

/* Get the second start byte for a Basic frame with given payload type */
static inline uint8_t get_basic_second_start_byte(uint8_t payload_type_value) {
  return PAYLOAD_TYPE_BASE + payload_type_value;
}

/* Check if byte is a valid Basic frame second start byte */
static inline bool is_basic_second_start_byte(uint8_t byte) {
  return byte >= PAYLOAD_TYPE_BASE && byte <= (PAYLOAD_TYPE_BASE + MAX_PAYLOAD_TYPE);
}

/* Extract payload type value from Basic second start byte */
static inline uint8_t get_payload_type_from_basic(uint8_t byte) { return byte - PAYLOAD_TYPE_BASE; }
