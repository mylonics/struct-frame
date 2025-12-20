/* Base definitions for payload types */
/* Payload types define message structure (length fields, CRC, extra fields) */

#pragma once

#include <stdint.h>
#include <stdbool.h>

/* Payload type enumeration */
typedef enum payload_type {
    PAYLOAD_MINIMAL = 0,                      /* [MSG_ID] [PACKET] */
    PAYLOAD_DEFAULT = 1,                      /* [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
    PAYLOAD_EXTENDED_MSG_IDS = 2,             /* [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
    PAYLOAD_EXTENDED_LENGTH = 3,              /* [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2] */
    PAYLOAD_EXTENDED = 4,                     /* [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
    PAYLOAD_SYS_COMP = 5,                     /* [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
    PAYLOAD_SEQ = 6,                          /* [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
    PAYLOAD_MULTI_SYSTEM_STREAM = 7,          /* [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] */
    PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM = 8  /* [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] */
} payload_type_t;

/* Maximum payload type value (for range checking) */
#define MAX_PAYLOAD_TYPE_VALUE 8

/* Configuration for a payload type */
typedef struct payload_config {
    payload_type_t payload_type;
    const char* name;
    bool has_crc;
    uint8_t crc_bytes;
    bool has_length;
    uint8_t length_bytes;  /* 1 or 2 */
    bool has_sequence;
    bool has_system_id;
    bool has_component_id;
    bool has_package_id;
    const char* description;
} payload_config_t;

/* Helper function to calculate header size from payload config */
static inline uint8_t payload_config_header_size(const payload_config_t* config) {
    uint8_t size = 1;  /* msg_id */
    if (config->has_length) {
        size += config->length_bytes;
    }
    if (config->has_sequence) {
        size += 1;
    }
    if (config->has_system_id) {
        size += 1;
    }
    if (config->has_component_id) {
        size += 1;
    }
    if (config->has_package_id) {
        size += 1;
    }
    return size;
}

/* Helper function to calculate footer size from payload config */
static inline uint8_t payload_config_footer_size(const payload_config_t* config) {
    return config->crc_bytes;
}

/* Helper function to calculate overhead from payload config */
static inline uint8_t payload_config_overhead(const payload_config_t* config) {
    return payload_config_header_size(config) + payload_config_footer_size(config);
}
