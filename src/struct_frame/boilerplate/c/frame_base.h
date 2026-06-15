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
 * Calculate Fletcher-16 checksum with extension-aware magic mixing.
 *
 * Wire-evolution policy: base bytes are mixed first, then the message's two
 * magic bytes, then the extension bytes. This means:
 *   - Magic bytes act as a "schema seed" that depends only on the immutable
 *     base portion (computed at code-gen time from non-extension fields).
 *   - Extension bytes are still covered by the CRC, so silent corruption of
 *     extension data is still detected.
 *   - Truncating trailing zero-extension bytes does not invalidate the
 *     checksum on length-bearing profiles (parser zero-fills the missing
 *     bytes before re-computing).
 *
 * When base_len == total_len (no extensions, or extensions disabled because
 * the profile lacks a length field), the result is byte-identical to
 * frame_fletcher_checksum_with_magic(data, total_len, magic1, magic2).
 */
static inline frame_checksum_t frame_fletcher_checksum_with_magic_ext(const uint8_t* data, size_t base_len,
                                                                      size_t total_len, uint8_t magic1,
                                                                      uint8_t magic2) {
  frame_checksum_t ck = {0, 0};
  for (size_t i = 0; i < base_len; i++) {
    ck.byte1 = (uint8_t)(ck.byte1 + data[i]);
    ck.byte2 = (uint8_t)(ck.byte2 + ck.byte1);
  }
  ck.byte1 = (uint8_t)(ck.byte1 + magic1);
  ck.byte2 = (uint8_t)(ck.byte2 + ck.byte1);
  ck.byte1 = (uint8_t)(ck.byte1 + magic2);
  ck.byte2 = (uint8_t)(ck.byte2 + ck.byte1);
  for (size_t i = base_len; i < total_len; i++) {
    ck.byte1 = (uint8_t)(ck.byte1 + data[i]);
    ck.byte2 = (uint8_t)(ck.byte2 + ck.byte1);
  }
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
  size_t size;       /* total payload size (base + extensions) */
  size_t base_size;  /* size of the non-extension portion; equal to size when
                        the message has no extensions or is used over a
                        profile without a length field */
  size_t min_size;   /* minimum valid payload size; equal to base_size for
                        fixed messages, MIN_SIZE for variable messages */
  uint8_t magic1;
  uint8_t magic2;
} message_info_t;

/* Parse result */
typedef enum frame_msg_status {
  FRAME_MSG_STATUS_NONE = 0,             /**< Default / unset. */
  FRAME_MSG_STATUS_WAITING_FOR_START = 1,/**< Searching for a start byte. */
  FRAME_MSG_STATUS_COLLECTING = 2,       /**< Accumulating bytes; frame in progress. */
  FRAME_MSG_STATUS_CRC_FAILURE = 3,      /**< Complete frame but CRC did not match. */
  FRAME_MSG_STATUS_SYNC_RECOVERY = 4,    /**< Bytes discarded to re-find frame start. */
} frame_msg_status_t;

struct frame_parser_diagnostics;

typedef struct frame_msg_info {
  bool valid;
  uint16_t msg_id; /* 16-bit to support pkg_id (high byte) + msg_id (low byte) */
  size_t msg_len;
  uint8_t* msg_data;
  frame_msg_status_t status;
  size_t frame_size; /* total bytes consumed by this frame (header + payload + footer);
                        set even on CRC failure so callers can skip past it */
  const struct frame_parser_diagnostics* diagnostics;
} frame_msg_info_t;

/**
 * Diagnostic counters for the accumulating_reader_t (stream mode).
 *
 * All counters accumulate over the reader's lifetime.  Call
 * accumulating_reader_reset_diagnostics() to clear them.
 *
 * cnt_crc_failures:   Complete frames received with a bad CRC.
 *                     Indicates noise or corruption on the line.
 * cnt_sync_recoveries: Times the parser discarded bytes and re-searched for
 *                     a frame start.  Indicates lost bytes or buffer overflows.
 * cnt_failed_bytes:   Total bytes discarded when failures forced a reset to
 *                     searching for frame start.
 * cnt_len_errors:     Frames where the header length field does not match the
 *                     expected message-struct size from get_message_info.
 *                     Vital for detecting mismatched definitions on profiles
 *                     with an explicit length field.
 * cnt_seq_gaps:       Sequence-number gaps.  Only incremented on profiles that
 *                     carry a sequence field (e.g. network_accumulating_reader).
 *                     Indicates dropped packets.
 */
typedef struct frame_parser_diagnostics {
  uint32_t cnt_crc_failures;
  uint32_t cnt_sync_recoveries;
  uint32_t cnt_failed_bytes;
  uint32_t cnt_len_errors;
  uint32_t cnt_seq_gaps;
} frame_parser_diagnostics_t;

