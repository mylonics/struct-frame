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
    
    /* Read message ID (16-bit: high byte is pkg_id when has_pkg_id, low byte is msg_id) */
    uint16_t msg_id = 0;
    if (config->has_pkg_id) {
        msg_id = (uint16_t)buffer[idx++] << 8;  /* pkg_id (high byte) */
    }
    msg_id |= buffer[idx++];  /* msg_id (low byte) */
    
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
/* When msg_id > 255, the high byte is used as pkg_id */
static inline size_t encode_profile_bulk(uint8_t* buffer, size_t buffer_size,
                                         uint16_t msg_id,
                                         const uint8_t* payload, size_t payload_size) {
    uint8_t pkg_id = (uint8_t)((msg_id >> 8) & 0xFF);  /* high byte */
    uint8_t low_msg_id = (uint8_t)(msg_id & 0xFF);     /* low byte */
    return frame_format_encode_with_crc(&PROFILE_BULK_CONFIG, buffer, buffer_size,
                                        0, 0, 0, pkg_id, low_msg_id, payload, payload_size);
}

static inline frame_msg_info_t parse_profile_bulk_buffer(const uint8_t* buffer, size_t length) {
    return frame_format_parse_with_crc(&PROFILE_BULK_CONFIG, buffer, length);
}

/* Profile Network (Basic + ExtendedMultiSystemStream) */
/* When msg_id > 255, the high byte is used as pkg_id */
static inline size_t encode_profile_network(uint8_t* buffer, size_t buffer_size,
                                            uint8_t sequence, uint8_t system_id,
                                            uint8_t component_id, uint16_t msg_id,
                                            const uint8_t* payload, size_t payload_size) {
    uint8_t pkg_id = (uint8_t)((msg_id >> 8) & 0xFF);  /* high byte */
    uint8_t low_msg_id = (uint8_t)(msg_id & 0xFF);     /* low byte */
    return frame_format_encode_with_crc(&PROFILE_NETWORK_CONFIG, buffer, buffer_size,
                                        sequence, system_id, component_id, pkg_id, low_msg_id,
                                        payload, payload_size);
}

static inline frame_msg_info_t parse_profile_network_buffer(const uint8_t* buffer, size_t length) {
    return frame_format_parse_with_crc(&PROFILE_NETWORK_CONFIG, buffer, length);
}

/*===========================================================================
 * BufferReader - Iterate through multiple frames in a buffer
 *===========================================================================*/

/**
 * BufferReader state structure for iterating through multiple frames.
 * 
 * Usage:
 *   buffer_reader_t reader;
 *   buffer_reader_init(&reader, &PROFILE_STANDARD_CONFIG, buffer, size, NULL);
 *   frame_msg_info_t result;
 *   while ((result = buffer_reader_next(&reader)).valid) {
 *       // Process result.msg_id, result.msg_data, result.msg_len
 *   }
 * 
 * For minimal profiles that need get_msg_length:
 *   buffer_reader_init(&reader, &PROFILE_SENSOR_CONFIG, buffer, size, get_msg_length);
 */
typedef struct buffer_reader {
    const frame_format_config_t* config;
    const uint8_t* buffer;
    size_t size;
    size_t offset;
    bool (*get_msg_length)(size_t msg_id, size_t* len);
} buffer_reader_t;

/**
 * Initialize a buffer reader
 */
static inline void buffer_reader_init(
    buffer_reader_t* reader,
    const frame_format_config_t* config,
    const uint8_t* buffer,
    size_t size,
    bool (*get_msg_length)(size_t msg_id, size_t* len))
{
    reader->config = config;
    reader->buffer = buffer;
    reader->size = size;
    reader->offset = 0;
    reader->get_msg_length = get_msg_length;
}

/**
 * Parse the next frame in the buffer.
 * Returns frame_msg_info_t with valid=true if successful, valid=false if no more frames.
 */
static inline frame_msg_info_t buffer_reader_next(buffer_reader_t* reader)
{
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (reader->offset >= reader->size) {
        return result;
    }
    
    const uint8_t* remaining = reader->buffer + reader->offset;
    size_t remaining_size = reader->size - reader->offset;
    
    if (reader->config->has_crc || reader->config->has_length) {
        result = frame_format_parse_with_crc(reader->config, remaining, remaining_size);
    } else {
        /* For minimal profiles, check if get_msg_length callback is provided */
        if (reader->get_msg_length == NULL) {
            reader->offset = reader->size;
            return result;
        }
        result = frame_format_parse_minimal(reader->config, remaining, remaining_size, reader->get_msg_length);
    }
    
    if (result.valid) {
        size_t frame_size = reader->config->header_size + reader->config->footer_size + result.msg_len;
        reader->offset += frame_size;
    } else {
        /* No more valid frames - stop parsing */
        reader->offset = reader->size;
    }
    
    return result;
}

/**
 * Reset the reader to the beginning of the buffer.
 */
static inline void buffer_reader_reset(buffer_reader_t* reader)
{
    reader->offset = 0;
}

/**
 * Get the current offset in the buffer.
 */
static inline size_t buffer_reader_offset(const buffer_reader_t* reader)
{
    return reader->offset;
}

/**
 * Get the remaining bytes in the buffer.
 */
static inline size_t buffer_reader_remaining(const buffer_reader_t* reader)
{
    return reader->size > reader->offset ? reader->size - reader->offset : 0;
}

/**
 * Check if there are more bytes to parse.
 */
static inline bool buffer_reader_has_more(const buffer_reader_t* reader)
{
    return reader->offset < reader->size;
}

/*===========================================================================
 * BufferWriter - Encode multiple frames with automatic offset tracking
 *===========================================================================*/

/**
 * BufferWriter state structure for encoding multiple frames.
 * 
 * Usage:
 *   uint8_t buffer[1024];
 *   buffer_writer_t writer;
 *   buffer_writer_init(&writer, &PROFILE_STANDARD_CONFIG, buffer, sizeof(buffer));
 *   buffer_writer_write(&writer, msg_id, payload, payload_size, 0, 0, 0, 0);
 *   size_t total_written = buffer_writer_size(&writer);
 */
typedef struct buffer_writer {
    const frame_format_config_t* config;
    uint8_t* buffer;
    size_t capacity;
    size_t offset;
} buffer_writer_t;

/**
 * Initialize a buffer writer
 */
static inline void buffer_writer_init(
    buffer_writer_t* writer,
    const frame_format_config_t* config,
    uint8_t* buffer,
    size_t capacity)
{
    writer->config = config;
    writer->buffer = buffer;
    writer->capacity = capacity;
    writer->offset = 0;
}

/**
 * Write a message to the buffer.
 * Returns the number of bytes written, or 0 on failure.
 */
static inline size_t buffer_writer_write(
    buffer_writer_t* writer,
    uint8_t msg_id,
    const uint8_t* payload,
    size_t payload_size,
    uint8_t seq,
    uint8_t sys_id,
    uint8_t comp_id,
    uint8_t pkg_id)
{
    size_t remaining = writer->capacity - writer->offset;
    size_t written;
    
    if (writer->config->has_crc || writer->config->has_length) {
        written = frame_format_encode_with_crc(
            writer->config,
            writer->buffer + writer->offset,
            remaining,
            seq, sys_id, comp_id, pkg_id, msg_id,
            payload, payload_size);
    } else {
        written = frame_format_encode_minimal(
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

/**
 * Reset the writer to the beginning of the buffer.
 */
static inline void buffer_writer_reset(buffer_writer_t* writer)
{
    writer->offset = 0;
}

/**
 * Get the total number of bytes written.
 */
static inline size_t buffer_writer_size(const buffer_writer_t* writer)
{
    return writer->offset;
}

/**
 * Get the remaining capacity in the buffer.
 */
static inline size_t buffer_writer_remaining(const buffer_writer_t* writer)
{
    return writer->capacity > writer->offset ? writer->capacity - writer->offset : 0;
}

/**
 * Get pointer to the buffer.
 */
static inline uint8_t* buffer_writer_data(buffer_writer_t* writer)
{
    return writer->buffer;
}

/*===========================================================================
 * AccumulatingReader - Unified parser for buffer and byte-by-byte streaming
 *===========================================================================*/

/**
 * Parser state enumeration for AccumulatingReader
 */
typedef enum accumulating_reader_state {
    ACC_STATE_IDLE = 0,
    ACC_STATE_LOOKING_FOR_START1 = 1,
    ACC_STATE_LOOKING_FOR_START2 = 2,
    ACC_STATE_COLLECTING_HEADER = 3,
    ACC_STATE_COLLECTING_PAYLOAD = 4,
    ACC_STATE_BUFFER_MODE = 5
} accumulating_reader_state_t;

/**
 * AccumulatingReader state structure for unified buffer and streaming parsing.
 * 
 * Buffer mode usage:
 *   accumulating_reader_t reader;
 *   accumulating_reader_init(&reader, &PROFILE_STANDARD_CONFIG, internal_buf, 1024, NULL);
 *   accumulating_reader_add_data(&reader, chunk, chunk_size);
 *   frame_msg_info_t result;
 *   while ((result = accumulating_reader_next(&reader)).valid) {
 *       // Process complete messages
 *   }
 * 
 * Stream mode usage:
 *   accumulating_reader_t reader;
 *   accumulating_reader_init(&reader, &PROFILE_STANDARD_CONFIG, internal_buf, 1024, NULL);
 *   while (receiving) {
 *       uint8_t byte = read_byte();
 *       frame_msg_info_t result = accumulating_reader_push_byte(&reader, byte);
 *       if (result.valid) {
 *           // Process complete message
 *       }
 *   }
 */
typedef struct accumulating_reader {
    const frame_format_config_t* config;
    bool (*get_msg_length)(size_t msg_id, size_t* len);
    
    /* Internal buffer for partial messages */
    uint8_t* internal_buffer;
    size_t buffer_size;
    size_t internal_data_len;
    size_t expected_frame_size;
    accumulating_reader_state_t state;
    
    /* Buffer mode state */
    const uint8_t* current_buffer;
    size_t current_size;
    size_t current_offset;
} accumulating_reader_t;

/**
 * Initialize an accumulating reader
 * Note: caller must provide the internal_buffer for partial message storage
 */
static inline void accumulating_reader_init(
    accumulating_reader_t* reader,
    const frame_format_config_t* config,
    uint8_t* internal_buffer,
    size_t buffer_size,
    bool (*get_msg_length)(size_t msg_id, size_t* len))
{
    reader->config = config;
    reader->get_msg_length = get_msg_length;
    reader->internal_buffer = internal_buffer;
    reader->buffer_size = buffer_size;
    reader->internal_data_len = 0;
    reader->expected_frame_size = 0;
    reader->state = ACC_STATE_IDLE;
    reader->current_buffer = NULL;
    reader->current_size = 0;
    reader->current_offset = 0;
}

/**
 * Add a new buffer of data to process (buffer mode).
 */
static inline void accumulating_reader_add_data(
    accumulating_reader_t* reader,
    const uint8_t* buffer,
    size_t size)
{
    reader->current_buffer = buffer;
    reader->current_size = size;
    reader->current_offset = 0;
    reader->state = ACC_STATE_BUFFER_MODE;
    
    /* If we have partial data, try to complete it */
    if (reader->internal_data_len > 0 && buffer != NULL) {
        size_t space_available = reader->buffer_size - reader->internal_data_len;
        size_t bytes_to_copy = (size < space_available) ? size : space_available;
        memcpy(reader->internal_buffer + reader->internal_data_len, buffer, bytes_to_copy);
        reader->internal_data_len += bytes_to_copy;
    }
}

/* Forward declarations for internal functions */
static inline frame_msg_info_t _acc_parse_buffer(
    const accumulating_reader_t* reader,
    const uint8_t* buffer,
    size_t size);

/**
 * Parse the next frame (buffer mode).
 */
static inline frame_msg_info_t accumulating_reader_next(accumulating_reader_t* reader)
{
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (reader->state != ACC_STATE_BUFFER_MODE) {
        return result;
    }
    
    /* First, try to complete a partial message from the internal buffer */
    if (reader->internal_data_len > 0 && reader->current_offset == 0) {
        result = _acc_parse_buffer(reader, reader->internal_buffer, reader->internal_data_len);
        
        if (result.valid) {
            size_t frame_size = reader->config->header_size + reader->config->footer_size + result.msg_len;
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
    
    /* Parse from current buffer */
    if (reader->current_buffer == NULL || reader->current_offset >= reader->current_size) {
        return result;
    }
    
    const uint8_t* remaining = reader->current_buffer + reader->current_offset;
    size_t remaining_size = reader->current_size - reader->current_offset;
    result = _acc_parse_buffer(reader, remaining, remaining_size);
    
    if (result.valid) {
        size_t frame_size = reader->config->header_size + reader->config->footer_size + result.msg_len;
        reader->current_offset += frame_size;
        return result;
    }
    
    /* Parse failed - might be partial message at end of buffer */
    size_t remaining_len = reader->current_size - reader->current_offset;
    if (remaining_len > 0 && remaining_len < reader->buffer_size) {
        memcpy(reader->internal_buffer, remaining, remaining_len);
        reader->internal_data_len = remaining_len;
        reader->current_offset = reader->current_size;
    }
    
    return result;
}

/**
 * Push a single byte for parsing (stream mode).
 */
static inline frame_msg_info_t accumulating_reader_push_byte(accumulating_reader_t* reader, uint8_t byte)
{
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    /* Initialize state on first byte if idle */
    if (reader->state == ACC_STATE_IDLE || reader->state == ACC_STATE_BUFFER_MODE) {
        reader->state = ACC_STATE_LOOKING_FOR_START1;
        reader->internal_data_len = 0;
        reader->expected_frame_size = 0;
    }
    
    switch (reader->state) {
        case ACC_STATE_LOOKING_FOR_START1:
            if (reader->config->num_start_bytes == 0) {
                reader->internal_buffer[0] = byte;
                reader->internal_data_len = 1;
                
                if (!reader->config->has_length && !reader->config->has_crc) {
                    /* Handle minimal msg_id */
                    if (reader->get_msg_length) {
                        size_t msg_len = 0;
                        if (reader->get_msg_length(byte, &msg_len)) {
                            reader->expected_frame_size = reader->config->header_size + msg_len;
                            
                            if (reader->expected_frame_size > reader->buffer_size) {
                                reader->state = ACC_STATE_LOOKING_FOR_START1;
                                reader->internal_data_len = 0;
                                return result;
                            }
                            
                            if (msg_len == 0) {
                                result.valid = true;
                                result.msg_id = byte;
                                result.msg_len = 0;
                                result.msg_data = reader->internal_buffer + reader->config->header_size;
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
                if (byte == reader->config->start_byte1) {
                    reader->internal_buffer[0] = byte;
                    reader->internal_data_len = 1;
                    
                    if (reader->config->num_start_bytes == 1) {
                        reader->state = ACC_STATE_COLLECTING_HEADER;
                    } else {
                        reader->state = ACC_STATE_LOOKING_FOR_START2;
                    }
                }
            }
            break;
            
        case ACC_STATE_LOOKING_FOR_START2:
            if (byte == reader->config->start_byte2) {
                reader->internal_buffer[reader->internal_data_len++] = byte;
                reader->state = ACC_STATE_COLLECTING_HEADER;
            } else if (byte == reader->config->start_byte1) {
                reader->internal_buffer[0] = byte;
                reader->internal_data_len = 1;
            } else {
                reader->state = ACC_STATE_LOOKING_FOR_START1;
                reader->internal_data_len = 0;
            }
            break;
            
        case ACC_STATE_COLLECTING_HEADER:
            if (reader->internal_data_len >= reader->buffer_size) {
                reader->state = ACC_STATE_LOOKING_FOR_START1;
                reader->internal_data_len = 0;
                return result;
            }
            
            reader->internal_buffer[reader->internal_data_len++] = byte;
            
            if (reader->internal_data_len >= reader->config->header_size) {
                if (!reader->config->has_length && !reader->config->has_crc) {
                    uint8_t msg_id = reader->internal_buffer[reader->config->header_size - 1];
                    if (reader->get_msg_length) {
                        size_t msg_len = 0;
                        if (reader->get_msg_length(msg_id, &msg_len)) {
                            reader->expected_frame_size = reader->config->header_size + msg_len;
                            
                            if (reader->expected_frame_size > reader->buffer_size) {
                                reader->state = ACC_STATE_LOOKING_FOR_START1;
                                reader->internal_data_len = 0;
                                return result;
                            }
                            
                            if (msg_len == 0) {
                                result.valid = true;
                                result.msg_id = msg_id;
                                result.msg_len = 0;
                                result.msg_data = reader->internal_buffer + reader->config->header_size;
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
                    /* Calculate payload length from header */
                    size_t len_offset = reader->config->num_start_bytes;
                    if (reader->config->has_seq) len_offset++;
                    if (reader->config->has_sys_id) len_offset++;
                    if (reader->config->has_comp_id) len_offset++;
                    
                    size_t payload_len = 0;
                    if (reader->config->has_length) {
                        if (reader->config->length_bytes == 1) {
                            payload_len = reader->internal_buffer[len_offset];
                        } else {
                            payload_len = reader->internal_buffer[len_offset] | 
                                         ((size_t)reader->internal_buffer[len_offset + 1] << 8);
                        }
                    }
                    
                    reader->expected_frame_size = reader->config->header_size + 
                                                  reader->config->footer_size + payload_len;
                    
                    if (reader->expected_frame_size > reader->buffer_size) {
                        reader->state = ACC_STATE_LOOKING_FOR_START1;
                        reader->internal_data_len = 0;
                        return result;
                    }
                    
                    if (reader->internal_data_len >= reader->expected_frame_size) {
                        result = _acc_parse_buffer(reader, reader->internal_buffer, reader->internal_data_len);
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
                reader->state = ACC_STATE_LOOKING_FOR_START1;
                reader->internal_data_len = 0;
                return result;
            }
            
            reader->internal_buffer[reader->internal_data_len++] = byte;
            
            if (reader->internal_data_len >= reader->expected_frame_size) {
                result = _acc_parse_buffer(reader, reader->internal_buffer, reader->internal_data_len);
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

/**
 * Internal helper to parse a buffer
 */
static inline frame_msg_info_t _acc_parse_buffer(
    const accumulating_reader_t* reader,
    const uint8_t* buffer,
    size_t size)
{
    if (reader->config->has_crc || reader->config->has_length) {
        return frame_format_parse_with_crc(reader->config, buffer, size);
    } else {
        return frame_format_parse_minimal(reader->config, buffer, size, reader->get_msg_length);
    }
}

/**
 * Check if there might be more data to parse (buffer mode only).
 */
static inline bool accumulating_reader_has_more(const accumulating_reader_t* reader)
{
    if (reader->state != ACC_STATE_BUFFER_MODE) return false;
    return (reader->internal_data_len > 0) || 
           (reader->current_buffer != NULL && reader->current_offset < reader->current_size);
}

/**
 * Check if there's a partial message waiting for more data.
 */
static inline bool accumulating_reader_has_partial(const accumulating_reader_t* reader)
{
    return reader->internal_data_len > 0;
}

/**
 * Get the size of the partial message data (0 if none).
 */
static inline size_t accumulating_reader_partial_size(const accumulating_reader_t* reader)
{
    return reader->internal_data_len;
}

/**
 * Get current parser state (for debugging).
 */
static inline accumulating_reader_state_t accumulating_reader_state(const accumulating_reader_t* reader)
{
    return reader->state;
}

/**
 * Reset the reader, clearing any partial message data.
 */
static inline void accumulating_reader_reset(accumulating_reader_t* reader)
{
    reader->internal_data_len = 0;
    reader->expected_frame_size = 0;
    reader->state = ACC_STATE_IDLE;
    reader->current_buffer = NULL;
    reader->current_size = 0;
    reader->current_offset = 0;
}
