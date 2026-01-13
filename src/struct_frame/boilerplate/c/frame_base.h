/* Struct-frame boilerplate: frame parser base utilities */

#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/*===========================================================================
 * Checksum Calculation
 *===========================================================================*/

typedef struct frame_checksum {
  uint8_t byte1;
  uint8_t byte2;
} frame_checksum_t;

/**
 * Calculate Fletcher-16 checksum with magic numbers added at the end
 */
static inline frame_checksum_t frame_fletcher_checksum_with_magic(const uint8_t* data, size_t length, uint8_t magic1,
                                                                  uint8_t magic2) {
  frame_checksum_t ck = {0, 0};
  for (size_t i = 0; i < length; i++) {
    ck.byte1 = (uint8_t)(ck.byte1 + data[i]);
    ck.byte2 = (uint8_t)(ck.byte2 + ck.byte1);
  }
  ck.byte1 = (uint8_t)(ck.byte1 + magic1);
  ck.byte2 = (uint8_t)(ck.byte2 + ck.byte1);
  ck.byte1 = (uint8_t)(ck.byte1 + magic2);
  ck.byte2 = (uint8_t)(ck.byte2 + ck.byte1);
  return ck;
}

/**
 * Calculate Fletcher-16 checksum over the given data
 */
static inline frame_checksum_t frame_fletcher_checksum(const uint8_t* data, size_t length) {
  return frame_fletcher_checksum_with_magic(data, length, 0, 0);
}

/* Message info - unified type for size and magic numbers lookup */
typedef struct message_info {
  size_t size;
  uint8_t magic1;
  uint8_t magic2;
} message_info_t;

/* Parse result */
typedef struct frame_msg_info {
  bool valid;
  uint16_t msg_id; /* 16-bit to support pkg_id (high byte) + msg_id (low byte) */
  size_t msg_len;
  uint8_t* msg_data;
} frame_msg_info_t;

/*===========================================================================
 * Shared Payload Parsing Functions
 *===========================================================================
 * These functions handle payload validation/encoding independent of framing.
 * Frame formats (Tiny/Basic) use these for the common parsing logic.
 */

/**
 * Validate a payload with CRC (shared by Default, Extended, etc. payload types).
 *
 * @param buffer Complete packet buffer (including any start bytes)
 * @param length Total buffer length
 * @param header_size Size of header (start_bytes + length + msg_id + extra fields)
 * @param length_bytes Number of length bytes (1 or 2)
 * @param crc_start_offset Offset from start of buffer where CRC calculation begins
 * @return frame_msg_info_t with valid=true if checksum matches
 */
static inline frame_msg_info_t frame_validate_payload_with_crc(const uint8_t* buffer, size_t length, size_t header_size,
                                                               size_t length_bytes, size_t crc_start_offset) {
  frame_msg_info_t result = {false, 0, 0, NULL};
  const size_t footer_size = 2; /* CRC is always 2 bytes */
  const size_t overhead = header_size + footer_size;

  if (length < overhead) {
    return result;
  }

  size_t msg_length = length - overhead;

  /* Calculate expected CRC range: from crc_start_offset to before the CRC bytes */
  size_t crc_data_len = msg_length + 1 + length_bytes; /* msg_id (1) + length_bytes + payload */
  frame_checksum_t ck = frame_fletcher_checksum(buffer + crc_start_offset, crc_data_len);

  if (ck.byte1 == buffer[length - 2] && ck.byte2 == buffer[length - 1]) {
    result.valid = true;
    result.msg_id = buffer[header_size - 1]; /* msg_id is last byte of header */
    result.msg_len = msg_length;
    result.msg_data = (uint8_t*)(buffer + header_size);
  }

  return result;
}

/**
 * Validate a minimal payload (no CRC, no length field).
 *
 * @param buffer Complete packet buffer (including any start bytes)
 * @param length Total buffer length
 * @param header_size Size of header (start_bytes + msg_id)
 * @return frame_msg_info_t with packet data
 */
static inline frame_msg_info_t frame_validate_payload_minimal(const uint8_t* buffer, size_t length,
                                                              size_t header_size) {
  frame_msg_info_t result = {false, 0, 0, NULL};

  if (length < header_size) {
    return result;
  }

  result.valid = true;
  result.msg_id = buffer[header_size - 1]; /* msg_id is last byte of header */
  result.msg_len = length - header_size;
  result.msg_data = (uint8_t*)(buffer + header_size);

  return result;
}

/**
 * Encode payload with length and CRC into output buffer.
 *
 * @param output Output buffer to write to (after start bytes)
 * @param msg_id Message ID
 * @param msg Message payload data
 * @param msg_size Size of message payload
 * @param length_bytes Number of length bytes (1 or 2)
 * @param crc_start Pointer to start of CRC calculation (typically after start bytes)
 * @return Number of bytes written (length + msg_id + payload + CRC)
 */
static inline size_t frame_encode_payload_with_crc(uint8_t* output, uint8_t msg_id, const uint8_t* msg, size_t msg_size,
                                                   size_t length_bytes, const uint8_t* crc_start) {
  size_t idx = 0;

  /* Add length field */
  if (length_bytes == 1) {
    output[idx++] = (uint8_t)(msg_size & 0xFF);
  } else {
    output[idx++] = (uint8_t)(msg_size & 0xFF);
    output[idx++] = (uint8_t)((msg_size >> 8) & 0xFF);
  }

  /* Add msg_id */
  output[idx++] = msg_id;

  /* Add payload */
  if (msg_size > 0 && msg != NULL) {
    memcpy(output + idx, msg, msg_size);
    idx += msg_size;
  }

  /* Calculate and add CRC */
  size_t crc_data_len = msg_size + 1 + length_bytes;
  frame_checksum_t ck = frame_fletcher_checksum(crc_start, crc_data_len);
  output[idx++] = ck.byte1;
  output[idx++] = ck.byte2;

  return idx;
}

/**
 * Encode minimal payload (no length, no CRC) into output buffer.
 *
 * @param output Output buffer to write to (after start bytes)
 * @param msg_id Message ID
 * @param msg Message payload data
 * @param msg_size Size of message payload
 * @return Number of bytes written (msg_id + payload)
 */
static inline size_t frame_encode_payload_minimal(uint8_t* output, uint8_t msg_id, const uint8_t* msg,
                                                  size_t msg_size) {
  size_t idx = 0;

  /* Add msg_id */
  output[idx++] = msg_id;

  /* Add payload */
  if (msg_size > 0 && msg != NULL) {
    memcpy(output + idx, msg, msg_size);
    idx += msg_size;
  }

  return idx;
}
