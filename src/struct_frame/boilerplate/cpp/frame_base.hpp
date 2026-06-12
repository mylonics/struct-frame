/* Struct-frame boilerplate: frame parser base utilities */

#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <type_traits>

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

// Parse result status.
//
// Buffer parsers (BufferParserWithCrc/BufferParserMinimal) report on failure:
//   WaitingForStart — the data at the buffer head is not a frame start
//                     (caller may discard bytes and re-scan for a start byte).
//   Collecting      — the data looks like a frame but more bytes are needed.
//   CrcFailure      — a complete frame was found but its CRC did not match
//                     (frame_size is set so the caller can skip the bad frame).
//   SyncRecovery    — the frame is definitively invalid (e.g. unknown msg_id
//                     on a profile without a length field); caller should
//                     discard bytes and re-find a frame start.
enum class FrameMsgStatus : uint8_t {
  None = 0,            ///< Default / unset.
  WaitingForStart = 1, ///< No frame start at the current position.
  Collecting = 2,      ///< A frame is in progress; more bytes are needed.
  CrcFailure = 3,      ///< Complete frame received but CRC did not match.
  SyncRecovery = 4,    ///< Bytes must be discarded to re-find a valid frame start.
};

struct ParserDiagnostics;

struct FrameMsgInfo {
  bool valid;
  uint16_t msg_id;
  size_t msg_len;     // Payload length (message data only)
  size_t frame_size;  // Total frame size (header + payload + footer)
  const uint8_t* msg_data;
  const uint8_t* frame_data;  // Full frame bytes, including framing overhead
  FrameMsgStatus status;
  const ParserDiagnostics* diagnostics;

  FrameMsgInfo()
      : valid(false), msg_id(0), msg_len(0), frame_size(0), msg_data(nullptr), frame_data(nullptr),
        status(FrameMsgStatus::None), diagnostics(nullptr) {}
  FrameMsgInfo(bool v, uint16_t id, size_t len, size_t fsize, const uint8_t* data,
               const uint8_t* frame = nullptr, FrameMsgStatus st = FrameMsgStatus::None,
               const ParserDiagnostics* diag = nullptr)
      : valid(v), msg_id(id), msg_len(len), frame_size(fsize), msg_data(data), frame_data(frame), status(st),
        diagnostics(diag) {}

  // Legacy constructor for backwards compatibility
  FrameMsgInfo(bool v, uint16_t id, size_t len, const uint8_t* data)
      : valid(v), msg_id(id), msg_len(len), frame_size(0), msg_data(data), frame_data(nullptr),
        status(FrameMsgStatus::None), diagnostics(nullptr) {}

  // Allow use in boolean context (e.g., while (auto result = reader.next()) { ... })
  explicit operator bool() const { return valid; }

  // Returns an immutable diagnostics view; defaults to empty counters when unavailable.
  const ParserDiagnostics& parser_diagnostics() const;
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
 * cnt_failed_bytes:   Total bytes discarded when failures forced a reset to
 *                     searching for frame start. Tracks how much data was
 *                     dropped during sync recovery events.
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
  uint32_t cnt_failed_bytes;
  uint32_t cnt_len_errors;
  uint32_t cnt_seq_gaps;

  ParserDiagnostics()
      : cnt_crc_failures(0), cnt_sync_recoveries(0), cnt_failed_bytes(0), cnt_len_errors(0), cnt_seq_gaps(0) {}
};

inline const ParserDiagnostics& FrameMsgInfo::parser_diagnostics() const {
  static const ParserDiagnostics kEmptyDiagnostics{};
  return diagnostics ? *diagnostics : kEmptyDiagnostics;
}

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
  const uint8_t* data() const {
    static_assert(std::is_standard_layout_v<Derived>, "Message types must be standard-layout");
    return reinterpret_cast<const uint8_t*>(static_cast<const Derived*>(this));
  }

  uint8_t* data() {
    static_assert(std::is_standard_layout_v<Derived>, "Message types must be standard-layout");
    return reinterpret_cast<uint8_t*>(static_cast<Derived*>(this));
  }

  // Get the message size
  static constexpr size_t size() { return MaxSize; }

  // Get the message ID
  static constexpr uint16_t msg_id() { return MsgId; }
};

/**
 * Concept satisfied by generated message types (anything derived from
 * MessageBase). Used by encoders and the SDK so constraint failures produce
 * a single readable diagnostic instead of an SFINAE wall.
 */
template <typename T>
concept FramedMessage =
    std::is_base_of_v<MessageBase<T, T::MSG_ID, T::MAX_SIZE, T::MAGIC1, T::MAGIC2, T::BASE_SIZE>, T>;

/**
 * Returns true when a get_message_info callback is null. Callbacks that are
 * not testable against null (e.g. capturing lambdas) are treated as non-null.
 */
template <typename Fn>
constexpr bool is_null_callback(const Fn& fn) {
  if constexpr (std::is_convertible_v<const Fn&, bool>) {
    return !static_cast<bool>(fn);
  } else {
    return false;
  }
}

}  // namespace structframe
