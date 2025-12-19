/* Base definitions for frame headers */
/* Header types define start byte patterns and header-specific parsing */

#pragma once

#include <stdint.h>
#include <stdbool.h>

/* Header type enumeration */
typedef enum header_type {
    HEADER_NONE = 0,       /* No start bytes */
    HEADER_TINY = 1,       /* 1 start byte [0x70+PayloadType] */
    HEADER_BASIC = 2,      /* 2 start bytes [0x90] [0x70+PayloadType] */
    HEADER_UBX = 3,        /* 2 start bytes [0xB5] [0x62] */
    HEADER_MAVLINK_V1 = 4, /* 1 start byte [0xFE] */
    HEADER_MAVLINK_V2 = 5  /* 1 start byte [0xFD] */
} header_type_t;

/* Configuration for a header type */
typedef struct header_config {
    header_type_t header_type;
    const char* name;
    uint8_t start_bytes[2];         /* Fixed start bytes (0 for dynamic) */
    uint8_t num_start_bytes;        /* Number of start bytes (0, 1, or 2) */
    bool encodes_payload_type;      /* True if start byte encodes payload type */
    int8_t payload_type_byte_index; /* Which byte encodes payload type (-1 if none) */
    const char* description;
} header_config_t;

/* Constants used across headers */
#define BASIC_START_BYTE 0x90
#define PAYLOAD_TYPE_BASE 0x70  /* Payload type encoded as 0x70 + payload_type */
#define UBX_SYNC1 0xB5
#define UBX_SYNC2 0x62
#define MAVLINK_V1_STX 0xFE
#define MAVLINK_V2_STX 0xFD
#define MAX_PAYLOAD_TYPE 8
