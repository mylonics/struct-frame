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
    
    frame_msg_info_t result = {false, 0, 0, NULL, FRAME_MSG_STATUS_NONE, 0, NULL};
    uint8_t header_size = profile_header_size(config);
    uint8_t footer_size = profile_footer_size(config);
    size_t overhead = header_size + footer_size;
    
    if (length < overhead) {
        return result;
    }
    
    /* Verify start bytes */
    size_t idx = 0;
    if (config->header.num_start_bytes >= 1 && buffer[idx++] != config->header.start_byte1) {
        result.status = FRAME_MSG_STATUS_WAITING_FOR_START;
        return result;
    }
    if (config->header.num_start_bytes >= 2) {
        uint8_t expected_start2 = config->header.encodes_payload_type ?
            get_basic_second_start_byte(config->payload.payload_type) :
            config->header.start_byte2;
        if (buffer[idx++] != expected_start2) {
            result.status = FRAME_MSG_STATUS_WAITING_FOR_START;
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
        result.status = FRAME_MSG_STATUS_COLLECTING;
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
            result.frame_size = total_size;
            result.status = FRAME_MSG_STATUS_CRC_FAILURE;
            return result;
        }
    }

    result.valid = true;
    result.msg_id = msg_id;
    result.msg_len = msg_len;
    result.msg_data = (uint8_t*)(buffer + header_size);
    result.frame_size = total_size;

    return result;
}

/**
 * Generic parse function for minimal frames (requires get_message_info callback)
 */
static inline frame_msg_info_t profile_parse_minimal(
    const profile_config_t* config,
    const uint8_t* buffer, size_t length,
    bool (*get_message_info)(uint16_t msg_id, message_info_t* info)) {
    
    frame_msg_info_t result = {false, 0, 0, NULL, FRAME_MSG_STATUS_NONE, 0, NULL};
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
            result.status = FRAME_MSG_STATUS_WAITING_FOR_START;
            return result;
        }
    }
    if (config->header.num_start_bytes >= 2 && buffer[idx++] != config->header.start_byte2) {
        result.status = FRAME_MSG_STATUS_WAITING_FOR_START;
        return result;
    }

    /* Read message ID */
    uint8_t msg_id = buffer[idx];

    /* Get message length from callback */
    size_t msg_len = 0;
    message_info_t info;
    if (!get_message_info || !get_message_info(msg_id, &info)) {
        result.status = FRAME_MSG_STATUS_WAITING_FOR_START;
        return result;
    }
    msg_len = info.size;

    size_t total_size = header_size + msg_len;
    if (length < total_size) {
        result.status = FRAME_MSG_STATUS_COLLECTING;
        return result;
    }

    result.valid = true;
    result.msg_id = msg_id;
    result.msg_len = msg_len;
    result.msg_data = (uint8_t*)(buffer + header_size);
    result.frame_size = total_size;

    return result;
}

/*===========================================================================
 * Config-dispatched entry points — match Python/TS/C# single-function API
 *===========================================================================*/

/**
 * Encode a frame using the profile config.
 * Dispatches to profile_encode_with_crc_ext or profile_encode_minimal based on
 * config->payload.has_crc. Matches the Python encode_message() / TS encodeMessage()
 * / C# FrameEncoder.Encode() calling convention.
 */
static inline size_t profile_encode_message(
    const profile_config_t* config,
    uint8_t* buffer, size_t buffer_size,
    uint8_t seq, uint8_t sys_id, uint8_t comp_id, uint8_t pkg_id,
    uint8_t msg_id, const uint8_t* payload_data, size_t payload_size,
    size_t base_size, uint8_t magic1, uint8_t magic2)
{
    if (config->payload.has_crc) {
        return profile_encode_with_crc_ext(config, buffer, buffer_size,
            seq, sys_id, comp_id, pkg_id, msg_id,
            payload_data, payload_size, base_size, magic1, magic2);
    } else {
        return profile_encode_minimal(config, buffer, buffer_size, msg_id, payload_data, payload_size);
    }
}

/**
 * Parse one frame from a buffer using the profile config.
 * Dispatches to profile_parse_with_crc or profile_parse_minimal based on
 * config->payload.has_crc. Matches the Python / TS / C# single parse entry point.
 */
static inline frame_msg_info_t profile_parse(
    const profile_config_t* config,
    const uint8_t* buffer, size_t length,
    bool (*get_message_info_func)(uint16_t msg_id, message_info_t* info))
{
    if (config->payload.has_crc || config->payload.has_length) {
        return profile_parse_with_crc(config, buffer, length, get_message_info_func);
    } else {
        return profile_parse_minimal(config, buffer, length, get_message_info_func);
    }
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
    frame_msg_info_t result = {false, 0, 0, NULL, FRAME_MSG_STATUS_NONE, 0, NULL};

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

    if (result.frame_size > 0) {
        /* Advance past complete frames — valid or CRC-failed */
        reader->offset += result.frame_size;
    } else if (result.status == FRAME_MSG_STATUS_WAITING_FOR_START) {
        /* Head byte is not a valid start — scan forward to next start byte */
        if (reader->config->header.num_start_bytes >= 1) {
            /* Compute the expected start byte for this profile */
            uint8_t sb1 = reader->config->header.start_byte1;
            if (reader->config->header.header_type == HEADER_TINY &&
                reader->config->header.encodes_payload_type) {
                sb1 = get_tiny_start_byte(reader->config->payload.payload_type);
            }
            size_t scan_start = reader->offset + 1;
            if (scan_start < reader->size) {
                const void* p = memchr(reader->buffer + scan_start,
                                       (int)sb1,
                                       reader->size - scan_start);
                reader->offset = p ? (size_t)((const uint8_t*)p - reader->buffer) : reader->size;
            } else {
                reader->offset = reader->size;
            }
        } else {
            reader->offset = reader->size;
        }
    }
    /* COLLECTING: leave offset unchanged — frame is incomplete (normal end-of-buffer) */

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
    size_t bytes_appended_to_internal; /* bytes copied from current buffer into internal buffer this add_data() call */
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
    reader->bytes_appended_to_internal = 0;
    reader->state = ACC_STATE_IDLE;
    reader->current_buffer = NULL;
    reader->current_size = 0;
    reader->current_offset = 0;
    frame_parser_diagnostics_t zero_diag = {0, 0, 0, 0, 0};
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
    reader->bytes_appended_to_internal = 0;

    if (reader->internal_data_len > 0 && buffer != NULL) {
        size_t space_available = reader->buffer_size - reader->internal_data_len;
        size_t bytes_to_copy = (size < space_available) ? size : space_available;
        memcpy(reader->internal_buffer + reader->internal_data_len, buffer, bytes_to_copy);
        reader->internal_data_len += bytes_to_copy;
        reader->bytes_appended_to_internal = bytes_to_copy;
    }
}

/* Forward declaration */
static inline frame_msg_info_t _acc_parse_buffer(
    const accumulating_reader_t* reader,
    const uint8_t* buffer,
    size_t size);

static inline frame_msg_info_t accumulating_reader_next(accumulating_reader_t* reader)
{
    frame_msg_info_t result = {false, 0, 0, NULL, FRAME_MSG_STATUS_NONE, 0, NULL};
    result.diagnostics = &reader->diagnostics;

    if (reader->state != ACC_STATE_BUFFER_MODE) {
        return result;
    }

    /* Compute start byte 1 (needed for memchr resync scan) */
    uint8_t sb1 = reader->config->header.start_byte1;
    if (reader->config->header.header_type == HEADER_TINY &&
        reader->config->header.encodes_payload_type) {
        sb1 = get_tiny_start_byte(reader->config->payload.payload_type);
    }

    /* First, try to complete a partial message from the internal buffer.
     * partial_len = bytes that came from a PREVIOUS add_data call (before
     * bytes_appended_to_internal were added this call). */
    if (reader->internal_data_len > 0 && reader->current_offset == 0) {
        size_t partial_len = reader->internal_data_len - reader->bytes_appended_to_internal;
        result = _acc_parse_buffer(reader, reader->internal_buffer, reader->internal_data_len);

        if (result.valid) {
            size_t bytes_from_current = result.frame_size > partial_len ? result.frame_size - partial_len : 0;
            reader->current_offset = bytes_from_current;
            reader->internal_data_len = 0;
            reader->bytes_appended_to_internal = 0;
            reader->expected_frame_size = 0;
            return result;
        }

        if (result.frame_size > 0) {
            /* Complete frame but CRC failed — count it and skip */
            reader->diagnostics.cnt_crc_failures++;
            reader->diagnostics.cnt_failed_bytes += (uint32_t)result.frame_size;
            size_t bytes_from_current = result.frame_size > partial_len ? result.frame_size - partial_len : 0;
            reader->current_offset = bytes_from_current;
            reader->internal_data_len = 0;
            reader->bytes_appended_to_internal = 0;
            reader->expected_frame_size = 0;
            return result;
        }

        /* Still not enough data for a complete frame — wait for next add_data() */
        return result;
    }

    /* Parse from current buffer */
    if (reader->current_buffer == NULL || reader->current_offset >= reader->current_size) {
        return result;
    }

    const uint8_t* cur = reader->current_buffer + reader->current_offset;
    size_t cur_remaining = reader->current_size - reader->current_offset;
    result = _acc_parse_buffer(reader, cur, cur_remaining);

    if (result.valid && result.frame_size > 0) {
        reader->current_offset += result.frame_size;
        return result;
    }

    if (!result.valid && result.frame_size > 0) {
        /* Complete frame with bad CRC — count it, skip it */
        reader->diagnostics.cnt_crc_failures++;
        reader->diagnostics.cnt_failed_bytes += (uint32_t)result.frame_size;
        reader->current_offset += result.frame_size;
        return result;
    }

    if (result.status == FRAME_MSG_STATUS_WAITING_FOR_START) {
        /* Head byte is not a start byte — scan forward */
        if (reader->config->header.num_start_bytes >= 1) {
            size_t scan_start = reader->current_offset + 1;
            if (scan_start < reader->current_size) {
                const void* p = memchr(reader->current_buffer + scan_start,
                                       (int)sb1,
                                       reader->current_size - scan_start);
                if (p) {
                    reader->current_offset = (size_t)((const uint8_t*)p - reader->current_buffer);
                    return result; /* caller calls next() again from new position */
                }
            }
        }
        reader->current_offset = reader->current_size;
        return result;
    }

    /* COLLECTING — save remaining bytes to internal buffer for next add_data() */
    size_t remaining = reader->current_size - reader->current_offset;
    if (remaining > 0 && remaining < reader->buffer_size) {
        memcpy(reader->internal_buffer, cur, remaining);
        reader->internal_data_len = remaining;
        reader->bytes_appended_to_internal = 0;
        reader->current_offset = reader->current_size;
    }

    return result;
}

static inline frame_msg_info_t accumulating_reader_push_byte(accumulating_reader_t* reader, uint8_t byte)
{
    frame_msg_info_t result = {false, 0, 0, NULL, FRAME_MSG_STATUS_NONE, 0, NULL};
    result.diagnostics = &reader->diagnostics;
    
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
                                reader->diagnostics.cnt_failed_bytes += (uint32_t)reader->internal_data_len;
                                reader->internal_data_len = 0;
                                reader->diagnostics.cnt_sync_recoveries++;
                                result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
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
                            reader->diagnostics.cnt_failed_bytes += (uint32_t)reader->internal_data_len;
                reader->diagnostics.cnt_sync_recoveries++;
                            reader->state = ACC_STATE_LOOKING_FOR_START1;
                            reader->internal_data_len = 0;
                            result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
                            return result;
                        }
                    } else {
                        reader->diagnostics.cnt_failed_bytes += (uint32_t)reader->internal_data_len;
                reader->diagnostics.cnt_sync_recoveries++;
                        reader->state = ACC_STATE_LOOKING_FOR_START1;
                        reader->internal_data_len = 0;
                        result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
                        return result;
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
                reader->diagnostics.cnt_failed_bytes += (uint32_t)(reader->internal_data_len + 1);
                reader->diagnostics.cnt_sync_recoveries++;
                reader->state = ACC_STATE_LOOKING_FOR_START1;
                reader->internal_data_len = 0;
                result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
                return result;
            }
            break;
            
        case ACC_STATE_COLLECTING_HEADER:
            if (reader->internal_data_len >= reader->buffer_size) {
                reader->diagnostics.cnt_failed_bytes += (uint32_t)(reader->internal_data_len + 1);
                reader->diagnostics.cnt_sync_recoveries++;
                reader->state = ACC_STATE_LOOKING_FOR_START1;
                reader->internal_data_len = 0;
                result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
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
                                reader->diagnostics.cnt_failed_bytes += (uint32_t)reader->internal_data_len;
                                reader->diagnostics.cnt_sync_recoveries++;
                                reader->state = ACC_STATE_LOOKING_FOR_START1;
                                reader->internal_data_len = 0;
                                result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
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
                            reader->diagnostics.cnt_failed_bytes += (uint32_t)reader->internal_data_len;
                            reader->diagnostics.cnt_sync_recoveries++;
                            reader->state = ACC_STATE_LOOKING_FOR_START1;
                            reader->internal_data_len = 0;
                            result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
                            return result;
                        }
                    } else {
                        reader->diagnostics.cnt_failed_bytes += (uint32_t)reader->internal_data_len;
                        reader->diagnostics.cnt_sync_recoveries++;
                        reader->state = ACC_STATE_LOOKING_FOR_START1;
                        reader->internal_data_len = 0;
                        result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
                        return result;
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

                    /* Check for length out-of-range against expected message struct size.
                     * Variable messages may legitimately encode shorter than max size, so
                     * flag only when payload_len > size (truncated) or < min_size (too short). */
                    if (reader->config->payload.has_length && reader->get_message_info) {
                        uint16_t full_msg_id = 0;
                        if (reader->config->payload.has_pkg_id) {
                            full_msg_id = (uint16_t)reader->internal_buffer[header_size - 2] << 8;
                        }
                        full_msg_id |= reader->internal_buffer[header_size - 1];
                        message_info_t len_info;
                        if (reader->get_message_info(full_msg_id, &len_info) &&
                            (payload_len > len_info.size || payload_len < len_info.min_size)) {
                            reader->diagnostics.cnt_len_errors++;
                        }
                    }
                    
                    uint8_t footer_size = profile_footer_size(reader->config);
                    reader->expected_frame_size = header_size + footer_size + payload_len;
                    
                    if (reader->expected_frame_size > reader->buffer_size) {
                        reader->diagnostics.cnt_failed_bytes += (uint32_t)reader->internal_data_len;
                        reader->diagnostics.cnt_sync_recoveries++;
                        reader->state = ACC_STATE_LOOKING_FOR_START1;
                        reader->internal_data_len = 0;
                        result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
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
                            if (reader->config->payload.has_crc) {
                                reader->diagnostics.cnt_crc_failures++;
                                result.status = FRAME_MSG_STATUS_CRC_FAILURE;
                            } else {
                                result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
                            }
                            reader->diagnostics.cnt_failed_bytes += (uint32_t)reader->internal_data_len;
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
                reader->diagnostics.cnt_failed_bytes += (uint32_t)(reader->internal_data_len + 1);
                reader->diagnostics.cnt_sync_recoveries++;
                reader->state = ACC_STATE_LOOKING_FOR_START1;
                reader->internal_data_len = 0;
                result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
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
                    if (reader->config->payload.has_crc) {
                        reader->diagnostics.cnt_crc_failures++;
                        result.status = FRAME_MSG_STATUS_CRC_FAILURE;
                    } else {
                        result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
                    }
                    reader->diagnostics.cnt_failed_bytes += (uint32_t)reader->internal_data_len;
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
    
    /* Set status based on current parser state */
    if (reader->state == ACC_STATE_LOOKING_FOR_START1) {
        result.status = FRAME_MSG_STATUS_WAITING_FOR_START;
    } else {
        result.status = FRAME_MSG_STATUS_COLLECTING;
    }
    return result;
}

static inline frame_msg_info_t _acc_parse_buffer(
    const accumulating_reader_t* reader,
    const uint8_t* buffer,
    size_t size)
{
    frame_msg_info_t result;
    if (reader->config->payload.has_crc || reader->config->payload.has_length) {
        result = profile_parse_with_crc(reader->config, buffer, size, reader->get_message_info);
    } else {
        result = profile_parse_minimal(reader->config, buffer, size, reader->get_message_info);
    }
    result.diagnostics = &reader->diagnostics;
    return result;
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
    frame_parser_diagnostics_t zero_diag = {0, 0, 0, 0, 0};
    reader->diagnostics = zero_diag;
}

static inline void accumulating_reader_reset(accumulating_reader_t* reader) {
    reader->internal_data_len = 0;
    reader->expected_frame_size = 0;
    reader->bytes_appended_to_internal = 0;
    reader->state = ACC_STATE_IDLE;
    reader->current_buffer = NULL;
    reader->current_size = 0;
    reader->current_offset = 0;
    reader->last_seq = 0;
    reader->last_seq_valid = false;
}



