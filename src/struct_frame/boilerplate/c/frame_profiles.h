/* Frame Profiles - Pre-defined Header + Payload combinations (C) */
/* 
 * This file provides ready-to-use encode/parse functions for frame format profiles.
 * It builds on the generic frame encoding/parsing infrastructure, composing
 * header configurations with payload configurations.
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
#include "frame_headers.h"
#include "payload_types.h"

/*===========================================================================
 * Profile Configuration - Composed from Header + Payload configs
 *===========================================================================*/

/**
 * Profile configuration - combines header type with payload type
 * Derived fields are computed from the component configs.
 */
typedef struct profile_config {
    header_config_t header;
    payload_config_t payload;
} profile_config_t;

/* Helper to calculate total header size (start bytes + payload header fields) */
static inline uint8_t profile_header_size(const profile_config_t* config) {
    return config->header.num_start_bytes + payload_config_header_size(&config->payload);
}

/* Helper to calculate footer size */
static inline uint8_t profile_footer_size(const profile_config_t* config) {
    return payload_config_footer_size(&config->payload);
}

/* Helper to calculate total overhead */
static inline uint8_t profile_overhead(const profile_config_t* config) {
    return profile_header_size(config) + profile_footer_size(config);
}

/*===========================================================================
 * Pre-defined Profile Configurations
 *===========================================================================*/

/* Profile Standard: Basic + Default */
static const profile_config_t PROFILE_STANDARD_CONFIG = {
    .header = HEADER_BASIC_CONFIG,
    .payload = PAYLOAD_DEFAULT_CONFIG
};

/* Profile Sensor: Tiny + Minimal */
static const profile_config_t PROFILE_SENSOR_CONFIG = {
    .header = HEADER_TINY_CONFIG,
    .payload = PAYLOAD_MINIMAL_CONFIG
};

/* Profile IPC: None + Minimal */
static const profile_config_t PROFILE_IPC_CONFIG = {
    .header = HEADER_NONE_CONFIG,
    .payload = PAYLOAD_MINIMAL_CONFIG
};

/* Profile Bulk: Basic + Extended */
static const profile_config_t PROFILE_BULK_CONFIG = {
    .header = HEADER_BASIC_CONFIG,
    .payload = PAYLOAD_EXTENDED_CONFIG
};

/* Profile Network: Basic + ExtendedMultiSystemStream */
static const profile_config_t PROFILE_NETWORK_CONFIG = {
    .header = HEADER_BASIC_CONFIG,
    .payload = PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG
};

/*===========================================================================
 * Generic Encode/Parse Functions
 *===========================================================================*/

/**
 * Generic encode function for frames with CRC (Default, Extended, etc.)
 * Uses the profile configuration to encode any supported frame type.
 */
/**
 * Encode a frame with CRC, extension-aware variant. base_size is the size of
 * the message's non-extension portion (use payload_size when the message
 * has no extensions). The CRC is computed via
 * frame_fletcher_checksum_with_magic_ext, which mixes base bytes, the magic
 * pair, then the extension bytes — so legacy messages (base_size ==
 * payload_size) produce byte-identical wire output to the pre-extension
 * format.
 */
static inline size_t profile_encode_with_crc_ext(
    const profile_config_t* config,
    uint8_t* buffer, size_t buffer_size,
    uint8_t seq, uint8_t sys_id, uint8_t comp_id,
    uint8_t pkg_id, uint8_t msg_id,
    const uint8_t* payload_data, size_t payload_size,
    size_t base_size,
    uint8_t magic1, uint8_t magic2) {
    
    uint8_t header_size = profile_header_size(config);
    uint8_t footer_size = profile_footer_size(config);
    size_t overhead = header_size + footer_size;
    size_t total_size = overhead + payload_size;
    size_t max_payload = (config->payload.length_bytes == 1) ? 255 : 65535;
    
    if (buffer_size < total_size || payload_size > max_payload) {
        return 0;
    }
    
    size_t idx = 0;
    
    /* Write start bytes */
    if (config->header.num_start_bytes >= 1) {
        buffer[idx++] = config->header.start_byte1;
    }
    if (config->header.num_start_bytes >= 2) {
        /* Second start byte encodes payload type */
        buffer[idx++] = config->header.encodes_payload_type ?
            get_basic_second_start_byte(config->payload.payload_type) :
            config->header.start_byte2;
    }
    
    size_t crc_start = idx;  /* CRC calculation starts after start bytes */
    
    /* Write optional fields before length */
    if (config->payload.has_seq) {
        buffer[idx++] = seq;
    }
    if (config->payload.has_sys_id) {
        buffer[idx++] = sys_id;
    }
    if (config->payload.has_comp_id) {
        buffer[idx++] = comp_id;
    }
    
    /* Write length field */
    if (config->payload.has_length) {
        if (config->payload.length_bytes == 1) {
            buffer[idx++] = (uint8_t)(payload_size & 0xFF);
        } else {
            buffer[idx++] = (uint8_t)(payload_size & 0xFF);
            buffer[idx++] = (uint8_t)((payload_size >> 8) & 0xFF);
        }
    }
    
    /* Write package ID if present */
    if (config->payload.has_pkg_id) {
        buffer[idx++] = pkg_id;
    }
    
    /* Write message ID */
    buffer[idx++] = msg_id;
    
    /* Write payload */
    if (payload_size > 0 && payload_data != NULL) {
        memcpy(buffer + idx, payload_data, payload_size);
        idx += payload_size;
    }
    
    /* Calculate and write CRC */
    if (config->payload.has_crc) {
        size_t crc_len = idx - crc_start;
        /* effective_base is the offset within the CRC input at which the
         * payload's extension portion begins. The base portion includes the
         * pre-payload overhead (seq/sys_id/comp_id/length/pkg_id/msg_id) plus
         * the message's non-extension fields. For profiles without a length
         * field, extension bytes cannot be truncated on receive, so the
         * post-magic mix collapses into the pre-magic mix (silent fallback).
         */
        size_t effective_base = crc_len;
        if (config->payload.has_length && base_size <= payload_size) {
            effective_base = (crc_len - payload_size) + base_size;
        }
        frame_checksum_t ck = frame_fletcher_checksum_with_magic_ext(
            buffer + crc_start, effective_base, crc_len, magic1, magic2);
        buffer[idx++] = ck.byte1;
        buffer[idx++] = ck.byte2;
    }
    
    return idx;
}

/**
 * Backwards-compatible wrapper: no extension support (base_size == payload_size).
 * Existing code may continue to call this; for messages without
 * `option extensions_start = N;` the result is byte-identical to the
 * extension-aware variant.
 */
static inline size_t profile_encode_with_crc(
    const profile_config_t* config,
    uint8_t* buffer, size_t buffer_size,
    uint8_t seq, uint8_t sys_id, uint8_t comp_id,
    uint8_t pkg_id, uint8_t msg_id,
    const uint8_t* payload_data, size_t payload_size,
    uint8_t magic1, uint8_t magic2) {
    return profile_encode_with_crc_ext(
        config, buffer, buffer_size,
        seq, sys_id, comp_id, pkg_id, msg_id,
        payload_data, payload_size, payload_size,
        magic1, magic2);
}

/**
 * Generic encode function for minimal frames (no length, no CRC)
 */
static inline size_t profile_encode_minimal(
    const profile_config_t* config,
    uint8_t* buffer, size_t buffer_size,
    uint8_t msg_id,
    const uint8_t* payload_data, size_t payload_size) {
    
    uint8_t header_size = profile_header_size(config);
    size_t total_size = header_size + payload_size;
    
    if (buffer_size < total_size) {
        return 0;
    }
    
    size_t idx = 0;
    
    /* Write start bytes */
    if (config->header.num_start_bytes >= 1) {
        /* First/only start byte may encode payload type for tiny headers */
        if (config->header.header_type == HEADER_TINY && config->header.encodes_payload_type) {
            buffer[idx++] = get_tiny_start_byte(config->payload.payload_type);
        } else {
            buffer[idx++] = config->header.start_byte1;
        }
    }
    if (config->header.num_start_bytes >= 2) {
        buffer[idx++] = config->header.start_byte2;
    }
    
    /* Write message ID */
    buffer[idx++] = msg_id;
    
    /* Write payload */
    if (payload_size > 0 && payload_data != NULL) {
        memcpy(buffer + idx, payload_data, payload_size);
        idx += payload_size;
    }
    
    return idx;
}

/**
 * Generic parse function for frames with CRC
 */
static inline frame_msg_info_t profile_parse_with_crc(
    const profile_config_t* config,
    const uint8_t* buffer, size_t length,
    bool (*get_message_info_func)(uint16_t, message_info_t*)) {
    
    frame_msg_info_t result = {false, 0, 0, NULL};
    uint8_t header_size = profile_header_size(config);
    uint8_t footer_size = profile_footer_size(config);
    size_t overhead = header_size + footer_size;
    
    if (length < overhead) {
        return result;
    }
    
    /* Verify start bytes */
    size_t idx = 0;
    if (config->header.num_start_bytes >= 1 && buffer[idx++] != config->header.start_byte1) {
        return result;
    }
    if (config->header.num_start_bytes >= 2) {
        uint8_t expected_start2 = config->header.encodes_payload_type ?
            get_basic_second_start_byte(config->payload.payload_type) :
            config->header.start_byte2;
        if (buffer[idx++] != expected_start2) {
            return result;
        }
    }
    
    size_t crc_start = idx;
    
    /* Skip optional fields before length */
    if (config->payload.has_seq) idx++;
    if (config->payload.has_sys_id) idx++;
    if (config->payload.has_comp_id) idx++;
    
    /* Read length field */
    size_t msg_len = 0;
    if (config->payload.has_length) {
        if (config->payload.length_bytes == 1) {
            msg_len = buffer[idx++];
        } else {
            msg_len = buffer[idx] | ((size_t)buffer[idx + 1] << 8);
            idx += 2;
        }
    }
    
    /* Read message ID (16-bit: high byte is pkg_id when has_pkg_id, low byte is msg_id) */
    uint16_t msg_id = 0;
    if (config->payload.has_pkg_id) {
        msg_id = (uint16_t)buffer[idx++] << 8;  /* pkg_id (high byte) */
    }
    msg_id |= buffer[idx++];  /* msg_id (low byte) */
    
    /* Verify total size */
    size_t total_size = overhead + msg_len;
    if (length < total_size) {
        return result;
    }
    
    /* Verify CRC */
    if (config->payload.has_crc) {
        size_t crc_len = total_size - crc_start - footer_size;
        
        /* Get magic numbers and base size for this message type */
        uint8_t magic1 = 0, magic2 = 0;
        size_t base_size = 0;
        bool have_info = false;
        if (get_message_info_func) {
            message_info_t info;
            if (get_message_info_func(msg_id, &info)) {
                magic1 = info.magic1;
                magic2 = info.magic2;
                base_size = info.base_size;
                have_info = true;
            }
        }
        
        /* effective_base mirrors the encoder logic: split the CRC input at
         * the offset where extension payload bytes begin. For non-length
         * profiles, base_size equals total payload size so the split is a
         * no-op and the result is identical to the pre-extension format.
         */
        size_t effective_base = crc_len;
        if (have_info && config->payload.has_length && base_size <= msg_len) {
            effective_base = (crc_len - msg_len) + base_size;
        }
        frame_checksum_t ck = frame_fletcher_checksum_with_magic_ext(
            buffer + crc_start, effective_base, crc_len, magic1, magic2);
        if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
            return result;
        }
    }
    
    result.valid = true;
    result.msg_id = msg_id;
    result.msg_len = msg_len;
    result.msg_data = (uint8_t*)(buffer + header_size);
    
    return result;
}

/**
 * Generic parse function for minimal frames (requires get_message_info callback)
 */
static inline frame_msg_info_t profile_parse_minimal(
    const profile_config_t* config,
    const uint8_t* buffer, size_t length,
    bool (*get_message_info)(uint16_t msg_id, message_info_t* info)) {
    
    frame_msg_info_t result = {false, 0, 0, NULL};
    uint8_t header_size = profile_header_size(config);
    
    if (length < header_size) {
        return result;
    }
    
    /* Verify start bytes */
    size_t idx = 0;
    if (config->header.num_start_bytes >= 1) {
        uint8_t expected_start1 = config->header.start_byte1;
        if (config->header.header_type == HEADER_TINY && config->header.encodes_payload_type) {
            expected_start1 = get_tiny_start_byte(config->payload.payload_type);
        }
        if (buffer[idx++] != expected_start1) {
            return result;
        }
    }
    if (config->header.num_start_bytes >= 2 && buffer[idx++] != config->header.start_byte2) {
        return result;
    }
    
    /* Read message ID */
    uint8_t msg_id = buffer[idx];
    
    /* Get message length from callback */
    size_t msg_len = 0;
    message_info_t info;
    if (!get_message_info || !get_message_info(msg_id, &info)) {
        return result;
    }
    msg_len = info.size;
    
    size_t total_size = header_size + msg_len;
    if (length < total_size) {
        return result;
    }
    
    result.valid = true;
    result.msg_id = msg_id;
    result.msg_len = msg_len;
    result.msg_data = (uint8_t*)(buffer + header_size);
    
    return result;
}

/*===========================================================================
 * Profile-Specific Convenience Functions
 *===========================================================================*/

/* Profile Standard (Basic + Default) */
static inline size_t encode_profile_standard(uint8_t* buffer, size_t buffer_size,
                                             uint8_t msg_id,
                                             const uint8_t* payload, size_t payload_size) {
    return profile_encode_with_crc(&PROFILE_STANDARD_CONFIG, buffer, buffer_size,
                                   0, 0, 0, 0, msg_id, payload, payload_size, 0, 0);
}

static inline frame_msg_info_t parse_profile_standard_buffer(const uint8_t* buffer, size_t length) {
    return profile_parse_with_crc(&PROFILE_STANDARD_CONFIG, buffer, length, NULL);
}

/* Profile Sensor (Tiny + Minimal) */
static inline size_t encode_profile_sensor(uint8_t* buffer, size_t buffer_size,
                                           uint8_t msg_id,
                                           const uint8_t* payload, size_t payload_size) {
    return profile_encode_minimal(&PROFILE_SENSOR_CONFIG, buffer, buffer_size,
                                  msg_id, payload, payload_size);
}

static inline frame_msg_info_t parse_profile_sensor_buffer(const uint8_t* buffer, size_t length,
                                                           bool (*get_message_info)(uint16_t msg_id, message_info_t* info)) {
    return profile_parse_minimal(&PROFILE_SENSOR_CONFIG, buffer, length, get_message_info);
}

/* Profile IPC (None + Minimal) */
static inline size_t encode_profile_ipc(uint8_t* buffer, size_t buffer_size,
                                        uint8_t msg_id,
                                        const uint8_t* payload, size_t payload_size) {
    return profile_encode_minimal(&PROFILE_IPC_CONFIG, buffer, buffer_size,
                                  msg_id, payload, payload_size);
}

static inline frame_msg_info_t parse_profile_ipc_buffer(const uint8_t* buffer, size_t length,
                                                        bool (*get_message_info)(uint16_t msg_id, message_info_t* info)) {
    return profile_parse_minimal(&PROFILE_IPC_CONFIG, buffer, length, get_message_info);
}

/* Profile Bulk (Basic + Extended) */
static inline size_t encode_profile_bulk(uint8_t* buffer, size_t buffer_size,
                                         uint16_t msg_id,
                                         const uint8_t* payload, size_t payload_size) {
    uint8_t pkg_id = (uint8_t)((msg_id >> 8) & 0xFF);
    uint8_t low_msg_id = (uint8_t)(msg_id & 0xFF);
    return profile_encode_with_crc(&PROFILE_BULK_CONFIG, buffer, buffer_size,
                                   0, 0, 0, pkg_id, low_msg_id, payload, payload_size, 0, 0);
}

static inline frame_msg_info_t parse_profile_bulk_buffer(const uint8_t* buffer, size_t length) {
    return profile_parse_with_crc(&PROFILE_BULK_CONFIG, buffer, length, NULL);
}

/* Profile Network (Basic + ExtendedMultiSystemStream) */
static inline size_t encode_profile_network(uint8_t* buffer, size_t buffer_size,
                                            uint8_t sequence, uint8_t system_id,
                                            uint8_t component_id, uint16_t msg_id,
                                            const uint8_t* payload, size_t payload_size) {
    uint8_t pkg_id = (uint8_t)((msg_id >> 8) & 0xFF);
    uint8_t low_msg_id = (uint8_t)(msg_id & 0xFF);
    return profile_encode_with_crc(&PROFILE_NETWORK_CONFIG, buffer, buffer_size,
                                   sequence, system_id, component_id, pkg_id, low_msg_id,
                                   payload, payload_size, 0, 0);
}

static inline frame_msg_info_t parse_profile_network_buffer(const uint8_t* buffer, size_t length) {
    return profile_parse_with_crc(&PROFILE_NETWORK_CONFIG, buffer, length, NULL);
}

/*===========================================================================
 * BufferReader - Iterate through multiple frames in a buffer
 *===========================================================================*/

typedef struct buffer_reader {
    const profile_config_t* config;
    const uint8_t* buffer;
    size_t size;
    size_t offset;
    bool (*get_message_info)(uint16_t msg_id, message_info_t* info);
} buffer_reader_t;

static inline void buffer_reader_init(
    buffer_reader_t* reader,
    const profile_config_t* config,
    const uint8_t* buffer,
    size_t size,
    bool (*get_message_info)(uint16_t msg_id, message_info_t* info))
{
    reader->config = config;
    reader->buffer = buffer;
    reader->size = size;
    reader->offset = 0;
    reader->get_message_info = get_message_info;
}

static inline frame_msg_info_t buffer_reader_next(buffer_reader_t* reader)
{
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (reader->offset >= reader->size) {
        return result;
    }
    
    const uint8_t* remaining = reader->buffer + reader->offset;
    size_t remaining_size = reader->size - reader->offset;
    
    if (reader->config->payload.has_crc || reader->config->payload.has_length) {
        result = profile_parse_with_crc(reader->config, remaining, remaining_size, reader->get_message_info);
    } else {
        if (reader->get_message_info == NULL) {
            reader->offset = reader->size;
            return result;
        }
        result = profile_parse_minimal(reader->config, remaining, remaining_size, reader->get_message_info);
    }
    
    if (result.valid) {
        size_t frame_size = profile_overhead(reader->config) + result.msg_len;
        reader->offset += frame_size;
    } else {
        reader->offset = reader->size;
    }
    
    return result;
}

static inline void buffer_reader_reset(buffer_reader_t* reader) { reader->offset = 0; }
static inline size_t buffer_reader_offset(const buffer_reader_t* reader) { return reader->offset; }
static inline size_t buffer_reader_remaining(const buffer_reader_t* reader) {
    return reader->size > reader->offset ? reader->size - reader->offset : 0;
}
static inline bool buffer_reader_has_more(const buffer_reader_t* reader) {
    return reader->offset < reader->size;
}

/*===========================================================================
 * BufferWriter - Encode multiple frames with automatic offset tracking
 *===========================================================================*/

typedef struct buffer_writer {
    const profile_config_t* config;
    uint8_t* buffer;
    size_t capacity;
    size_t offset;
} buffer_writer_t;

static inline void buffer_writer_init(
    buffer_writer_t* writer,
    const profile_config_t* config,
    uint8_t* buffer,
    size_t capacity)
{
    writer->config = config;
    writer->buffer = buffer;
    writer->capacity = capacity;
    writer->offset = 0;
}

static inline size_t buffer_writer_write_ext(
    buffer_writer_t* writer,
    uint8_t msg_id,
    const uint8_t* payload,
    size_t payload_size,
    uint8_t seq,
    uint8_t sys_id,
    uint8_t comp_id,
    uint8_t pkg_id,
    size_t base_size,
    uint8_t magic1,
    uint8_t magic2)
{
    size_t remaining = writer->capacity - writer->offset;
    size_t written;
    
    if (writer->config->payload.has_crc || writer->config->payload.has_length) {
        written = profile_encode_with_crc_ext(
            writer->config,
            writer->buffer + writer->offset,
            remaining,
            seq, sys_id, comp_id, pkg_id, msg_id,
            payload, payload_size, base_size, magic1, magic2);
    } else {
        written = profile_encode_minimal(
            writer->config,
            writer->buffer + writer->offset,
            remaining,
            msg_id, payload, payload_size);
    }
    
    if (written > 0) {
        writer->offset += written;
    }
    
    return written;
}

/* Backwards-compatible wrapper: callers that don't know base_size pass
 * payload_size implicitly (no extension support). Identical wire output to
 * the extension-aware variant for messages without extensions. */
static inline size_t buffer_writer_write(
    buffer_writer_t* writer,
    uint8_t msg_id,
    const uint8_t* payload,
    size_t payload_size,
    uint8_t seq,
    uint8_t sys_id,
    uint8_t comp_id,
    uint8_t pkg_id,
    uint8_t magic1,
    uint8_t magic2)
{
    return buffer_writer_write_ext(writer, msg_id, payload, payload_size,
                                   seq, sys_id, comp_id, pkg_id,
                                   payload_size, magic1, magic2);
}

static inline void buffer_writer_reset(buffer_writer_t* writer) { writer->offset = 0; }
static inline size_t buffer_writer_size(const buffer_writer_t* writer) { return writer->offset; }
static inline size_t buffer_writer_remaining(const buffer_writer_t* writer) {
    return writer->capacity > writer->offset ? writer->capacity - writer->offset : 0;
}
static inline uint8_t* buffer_writer_data(buffer_writer_t* writer) { return writer->buffer; }

/*===========================================================================
 * Helper Macros for Variable Message Encoding
 *===========================================================================*/

/**
 * Get the payload and size for encoding a message.
 * For variable messages with length field support, uses pack_variable() to truncate unused space.
 * For non-variable messages or minimal profiles, uses the full buffer.
 * 
 * Usage:
 *   GET_PAYLOAD_FOR_ENCODING(SerializationTestMyMessage, &msg, payload_ptr, payload_len);
 *   buffer_writer_write(writer, msg_id, payload_ptr, payload_len, ...);
 */
#define GET_PAYLOAD_FOR_ENCODING(MSG_TYPE, msg_ptr, out_payload, out_size) \
    do { \
        static uint8_t _temp_pack_buffer[MSG_TYPE##_MAX_SIZE]; \
        (void)_temp_pack_buffer; \
        if (SUPPORTS_VARIABLE_ENCODING(MSG_TYPE)) { \
            (out_size) = MSG_TYPE##_pack_variable((msg_ptr), _temp_pack_buffer); \
            (out_payload) = _temp_pack_buffer; \
        } else { \
            (out_payload) = (const uint8_t*)(msg_ptr); \
            (out_size) = sizeof(*(msg_ptr)); \
        } \
    } while(0)

/**
 * Check if variable encoding is supported for a message type.
 * Returns true if the message has IS_VARIABLE defined (message is variable)
 * AND the config has a length field (not a minimal profile).
 */
#define SUPPORTS_VARIABLE_ENCODING(MSG_TYPE) \
    (IS_VARIABLE_MESSAGE(MSG_TYPE) && has_length_field_for_variable_encoding)

/**
 * Check if a message type has the IS_VARIABLE flag defined.
 */
#define IS_VARIABLE_MESSAGE(MSG_TYPE) \
    (defined(MSG_TYPE##_IS_VARIABLE) && MSG_TYPE##_IS_VARIABLE)

/**
 * Set this variable based on the profile config before encoding.
 * For profiles with length fields (Standard, Bulk, Network): true
 * For minimal profiles (Sensor, IPC): false
 */
static bool has_length_field_for_variable_encoding = true;

/*===========================================================================
 * AccumulatingReader - Unified parser for buffer and byte-by-byte streaming
 *===========================================================================*/

typedef enum accumulating_reader_state {
    ACC_STATE_IDLE = 0,
    ACC_STATE_LOOKING_FOR_START1 = 1,
    ACC_STATE_LOOKING_FOR_START2 = 2,
    ACC_STATE_COLLECTING_HEADER = 3,
    ACC_STATE_COLLECTING_PAYLOAD = 4,
    ACC_STATE_BUFFER_MODE = 5
} accumulating_reader_state_t;

typedef struct accumulating_reader {
    const profile_config_t* config;
    bool (*get_message_info)(uint16_t msg_id, message_info_t* info);
    
    uint8_t* internal_buffer;
    size_t buffer_size;
    size_t internal_data_len;
    size_t expected_frame_size;
    accumulating_reader_state_t state;
    
    const uint8_t* current_buffer;
    size_t current_size;
    size_t current_offset;

    /* Diagnostic counters (stream mode) */
    frame_parser_diagnostics_t diagnostics;
    uint8_t last_seq;
    bool last_seq_valid;
} accumulating_reader_t;

static inline void accumulating_reader_init(
    accumulating_reader_t* reader,
    const profile_config_t* config,
    uint8_t* internal_buffer,
    size_t buffer_size,
    bool (*get_message_info)(uint16_t msg_id, message_info_t* info))
{
    reader->config = config;
    reader->get_message_info = get_message_info;
    reader->internal_buffer = internal_buffer;
    reader->buffer_size = buffer_size;
    reader->internal_data_len = 0;
    reader->expected_frame_size = 0;
    reader->state = ACC_STATE_IDLE;
    reader->current_buffer = NULL;
    reader->current_size = 0;
    reader->current_offset = 0;
    frame_parser_diagnostics_t zero_diag = {0, 0, 0, 0};
    reader->diagnostics = zero_diag;
    reader->last_seq = 0;
    reader->last_seq_valid = false;
}

static inline void accumulating_reader_add_data(
    accumulating_reader_t* reader,
    const uint8_t* buffer,
    size_t size)
{
    reader->current_buffer = buffer;
    reader->current_size = size;
    reader->current_offset = 0;
    reader->state = ACC_STATE_BUFFER_MODE;
    
    if (reader->internal_data_len > 0 && buffer != NULL) {
        size_t space_available = reader->buffer_size - reader->internal_data_len;
        size_t bytes_to_copy = (size < space_available) ? size : space_available;
        memcpy(reader->internal_buffer + reader->internal_data_len, buffer, bytes_to_copy);
        reader->internal_data_len += bytes_to_copy;
    }
}

/* Forward declaration */
static inline frame_msg_info_t _acc_parse_buffer(
    const accumulating_reader_t* reader,
    const uint8_t* buffer,
    size_t size);

static inline frame_msg_info_t accumulating_reader_next(accumulating_reader_t* reader)
{
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (reader->state != ACC_STATE_BUFFER_MODE) {
        return result;
    }
    
    uint8_t header_size = profile_header_size(reader->config);
    uint8_t footer_size = profile_footer_size(reader->config);
    
    if (reader->internal_data_len > 0 && reader->current_offset == 0) {
        result = _acc_parse_buffer(reader, reader->internal_buffer, reader->internal_data_len);
        
        if (result.valid) {
            size_t frame_size = header_size + footer_size + result.msg_len;
            size_t partial_len = reader->internal_data_len > reader->current_size ? 
                                 reader->internal_data_len - reader->current_size : 0;
            size_t bytes_from_current = frame_size > partial_len ? frame_size - partial_len : 0;
            reader->current_offset = bytes_from_current;
            reader->internal_data_len = 0;
            reader->expected_frame_size = 0;
            return result;
        } else {
            return result;
        }
    }
    
    if (reader->current_buffer == NULL || reader->current_offset >= reader->current_size) {
        return result;
    }
    
    const uint8_t* remaining = reader->current_buffer + reader->current_offset;
    size_t remaining_size = reader->current_size - reader->current_offset;
    result = _acc_parse_buffer(reader, remaining, remaining_size);
    
    if (result.valid) {
        size_t frame_size = header_size + footer_size + result.msg_len;
        reader->current_offset += frame_size;
        return result;
    }
    
    size_t remaining_len = reader->current_size - reader->current_offset;
    if (remaining_len > 0 && remaining_len < reader->buffer_size) {
        memcpy(reader->internal_buffer, remaining, remaining_len);
        reader->internal_data_len = remaining_len;
        reader->current_offset = reader->current_size;
    }
    
    return result;
}

static inline frame_msg_info_t accumulating_reader_push_byte(accumulating_reader_t* reader, uint8_t byte)
{
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    uint8_t header_size = profile_header_size(reader->config);
    uint8_t start_byte1 = reader->config->header.start_byte1;
    uint8_t start_byte2 = reader->config->header.start_byte2;
    
    /* For tiny headers, start byte encodes payload type */
    if (reader->config->header.header_type == HEADER_TINY && reader->config->header.encodes_payload_type) {
        start_byte1 = get_tiny_start_byte(reader->config->payload.payload_type);
    }
    /* For basic headers, second start byte encodes payload type */
    if (reader->config->header.header_type == HEADER_BASIC && reader->config->header.encodes_payload_type) {
        start_byte2 = get_basic_second_start_byte(reader->config->payload.payload_type);
    }
    
    if (reader->state == ACC_STATE_IDLE || reader->state == ACC_STATE_BUFFER_MODE) {
        reader->state = ACC_STATE_LOOKING_FOR_START1;
        reader->internal_data_len = 0;
        reader->expected_frame_size = 0;
    }
    
    switch (reader->state) {
        case ACC_STATE_LOOKING_FOR_START1:
            if (reader->config->header.num_start_bytes == 0) {
                reader->internal_buffer[0] = byte;
                reader->internal_data_len = 1;
                
                if (!reader->config->payload.has_length && !reader->config->payload.has_crc) {
                    if (reader->get_message_info) {
                        message_info_t info;
                        if (reader->get_message_info(byte, &info)) {
                            size_t msg_len = info.size;
                            reader->expected_frame_size = header_size + msg_len;
                            
                            if (reader->expected_frame_size > reader->buffer_size) {
                                reader->state = ACC_STATE_LOOKING_FOR_START1;
                                reader->internal_data_len = 0;
                                return result;
                            }
                            
                            if (msg_len == 0) {
                                result.valid = true;
                                result.msg_id = byte;
                                result.msg_len = 0;
                                result.msg_data = reader->internal_buffer + header_size;
                                reader->state = ACC_STATE_LOOKING_FOR_START1;
                                reader->internal_data_len = 0;
                                reader->expected_frame_size = 0;
                                return result;
                            }
                            
                            reader->state = ACC_STATE_COLLECTING_PAYLOAD;
                        } else {
                            reader->state = ACC_STATE_LOOKING_FOR_START1;
                            reader->internal_data_len = 0;
                        }
                    } else {
                        reader->state = ACC_STATE_LOOKING_FOR_START1;
                        reader->internal_data_len = 0;
                    }
                } else {
                    reader->state = ACC_STATE_COLLECTING_HEADER;
                }
            } else {
                if (byte == start_byte1) {
                    reader->internal_buffer[0] = byte;
                    reader->internal_data_len = 1;
                    
                    if (reader->config->header.num_start_bytes == 1) {
                        reader->state = ACC_STATE_COLLECTING_HEADER;
                    } else {
                        reader->state = ACC_STATE_LOOKING_FOR_START2;
                    }
                }
            }
            break;
            
        case ACC_STATE_LOOKING_FOR_START2:
            if (byte == start_byte2) {
                reader->internal_buffer[reader->internal_data_len++] = byte;
                reader->state = ACC_STATE_COLLECTING_HEADER;
            } else if (byte == start_byte1) {
                reader->internal_buffer[0] = byte;
                reader->internal_data_len = 1;
            } else {
                reader->diagnostics.cnt_sync_recoveries++;
                reader->state = ACC_STATE_LOOKING_FOR_START1;
                reader->internal_data_len = 0;
            }
            break;
            
        case ACC_STATE_COLLECTING_HEADER:
            if (reader->internal_data_len >= reader->buffer_size) {
                reader->diagnostics.cnt_sync_recoveries++;
                reader->state = ACC_STATE_LOOKING_FOR_START1;
                reader->internal_data_len = 0;
                return result;
            }
            
            reader->internal_buffer[reader->internal_data_len++] = byte;
            
            if (reader->internal_data_len >= header_size) {
                if (!reader->config->payload.has_length && !reader->config->payload.has_crc) {
                    uint8_t msg_id = reader->internal_buffer[header_size - 1];
                    if (reader->get_message_info) {
                        message_info_t info;
                        if (reader->get_message_info(msg_id, &info)) {
                            size_t msg_len = info.size;
                            reader->expected_frame_size = header_size + msg_len;
                            
                            if (reader->expected_frame_size > reader->buffer_size) {
                                reader->diagnostics.cnt_sync_recoveries++;
                                reader->state = ACC_STATE_LOOKING_FOR_START1;
                                reader->internal_data_len = 0;
                                return result;
                            }
                            
                            if (msg_len == 0) {
                                result.valid = true;
                                result.msg_id = msg_id;
                                result.msg_len = 0;
                                result.msg_data = reader->internal_buffer + header_size;
                                reader->state = ACC_STATE_LOOKING_FOR_START1;
                                reader->internal_data_len = 0;
                                reader->expected_frame_size = 0;
                                return result;
                            }
                            
                            reader->state = ACC_STATE_COLLECTING_PAYLOAD;
                        } else {
                            reader->diagnostics.cnt_sync_recoveries++;
                            reader->state = ACC_STATE_LOOKING_FOR_START1;
                            reader->internal_data_len = 0;
                        }
                    } else {
                        reader->diagnostics.cnt_sync_recoveries++;
                        reader->state = ACC_STATE_LOOKING_FOR_START1;
                        reader->internal_data_len = 0;
                    }
                } else {
                    size_t len_offset = reader->config->header.num_start_bytes;
                    if (reader->config->payload.has_seq) len_offset++;
                    if (reader->config->payload.has_sys_id) len_offset++;
                    if (reader->config->payload.has_comp_id) len_offset++;
                    
                    size_t payload_len = 0;
                    if (reader->config->payload.has_length) {
                        if (reader->config->payload.length_bytes == 1) {
                            payload_len = reader->internal_buffer[len_offset];
                        } else {
                            payload_len = reader->internal_buffer[len_offset] | 
                                         ((size_t)reader->internal_buffer[len_offset + 1] << 8);
                        }
                    }

                    /* Check for length mismatch against expected message struct size */
                    if (reader->config->payload.has_length && reader->get_message_info) {
                        uint16_t full_msg_id = 0;
                        if (reader->config->payload.has_pkg_id) {
                            full_msg_id = (uint16_t)reader->internal_buffer[header_size - 2] << 8;
                        }
                        full_msg_id |= reader->internal_buffer[header_size - 1];
                        message_info_t len_info;
                        if (reader->get_message_info(full_msg_id, &len_info) &&
                            len_info.size != payload_len) {
                            reader->diagnostics.cnt_len_errors++;
                        }
                    }
                    
                    uint8_t footer_size = profile_footer_size(reader->config);
                    reader->expected_frame_size = header_size + footer_size + payload_len;
                    
                    if (reader->expected_frame_size > reader->buffer_size) {
                        reader->diagnostics.cnt_sync_recoveries++;
                        reader->state = ACC_STATE_LOOKING_FOR_START1;
                        reader->internal_data_len = 0;
                        return result;
                    }
                    
                    if (reader->internal_data_len >= reader->expected_frame_size) {
                        result = _acc_parse_buffer(reader, reader->internal_buffer, reader->internal_data_len);
                        if (result.valid) {
                            if (reader->config->payload.has_seq) {
                                uint8_t seq = reader->internal_buffer[reader->config->header.num_start_bytes];
                                if (reader->last_seq_valid) {
                                    uint8_t expected_seq = (uint8_t)(reader->last_seq + 1);
                                    if (seq != expected_seq) reader->diagnostics.cnt_seq_gaps++;
                                }
                                reader->last_seq = seq;
                                reader->last_seq_valid = true;
                            }
                        } else {
                            if (reader->config->payload.has_crc) reader->diagnostics.cnt_crc_failures++;
                            reader->diagnostics.cnt_sync_recoveries++;
                        }
                        reader->state = ACC_STATE_LOOKING_FOR_START1;
                        reader->internal_data_len = 0;
                        reader->expected_frame_size = 0;
                        return result;
                    }
                    
                    reader->state = ACC_STATE_COLLECTING_PAYLOAD;
                }
            }
            break;
            
        case ACC_STATE_COLLECTING_PAYLOAD:
            if (reader->internal_data_len >= reader->buffer_size) {
                reader->diagnostics.cnt_sync_recoveries++;
                reader->state = ACC_STATE_LOOKING_FOR_START1;
                reader->internal_data_len = 0;
                return result;
            }
            
            reader->internal_buffer[reader->internal_data_len++] = byte;
            
            if (reader->internal_data_len >= reader->expected_frame_size) {
                result = _acc_parse_buffer(reader, reader->internal_buffer, reader->internal_data_len);
                if (result.valid) {
                    if (reader->config->payload.has_seq) {
                        uint8_t seq = reader->internal_buffer[reader->config->header.num_start_bytes];
                        if (reader->last_seq_valid) {
                            uint8_t expected_seq = (uint8_t)(reader->last_seq + 1);
                            if (seq != expected_seq) reader->diagnostics.cnt_seq_gaps++;
                        }
                        reader->last_seq = seq;
                        reader->last_seq_valid = true;
                    }
                } else {
                    if (reader->config->payload.has_crc) reader->diagnostics.cnt_crc_failures++;
                    reader->diagnostics.cnt_sync_recoveries++;
                }
                reader->state = ACC_STATE_LOOKING_FOR_START1;
                reader->internal_data_len = 0;
                reader->expected_frame_size = 0;
                return result;
            }
            break;
            
        default:
            reader->state = ACC_STATE_LOOKING_FOR_START1;
            break;
    }
    
    return result;
}

static inline frame_msg_info_t _acc_parse_buffer(
    const accumulating_reader_t* reader,
    const uint8_t* buffer,
    size_t size)
{
    if (reader->config->payload.has_crc || reader->config->payload.has_length) {
        return profile_parse_with_crc(reader->config, buffer, size, reader->get_message_info);
    } else {
        return profile_parse_minimal(reader->config, buffer, size, reader->get_message_info);
    }
}

static inline bool accumulating_reader_has_more(const accumulating_reader_t* reader) {
    if (reader->state != ACC_STATE_BUFFER_MODE) return false;
    return (reader->internal_data_len > 0) || 
           (reader->current_buffer != NULL && reader->current_offset < reader->current_size);
}

static inline bool accumulating_reader_has_partial(const accumulating_reader_t* reader) {
    return reader->internal_data_len > 0;
}

static inline size_t accumulating_reader_partial_size(const accumulating_reader_t* reader) {
    return reader->internal_data_len;
}

static inline accumulating_reader_state_t accumulating_reader_state(const accumulating_reader_t* reader) {
    return reader->state;
}

static inline frame_parser_diagnostics_t accumulating_reader_diagnostics(const accumulating_reader_t* reader) {
    return reader->diagnostics;
}

static inline void accumulating_reader_reset_diagnostics(accumulating_reader_t* reader) {
    frame_parser_diagnostics_t zero_diag = {0, 0, 0, 0};
    reader->diagnostics = zero_diag;
}

static inline void accumulating_reader_reset(accumulating_reader_t* reader) {
    reader->internal_data_len = 0;
    reader->expected_frame_size = 0;
    reader->state = ACC_STATE_IDLE;
    reader->current_buffer = NULL;
    reader->current_size = 0;
    reader->current_offset = 0;
    reader->last_seq = 0;
    reader->last_seq_valid = false;
}
