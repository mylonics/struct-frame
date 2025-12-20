/**
 * Compatibility layer for frame parser functions
 * Provides encode/decode functions composed from separated header and payload types
 */

#pragma once

#include "frame_base.h"
#include "frame_headers/base.h"
#include "frame_headers/header_tiny.h"
#include "frame_headers/header_basic.h"
#include "payload_types/base.h"
#include "payload_types/payload_default.h"
#include "payload_types/payload_minimal.h"
#include "payload_types/payload_extended.h"
#include "payload_types/payload_extended_multi_system_stream.h"

/* Basic + Default */
static inline size_t basic_default_encode(uint8_t* buffer, size_t buffer_size,
                                          uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 4;  /* [0x90] [0x71] [LEN] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 255) {
        return 0;
    }
    
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = get_basic_second_start_byte(PAYLOAD_DEFAULT_CONFIG.payload_type);
    buffer[2] = (uint8_t)msg_size;
    buffer[3] = msg_id;
    memcpy(buffer + header_size, msg, msg_size);
    
    frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, msg_size + 2);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

static inline frame_msg_info_t basic_default_validate_packet(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < 6 || buffer[0] != BASIC_START_BYTE || 
        !is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return frame_validate_payload_with_crc(buffer, length, 4, 1, 2);
}

/* Tiny + Minimal */
static inline size_t tiny_minimal_encode(uint8_t* buffer, size_t buffer_size,
                                        uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 2;  /* [0x70] [MSG_ID] */
    const size_t total_size = header_size + msg_size;
    
    if (buffer_size < total_size) {
        return 0;
    }
    
    buffer[0] = get_tiny_start_byte(PAYLOAD_MINIMAL_CONFIG.payload_type);
    buffer[1] = msg_id;
    memcpy(buffer + header_size, msg, msg_size);
    
    return total_size;
}

static inline frame_msg_info_t tiny_minimal_validate_packet(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < 2 || !is_tiny_start_byte(buffer[0])) {
        return result;
    }
    
    return frame_validate_payload_minimal(buffer, length, 2);
}

/* Basic + Extended */
static inline size_t basic_extended_encode(uint8_t* buffer, size_t buffer_size,
                                           uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 6;  /* [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 65535) {
        return 0;
    }
    
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = get_basic_second_start_byte(PAYLOAD_EXTENDED_CONFIG.payload_type);
    buffer[2] = (uint8_t)(msg_size & 0xFF);
    buffer[3] = (uint8_t)((msg_size >> 8) & 0xFF);
    buffer[4] = 0;  /* PKG_ID = 0 */
    buffer[5] = msg_id;
    memcpy(buffer + header_size, msg, msg_size);
    
    frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, msg_size + 4);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

static inline frame_msg_info_t basic_extended_validate_packet(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < 8 || buffer[0] != BASIC_START_BYTE || 
        !is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return frame_validate_payload_with_crc(buffer, length, 6, 2, 2);
}

/* Basic + Extended Multi System Stream */
static inline size_t basic_extended_multi_system_stream_encode(uint8_t* buffer, size_t buffer_size,
                                                                uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 9;  /* [0x90] [0x78] [SEQ] [SYS] [COMP] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 65535) {
        return 0;
    }
    
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = get_basic_second_start_byte(PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG.payload_type);
    buffer[2] = 0;  /* SEQ = 0 */
    buffer[3] = 0;  /* SYS_ID = 0 */
    buffer[4] = 0;  /* COMP_ID = 0 */
    buffer[5] = (uint8_t)(msg_size & 0xFF);
    buffer[6] = (uint8_t)((msg_size >> 8) & 0xFF);
    buffer[7] = 0;  /* PKG_ID = 0 */
    buffer[8] = msg_id;
    memcpy(buffer + header_size, msg, msg_size);
    
    frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, msg_size + 7);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

static inline frame_msg_info_t basic_extended_multi_system_stream_validate_packet(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < 11 || buffer[0] != BASIC_START_BYTE || 
        !is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return frame_validate_payload_with_crc(buffer, length, 9, 2, 2);
}

/* Basic + Minimal */
static inline size_t basic_minimal_encode(uint8_t* buffer, size_t buffer_size,
                                          uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 3;  /* [0x90] [0x70] [MSG_ID] */
    const size_t total_size = header_size + msg_size;
    
    if (buffer_size < total_size) {
        return 0;
    }
    
    buffer[0] = BASIC_START_BYTE;
    buffer[1] = get_basic_second_start_byte(PAYLOAD_MINIMAL_CONFIG.payload_type);
    buffer[2] = msg_id;
    memcpy(buffer + header_size, msg, msg_size);
    
    return total_size;
}

static inline frame_msg_info_t basic_minimal_validate_packet(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < 3 || buffer[0] != BASIC_START_BYTE || 
        !is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return frame_validate_payload_minimal(buffer, length, 3);
}

/* Tiny + Default */
static inline size_t tiny_default_encode(uint8_t* buffer, size_t buffer_size,
                                        uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 3;  /* [0x71] [LEN] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 255) {
        return 0;
    }
    
    buffer[0] = get_tiny_start_byte(PAYLOAD_DEFAULT_CONFIG.payload_type);
    buffer[1] = (uint8_t)msg_size;
    buffer[2] = msg_id;
    memcpy(buffer + header_size, msg, msg_size);
    
    frame_checksum_t ck = frame_fletcher_checksum(buffer + 1, msg_size + 2);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

static inline frame_msg_info_t tiny_default_validate_packet(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < 5 || !is_tiny_start_byte(buffer[0])) {
        return result;
    }
    
    return frame_validate_payload_with_crc(buffer, length, 3, 1, 1);
}
