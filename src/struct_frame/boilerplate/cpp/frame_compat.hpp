/**
 * Compatibility layer for frame parser functions (C++)
 * Provides encode/decode functions composed from separated header and payload types
 */

#pragma once

#include "frame_base.hpp"
#include "frame_headers/base.hpp"
#include "frame_headers/header_tiny.hpp"
#include "frame_headers/header_basic.hpp"
#include "payload_types/base.hpp"
#include "payload_types/payload_default.hpp"
#include "payload_types/payload_minimal.hpp"
#include "payload_types/payload_extended.hpp"
#include "payload_types/payload_extended_multi_system_stream.hpp"

#include <cstring>

namespace FrameParsers {

/* Basic + Default */
inline size_t basic_default_encode(uint8_t* buffer, size_t buffer_size,
                                   uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 4;  /* [0x90] [0x71] [LEN] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 255) {
        return 0;
    }
    
    buffer[0] = FrameHeaders::BASIC_START_BYTE;
    buffer[1] = FrameHeaders::get_basic_second_start_byte(static_cast<uint8_t>(PayloadTypes::PAYLOAD_DEFAULT_CONFIG.payload_type));
    buffer[2] = static_cast<uint8_t>(msg_size);
    buffer[3] = msg_id;
    std::memcpy(buffer + header_size, msg, msg_size);
    
    FrameChecksum ck = fletcher_checksum(buffer + 2, msg_size + 2);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

inline FrameMsgInfo basic_default_validate_packet(const uint8_t* buffer, size_t length) {
    FrameMsgInfo result = {false, 0, 0, nullptr};
    
    if (length < 6 || buffer[0] != FrameHeaders::BASIC_START_BYTE || 
        !FrameHeaders::is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return validate_payload_with_crc(buffer, length, 4, 1, 2);
}

/* Tiny + Minimal */
inline size_t tiny_minimal_encode(uint8_t* buffer, size_t buffer_size,
                                  uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 2;  /* [0x70] [MSG_ID] */
    const size_t total_size = header_size + msg_size;
    
    if (buffer_size < total_size) {
        return 0;
    }
    
    buffer[0] = FrameHeaders::get_tiny_start_byte(static_cast<uint8_t>(PayloadTypes::PAYLOAD_MINIMAL_CONFIG.payload_type));
    buffer[1] = msg_id;
    std::memcpy(buffer + header_size, msg, msg_size);
    
    return total_size;
}

inline FrameMsgInfo tiny_minimal_validate_packet(const uint8_t* buffer, size_t length) {
    FrameMsgInfo result = {false, 0, 0, nullptr};
    
    if (length < 2 || !FrameHeaders::is_tiny_start_byte(buffer[0])) {
        return result;
    }
    
    return validate_payload_minimal(buffer, length, 2);
}

/* Basic + Extended */
inline size_t basic_extended_encode(uint8_t* buffer, size_t buffer_size,
                                    uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 6;  /* [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 65535) {
        return 0;
    }
    
    buffer[0] = FrameHeaders::BASIC_START_BYTE;
    buffer[1] = FrameHeaders::get_basic_second_start_byte(static_cast<uint8_t>(PayloadTypes::PAYLOAD_EXTENDED_CONFIG.payload_type));
    buffer[2] = static_cast<uint8_t>(msg_size & 0xFF);
    buffer[3] = static_cast<uint8_t>((msg_size >> 8) & 0xFF);
    buffer[4] = 0;  /* PKG_ID = 0 */
    buffer[5] = msg_id;
    std::memcpy(buffer + header_size, msg, msg_size);
    
    FrameChecksum ck = fletcher_checksum(buffer + 2, msg_size + 4);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

inline FrameMsgInfo basic_extended_validate_packet(const uint8_t* buffer, size_t length) {
    FrameMsgInfo result = {false, 0, 0, nullptr};
    
    if (length < 8 || buffer[0] != FrameHeaders::BASIC_START_BYTE || 
        !FrameHeaders::is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return validate_payload_with_crc(buffer, length, 6, 2, 2);
}

/* Basic + Extended Multi System Stream */
inline size_t basic_extended_multi_system_stream_encode(uint8_t* buffer, size_t buffer_size,
                                                         uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 9;  /* [0x90] [0x78] [SEQ] [SYS] [COMP] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 65535) {
        return 0;
    }
    
    buffer[0] = FrameHeaders::BASIC_START_BYTE;
    buffer[1] = FrameHeaders::get_basic_second_start_byte(static_cast<uint8_t>(PayloadTypes::PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG.payload_type));
    buffer[2] = 0;  /* SEQ = 0 */
    buffer[3] = 0;  /* SYS_ID = 0 */
    buffer[4] = 0;  /* COMP_ID = 0 */
    buffer[5] = static_cast<uint8_t>(msg_size & 0xFF);
    buffer[6] = static_cast<uint8_t>((msg_size >> 8) & 0xFF);
    buffer[7] = 0;  /* PKG_ID = 0 */
    buffer[8] = msg_id;
    std::memcpy(buffer + header_size, msg, msg_size);
    
    FrameChecksum ck = fletcher_checksum(buffer + 2, msg_size + 7);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

inline FrameMsgInfo basic_extended_multi_system_stream_validate_packet(const uint8_t* buffer, size_t length) {
    FrameMsgInfo result = {false, 0, 0, nullptr};
    
    if (length < 11 || buffer[0] != FrameHeaders::BASIC_START_BYTE || 
        !FrameHeaders::is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return validate_payload_with_crc(buffer, length, 9, 2, 2);
}

/* Basic + Minimal */
inline size_t basic_minimal_encode(uint8_t* buffer, size_t buffer_size,
                                   uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 3;  /* [0x90] [0x70] [MSG_ID] */
    const size_t total_size = header_size + msg_size;
    
    if (buffer_size < total_size) {
        return 0;
    }
    
    buffer[0] = FrameHeaders::BASIC_START_BYTE;
    buffer[1] = FrameHeaders::get_basic_second_start_byte(static_cast<uint8_t>(PayloadTypes::PAYLOAD_MINIMAL_CONFIG.payload_type));
    buffer[2] = msg_id;
    std::memcpy(buffer + header_size, msg, msg_size);
    
    return total_size;
}

inline FrameMsgInfo basic_minimal_validate_packet(const uint8_t* buffer, size_t length) {
    FrameMsgInfo result = {false, 0, 0, nullptr};
    
    if (length < 3 || buffer[0] != FrameHeaders::BASIC_START_BYTE || 
        !FrameHeaders::is_basic_second_start_byte(buffer[1])) {
        return result;
    }
    
    return validate_payload_minimal(buffer, length, 3);
}

/* Tiny + Default */
inline size_t tiny_default_encode(uint8_t* buffer, size_t buffer_size,
                                  uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
    const size_t header_size = 3;  /* [0x71] [LEN] [MSG_ID] */
    const size_t footer_size = 2;  /* [CRC1] [CRC2] */
    const size_t total_size = header_size + msg_size + footer_size;
    
    if (buffer_size < total_size || msg_size > 255) {
        return 0;
    }
    
    buffer[0] = FrameHeaders::get_tiny_start_byte(static_cast<uint8_t>(PayloadTypes::PAYLOAD_DEFAULT_CONFIG.payload_type));
    buffer[1] = static_cast<uint8_t>(msg_size);
    buffer[2] = msg_id;
    std::memcpy(buffer + header_size, msg, msg_size);
    
    FrameChecksum ck = fletcher_checksum(buffer + 1, msg_size + 2);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

inline FrameMsgInfo tiny_default_validate_packet(const uint8_t* buffer, size_t length) {
    FrameMsgInfo result = {false, 0, 0, nullptr};
    
    if (length < 5 || !FrameHeaders::is_tiny_start_byte(buffer[0])) {
        return result;
    }
    
    return validate_payload_with_crc(buffer, length, 3, 1, 1);
}

} // namespace FrameParsers
