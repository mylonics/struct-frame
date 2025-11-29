/*
 * BasicFrameWithLen - Frame format with embedded length and CRC
 * 
 * Format: [START1=0x90] [START2=0x92] [MSG_ID] [LEN] [MSG...] [CRC1] [CRC2]
 * 
 * This frame format includes the message length in the packet header,
 * so no msg_id to length lookup is required.
 * 
 * Use Case: When message lengths may vary or are not known at compile time.
 */

#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* Frame constants */
#define BASIC_FRAME_WITH_LEN_START_BYTE1      0x90
#define BASIC_FRAME_WITH_LEN_START_BYTE2      0x92
#define BASIC_FRAME_WITH_LEN_HEADER_SIZE      4  /* start1 + start2 + msg_id + len */
#define BASIC_FRAME_WITH_LEN_FOOTER_SIZE      2  /* crc1 + crc2 */
#define BASIC_FRAME_WITH_LEN_OVERHEAD         (BASIC_FRAME_WITH_LEN_HEADER_SIZE + BASIC_FRAME_WITH_LEN_FOOTER_SIZE)
#define BASIC_FRAME_WITH_LEN_MAX_MSG_SIZE     255  /* Limited by 1-byte length field */

/* Checksum result */
typedef struct basic_frame_with_len_checksum {
    uint8_t byte1;
    uint8_t byte2;
} basic_frame_with_len_checksum_t;

/* Parse result */
typedef struct basic_frame_with_len_msg_info {
    bool valid;
    uint8_t msg_id;
    uint8_t msg_len;
    uint8_t* msg_data;
} basic_frame_with_len_msg_info_t;

/* Parser state enumeration */
typedef enum basic_frame_with_len_parser_state {
    BASIC_FRAME_WITH_LEN_LOOKING_FOR_START1 = 0,
    BASIC_FRAME_WITH_LEN_LOOKING_FOR_START2 = 1,
    BASIC_FRAME_WITH_LEN_GETTING_MSG_ID = 2,
    BASIC_FRAME_WITH_LEN_GETTING_LENGTH = 3,
    BASIC_FRAME_WITH_LEN_GETTING_PAYLOAD = 4
} basic_frame_with_len_parser_state_t;

/* Parser state structure */
typedef struct basic_frame_with_len_parser {
    basic_frame_with_len_parser_state_t state;
    uint8_t* buffer;
    size_t buffer_max_size;
    size_t buffer_index;
    size_t packet_size;
    uint8_t msg_id;
    uint8_t msg_len;
} basic_frame_with_len_parser_t;

/* Encode buffer structure */
typedef struct basic_frame_with_len_encode_buffer {
    uint8_t* data;
    size_t max_size;
    size_t size;
    bool in_progress;
    uint8_t reserved_msg_size;  /* Stored for finish() */
} basic_frame_with_len_encode_buffer_t;

/*===========================================================================
 * Checksum Calculation
 *===========================================================================*/

/**
 * Calculate Fletcher-16 checksum over the given data
 */
static inline basic_frame_with_len_checksum_t basic_frame_with_len_checksum(const uint8_t* data, size_t length) {
    basic_frame_with_len_checksum_t ck = {0, 0};
    for (size_t i = 0; i < length; i++) {
        ck.byte1 = (uint8_t)(ck.byte1 + data[i]);
        ck.byte2 = (uint8_t)(ck.byte2 + ck.byte1);
    }
    return ck;
}

/*===========================================================================
 * Encoding Functions
 *===========================================================================*/

/**
 * Initialize an encode buffer
 */
static inline void basic_frame_with_len_encode_init(basic_frame_with_len_encode_buffer_t* buf, 
                                                     uint8_t* data, size_t max_size) {
    buf->data = data;
    buf->max_size = max_size;
    buf->size = 0;
    buf->in_progress = false;
    buf->reserved_msg_size = 0;
}

/**
 * Reset the encode buffer
 */
static inline void basic_frame_with_len_encode_reset(basic_frame_with_len_encode_buffer_t* buf) {
    buf->size = 0;
    buf->in_progress = false;
    buf->reserved_msg_size = 0;
}

/**
 * Encode a message into the buffer
 * Returns the number of bytes written, or 0 on failure
 */
static inline size_t basic_frame_with_len_encode(uint8_t* buffer, size_t buffer_size, 
                                                  uint8_t msg_id, const uint8_t* msg, uint8_t msg_size) {
    size_t total_size = BASIC_FRAME_WITH_LEN_OVERHEAD + msg_size;
    if (buffer_size < total_size) {
        return 0;
    }
    
    /* Write header */
    buffer[0] = BASIC_FRAME_WITH_LEN_START_BYTE1;
    buffer[1] = BASIC_FRAME_WITH_LEN_START_BYTE2;
    buffer[2] = msg_id;
    buffer[3] = msg_size;
    
    /* Write message data */
    if (msg_size > 0 && msg != NULL) {
        memcpy(buffer + BASIC_FRAME_WITH_LEN_HEADER_SIZE, msg, msg_size);
    }
    
    /* Calculate checksum over msg_id + len + msg data */
    basic_frame_with_len_checksum_t ck = basic_frame_with_len_checksum(buffer + 2, msg_size + 2);
    buffer[BASIC_FRAME_WITH_LEN_HEADER_SIZE + msg_size] = ck.byte1;
    buffer[BASIC_FRAME_WITH_LEN_HEADER_SIZE + msg_size + 1] = ck.byte2;
    
    return total_size;
}

/**
 * Encode a message using the encode buffer structure
 */
static inline bool basic_frame_with_len_encode_msg(basic_frame_with_len_encode_buffer_t* buf, 
                                                    uint8_t msg_id, const void* msg, uint8_t msg_size) {
    if (buf->in_progress) {
        return false;
    }
    
    size_t written = basic_frame_with_len_encode(buf->data + buf->size, 
                                                  buf->max_size - buf->size,
                                                  msg_id, (const uint8_t*)msg, msg_size);
    if (written == 0) {
        return false;
    }
    
    buf->size += written;
    return true;
}

/**
 * Reserve space in buffer for zero-copy encoding
 * Returns pointer to message data area, or NULL on failure
 */
static inline uint8_t* basic_frame_with_len_encode_reserve(basic_frame_with_len_encode_buffer_t* buf, 
                                                            uint8_t msg_id, uint8_t msg_size) {
    if (buf->in_progress) {
        return NULL;
    }
    
    size_t total_size = BASIC_FRAME_WITH_LEN_OVERHEAD + msg_size;
    if (buf->size + total_size > buf->max_size) {
        return NULL;
    }
    
    uint8_t* packet_start = buf->data + buf->size;
    
    /* Write header */
    packet_start[0] = BASIC_FRAME_WITH_LEN_START_BYTE1;
    packet_start[1] = BASIC_FRAME_WITH_LEN_START_BYTE2;
    packet_start[2] = msg_id;
    packet_start[3] = msg_size;
    
    buf->in_progress = true;
    buf->reserved_msg_size = msg_size;
    return packet_start + BASIC_FRAME_WITH_LEN_HEADER_SIZE;
}

/**
 * Finish a reserved encoding by adding checksum
 */
static inline bool basic_frame_with_len_encode_finish(basic_frame_with_len_encode_buffer_t* buf) {
    if (!buf->in_progress) {
        return false;
    }
    
    uint8_t* packet_start = buf->data + buf->size;
    uint8_t msg_size = buf->reserved_msg_size;
    
    /* Calculate checksum over msg_id + len + msg data */
    basic_frame_with_len_checksum_t ck = basic_frame_with_len_checksum(packet_start + 2, msg_size + 2);
    packet_start[BASIC_FRAME_WITH_LEN_HEADER_SIZE + msg_size] = ck.byte1;
    packet_start[BASIC_FRAME_WITH_LEN_HEADER_SIZE + msg_size + 1] = ck.byte2;
    
    buf->size += BASIC_FRAME_WITH_LEN_OVERHEAD + msg_size;
    buf->in_progress = false;
    return true;
}

/*===========================================================================
 * Decoding/Parsing Functions
 *===========================================================================*/

/**
 * Initialize a parser
 * 
 * @param parser Parser structure to initialize
 * @param buffer Buffer for storing incoming packet data
 * @param buffer_size Maximum size of the buffer
 */
static inline void basic_frame_with_len_parser_init(basic_frame_with_len_parser_t* parser, 
                                                     uint8_t* buffer, size_t buffer_size) {
    parser->state = BASIC_FRAME_WITH_LEN_LOOKING_FOR_START1;
    parser->buffer = buffer;
    parser->buffer_max_size = buffer_size;
    parser->buffer_index = 0;
    parser->packet_size = 0;
    parser->msg_id = 0;
    parser->msg_len = 0;
}

/**
 * Reset parser state
 */
static inline void basic_frame_with_len_parser_reset(basic_frame_with_len_parser_t* parser) {
    parser->state = BASIC_FRAME_WITH_LEN_LOOKING_FOR_START1;
    parser->buffer_index = 0;
    parser->packet_size = 0;
    parser->msg_id = 0;
    parser->msg_len = 0;
}

/**
 * Parse a single byte
 * Returns a msg_info with valid=true when a complete valid message is received
 */
static inline basic_frame_with_len_msg_info_t basic_frame_with_len_parse_byte(
    basic_frame_with_len_parser_t* parser, uint8_t byte) {
    
    basic_frame_with_len_msg_info_t result = {false, 0, 0, NULL};
    
    switch (parser->state) {
        case BASIC_FRAME_WITH_LEN_LOOKING_FOR_START1:
            if (byte == BASIC_FRAME_WITH_LEN_START_BYTE1) {
                parser->buffer[0] = byte;
                parser->buffer_index = 1;
                parser->state = BASIC_FRAME_WITH_LEN_LOOKING_FOR_START2;
            }
            break;
            
        case BASIC_FRAME_WITH_LEN_LOOKING_FOR_START2:
            if (byte == BASIC_FRAME_WITH_LEN_START_BYTE2) {
                parser->buffer[1] = byte;
                parser->buffer_index = 2;
                parser->state = BASIC_FRAME_WITH_LEN_GETTING_MSG_ID;
            } else if (byte == BASIC_FRAME_WITH_LEN_START_BYTE1) {
                /* Could be new packet starting */
                parser->buffer[0] = byte;
                parser->buffer_index = 1;
            } else {
                parser->state = BASIC_FRAME_WITH_LEN_LOOKING_FOR_START1;
            }
            break;
            
        case BASIC_FRAME_WITH_LEN_GETTING_MSG_ID:
            parser->buffer[2] = byte;
            parser->buffer_index = 3;
            parser->msg_id = byte;
            parser->state = BASIC_FRAME_WITH_LEN_GETTING_LENGTH;
            break;
            
        case BASIC_FRAME_WITH_LEN_GETTING_LENGTH:
            parser->buffer[3] = byte;
            parser->buffer_index = 4;
            parser->msg_len = byte;
            parser->packet_size = BASIC_FRAME_WITH_LEN_OVERHEAD + byte;
            
            if (parser->packet_size <= parser->buffer_max_size) {
                parser->state = BASIC_FRAME_WITH_LEN_GETTING_PAYLOAD;
            } else {
                /* Packet too large for buffer */
                parser->state = BASIC_FRAME_WITH_LEN_LOOKING_FOR_START1;
            }
            break;
            
        case BASIC_FRAME_WITH_LEN_GETTING_PAYLOAD:
            if (parser->buffer_index < parser->buffer_max_size) {
                parser->buffer[parser->buffer_index++] = byte;
            }
            
            if (parser->buffer_index >= parser->packet_size) {
                /* Packet complete, validate checksum */
                basic_frame_with_len_checksum_t ck = basic_frame_with_len_checksum(
                    parser->buffer + 2, parser->msg_len + 2);
                
                if (ck.byte1 == parser->buffer[parser->packet_size - 2] &&
                    ck.byte2 == parser->buffer[parser->packet_size - 1]) {
                    result.valid = true;
                    result.msg_id = parser->msg_id;
                    result.msg_len = parser->msg_len;
                    result.msg_data = parser->buffer + BASIC_FRAME_WITH_LEN_HEADER_SIZE;
                }
                
                parser->state = BASIC_FRAME_WITH_LEN_LOOKING_FOR_START1;
            }
            break;
    }
    
    return result;
}

/**
 * Parse a buffer of bytes
 * Continues parsing from r_loc and returns when a message is found or buffer is exhausted
 * Updates r_loc to the position after the found message
 * Returns msg_info with valid=true when a complete valid message is found
 */
static inline basic_frame_with_len_msg_info_t basic_frame_with_len_parse_buffer(
    basic_frame_with_len_parser_t* parser,
    const uint8_t* data, size_t data_size,
    size_t* r_loc) {
    
    basic_frame_with_len_msg_info_t result = {false, 0, 0, NULL};
    
    while (*r_loc < data_size) {
        result = basic_frame_with_len_parse_byte(parser, data[*r_loc]);
        (*r_loc)++;
        if (result.valid) {
            return result;
        }
    }
    
    return result;
}

/**
 * Validate a complete packet in a buffer
 * Useful for validating data received all at once
 */
static inline basic_frame_with_len_msg_info_t basic_frame_with_len_validate_packet(
    const uint8_t* buffer, size_t length) {
    
    basic_frame_with_len_msg_info_t result = {false, 0, 0, NULL};
    
    if (length < BASIC_FRAME_WITH_LEN_OVERHEAD) {
        return result;
    }
    
    /* Check start bytes */
    if (buffer[0] != BASIC_FRAME_WITH_LEN_START_BYTE1 || 
        buffer[1] != BASIC_FRAME_WITH_LEN_START_BYTE2) {
        return result;
    }
    
    uint8_t msg_len = buffer[3];
    size_t expected_length = BASIC_FRAME_WITH_LEN_OVERHEAD + msg_len;
    
    if (length != expected_length) {
        return result;
    }
    
    /* Validate checksum over msg_id + len + msg data */
    basic_frame_with_len_checksum_t ck = basic_frame_with_len_checksum(buffer + 2, msg_len + 2);
    if (ck.byte1 == buffer[length - 2] && ck.byte2 == buffer[length - 1]) {
        result.valid = true;
        result.msg_id = buffer[2];
        result.msg_len = msg_len;
        result.msg_data = (uint8_t*)(buffer + BASIC_FRAME_WITH_LEN_HEADER_SIZE);
    }
    
    return result;
}

/*===========================================================================
 * Helper Macros for Message Types
 *===========================================================================*/

/**
 * Generate helper functions for a specific message type
 * 
 * Usage: BASIC_FRAME_WITH_LEN_MESSAGE_HELPERS(my_message, MyMessage, 10, 1)
 * 
 * This creates:
 *   - my_message_encode(buf, msg) - Encode message to buffer
 *   - my_message_reserve(buf, &msg_ptr) - Reserve space for zero-copy
 *   - my_message_finish(buf) - Finish reserved encoding
 *   - my_message_get(info) - Get message copy from parse result
 *   - my_message_get_ref(info) - Get message pointer from parse result
 */
#define BASIC_FRAME_WITH_LEN_MESSAGE_HELPERS(funcname, typename, msg_size, msg_id)                              \
    static inline bool funcname##_encode(basic_frame_with_len_encode_buffer_t* buf, const typename* msg) {      \
        return basic_frame_with_len_encode_msg(buf, (msg_id), msg, (msg_size));                                 \
    }                                                                                                           \
    static inline bool funcname##_reserve(basic_frame_with_len_encode_buffer_t* buf, typename** msg) {          \
        uint8_t* ptr = basic_frame_with_len_encode_reserve(buf, (msg_id), (msg_size));                          \
        if (ptr) {                                                                                              \
            *msg = (typename*)ptr;                                                                              \
            return true;                                                                                        \
        }                                                                                                       \
        return false;                                                                                           \
    }                                                                                                           \
    static inline bool funcname##_finish(basic_frame_with_len_encode_buffer_t* buf) {                           \
        return basic_frame_with_len_encode_finish(buf);                                                         \
    }                                                                                                           \
    static inline typename funcname##_get(basic_frame_with_len_msg_info_t info) {                               \
        return *(typename*)(info.msg_data);                                                                     \
    }                                                                                                           \
    static inline typename* funcname##_get_ref(basic_frame_with_len_msg_info_t info) {                          \
        return (typename*)(info.msg_data);                                                                      \
    }
