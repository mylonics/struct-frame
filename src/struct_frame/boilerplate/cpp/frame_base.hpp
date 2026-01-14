/* Struct-frame boilerplate: frame parser base utilities */

#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>

namespace FrameParsers {

// Message info structure for unified callback
struct MessageInfo {
  size_t size;
  uint8_t magic1;
  uint8_t magic2;
  bool valid;  // True if message info is valid
  
  MessageInfo() : size(0), magic1(0), magic2(0), valid(false) {}
  MessageInfo(size_t s, uint8_t m1, uint8_t m2) : size(s), magic1(m1), magic2(m2), valid(true) {}
  
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

// Parse result
struct FrameMsgInfo {
  bool valid;
  uint16_t msg_id;
  size_t msg_len;     // Payload length (message data only)
  size_t frame_size;  // Total frame size (header + payload + footer)
  uint8_t* msg_data;

  FrameMsgInfo() : valid(false), msg_id(0), msg_len(0), frame_size(0), msg_data(nullptr) {}
  FrameMsgInfo(bool v, uint16_t id, size_t len, size_t fsize, uint8_t* data)
      : valid(v), msg_id(id), msg_len(len), frame_size(fsize), msg_data(data) {}

  // Legacy constructor for backwards compatibility
  FrameMsgInfo(bool v, uint16_t id, size_t len, uint8_t* data)
      : valid(v), msg_id(id), msg_len(len), frame_size(0), msg_data(data) {}

  // Allow use in boolean context (e.g., while (auto result = reader.next()) { ... })
  explicit operator bool() const { return valid; }
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
template <typename Derived, uint16_t MsgId, size_t MaxSize, uint8_t Magic1, uint8_t Magic2>
struct MessageBase {
  static constexpr uint16_t MSG_ID = MsgId;
  static constexpr size_t MAX_SIZE = MaxSize;
  static constexpr uint8_t MAGIC1 = Magic1;
  static constexpr uint8_t MAGIC2 = Magic2;

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
    return FrameMsgInfo(true, buffer[header_size - 1], msg_length, const_cast<uint8_t*>(buffer + header_size));
  }

  return FrameMsgInfo();
}

/**
 * Validate a minimal payload (no CRC, no length field).
 */
inline FrameMsgInfo validate_payload_minimal(const uint8_t* buffer, size_t length, size_t header_size) {
  if (length < header_size) {
    return FrameMsgInfo();
  }

  return FrameMsgInfo(true, buffer[header_size - 1], length - header_size, const_cast<uint8_t*>(buffer + header_size));
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

}  // namespace FrameParsers
