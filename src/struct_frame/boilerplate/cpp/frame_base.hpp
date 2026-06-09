/* Struct-frame boilerplate: frame parser base utilities */

#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>

namespace structframe {

// Message info structure for unified callback
struct MessageInfo {
  size_t size;       // Full payload size
  uint8_t magic1;
  uint8_t magic2;
  bool valid;        // True if message info is valid
  size_t base_size;  // Non-extension portion size (== size when no extensions)
  
  MessageInfo() : size(0), magic1(0), magic2(0), valid(false), base_size(0) {}
  MessageInfo(size_t s, uint8_t m1, uint8_t m2) : size(s), magic1(m1), magic2(m2), valid(true), base_size(s) {}
  MessageInfo(size_t s, uint8_t m1, uint8_t m2, size_t bs) : size(s), magic1(m1), magic2(m2), valid(true), base_size(bs) {}
  
  explicit operator bool() const { return valid; }
};

// Checksum result
struct FrameChecksum {
  uint8_t byte1;
  uint8_t byte2;
};

// Fletcher-16 checksum calculation
inline FrameChecksum fletcher_checksum(const uint8_t* data, size_t length, uint8_t magic1 = 0, uint8_t magic2 = 0) {
  FrameChecksum ck{0, 0};
  for (size_t i = 0; i < length; i++) {
    ck.byte1 = static_cast<uint8_t>(ck.byte1 + data[i]);
    ck.byte2 = static_cast<uint8_t>(ck.byte2 + ck.byte1);
  }
  ck.byte1 = static_cast<uint8_t>(ck.byte1 + magic1);
  ck.byte2 = static_cast<uint8_t>(ck.byte2 + ck.byte1);
  ck.byte1 = static_cast<uint8_t>(ck.byte1 + magic2);
  ck.byte2 = static_cast<uint8_t>(ck.byte2 + ck.byte1);
  return ck;
}

// Extension-aware Fletcher-16 checksum.
// Computes: Fletcher(data[0..base_len]) → mix magic1/magic2 → Fletcher(data[base_len..total_len]).
// When base_len == total_len the result is identical to fletcher_checksum.
inline FrameChecksum fletcher_checksum_ext(const uint8_t* data, size_t base_len, size_t total_len,
                                           uint8_t magic1 = 0, uint8_t magic2 = 0) {
  FrameChecksum ck{0, 0};
  for (size_t i = 0; i < base_len; i++) {
    ck.byte1 = static_cast<uint8_t>(ck.byte1 + data[i]);
    ck.byte2 = static_cast<uint8_t>(ck.byte2 + ck.byte1);
  }
  ck.byte1 = static_cast<uint8_t>(ck.byte1 + magic1);
  ck.byte2 = static_cast<uint8_t>(ck.byte2 + ck.byte1);
  ck.byte1 = static_cast<uint8_t>(ck.byte1 + magic2);
  ck.byte2 = static_cast<uint8_t>(ck.byte2 + ck.byte1);
  for (size_t i = base_len; i < total_len; i++) {
    ck.byte1 = static_cast<uint8_t>(ck.byte1 + data[i]);
    ck.byte2 = static_cast<uint8_t>(ck.byte2 + ck.byte1);
  }
  return ck;
}

// Parse result
enum class FrameMsgStatus : uint8_t {
  None = 0,            ///< Default / unset.
  WaitingForStart = 1, ///< Parser is idle, searching for a start byte.
  Collecting = 2,      ///< A frame is in progress; accumulating bytes.
  CrcFailure = 3,      ///< Complete frame received but CRC did not match.
  SyncRecovery = 4,    ///< Bytes discarded to re-find a valid frame start.
};

struct FrameMsgInfo {
  bool valid;
  uint16_t msg_id;
  size_t msg_len;     // Payload length (message data only)
  size_t frame_size;  // Total frame size (header + payload + footer)
  uint8_t* msg_data;
  const uint8_t* frame_data;  // Full frame bytes, including framing overhead
  FrameMsgStatus status;

  FrameMsgInfo()
      : valid(false), msg_id(0), msg_len(0), frame_size(0), msg_data(nullptr), frame_data(nullptr),
        status(FrameMsgStatus::None) {}
  FrameMsgInfo(bool v, uint16_t id, size_t len, size_t fsize, uint8_t* data,
               const uint8_t* frame = nullptr, FrameMsgStatus st = FrameMsgStatus::None)
      : valid(v), msg_id(id), msg_len(len), frame_size(fsize), msg_data(data), frame_data(frame), status(st) {}

  // Legacy constructor for backwards compatibility
  FrameMsgInfo(bool v, uint16_t id, size_t len, uint8_t* data)
      : valid(v), msg_id(id), msg_len(len), frame_size(0), msg_data(data), frame_data(nullptr),
        status(FrameMsgStatus::None) {}

  // Allow use in boolean context (e.g., while (auto result = reader.next()) { ... })
  explicit operator bool() const { return valid; }
};

/**
 * Diagnostic counters for the AccumulatingReader (stream mode).
 *
 * All counters accumulate over the reader's lifetime. Call
 * reset_diagnostics() to clear them.
 *
 * cnt_crc_failures:   Complete frames received with a bad CRC.
 *                     Indicates noise or corruption on the line.
 * cnt_sync_recoveries: Times the parser discarded bytes and re-searched for
 *                     a frame start. Indicates lost bytes or buffer overflows.
 * cnt_len_errors:     Frames where the header length field does not match the
 *                     expected message-struct size from get_message_info().
 *                     Vital for detecting mismatched definitions on profiles
 *                     that carry an explicit length.
 * cnt_seq_gaps:       Sequence-number gaps. Only incremented on profiles that
 *                     carry a sequence field (e.g. ProfileNetwork). Indicates
 *                     dropped packets.
 */
struct ParserDiagnostics {
  uint32_t cnt_crc_failures;
  uint32_t cnt_sync_recoveries;
  uint32_t cnt_len_errors;
  uint32_t cnt_seq_gaps;

  ParserDiagnostics()
      : cnt_crc_failures(0), cnt_sync_recoveries(0), cnt_len_errors(0), cnt_seq_gaps(0) {}
};

/**
 * Base class for message types with associated metadata.
 * Template parameters embed msg_id, max_size, and magic bytes as compile-time constants.
 *
 * Usage:
 *   struct MyMessage : MessageBase<MyMessage, MSG_ID, MAX_SIZE, MAGIC1, MAGIC2> {
 *       uint32_t field1;
 *       float field2;
 *   };
 *
 *   // Encode directly without passing msg_id/size/magic:
 *   MyMessage msg{.field1 = 42, .field2 = 3.14f};
 *   encode_profile_standard(buffer, sizeof(buffer), msg);
 */
template <typename Derived, uint16_t MsgId, size_t MaxSize, uint8_t Magic1, uint8_t Magic2, size_t BaseSize = MaxSize>
struct MessageBase {
  static constexpr uint16_t MSG_ID = MsgId;
  static constexpr size_t MAX_SIZE = MaxSize;
  static constexpr uint8_t MAGIC1 = Magic1;
  static constexpr uint8_t MAGIC2 = Magic2;
  static constexpr size_t BASE_SIZE = BaseSize;  // Non-extension portion size

  // Get pointer to the message data (cast to derived type's data)
  const uint8_t* data() const { return reinterpret_cast<const uint8_t*>(static_cast<const Derived*>(this)); }

  uint8_t* data() { return reinterpret_cast<uint8_t*>(static_cast<Derived*>(this)); }

  // Get the message size
  static constexpr size_t size() { return MaxSize; }

  // Get the message ID
  static constexpr uint16_t msg_id() { return MsgId; }
};

// =============================================================================
// Shared Payload Parsing Functions
// =============================================================================
// These functions handle payload validation/encoding independent of framing.
// Frame formats (Tiny/Basic) use these for the common parsing logic.

/**
 * Validate a payload with CRC (shared by Default, Extended, etc. payload types).
 */
inline FrameMsgInfo validate_payload_with_crc(const uint8_t* buffer, size_t length, size_t header_size,
                                              size_t length_bytes, size_t crc_start_offset, uint8_t magic1 = 0,
                                              uint8_t magic2 = 0) {
  constexpr size_t footer_size = 2;  // CRC is always 2 bytes
  const size_t overhead = header_size + footer_size;

  if (length < overhead) {
    return FrameMsgInfo();
  }

  size_t msg_length = length - overhead;

  // Calculate expected CRC range: from crc_start_offset to before the CRC bytes
  size_t crc_data_len = msg_length + 1 + length_bytes;  // msg_id (1) + length_bytes + payload
  FrameChecksum ck = fletcher_checksum(buffer + crc_start_offset, crc_data_len, magic1, magic2);

  if (ck.byte1 == buffer[length - 2] && ck.byte2 == buffer[length - 1]) {
    return FrameMsgInfo(true, buffer[header_size - 1], msg_length, length,
                        const_cast<uint8_t*>(buffer + header_size), buffer);
  }

  return FrameMsgInfo(false, buffer[header_size - 1], msg_length, length,
                      const_cast<uint8_t*>(buffer + header_size), buffer,
                      FrameMsgStatus::CrcFailure);
}

/**
 * Validate a minimal payload (no CRC, no length field).
 */
inline FrameMsgInfo validate_payload_minimal(const uint8_t* buffer, size_t length, size_t header_size) {
  if (length < header_size) {
    return FrameMsgInfo();
  }

  return FrameMsgInfo(true, buffer[header_size - 1], length - header_size, length,
                      const_cast<uint8_t*>(buffer + header_size), buffer);
}

/**
 * Encode payload with length and CRC into output buffer.
 * Returns number of bytes written (length + msg_id + payload + CRC)
 */
inline size_t encode_payload_with_crc(uint8_t* output, uint8_t msg_id, const uint8_t* msg, size_t msg_size,
                                      size_t length_bytes, const uint8_t* crc_start, uint8_t magic1 = 0,
                                      uint8_t magic2 = 0) {
  size_t idx = 0;

  // Add length field
  if (length_bytes == 1) {
    output[idx++] = static_cast<uint8_t>(msg_size & 0xFF);
  } else {
    output[idx++] = static_cast<uint8_t>(msg_size & 0xFF);
    output[idx++] = static_cast<uint8_t>((msg_size >> 8) & 0xFF);
  }

  // Add msg_id
  output[idx++] = msg_id;

  // Add payload
  if (msg_size > 0 && msg != nullptr) {
    std::memcpy(output + idx, msg, msg_size);
    idx += msg_size;
  }

  // Calculate and add CRC
  size_t crc_data_len = msg_size + 1 + length_bytes;
  FrameChecksum ck = fletcher_checksum(crc_start, crc_data_len, magic1, magic2);
  output[idx++] = ck.byte1;
  output[idx++] = ck.byte2;

  return idx;
}

/**
 * Encode minimal payload (no length, no CRC) into output buffer.
 * Returns number of bytes written (msg_id + payload)
 */
inline size_t encode_payload_minimal(uint8_t* output, uint8_t msg_id, const uint8_t* msg, size_t msg_size) {
  size_t idx = 0;

  // Add msg_id
  output[idx++] = msg_id;

  // Add payload
  if (msg_size > 0 && msg != nullptr) {
    std::memcpy(output + idx, msg, msg_size);
    idx += msg_size;
  }

  return idx;
}

}  // namespace structframe
