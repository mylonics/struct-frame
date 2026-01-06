/* Frame Profiles - Pre-defined Header + Payload combinations */
/* 
 * This file provides ready-to-use encode/parse functions for frame format profiles.
 * It builds on the generic frame encoding/parsing infrastructure in frame_base.h,
 * frame_headers/, and payload_types/.
 *
 * Standard Profiles:
 * - Profile Standard: Basic + Default (General serial/UART)
 * - Profile Sensor: Tiny + Minimal (Low-bandwidth sensors)
 * - Profile IPC: None + Minimal (Trusted inter-process communication)
 * - Profile Bulk: Basic + Extended (Large data transfers with package namespacing)
 * - Profile Network: Basic + ExtendedMultiSystemStream (Multi-system networked communication)
 */

#pragma once

#include "frame_base.h"
#include "frame_headers/base.h"
#include "frame_headers/header_basic.h"
#include "frame_headers/header_tiny.h"
#include "frame_headers/header_none.h"
#include "payload_types/base.h"
#include "payload_types/payload_default.h"
#include "payload_types/payload_minimal.h"
#include "payload_types/payload_extended.h"
#include "payload_types/payload_extended_multi_system_stream.h"

/*===========================================================================
 * Generic Frame Format Configuration
 *===========================================================================*/

/**
 * Frame format configuration - combines header type with payload type
 */
typedef struct frame_format_config {
    uint8_t header_type;           /* Header type (from header_type_t enum) */
    uint8_t payload_type;          /* Payload type (from payload_type_t enum) */
    uint8_t num_start_bytes;       /* Number of start bytes (0, 1, or 2) */
    uint8_t start_byte1;           /* First start byte (if applicable) */
    uint8_t start_byte2;           /* Second start byte (if applicable) */
    uint8_t header_size;           /* Total header size (start bytes + payload header fields) */
    uint8_t footer_size;           /* Footer size (CRC bytes) */
    bool has_length;               /* Has length field */
    uint8_t length_bytes;          /* Length field size (1 or 2) */
    bool has_crc;                  /* Has CRC */
    bool has_pkg_id;               /* Has package ID field */
    bool has_seq;                  /* Has sequence field */
    bool has_sys_id;               /* Has system ID field */
    bool has_comp_id;              /* Has component ID field */
} frame_format_config_t;

/*===========================================================================
 * Generic Encode/Parse Functions
 *===========================================================================*/

/**
 * Generic encode function for frames with CRC (Default, Extended, etc.)
 * Uses the frame format configuration to encode any supported frame type.
 */
static inline size_t frame_format_encode_with_crc(
    const frame_format_config_t* config,
    uint8_t* buffer, size_t buffer_size,
    uint8_t seq, uint8_t sys_id, uint8_t comp_id,
    uint8_t pkg_id, uint8_t msg_id,
    const uint8_t* payload, size_t payload_size) {
    
    size_t overhead = config->header_size + config->footer_size;
    size_t total_size = overhead + payload_size;
    size_t max_payload = (config->length_bytes == 1) ? 255 : 65535;
    
    if (buffer_size < total_size || payload_size > max_payload) {
        return 0;
    }
    
    size_t idx = 0;
    
    /* Write start bytes */
    if (config->num_start_bytes >= 1) {
        buffer[idx++] = config->start_byte1;
    }
    if (config->num_start_bytes >= 2) {
        buffer[idx++] = config->start_byte2;
    }
    
    size_t crc_start = idx;  /* CRC calculation starts after start bytes */
    
    /* Write optional fields before length */
    if (config->has_seq) {
        buffer[idx++] = seq;
    }
    if (config->has_sys_id) {
        buffer[idx++] = sys_id;
    }
    if (config->has_comp_id) {
        buffer[idx++] = comp_id;
    }
    
    /* Write length field */
    if (config->has_length) {
        if (config->length_bytes == 1) {
            buffer[idx++] = (uint8_t)(payload_size & 0xFF);
        } else {
            buffer[idx++] = (uint8_t)(payload_size & 0xFF);
            buffer[idx++] = (uint8_t)((payload_size >> 8) & 0xFF);
        }
    }
    
    /* Write package ID if present */
    if (config->has_pkg_id) {
        buffer[idx++] = pkg_id;
    }
    
    /* Write message ID */
    buffer[idx++] = msg_id;
    
    /* Write payload */
    if (payload_size > 0 && payload != NULL) {
        memcpy(buffer + idx, payload, payload_size);
        idx += payload_size;
    }
    
    /* Calculate and write CRC */
    if (config->has_crc) {
        size_t crc_len = idx - crc_start;
        frame_checksum_t ck = frame_fletcher_checksum(buffer + crc_start, crc_len);
        buffer[idx++] = ck.byte1;
        buffer[idx++] = ck.byte2;
    }
    
    return idx;
}

/**
 * Generic encode function for minimal frames (no length, no CRC)
 */
static inline size_t frame_format_encode_minimal(
    const frame_format_config_t* config,
    uint8_t* buffer, size_t buffer_size,
    uint8_t msg_id,
    const uint8_t* payload, size_t payload_size) {
    
    size_t overhead = config->header_size + config->footer_size;
    size_t total_size = overhead + payload_size;
    
    if (buffer_size < total_size) {
        return 0;
    }
    
    size_t idx = 0;
    
    /* Write start bytes */
    if (config->num_start_bytes >= 1) {
        buffer[idx++] = config->start_byte1;
    }
    if (config->num_start_bytes >= 2) {
        buffer[idx++] = config->start_byte2;
    }
    
    /* Write message ID */
    buffer[idx++] = msg_id;
    
    /* Write payload */
    if (payload_size > 0 && payload != NULL) {
        memcpy(buffer + idx, payload, payload_size);
        idx += payload_size;
    }
    
    return idx;
}

/**
 * Generic parse function for frames with CRC
 */
static inline frame_msg_info_t frame_format_parse_with_crc(
    const frame_format_config_t* config,
    const uint8_t* buffer, size_t length) {
    
    frame_msg_info_t result = {false, 0, 0, NULL};
    size_t overhead = config->header_size + config->footer_size;
    
    if (length < overhead) {
        return result;
    }
    
    /* Verify start bytes */
    size_t idx = 0;
    if (config->num_start_bytes >= 1 && buffer[idx++] != config->start_byte1) {
        return result;
    }
    if (config->num_start_bytes >= 2 && buffer[idx++] != config->start_byte2) {
        return result;
    }
    
    size_t crc_start = idx;
    
    /* Skip optional fields before length */
    if (config->has_seq) idx++;
    if (config->has_sys_id) idx++;
    if (config->has_comp_id) idx++;
    
    /* Read length field */
    size_t msg_len = 0;
    if (config->has_length) {
        if (config->length_bytes == 1) {
            msg_len = buffer[idx++];
        } else {
            msg_len = buffer[idx] | ((size_t)buffer[idx + 1] << 8);
            idx += 2;
        }
    }
    
    /* Skip package ID */
    if (config->has_pkg_id) idx++;
    
    /* Read message ID */
    uint8_t msg_id = buffer[idx++];
    
    /* Verify total size */
    size_t total_size = overhead + msg_len;
    if (length < total_size) {
        return result;
    }
    
    /* Verify CRC */
    if (config->has_crc) {
        size_t crc_len = total_size - crc_start - config->footer_size;
        frame_checksum_t ck = frame_fletcher_checksum(buffer + crc_start, crc_len);
        if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
            return result;
        }
    }
    
    result.valid = true;
    result.msg_id = msg_id;
    result.msg_len = msg_len;
    result.msg_data = (uint8_t*)(buffer + config->header_size);
    
    return result;
}

/**
 * Generic parse function for minimal frames (requires get_msg_length callback)
 */
static inline frame_msg_info_t frame_format_parse_minimal(
    const frame_format_config_t* config,
    const uint8_t* buffer, size_t length,
    bool (*get_msg_length)(size_t msg_id, size_t* len)) {
    
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < config->header_size) {
        return result;
    }
    
    /* Verify start bytes */
    size_t idx = 0;
    if (config->num_start_bytes >= 1 && buffer[idx++] != config->start_byte1) {
        return result;
    }
    if (config->num_start_bytes >= 2 && buffer[idx++] != config->start_byte2) {
        return result;
    }
    
    /* Read message ID */
    uint8_t msg_id = buffer[idx];
    
    /* Get message length from callback */
    size_t msg_len = 0;
    if (!get_msg_length || !get_msg_length(msg_id, &msg_len)) {
        return result;
    }
    
    size_t total_size = config->header_size + msg_len;
    if (length < total_size) {
        return result;
    }
    
    result.valid = true;
    result.msg_id = msg_id;
    result.msg_len = msg_len;
    result.msg_data = (uint8_t*)(buffer + config->header_size);
    
    return result;
}

/*===========================================================================
 * Profile Configurations
 *===========================================================================*/

/* Profile Standard: Basic + Default */
static const frame_format_config_t PROFILE_STANDARD_CONFIG = {
    .header_type = HEADER_BASIC,
    .payload_type = PAYLOAD_DEFAULT,
    .num_start_bytes = 2,
    .start_byte1 = BASIC_START_BYTE,
    .start_byte2 = PAYLOAD_TYPE_BASE + PAYLOAD_DEFAULT,
    .header_size = 4,   /* start1 + start2 + len + msg_id */
    .footer_size = 2,   /* CRC */
    .has_length = true,
    .length_bytes = 1,
    .has_crc = true,
    .has_pkg_id = false,
    .has_seq = false,
    .has_sys_id = false,
    .has_comp_id = false
};

/* Profile Sensor: Tiny + Minimal */
static const frame_format_config_t PROFILE_SENSOR_CONFIG = {
    .header_type = HEADER_TINY,
    .payload_type = PAYLOAD_MINIMAL,
    .num_start_bytes = 1,
    .start_byte1 = PAYLOAD_TYPE_BASE + PAYLOAD_MINIMAL,
    .start_byte2 = 0,
    .header_size = 2,   /* start + msg_id */
    .footer_size = 0,
    .has_length = false,
    .length_bytes = 0,
    .has_crc = false,
    .has_pkg_id = false,
    .has_seq = false,
    .has_sys_id = false,
    .has_comp_id = false
};

/* Profile IPC: None + Minimal */
static const frame_format_config_t PROFILE_IPC_CONFIG = {
    .header_type = HEADER_NONE,
    .payload_type = PAYLOAD_MINIMAL,
    .num_start_bytes = 0,
    .start_byte1 = 0,
    .start_byte2 = 0,
    .header_size = 1,   /* msg_id only */
    .footer_size = 0,
    .has_length = false,
    .length_bytes = 0,
    .has_crc = false,
    .has_pkg_id = false,
    .has_seq = false,
    .has_sys_id = false,
    .has_comp_id = false
};

/* Profile Bulk: Basic + Extended */
static const frame_format_config_t PROFILE_BULK_CONFIG = {
    .header_type = HEADER_BASIC,
    .payload_type = PAYLOAD_EXTENDED,
    .num_start_bytes = 2,
    .start_byte1 = BASIC_START_BYTE,
    .start_byte2 = PAYLOAD_TYPE_BASE + PAYLOAD_EXTENDED,
    .header_size = 6,   /* start1 + start2 + len16 + pkg_id + msg_id */
    .footer_size = 2,   /* CRC */
    .has_length = true,
    .length_bytes = 2,
    .has_crc = true,
    .has_pkg_id = true,
    .has_seq = false,
    .has_sys_id = false,
    .has_comp_id = false
};

/* Profile Network: Basic + ExtendedMultiSystemStream */
static const frame_format_config_t PROFILE_NETWORK_CONFIG = {
    .header_type = HEADER_BASIC,
    .payload_type = PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM,
    .num_start_bytes = 2,
    .start_byte1 = BASIC_START_BYTE,
    .start_byte2 = PAYLOAD_TYPE_BASE + PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM,
    .header_size = 9,   /* start1 + start2 + seq + sys + comp + len16 + pkg_id + msg_id */
    .footer_size = 2,   /* CRC */
    .has_length = true,
    .length_bytes = 2,
    .has_crc = true,
    .has_pkg_id = true,
    .has_seq = true,
    .has_sys_id = true,
    .has_comp_id = true
};

/*===========================================================================
 * Profile-Specific Convenience Functions
 * These are thin wrappers around the generic functions with profile configs.
 *===========================================================================*/

/* Profile Standard (Basic + Default) */
static inline size_t encode_profile_standard(uint8_t* buffer, size_t buffer_size,
                                             uint8_t msg_id,
                                             const uint8_t* payload, size_t payload_size) {
    return frame_format_encode_with_crc(&PROFILE_STANDARD_CONFIG, buffer, buffer_size,
                                        0, 0, 0, 0, msg_id, payload, payload_size);
}

static inline frame_msg_info_t parse_profile_standard_buffer(const uint8_t* buffer, size_t length) {
    return frame_format_parse_with_crc(&PROFILE_STANDARD_CONFIG, buffer, length);
}

/* Profile Sensor (Tiny + Minimal) */
static inline size_t encode_profile_sensor(uint8_t* buffer, size_t buffer_size,
                                           uint8_t msg_id,
                                           const uint8_t* payload, size_t payload_size) {
    return frame_format_encode_minimal(&PROFILE_SENSOR_CONFIG, buffer, buffer_size,
                                       msg_id, payload, payload_size);
}

static inline frame_msg_info_t parse_profile_sensor_buffer(const uint8_t* buffer, size_t length,
                                                           bool (*get_msg_length)(size_t msg_id, size_t* len)) {
    return frame_format_parse_minimal(&PROFILE_SENSOR_CONFIG, buffer, length, get_msg_length);
}

/* Profile IPC (None + Minimal) */
static inline size_t encode_profile_ipc(uint8_t* buffer, size_t buffer_size,
                                        uint8_t msg_id,
                                        const uint8_t* payload, size_t payload_size) {
    return frame_format_encode_minimal(&PROFILE_IPC_CONFIG, buffer, buffer_size,
                                       msg_id, payload, payload_size);
}

static inline frame_msg_info_t parse_profile_ipc_buffer(const uint8_t* buffer, size_t length,
                                                        bool (*get_msg_length)(size_t msg_id, size_t* len)) {
    return frame_format_parse_minimal(&PROFILE_IPC_CONFIG, buffer, length, get_msg_length);
}

/* Profile Bulk (Basic + Extended) */
static inline size_t encode_profile_bulk(uint8_t* buffer, size_t buffer_size,
                                         uint8_t pkg_id, uint8_t msg_id,
                                         const uint8_t* payload, size_t payload_size) {
    return frame_format_encode_with_crc(&PROFILE_BULK_CONFIG, buffer, buffer_size,
                                        0, 0, 0, pkg_id, msg_id, payload, payload_size);
}

static inline frame_msg_info_t parse_profile_bulk_buffer(const uint8_t* buffer, size_t length) {
    return frame_format_parse_with_crc(&PROFILE_BULK_CONFIG, buffer, length);
}

/* Profile Network (Basic + ExtendedMultiSystemStream) */
static inline size_t encode_profile_network(uint8_t* buffer, size_t buffer_size,
                                            uint8_t sequence, uint8_t system_id,
                                            uint8_t component_id, uint8_t pkg_id,
                                            uint8_t msg_id,
                                            const uint8_t* payload, size_t payload_size) {
    return frame_format_encode_with_crc(&PROFILE_NETWORK_CONFIG, buffer, buffer_size,
                                        sequence, system_id, component_id, pkg_id, msg_id,
                                        payload, payload_size);
}

static inline frame_msg_info_t parse_profile_network_buffer(const uint8_t* buffer, size_t length) {
    return frame_format_parse_with_crc(&PROFILE_NETWORK_CONFIG, buffer, length);
}
