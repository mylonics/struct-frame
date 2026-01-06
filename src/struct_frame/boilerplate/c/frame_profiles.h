/* Frame Profiles - Pre-defined Header + Payload combinations */
/* 
 * This file provides ready-to-use encode/parse functions for the 5 standard profiles:
 * - Profile Standard: Basic + Default (General serial/UART)
 * - Profile Sensor: Tiny + Minimal (Low-bandwidth sensors)
 * - Profile IPC: None + Minimal (Trusted inter-process communication)
 * - Profile Bulk: Basic + Extended (Large data transfers with package namespacing)
 * - Profile Network: Basic + ExtendedMultiSystemStream (Multi-system networked communication)
 */

#pragma once

#include "frame_base.h"
#include "frame_headers/base.h"
#include "payload_types/base.h"

/*===========================================================================
 * Profile Standard: Basic + Default
 * Frame: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * Overhead: 6 bytes. Max payload: 255 bytes.
 *===========================================================================*/

#define PROFILE_STANDARD_START_BYTE1    0x90
#define PROFILE_STANDARD_START_BYTE2    0x71
#define PROFILE_STANDARD_HEADER_SIZE    4  /* start1 + start2 + len + msg_id */
#define PROFILE_STANDARD_FOOTER_SIZE    2  /* CRC */
#define PROFILE_STANDARD_OVERHEAD       (PROFILE_STANDARD_HEADER_SIZE + PROFILE_STANDARD_FOOTER_SIZE)

/**
 * Encode a message using Profile Standard (Basic + Default) format.
 * 
 * @param buffer Output buffer to write the encoded frame
 * @param buffer_size Size of the output buffer
 * @param msg_id Message ID
 * @param payload Pointer to payload data
 * @param payload_size Size of payload in bytes (max 255)
 * @return Number of bytes written, or 0 on failure
 */
static inline size_t encode_profile_standard(uint8_t* buffer, size_t buffer_size,
                                             uint8_t msg_id,
                                             const uint8_t* payload, size_t payload_size) {
    size_t total_size = PROFILE_STANDARD_OVERHEAD + payload_size;
    
    if (buffer_size < total_size || payload_size > 255) {
        return 0;
    }
    
    buffer[0] = PROFILE_STANDARD_START_BYTE1;
    buffer[1] = PROFILE_STANDARD_START_BYTE2;
    buffer[2] = (uint8_t)payload_size;
    buffer[3] = msg_id;
    
    if (payload_size > 0 && payload != NULL) {
        memcpy(buffer + PROFILE_STANDARD_HEADER_SIZE, payload, payload_size);
    }
    
    /* CRC covers: [LEN] [MSG_ID] [PAYLOAD] */
    frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, payload_size + 2);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

/**
 * Parse/validate a complete Profile Standard frame from a buffer.
 * 
 * @param buffer Input buffer containing the frame
 * @param length Length of data in buffer
 * @return frame_msg_info_t with valid=true if frame is valid
 */
static inline frame_msg_info_t parse_profile_standard_buffer(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < PROFILE_STANDARD_OVERHEAD) {
        return result;
    }
    
    if (buffer[0] != PROFILE_STANDARD_START_BYTE1 || buffer[1] != PROFILE_STANDARD_START_BYTE2) {
        return result;
    }
    
    size_t msg_len = buffer[2];
    size_t total_size = PROFILE_STANDARD_OVERHEAD + msg_len;
    
    if (length < total_size) {
        return result;
    }
    
    /* Verify CRC: covers [LEN] [MSG_ID] [PAYLOAD] */
    frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, msg_len + 2);
    if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
        return result;
    }
    
    result.valid = true;
    result.msg_id = buffer[3];
    result.msg_len = msg_len;
    result.msg_data = (uint8_t*)(buffer + PROFILE_STANDARD_HEADER_SIZE);
    
    return result;
}


/*===========================================================================
 * Profile Sensor: Tiny + Minimal
 * Frame: [0x70] [MSG_ID] [PAYLOAD]
 * Overhead: 2 bytes. No length field or CRC. Requires known message sizes.
 *===========================================================================*/

#define PROFILE_SENSOR_START_BYTE       0x70
#define PROFILE_SENSOR_HEADER_SIZE      2  /* start + msg_id */
#define PROFILE_SENSOR_FOOTER_SIZE      0
#define PROFILE_SENSOR_OVERHEAD         (PROFILE_SENSOR_HEADER_SIZE + PROFILE_SENSOR_FOOTER_SIZE)

/**
 * Encode a message using Profile Sensor (Tiny + Minimal) format.
 * 
 * @param buffer Output buffer to write the encoded frame
 * @param buffer_size Size of the output buffer
 * @param msg_id Message ID
 * @param payload Pointer to payload data
 * @param payload_size Size of payload in bytes
 * @return Number of bytes written, or 0 on failure
 */
static inline size_t encode_profile_sensor(uint8_t* buffer, size_t buffer_size,
                                           uint8_t msg_id,
                                           const uint8_t* payload, size_t payload_size) {
    size_t total_size = PROFILE_SENSOR_OVERHEAD + payload_size;
    
    if (buffer_size < total_size) {
        return 0;
    }
    
    buffer[0] = PROFILE_SENSOR_START_BYTE;
    buffer[1] = msg_id;
    
    if (payload_size > 0 && payload != NULL) {
        memcpy(buffer + PROFILE_SENSOR_HEADER_SIZE, payload, payload_size);
    }
    
    return total_size;
}

/**
 * Parse/validate a Profile Sensor frame from a buffer.
 * Requires the caller to provide the expected message size (no length field in frame).
 * 
 * @param buffer Input buffer containing the frame
 * @param length Length of data in buffer
 * @param get_msg_length Callback to get expected message length from msg_id.
 *        Uses size_t for msg_id to match generated get_message_length() signature.
 * @return frame_msg_info_t with valid=true if frame is valid
 */
static inline frame_msg_info_t parse_profile_sensor_buffer(const uint8_t* buffer, size_t length,
                                                           bool (*get_msg_length)(size_t msg_id, size_t* len)) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < PROFILE_SENSOR_OVERHEAD) {
        return result;
    }
    
    if (buffer[0] != PROFILE_SENSOR_START_BYTE) {
        return result;
    }
    
    uint8_t msg_id = buffer[1];
    size_t msg_len = 0;
    
    if (!get_msg_length || !get_msg_length(msg_id, &msg_len)) {
        return result;
    }
    
    size_t total_size = PROFILE_SENSOR_OVERHEAD + msg_len;
    if (length < total_size) {
        return result;
    }
    
    result.valid = true;
    result.msg_id = msg_id;
    result.msg_len = msg_len;
    result.msg_data = (uint8_t*)(buffer + PROFILE_SENSOR_HEADER_SIZE);
    
    return result;
}


/*===========================================================================
 * Profile IPC: None + Minimal
 * Frame: [MSG_ID] [PAYLOAD]
 * Overhead: 1 byte. No start bytes, no CRC. Relies on external synchronization.
 *===========================================================================*/

#define PROFILE_IPC_HEADER_SIZE         1  /* msg_id only */
#define PROFILE_IPC_FOOTER_SIZE         0
#define PROFILE_IPC_OVERHEAD            (PROFILE_IPC_HEADER_SIZE + PROFILE_IPC_FOOTER_SIZE)

/**
 * Encode a message using Profile IPC (None + Minimal) format.
 * 
 * @param buffer Output buffer to write the encoded frame
 * @param buffer_size Size of the output buffer
 * @param msg_id Message ID
 * @param payload Pointer to payload data
 * @param payload_size Size of payload in bytes
 * @return Number of bytes written, or 0 on failure
 */
static inline size_t encode_profile_ipc(uint8_t* buffer, size_t buffer_size,
                                        uint8_t msg_id,
                                        const uint8_t* payload, size_t payload_size) {
    size_t total_size = PROFILE_IPC_OVERHEAD + payload_size;
    
    if (buffer_size < total_size) {
        return 0;
    }
    
    buffer[0] = msg_id;
    
    if (payload_size > 0 && payload != NULL) {
        memcpy(buffer + PROFILE_IPC_HEADER_SIZE, payload, payload_size);
    }
    
    return total_size;
}

/**
 * Parse/validate a Profile IPC frame from a buffer.
 * Requires the caller to provide the expected message size (no length field in frame).
 * 
 * @param buffer Input buffer containing the frame
 * @param length Length of data in buffer
 * @param get_msg_length Callback to get expected message length from msg_id.
 *        Uses size_t for msg_id to match generated get_message_length() signature.
 * @return frame_msg_info_t with valid=true if frame is valid
 */
static inline frame_msg_info_t parse_profile_ipc_buffer(const uint8_t* buffer, size_t length,
                                                        bool (*get_msg_length)(size_t msg_id, size_t* len)) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < PROFILE_IPC_OVERHEAD) {
        return result;
    }
    
    uint8_t msg_id = buffer[0];
    size_t msg_len = 0;
    
    if (!get_msg_length || !get_msg_length(msg_id, &msg_len)) {
        return result;
    }
    
    size_t total_size = PROFILE_IPC_OVERHEAD + msg_len;
    if (length < total_size) {
        return result;
    }
    
    result.valid = true;
    result.msg_id = msg_id;
    result.msg_len = msg_len;
    result.msg_data = (uint8_t*)(buffer + PROFILE_IPC_HEADER_SIZE);
    
    return result;
}


/*===========================================================================
 * Profile Bulk: Basic + Extended
 * Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * Overhead: 8 bytes. Max payload: 64KB. Supports package namespaces.
 *===========================================================================*/

#define PROFILE_BULK_START_BYTE1        0x90
#define PROFILE_BULK_START_BYTE2        0x74
#define PROFILE_BULK_HEADER_SIZE        6  /* start1 + start2 + len16 + pkg_id + msg_id */
#define PROFILE_BULK_FOOTER_SIZE        2  /* CRC */
#define PROFILE_BULK_OVERHEAD           (PROFILE_BULK_HEADER_SIZE + PROFILE_BULK_FOOTER_SIZE)

/**
 * Encode a message using Profile Bulk (Basic + Extended) format.
 * 
 * @param buffer Output buffer to write the encoded frame
 * @param buffer_size Size of the output buffer
 * @param pkg_id Package ID (0-255)
 * @param msg_id Message ID
 * @param payload Pointer to payload data
 * @param payload_size Size of payload in bytes (max 65535)
 * @return Number of bytes written, or 0 on failure
 */
static inline size_t encode_profile_bulk(uint8_t* buffer, size_t buffer_size,
                                         uint8_t pkg_id, uint8_t msg_id,
                                         const uint8_t* payload, size_t payload_size) {
    size_t total_size = PROFILE_BULK_OVERHEAD + payload_size;
    
    if (buffer_size < total_size || payload_size > 65535) {
        return 0;
    }
    
    buffer[0] = PROFILE_BULK_START_BYTE1;
    buffer[1] = PROFILE_BULK_START_BYTE2;
    buffer[2] = (uint8_t)(payload_size & 0xFF);
    buffer[3] = (uint8_t)((payload_size >> 8) & 0xFF);
    buffer[4] = pkg_id;
    buffer[5] = msg_id;
    
    if (payload_size > 0 && payload != NULL) {
        memcpy(buffer + PROFILE_BULK_HEADER_SIZE, payload, payload_size);
    }
    
    /* CRC covers: [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] */
    frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, payload_size + 4);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

/**
 * Parse/validate a complete Profile Bulk frame from a buffer.
 * 
 * @param buffer Input buffer containing the frame
 * @param length Length of data in buffer
 * @return frame_msg_info_t with valid=true if frame is valid
 */
static inline frame_msg_info_t parse_profile_bulk_buffer(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < PROFILE_BULK_OVERHEAD) {
        return result;
    }
    
    if (buffer[0] != PROFILE_BULK_START_BYTE1 || buffer[1] != PROFILE_BULK_START_BYTE2) {
        return result;
    }
    
    size_t msg_len = buffer[2] | ((size_t)buffer[3] << 8);
    size_t total_size = PROFILE_BULK_OVERHEAD + msg_len;
    
    if (length < total_size) {
        return result;
    }
    
    /* Verify CRC: covers [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] */
    frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, msg_len + 4);
    if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
        return result;
    }
    
    result.valid = true;
    result.msg_id = buffer[5];
    result.msg_len = msg_len;
    result.msg_data = (uint8_t*)(buffer + PROFILE_BULK_HEADER_SIZE);
    
    return result;
}


/*===========================================================================
 * Profile Network: Basic + ExtendedMultiSystemStream
 * Frame: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
 * Overhead: 11 bytes. Max payload: 64KB. Full routing and sequencing support.
 *===========================================================================*/

#define PROFILE_NETWORK_START_BYTE1     0x90
#define PROFILE_NETWORK_START_BYTE2     0x78
#define PROFILE_NETWORK_HEADER_SIZE     9  /* start1 + start2 + seq + sys + comp + len16 + pkg_id + msg_id */
#define PROFILE_NETWORK_FOOTER_SIZE     2  /* CRC */
#define PROFILE_NETWORK_OVERHEAD        (PROFILE_NETWORK_HEADER_SIZE + PROFILE_NETWORK_FOOTER_SIZE)

/**
 * Encode a message using Profile Network (Basic + ExtendedMultiSystemStream) format.
 * 
 * @param buffer Output buffer to write the encoded frame
 * @param buffer_size Size of the output buffer
 * @param sequence Sequence number (0-255)
 * @param system_id System ID (0-255)
 * @param component_id Component ID (0-255)
 * @param pkg_id Package ID (0-255)
 * @param msg_id Message ID
 * @param payload Pointer to payload data
 * @param payload_size Size of payload in bytes (max 65535)
 * @return Number of bytes written, or 0 on failure
 */
static inline size_t encode_profile_network(uint8_t* buffer, size_t buffer_size,
                                            uint8_t sequence, uint8_t system_id,
                                            uint8_t component_id, uint8_t pkg_id,
                                            uint8_t msg_id,
                                            const uint8_t* payload, size_t payload_size) {
    size_t total_size = PROFILE_NETWORK_OVERHEAD + payload_size;
    
    if (buffer_size < total_size || payload_size > 65535) {
        return 0;
    }
    
    buffer[0] = PROFILE_NETWORK_START_BYTE1;
    buffer[1] = PROFILE_NETWORK_START_BYTE2;
    buffer[2] = sequence;
    buffer[3] = system_id;
    buffer[4] = component_id;
    buffer[5] = (uint8_t)(payload_size & 0xFF);
    buffer[6] = (uint8_t)((payload_size >> 8) & 0xFF);
    buffer[7] = pkg_id;
    buffer[8] = msg_id;
    
    if (payload_size > 0 && payload != NULL) {
        memcpy(buffer + PROFILE_NETWORK_HEADER_SIZE, payload, payload_size);
    }
    
    /* CRC covers: [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] */
    frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, payload_size + 7);
    buffer[total_size - 2] = ck.byte1;
    buffer[total_size - 1] = ck.byte2;
    
    return total_size;
}

/**
 * Parse/validate a complete Profile Network frame from a buffer.
 * 
 * @param buffer Input buffer containing the frame
 * @param length Length of data in buffer
 * @return frame_msg_info_t with valid=true if frame is valid
 */
static inline frame_msg_info_t parse_profile_network_buffer(const uint8_t* buffer, size_t length) {
    frame_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < PROFILE_NETWORK_OVERHEAD) {
        return result;
    }
    
    if (buffer[0] != PROFILE_NETWORK_START_BYTE1 || buffer[1] != PROFILE_NETWORK_START_BYTE2) {
        return result;
    }
    
    size_t msg_len = buffer[5] | ((size_t)buffer[6] << 8);
    size_t total_size = PROFILE_NETWORK_OVERHEAD + msg_len;
    
    if (length < total_size) {
        return result;
    }
    
    /* Verify CRC: covers [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] */
    frame_checksum_t ck = frame_fletcher_checksum(buffer + 2, msg_len + 7);
    if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
        return result;
    }
    
    result.valid = true;
    result.msg_id = buffer[8];
    result.msg_len = msg_len;
    result.msg_data = (uint8_t*)(buffer + PROFILE_NETWORK_HEADER_SIZE);
    
    return result;
}
