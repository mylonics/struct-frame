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

/* System frames (payload type 9, start byte 0x79) carry struct-frame's own messages next to
 * the application's. Define SF_DISABLE_SYSTEM_FRAMES to compile the reader support out. */
#ifndef SF_DISABLE_SYSTEM_FRAMES
#define SF_SYSTEM_FRAMES_ENABLED 1
#include "sf_system_info.h"
#else
#define SF_SYSTEM_FRAMES_ENABLED 0
static inline bool sf_system_frame_message_info(uint16_t msg_id, message_info_t* info) {
    (void)msg_id;
    (void)info;
    return false;
}
#endif

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

/* First start byte of a profile (a Tiny header's only byte carries the payload type). */
static inline uint8_t profile_start_byte1(const profile_config_t* config) {
    if (config->header.encodes_payload_type && config->header.num_start_bytes == 1) {
        return get_tiny_start_byte((uint8_t)config->payload.payload_type);
    }
    return config->header.start_byte1;
}

/* Second start byte of a profile (a Basic header's second byte carries the payload type). */
static inline uint8_t profile_start_byte2(const profile_config_t* config) {
    if (config->header.encodes_payload_type && config->header.num_start_bytes == 2) {
        return get_basic_second_start_byte((uint8_t)config->payload.payload_type);
    }
    return config->header.start_byte2;
}

/* True when frames of config can be told apart from system frames: the header carries the
 * payload type in a start byte (Basic and Tiny headers). */
static inline bool profile_supports_system_frames(const profile_config_t* config) {
    return SF_SYSTEM_FRAMES_ENABLED && config->header.encodes_payload_type &&
           config->header.num_start_bytes >= 1;
}

/* The system-frame profile for the header of config. */
static inline profile_config_t profile_system_config(const profile_config_t* config) {
    profile_config_t sys;
    sys.header = config->header;
    sys.payload = PAYLOAD_SYSTEM_CONFIG;
    return sys;
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
    uint8_t pkg_id, uint16_t msg_id,
    const uint8_t* payload_data, size_t payload_size,
    size_t base_size,
    uint8_t magic1, uint8_t magic2) {
    
    uint8_t header_size = profile_header_size(config);
    uint8_t footer_size = profile_footer_size(config);
    /* The wire carries a 1-byte message id. Profiles with a package-id byte take the
     * high byte of a package-qualified id from pkg_id (the caller passes the low byte
     * as msg_id, or the full id, which is narrowed here). Profiles without one cannot
     * represent a larger id: refuse rather than truncate. */
    if (!config->payload.has_pkg_id && msg_id > 0xFF) {
        return 0;
    }

    size_t overhead = header_size + footer_size;
    size_t total_size = overhead + payload_size;
    size_t max_payload = (config->payload.length_bytes == 1) ? 255 : 65535;
    
    if (buffer_size < total_size || payload_size > max_payload) {
        return 0;
    }
    
    size_t idx = 0;
    
    /* Write start bytes (the payload type is folded in for Tiny/Basic headers) */
    if (config->header.num_start_bytes >= 1) {
        buffer[idx++] = profile_start_byte1(config);
    }
    if (config->header.num_start_bytes >= 2) {
        buffer[idx++] = profile_start_byte2(config);
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
    
    /* Write message ID (low byte; the high byte is the package id above) */
    buffer[idx++] = (uint8_t)(msg_id & 0xFF);

    /* Write payload (already in place when it was serialized into
     * buffer_writer_payload_slot) */
    if (payload_size > 0 && payload_data != NULL) {
        if (payload_data != buffer + idx) {
            memcpy(buffer + idx, payload_data, payload_size);
        }
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
    uint8_t pkg_id, uint16_t msg_id,
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
    uint16_t msg_id,
    const uint8_t* payload_data, size_t payload_size) {
    
    /* The wire carries a 1-byte message id (the package id travels separately).
     * Refuse to truncate: a larger id means the caller picked the wrong profile. */
    if (msg_id > 0xFF) {
        return 0;
    }

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
    
    /* Write payload (already in place when it was serialized into
     * buffer_writer_payload_slot) */
    if (payload_size > 0 && payload_data != NULL) {
        if (payload_data != buffer + idx) {
            memcpy(buffer + idx, payload_data, payload_size);
        }
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
    
    frame_msg_info_t result = frame_msg_info_empty();
    uint8_t header_size = profile_header_size(config);
    uint8_t footer_size = profile_footer_size(config);
    size_t overhead = header_size + footer_size;
    
    if (length < overhead) {
        return result;
    }
    
    /* Verify start bytes (the payload type is folded in for Tiny/Basic headers) */
    size_t idx = 0;
    if (config->header.num_start_bytes >= 1 && buffer[idx++] != profile_start_byte1(config)) {
        result.status = FRAME_MSG_STATUS_WAITING_FOR_START;
        return result;
    }
    if (config->header.num_start_bytes >= 2 && buffer[idx++] != profile_start_byte2(config)) {
        result.status = FRAME_MSG_STATUS_WAITING_FOR_START;
        return result;
    }

    size_t crc_start = idx;

    /* Optional fields before length */
    if (config->payload.has_seq) result.sequence = buffer[idx++];
    if (config->payload.has_sys_id) result.system_id = buffer[idx++];
    if (config->payload.has_comp_id) result.component_id = buffer[idx++];

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
        result.package_id = buffer[idx];
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
    
    frame_msg_info_t result = frame_msg_info_empty();
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
    uint16_t msg_id, const uint8_t* payload_data, size_t payload_size,
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
 * System frames - encode, and helpers shared by the readers
 *===========================================================================*/

/* Header size of a system frame for the header of config (where the fixed fields start). */
static inline size_t profile_system_header_size(const profile_config_t* config) {
    return (size_t)config->header.num_start_bytes + payload_config_header_size(&PAYLOAD_SYSTEM_CONFIG);
}

/**
 * Encode a system frame: system message system_msg_id with its serialized fixed fields and
 * an optional raw tail (Ping, Pong, LinkTestData, RpcRequest, RpcResponse). fixed and tail
 * may already sit in buffer (fixed at buffer + profile_system_header_size(config)).
 * Returns the frame size, or 0 when the profile cannot carry system frames, the message is
 * unknown, fixed_size is not its fixed size, the tail is too long or the buffer too small.
 */
static inline size_t profile_encode_system_frame(
    const profile_config_t* config,
    uint8_t* buffer, size_t buffer_size,
    uint8_t seq, uint8_t sys_id, uint8_t comp_id,
    uint8_t system_msg_id,
    const uint8_t* fixed, size_t fixed_size,
    const uint8_t* tail, size_t tail_size)
{
    message_info_t info;
    if (!profile_supports_system_frames(config) || !sf_system_frame_message_info(system_msg_id, &info)) {
        return 0;
    }
    if (fixed_size != info.min_size || tail_size > info.size - info.min_size) {
        return 0;
    }
    profile_config_t sys = profile_system_config(config);
    size_t header_size = profile_header_size(&sys);
    size_t payload_size = fixed_size + tail_size;
    if (buffer_size < header_size + payload_size + profile_footer_size(&sys)) {
        return 0;
    }
    uint8_t* slot = buffer + header_size;
    if (fixed_size > 0 && fixed != slot) memmove(slot, fixed, fixed_size);
    if (tail_size > 0 && tail != slot + fixed_size) memmove(slot + fixed_size, tail, tail_size);
    return profile_encode_with_crc_ext(&sys, buffer, buffer_size, seq, sys_id, comp_id, 0,
                                       system_msg_id, slot, payload_size, payload_size,
                                       info.magic1, info.magic2);
}

/* The tail of a valid system frame (the bytes after the message's fixed fields). */
static inline const uint8_t* sf_system_frame_tail(const frame_msg_info_t* frame, size_t* tail_size) {
    message_info_t info;
    *tail_size = 0;
    if (!frame->valid || !frame->is_system || !sf_system_frame_message_info(frame->msg_id, &info) ||
        frame->msg_len < info.min_size) {
        return NULL;
    }
    *tail_size = frame->msg_len - info.min_size;
    return frame->msg_data + info.min_size;
}

/* True when data starts with the start bytes of a system frame of sys. */
static inline bool _sf_is_system_start(const profile_config_t* sys, bool enabled,
                                       const uint8_t* data, size_t size) {
    if (!enabled || size < 1 || data[0] != profile_start_byte1(sys)) return false;
    if (sys->header.num_start_bytes >= 2) {
        return size >= 2 && data[1] == profile_start_byte2(sys);
    }
    return true;
}

/* Check the header of a candidate system frame: 1 when the system message id is known and
 * the length fits it, 0 when not, -1 while the header is incomplete. */
static inline int _sf_system_header_check(const profile_config_t* sys, const uint8_t* data, size_t size) {
    size_t hs = profile_header_size(sys);
    if (size < hs) return -1;
    size_t off = (size_t)sys->header.num_start_bytes + 3; /* after SEQ, SYS, COMP */
    size_t length = (size_t)data[off] | ((size_t)data[off + 1] << 8);
    message_info_t info;
    if (!sf_system_frame_message_info(data[hs - 1], &info)) return 0;
    return (length >= info.min_size && length <= info.size) ? 1 : 0;
}

/* Parse a frame known to start with system start bytes. */
static inline frame_msg_info_t _sf_parse_system(const profile_config_t* sys, const uint8_t* data, size_t size) {
    frame_msg_info_t result;
    if (_sf_system_header_check(sys, data, size) == 0) {
        memset(&result, 0, sizeof(result));
        result.status = FRAME_MSG_STATUS_WAITING_FOR_START;
        result.is_system = true;
        return result;
    }
    result = profile_parse_with_crc(sys, data, size, sf_system_frame_message_info);
    result.is_system = true;
    return result;
}

/* Index of the next byte in buf[begin, end) that can start an application frame (sb1) or a
 * system frame (sys_sb1, when system frames are enabled), or end when there is none. */
static inline size_t _sf_find_start(const uint8_t* buf, size_t begin, size_t end,
                                    uint8_t sb1, bool sys_enabled, uint8_t sys_sb1) {
    if (begin >= end) return end;
    const void* p = memchr(buf + begin, (int)sb1, end - begin);
    size_t nxt = p ? (size_t)((const uint8_t*)p - buf) : end;
    if (sys_enabled && sys_sb1 != sb1 && nxt > begin) {
        const void* q = memchr(buf + begin, (int)sys_sb1, nxt - begin);
        if (q) nxt = (size_t)((const uint8_t*)q - buf);
    }
    return nxt;
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
    /* System frames: skipped unless deliver_system_frames (see
     * buffer_reader_set_deliver_system_frames). */
    bool system_enabled;
    bool deliver_system_frames;
    profile_config_t system_config;
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
    reader->system_enabled = profile_supports_system_frames(config);
    reader->deliver_system_frames = false;
    reader->system_config = profile_system_config(config);
}

/* Return system frames (is_system) from buffer_reader_next() instead of skipping them. */
static inline void buffer_reader_set_deliver_system_frames(buffer_reader_t* reader, bool deliver) {
    reader->deliver_system_frames = deliver;
}

static inline frame_msg_info_t _buffer_reader_next_frame(buffer_reader_t* reader)
{
    frame_msg_info_t result = frame_msg_info_empty();

    if (reader->offset >= reader->size) {
        return result;
    }

    const uint8_t* remaining = reader->buffer + reader->offset;
    size_t remaining_size = reader->size - reader->offset;

    if (_sf_is_system_start(&reader->system_config, reader->system_enabled, remaining, remaining_size)) {
        result = _sf_parse_system(&reader->system_config, remaining, remaining_size);
    } else if (reader->config->payload.has_crc || reader->config->payload.has_length) {
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
        /* Head byte is not a valid start — scan forward to next start byte,
         * reporting a SyncRecovery event so try_next() keeps advancing. */
        size_t old_offset = reader->offset;
        if (reader->config->header.num_start_bytes >= 1) {
            reader->offset = _sf_find_start(reader->buffer, reader->offset + 1, reader->size,
                                            profile_start_byte1(reader->config), reader->system_enabled,
                                            profile_start_byte1(&reader->system_config));
        } else {
            /* No start bytes (e.g. IPC profile): advance one byte and retry so a
             * single unknown msg_id doesn't discard the rest of the buffer. */
            reader->offset += 1;
        }
        result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
        result.frame_size = reader->offset - old_offset;
    }
    /* COLLECTING: leave offset unchanged — frame is incomplete (normal end-of-buffer) */

    return result;
}

/* Parse the next frame. System frames are returned (is_system) only with
 * buffer_reader_set_deliver_system_frames(reader, true); otherwise they are skipped. */
static inline frame_msg_info_t buffer_reader_next(buffer_reader_t* reader)
{
    for (;;) {
        frame_msg_info_t result = _buffer_reader_next_frame(reader);
        if (result.valid && result.is_system && !reader->deliver_system_frames) continue;
        return result;
    }
}

static inline void buffer_reader_reset(buffer_reader_t* reader) { reader->offset = 0; }
static inline size_t buffer_reader_offset(const buffer_reader_t* reader) { return reader->offset; }
static inline size_t buffer_reader_remaining(const buffer_reader_t* reader) {
    return reader->size > reader->offset ? reader->size - reader->offset : 0;
}
static inline bool buffer_reader_has_more(const buffer_reader_t* reader) {
    return reader->offset < reader->size;
}

/* Try to parse the next frame, returning true while forward progress is made
 * (valid frame, CRC-failed frame, or resync bytes skipped).  Returns false only
 * when the buffer is drained or only a trailing partial frame remains.
 * Canonical drain loop:
 *   frame_msg_info_t f;
 *   while (buffer_reader_try_next(&reader, &f)) {
 *       if (f.valid) handle(f); // else CrcFailure or SyncRecovery
 *   } */
static inline bool buffer_reader_try_next(buffer_reader_t* reader, frame_msg_info_t* out) {
    *out = buffer_reader_next(reader);
    return out->valid || out->frame_size > 0;
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
    uint16_t msg_id,
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
    uint16_t msg_id,
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

/* Where the payload of the next frame goes, so a message can be serialized straight into
 * the writer's buffer (the generated <Type>_write helpers do this). Returns NULL when a frame
 * carrying max_payload bytes would not fit. Pass the returned pointer as the payload of
 * buffer_writer_write_ext; it is not copied again. */
static inline uint8_t* buffer_writer_payload_slot(buffer_writer_t* writer, size_t max_payload) {
    size_t needed = (size_t)profile_overhead(writer->config) + max_payload;
    if (writer->offset > writer->capacity || writer->capacity - writer->offset < needed) {
        return NULL;
    }
    return writer->buffer + writer->offset + profile_header_size(writer->config);
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

    /* Cached per-profile constants so the per-byte push path doesn't recompute
     * them on every call. */
    uint8_t cached_start_byte1;
    uint8_t cached_start_byte2;
    uint8_t cached_header_size;

    const uint8_t* current_buffer;
    size_t current_size;
    size_t current_offset;

    /* Diagnostic counters (stream mode) */
    frame_parser_diagnostics_t diagnostics;
    uint8_t last_seq;
    bool last_seq_valid;

    /* System frames (payload type 9) share the profile's header; they are counted and
     * skipped unless deliver_system_frames (accumulating_reader_set_deliver_system_frames).
     * Their sequence numbers are tracked separately from the application frames'. */
    bool system_enabled;
    bool deliver_system_frames;
    profile_config_t system_config;
    uint8_t sys_start_byte1;
    uint8_t sys_start_byte2;
    uint8_t sys_header_size;
    uint8_t last_sys_seq;
    bool last_sys_seq_valid;
    /* Stream mode: the frame being collected is a system frame. */
    bool collecting_system;
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

    /* Precompute the per-profile constants used on every push_byte() call. */
    reader->cached_start_byte1 = config->header.start_byte1;
    reader->cached_start_byte2 = config->header.start_byte2;
    if (config->header.header_type == HEADER_TINY && config->header.encodes_payload_type) {
        reader->cached_start_byte1 = get_tiny_start_byte(config->payload.payload_type);
    }
    if (config->header.header_type == HEADER_BASIC && config->header.encodes_payload_type) {
        reader->cached_start_byte2 = get_basic_second_start_byte(config->payload.payload_type);
    }
    reader->cached_header_size = profile_header_size(config);
    reader->current_buffer = NULL;
    reader->current_size = 0;
    reader->current_offset = 0;
    memset(&reader->diagnostics, 0, sizeof(reader->diagnostics));
    reader->last_seq = 0;
    reader->last_seq_valid = false;

    reader->system_enabled = profile_supports_system_frames(config);
    reader->deliver_system_frames = false;
    reader->system_config = profile_system_config(config);
    reader->sys_start_byte1 = profile_start_byte1(&reader->system_config);
    reader->sys_start_byte2 = profile_start_byte2(&reader->system_config);
    reader->sys_header_size = profile_header_size(&reader->system_config);
    reader->last_sys_seq = 0;
    reader->last_sys_seq_valid = false;
    reader->collecting_system = false;
}

/* Return system frames (is_system) from next()/push_byte() instead of only counting them. */
static inline void accumulating_reader_set_deliver_system_frames(accumulating_reader_t* reader, bool deliver) {
    reader->deliver_system_frames = deliver;
}

static inline void _acc_count_system_frame(accumulating_reader_t* reader, const frame_msg_info_t* frame) {
    reader->diagnostics.cnt_system_frames++;
    if (reader->last_sys_seq_valid && frame->sequence != (uint8_t)(reader->last_sys_seq + 1)) {
        reader->diagnostics.cnt_seq_gaps++;
    }
    reader->last_sys_seq = frame->sequence;
    reader->last_sys_seq_valid = true;
}

static inline size_t _acc_find_start(const accumulating_reader_t* reader, const uint8_t* buf,
                                     size_t begin, size_t end) {
    return _sf_find_start(buf, begin, end, profile_start_byte1(reader->config),
                          reader->system_enabled, reader->sys_start_byte1);
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

/* Record per-frame diagnostics for a complete frame consumed in buffer mode,
 * matching the stream-mode (push_byte) counter semantics:
 *  - cnt_len_errors when the header length is outside [min_size, size]
 *  - cnt_seq_gaps on valid frames for profiles that carry a sequence number
 * frame_start points at the first byte of the frame (start bytes included). */
static inline void _acc_record_frame_diagnostics(
    accumulating_reader_t* reader, const uint8_t* frame_start, bool valid)
{
    if (_sf_is_system_start(&reader->system_config, reader->system_enabled, frame_start,
                            reader->system_config.header.num_start_bytes)) {
        return; /* counted by _acc_count_system_frame; the header was already validated */
    }
    const profile_config_t* config = reader->config;
    if (config->payload.has_length && reader->get_message_info) {
        size_t len_offset = config->header.num_start_bytes;
        if (config->payload.has_seq) len_offset++;
        if (config->payload.has_sys_id) len_offset++;
        if (config->payload.has_comp_id) len_offset++;
        size_t payload_len;
        if (config->payload.length_bytes == 1) {
            payload_len = frame_start[len_offset];
        } else {
            payload_len = frame_start[len_offset] | ((size_t)frame_start[len_offset + 1] << 8);
        }
        uint8_t header_size = profile_header_size(config);
        uint16_t full_msg_id = 0;
        if (config->payload.has_pkg_id) {
            full_msg_id = (uint16_t)frame_start[header_size - 2] << 8;
        }
        full_msg_id |= frame_start[header_size - 1];
        message_info_t info;
        if (reader->get_message_info(full_msg_id, &info) &&
            (payload_len > info.size || payload_len < info.min_size)) {
            reader->diagnostics.cnt_len_errors++;
        }
    }
    if (valid && config->payload.has_seq) {
        uint8_t seq = frame_start[config->header.num_start_bytes];
        if (reader->last_seq_valid) {
            uint8_t expected_seq = (uint8_t)(reader->last_seq + 1);
            if (seq != expected_seq) reader->diagnostics.cnt_seq_gaps++;
        }
        reader->last_seq = seq;
        reader->last_seq_valid = true;
    }
}

/* True when the header at the start of data claims a frame that cannot fit in the internal
 * buffer (typically a corrupted length field). Only profiles with a length field carry such
 * a claim. Buffer mode uses it to resync immediately, as stream mode does, instead of
 * swallowing a buffer's worth of good data behind the bogus header. */
static inline bool _acc_claims_oversize_frame(
    const accumulating_reader_t* reader, const uint8_t* data, size_t size)
{
    const profile_config_t* config =
        _sf_is_system_start(&reader->system_config, reader->system_enabled, data, size)
            ? &reader->system_config : reader->config;
    if (!config->payload.has_length || size < profile_header_size(config)) return false;
    size_t off = config->header.num_start_bytes;
    if (config->payload.has_seq) off++;
    if (config->payload.has_sys_id) off++;
    if (config->payload.has_comp_id) off++;
    size_t payload_len = (config->payload.length_bytes == 1)
        ? data[off]
        : (size_t)(data[off] | ((size_t)data[off + 1] << 8));
    return profile_overhead(config) + payload_len > reader->buffer_size;
}

static inline frame_msg_info_t _acc_next_frame(accumulating_reader_t* reader)
{
    frame_msg_info_t result = frame_msg_info_empty();
    result.diagnostics = &reader->diagnostics;

    if (reader->state != ACC_STATE_BUFFER_MODE) {
        return result;
    }

    /* First, try to complete a partial message from the internal buffer.
     * partial_len = bytes that came from a PREVIOUS add_data call (before
     * bytes_appended_to_internal were added this call). */
    if (reader->internal_data_len > 0 && reader->current_offset == 0 &&
        reader->bytes_appended_to_internal == 0 &&
        reader->current_size > reader->current_offset) {
        /* Full-wedge escape: new data arrived but nothing could be appended
         * because the internal buffer is full. The buffered bytes can never
         * complete — discard them so parsing continues from the current
         * buffer instead of stalling forever. */
        reader->diagnostics.cnt_sync_recoveries++;
        reader->diagnostics.cnt_failed_bytes += (uint32_t)reader->internal_data_len;
        reader->internal_data_len = 0;
        reader->expected_frame_size = 0;
        /* fall through to current-buffer parsing below */
    }

    if (reader->internal_data_len > 0 && reader->current_offset == 0) {
        size_t partial_len = reader->internal_data_len - reader->bytes_appended_to_internal;
        result = _acc_parse_buffer(reader, reader->internal_buffer, reader->internal_data_len);

        if (result.valid) {
            _acc_record_frame_diagnostics(reader, reader->internal_buffer, true);
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
            reader->diagnostics.cnt_sync_recoveries++;
            _acc_record_frame_diagnostics(reader, reader->internal_buffer, false);
            size_t bytes_from_current = result.frame_size > partial_len ? result.frame_size - partial_len : 0;
            reader->current_offset = bytes_from_current;
            reader->internal_data_len = 0;
            reader->bytes_appended_to_internal = 0;
            reader->expected_frame_size = 0;
            return result;
        }

        /* Garbage prefix saved as a partial (WAITING_FOR_START), or a frame
         * that can never complete because its claimed size exceeds the
         * internal buffer (still collecting with the buffer full): resync
         * inside the internal buffer instead of waiting forever. */
        if (result.status == FRAME_MSG_STATUS_WAITING_FOR_START ||
            reader->internal_data_len >= reader->buffer_size ||
            _acc_claims_oversize_frame(reader, reader->internal_buffer, reader->internal_data_len)) {
            size_t discard = reader->internal_data_len;
            if (result.is_system && result.status == FRAME_MSG_STATUS_WAITING_FOR_START) {
                reader->diagnostics.cnt_system_rejected++;
            }
            if (reader->config->header.num_start_bytes >= 1) {
                discard = _acc_find_start(reader, reader->internal_buffer, 1, reader->internal_data_len);
            } else {
                /* No start bytes (e.g. IPC): advance one byte and retry. */
                discard = 1;
            }
            reader->diagnostics.cnt_sync_recoveries++;
            reader->diagnostics.cnt_failed_bytes += (uint32_t)discard;
            size_t keep = reader->internal_data_len - discard;
            if (keep > 0) {
                memmove(reader->internal_buffer, reader->internal_buffer + discard, keep);
            }
            /* Only the portion of the discard that reached into this cycle's
             * appended bytes reduces the appended count. */
            if (discard > partial_len) {
                reader->bytes_appended_to_internal -= (discard - partial_len);
            }
            reader->internal_data_len = keep;
            result.valid = false;
            result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
            result.frame_size = discard;
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
        _acc_record_frame_diagnostics(reader, cur, true);
        reader->current_offset += result.frame_size;
        return result;
    }

    if (!result.valid && result.frame_size > 0) {
        /* Complete frame with bad CRC — count it, skip it */
        reader->diagnostics.cnt_crc_failures++;
        reader->diagnostics.cnt_failed_bytes += (uint32_t)result.frame_size;
        reader->diagnostics.cnt_sync_recoveries++;
        _acc_record_frame_diagnostics(reader, cur, false);
        reader->current_offset += result.frame_size;
        return result;
    }

    if (result.status == FRAME_MSG_STATUS_WAITING_FOR_START) {
        /* Head byte is not a start byte — scan forward, reporting a SyncRecovery event
         * so accumulating_reader_try_next() keeps draining past garbage bytes. */
        size_t old_current_offset = reader->current_offset;
        if (result.is_system) {
            reader->diagnostics.cnt_system_rejected++;
        }
        if (reader->config->header.num_start_bytes >= 1) {
            reader->current_offset = _acc_find_start(reader, reader->current_buffer,
                                                     reader->current_offset + 1, reader->current_size);
        } else {
            /* No start bytes (e.g. IPC profile): advance one byte and retry so a
             * single unknown msg_id doesn't discard the rest of the buffer. */
            reader->current_offset += 1;
        }
        result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
        result.frame_size = reader->current_offset - old_current_offset;
        reader->diagnostics.cnt_sync_recoveries++;
        reader->diagnostics.cnt_failed_bytes += (uint32_t)result.frame_size;
        return result;
    }

    /* A header that claims a frame larger than the internal buffer can never complete:
     * resync past its start byte now rather than buffering good data behind it. */
    if (reader->config->header.num_start_bytes >= 1 &&
        _acc_claims_oversize_frame(reader, cur, cur_remaining)) {
        size_t old_current_offset = reader->current_offset;
        reader->current_offset = _acc_find_start(reader, reader->current_buffer,
                                                 reader->current_offset + 1, reader->current_size);
        result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
        result.frame_size = reader->current_offset - old_current_offset;
        reader->diagnostics.cnt_sync_recoveries++;
        reader->diagnostics.cnt_failed_bytes += (uint32_t)result.frame_size;
        return result;
    }

    /* COLLECTING — save remaining bytes to internal buffer for next add_data() */
    size_t remaining = reader->current_size - reader->current_offset;
    if (remaining > 0 && remaining < reader->buffer_size) {
        memcpy(reader->internal_buffer, cur, remaining);
        reader->internal_data_len = remaining;
        reader->bytes_appended_to_internal = 0;
        reader->current_offset = reader->current_size;
    } else if (remaining >= reader->buffer_size) {
        /* Partial too large to buffer — discard with diagnostics. */
        reader->diagnostics.cnt_sync_recoveries++;
        reader->diagnostics.cnt_failed_bytes += (uint32_t)remaining;
        reader->current_offset = reader->current_size;
    }

    return result;
}

/* Parse the next frame (buffer mode). System frames are returned (is_system) only with
 * accumulating_reader_set_deliver_system_frames(reader, true); otherwise they are counted
 * (cnt_system_frames) and skipped. */
static inline frame_msg_info_t accumulating_reader_next(accumulating_reader_t* reader)
{
    for (;;) {
        frame_msg_info_t result = _acc_next_frame(reader);
        if (result.valid && result.is_system) {
            _acc_count_system_frame(reader, &result);
            if (!reader->deliver_system_frames) continue;
        }
        return result;
    }
}

static inline frame_msg_info_t _acc_push_byte(accumulating_reader_t* reader, uint8_t byte)
{
    frame_msg_info_t result = frame_msg_info_empty();
    result.diagnostics = &reader->diagnostics;

    /* Use the constants precomputed at init instead of re-deriving them on
     * every pushed byte. cfg/header_size describe the frame being collected
     * (application or system); they are only used once a start byte chose it. */
    const profile_config_t* cfg = reader->collecting_system ? &reader->system_config : reader->config;
    uint8_t header_size = reader->collecting_system ? reader->sys_header_size : reader->cached_header_size;
    uint8_t start_byte1 = reader->cached_start_byte1;
    uint8_t start_byte2 = reader->cached_start_byte2;

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
                bool is_user = byte == start_byte1;
                if (is_user || (reader->system_enabled && byte == reader->sys_start_byte1)) {
                    reader->internal_buffer[0] = byte;
                    reader->internal_data_len = 1;
                    /* A Basic header shares its first byte with system frames: the second
                     * byte decides. A Tiny header's only byte decides now. */
                    reader->collecting_system = !is_user;

                    if (reader->config->header.num_start_bytes == 1) {
                        reader->state = ACC_STATE_COLLECTING_HEADER;
                    } else {
                        reader->state = ACC_STATE_LOOKING_FOR_START2;
                    }
                }
            }
            break;
            
        case ACC_STATE_LOOKING_FOR_START2:
            if (byte == start_byte2 || (reader->system_enabled && byte == reader->sys_start_byte2)) {
                reader->internal_buffer[reader->internal_data_len++] = byte;
                reader->collecting_system = byte != start_byte2;
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
                if (reader->collecting_system &&
                    _sf_system_header_check(cfg, reader->internal_buffer, reader->internal_data_len) != 1) {
                    /* Not a system frame after all: resync without collecting a payload. */
                    reader->diagnostics.cnt_system_rejected++;
                    reader->diagnostics.cnt_failed_bytes += (uint32_t)reader->internal_data_len;
                    reader->diagnostics.cnt_sync_recoveries++;
                    reader->state = ACC_STATE_LOOKING_FOR_START1;
                    reader->internal_data_len = 0;
                    reader->collecting_system = false;
                    result.status = FRAME_MSG_STATUS_SYNC_RECOVERY;
                    return result;
                }
                if (!cfg->payload.has_length && !cfg->payload.has_crc) {
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
                    size_t len_offset = cfg->header.num_start_bytes;
                    if (cfg->payload.has_seq) len_offset++;
                    if (cfg->payload.has_sys_id) len_offset++;
                    if (cfg->payload.has_comp_id) len_offset++;

                    size_t payload_len = 0;
                    if (cfg->payload.has_length) {
                        if (cfg->payload.length_bytes == 1) {
                            payload_len = reader->internal_buffer[len_offset];
                        } else {
                            payload_len = reader->internal_buffer[len_offset] | 
                                         ((size_t)reader->internal_buffer[len_offset + 1] << 8);
                        }
                    }

                    /* Check for length out-of-range against expected message struct size.
                     * Variable messages may legitimately encode shorter than max size, so
                     * flag only when payload_len > size (truncated) or < min_size (too short). */
                    if (!reader->collecting_system && cfg->payload.has_length && reader->get_message_info) {
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
                    
                    uint8_t footer_size = profile_footer_size(cfg);
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
                        if (result.valid && !result.is_system) {
                            if (reader->config->payload.has_seq) {
                                uint8_t seq = reader->internal_buffer[reader->config->header.num_start_bytes];
                                if (reader->last_seq_valid) {
                                    uint8_t expected_seq = (uint8_t)(reader->last_seq + 1);
                                    if (seq != expected_seq) reader->diagnostics.cnt_seq_gaps++;
                                }
                                reader->last_seq = seq;
                                reader->last_seq_valid = true;
                            }
                        } else if (!result.valid) {
                            if (cfg->payload.has_crc) {
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
                        reader->collecting_system = false;
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
                if (result.valid && !result.is_system) {
                    if (reader->config->payload.has_seq) {
                        uint8_t seq = reader->internal_buffer[reader->config->header.num_start_bytes];
                        if (reader->last_seq_valid) {
                            uint8_t expected_seq = (uint8_t)(reader->last_seq + 1);
                            if (seq != expected_seq) reader->diagnostics.cnt_seq_gaps++;
                        }
                        reader->last_seq = seq;
                        reader->last_seq_valid = true;
                    }
                } else if (!result.valid) {
                    if (cfg->payload.has_crc) {
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
                reader->collecting_system = false;
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

/* Push one byte (stream mode). System frames are returned (is_system) only with
 * accumulating_reader_set_deliver_system_frames(reader, true). */
static inline frame_msg_info_t accumulating_reader_push_byte(accumulating_reader_t* reader, uint8_t byte)
{
    frame_msg_info_t result = _acc_push_byte(reader, byte);
    if (result.valid && result.is_system) {
        _acc_count_system_frame(reader, &result);
        if (!reader->deliver_system_frames) {
            frame_msg_info_t hidden = frame_msg_info_empty();
            hidden.status = FRAME_MSG_STATUS_WAITING_FOR_START;
            hidden.diagnostics = &reader->diagnostics;
            return hidden;
        }
    }
    return result;
}

static inline frame_msg_info_t _acc_parse_buffer(
    const accumulating_reader_t* reader,
    const uint8_t* buffer,
    size_t size)
{
    frame_msg_info_t result;
    if (_sf_is_system_start(&reader->system_config, reader->system_enabled, buffer, size)) {
        result = _sf_parse_system(&reader->system_config, buffer, size);
    } else if (reader->config->payload.has_crc || reader->config->payload.has_length) {
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

/* Try to parse the next frame, returning true while forward progress is made
 * (valid frame, CRC-failed frame, or resync bytes skipped).  Returns false only
 * when the current buffer is exhausted or only a trailing partial is pending.
 * Canonical drain loop:
 *   frame_msg_info_t f;
 *   while (accumulating_reader_try_next(&reader, &f)) {
 *       if (f.valid) handle(f); // else CrcFailure or SyncRecovery
 *   }
 *   if (accumulating_reader_has_partial(&reader)) { // feed more data } */
static inline bool accumulating_reader_try_next(accumulating_reader_t* reader, frame_msg_info_t* out) {
    *out = accumulating_reader_next(reader);
    return out->valid || out->frame_size > 0;
}

static inline accumulating_reader_state_t accumulating_reader_state(const accumulating_reader_t* reader) {
    return reader->state;
}

static inline frame_parser_diagnostics_t accumulating_reader_diagnostics(const accumulating_reader_t* reader) {
    return reader->diagnostics;
}

static inline void accumulating_reader_reset_diagnostics(accumulating_reader_t* reader) {
    memset(&reader->diagnostics, 0, sizeof(reader->diagnostics));
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
    reader->last_sys_seq = 0;
    reader->last_sys_seq_valid = false;
    reader->collecting_system = false;
}



