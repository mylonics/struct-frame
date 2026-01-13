/* Frame Profiles - Pre-defined Header + Payload combinations */
/*
 * This file provides ready-to-use encode/parse functions for frame format profiles.
 * It uses C++ templates for maximum code reuse with zero runtime overhead.
 *
 * Standard Profiles:
 * - ProfileBasic: Basic + Default (General serial/UART)
 * - ProfileSensor: Tiny + Minimal (Low-bandwidth sensors)
 * - ProfileIPC: None + Minimal (Trusted inter-process communication)
 * - ProfileBulk: Basic + Extended (Large data transfers with package namespacing)
 * - ProfileNetwork: Basic + ExtendedMultiSystemStream (Multi-system networked communication)
 *
 * Each profile provides:
 * - Encoder: encode messages into a buffer
 * - BufferParser: parse/validate a complete frame in a buffer
 * - BufferReader: iterate through multiple frames in a buffer
 * - BufferWriter: encode multiple frames with automatic offset tracking
 * - AccumulatingReader: unified parser supporting both buffer chunks and byte-by-byte streaming
 */

#pragma once

#include <type_traits>

#include "frame_base.hpp"
#include "frame_headers.hpp"
#include "payload_types.hpp"

namespace FrameParsers {

/*===========================================================================
 * Profile Configuration - Composed from Header + Payload configs
 *===========================================================================*/

/**
 * Profile configuration - combines a HeaderConfig with a PayloadConfig.
 * Template parameters are constexpr configs, providing compile-time composition.
 *
 * Usage:
 *   using MyProfile = ProfileConfig<HEADER_BASIC_CONFIG, PAYLOAD_DEFAULT_CONFIG>;
 */
template <FrameHeaders::HeaderConfig Header, PayloadTypes::PayloadConfig Payload>
struct ProfileConfig {
  /* Header configuration */
  static constexpr auto header = Header;
  static constexpr uint8_t num_start_bytes = Header.num_start_bytes;
  static constexpr uint8_t start_byte1 = Header.start_byte1;
  static constexpr uint8_t start_byte2 = Header.start_byte2;

  /* Payload configuration */
  static constexpr auto payload = Payload;
  static constexpr bool has_length = Payload.has_length;
  static constexpr uint8_t length_bytes = Payload.length_bytes;
  static constexpr bool has_crc = Payload.has_crc;
  static constexpr bool has_pkg_id = Payload.has_pkg_id;
  static constexpr bool has_seq = Payload.has_seq;
  static constexpr bool has_sys_id = Payload.has_sys_id;
  static constexpr bool has_comp_id = Payload.has_comp_id;

  /* Combined sizes */
  static constexpr uint8_t header_size = Header.num_start_bytes + Payload.header_size();
  static constexpr uint8_t footer_size = Payload.footer_size();
  static constexpr size_t overhead = header_size + footer_size;
  static constexpr size_t max_payload = Payload.max_payload();

  /* Compute start byte2 dynamically for headers that encode payload type */
  static constexpr uint8_t computed_start_byte2() {
    if constexpr (Header.encodes_payload_type && Header.num_start_bytes == 2) {
      return FrameHeaders::PAYLOAD_TYPE_BASE + static_cast<uint8_t>(Payload.payload_type);
    } else {
      return Header.start_byte2;
    }
  }

  /* Compute start byte1 dynamically for Tiny header (single byte encodes payload type) */
  static constexpr uint8_t computed_start_byte1() {
    if constexpr (Header.encodes_payload_type && Header.num_start_bytes == 1) {
      return FrameHeaders::PAYLOAD_TYPE_BASE + static_cast<uint8_t>(Payload.payload_type);
    } else {
      return Header.start_byte1;
    }
  }
};

/*===========================================================================
 * Generic Frame Encoder/Parser Templates
 *===========================================================================*/

/**
 * Generic frame encoder for frames with CRC
 */
template <typename Config>
class FrameEncoderWithCrc {
 public:
  static size_t encode(uint8_t* buffer, size_t buffer_size, uint8_t seq, uint8_t sys_id, uint8_t comp_id,
                       uint16_t msg_id, const uint8_t* payload, size_t payload_size) {
    size_t total_size = Config::overhead + payload_size;

    if (buffer_size < total_size || payload_size > Config::max_payload) {
      return 0;
    }

    size_t idx = 0;

    // Write start bytes (use computed values for dynamic payload type encoding)
    if constexpr (Config::num_start_bytes >= 1) {
      buffer[idx++] = Config::computed_start_byte1();
    }
    if constexpr (Config::num_start_bytes >= 2) {
      buffer[idx++] = Config::computed_start_byte2();
    }

    size_t crc_start = idx;

    // Write optional fields before length
    if constexpr (Config::has_seq) {
      buffer[idx++] = seq;
    }
    if constexpr (Config::has_sys_id) {
      buffer[idx++] = sys_id;
    }
    if constexpr (Config::has_comp_id) {
      buffer[idx++] = comp_id;
    }

    // Write length field
    if constexpr (Config::has_length) {
      if constexpr (Config::length_bytes == 1) {
        buffer[idx++] = static_cast<uint8_t>(payload_size & 0xFF);
      } else {
        buffer[idx++] = static_cast<uint8_t>(payload_size & 0xFF);
        buffer[idx++] = static_cast<uint8_t>((payload_size >> 8) & 0xFF);
      }
    }

    // Write message ID (16-bit: high byte is pkg_id when has_pkg_id, low byte is msg_id)
    if constexpr (Config::has_pkg_id) {
      buffer[idx++] = static_cast<uint8_t>((msg_id >> 8) & 0xFF);  // pkg_id (high byte)
    }
    buffer[idx++] = static_cast<uint8_t>(msg_id & 0xFF);  // msg_id (low byte)

    // Write payload
    if (payload_size > 0 && payload != nullptr) {
      std::memcpy(buffer + idx, payload, payload_size);
      idx += payload_size;
    }

    // Calculate and write CRC
    if constexpr (Config::has_crc) {
      size_t crc_len = idx - crc_start;
      FrameChecksum ck = fletcher_checksum(buffer + crc_start, crc_len);
      buffer[idx++] = ck.byte1;
      buffer[idx++] = ck.byte2;
    }

    return idx;
  }
};

/**
 * Generic frame encoder for minimal frames (no length, no CRC)
 */
template <typename Config>
class FrameEncoderMinimal {
 public:
  static size_t encode(uint8_t* buffer, size_t buffer_size, uint8_t msg_id, const uint8_t* payload,
                       size_t payload_size) {
    size_t total_size = Config::overhead + payload_size;

    if (buffer_size < total_size) {
      return 0;
    }

    size_t idx = 0;

    // Write start bytes (use computed values for dynamic payload type encoding)
    if constexpr (Config::num_start_bytes >= 1) {
      buffer[idx++] = Config::computed_start_byte1();
    }
    if constexpr (Config::num_start_bytes >= 2) {
      buffer[idx++] = Config::computed_start_byte2();
    }

    // Write message ID
    buffer[idx++] = msg_id;

    // Write payload
    if (payload_size > 0 && payload != nullptr) {
      std::memcpy(buffer + idx, payload, payload_size);
      idx += payload_size;
    }

    return idx;
  }
};

/**
 * Generic buffer parser for frames with CRC
 */
template <typename Config>
class BufferParserWithCrc {
 public:
  static FrameMsgInfo parse(const uint8_t* buffer, size_t length) {
    if (length < Config::overhead) {
      return FrameMsgInfo();
    }

    size_t idx = 0;

    // Verify start bytes (use computed values for dynamic payload type encoding)
    if constexpr (Config::num_start_bytes >= 1) {
      if (buffer[idx++] != Config::computed_start_byte1()) {
        return FrameMsgInfo();
      }
    }
    if constexpr (Config::num_start_bytes >= 2) {
      if (buffer[idx++] != Config::computed_start_byte2()) {
        return FrameMsgInfo();
      }
    }

    size_t crc_start = idx;

    // Skip optional fields before length
    if constexpr (Config::has_seq) idx++;
    if constexpr (Config::has_sys_id) idx++;
    if constexpr (Config::has_comp_id) idx++;

    // Read length field
    size_t msg_len = 0;
    if constexpr (Config::has_length) {
      if constexpr (Config::length_bytes == 1) {
        msg_len = buffer[idx++];
      } else {
        msg_len = buffer[idx] | (static_cast<size_t>(buffer[idx + 1]) << 8);
        idx += 2;
      }
    }

    // Read message ID (16-bit: high byte is pkg_id when has_pkg_id, low byte is msg_id)
    uint16_t msg_id = 0;
    if constexpr (Config::has_pkg_id) {
      msg_id = static_cast<uint16_t>(buffer[idx++]) << 8;  // pkg_id (high byte)
    }
    msg_id |= buffer[idx++];  // msg_id (low byte)

    // Verify total size
    size_t total_size = Config::overhead + msg_len;
    if (length < total_size) {
      return FrameMsgInfo();
    }

    // Verify CRC
    if constexpr (Config::has_crc) {
      size_t crc_len = total_size - crc_start - Config::footer_size;
      FrameChecksum ck = fletcher_checksum(buffer + crc_start, crc_len);
      if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
        return FrameMsgInfo();
      }
    }

    return FrameMsgInfo(true, msg_id, msg_len, total_size, const_cast<uint8_t*>(buffer + Config::header_size));
  }
};

/**
 * Generic frame parser for minimal frames (requires get_msg_length callback)
 */
template <typename Config>
class BufferParserMinimal {
 public:
  static FrameMsgInfo parse(const uint8_t* buffer, size_t length,
                            std::function<bool(uint8_t, size_t*)> get_msg_length) {
    if (length < Config::header_size) {
      return FrameMsgInfo();
    }

    size_t idx = 0;

    // Verify start bytes (use computed values for dynamic payload type encoding)
    if constexpr (Config::num_start_bytes >= 1) {
      if (buffer[idx++] != Config::computed_start_byte1()) {
        return FrameMsgInfo();
      }
    }
    if constexpr (Config::num_start_bytes >= 2) {
      if (buffer[idx++] != Config::computed_start_byte2()) {
        return FrameMsgInfo();
      }
    }

    // Read message ID
    uint8_t msg_id = buffer[idx];

    // Get message length from callback
    size_t msg_len = 0;
    if (!get_msg_length || !get_msg_length(msg_id, &msg_len)) {
      return FrameMsgInfo();
    }

    size_t total_size = Config::header_size + msg_len;
    if (length < total_size) {
      return FrameMsgInfo();
    }

    return FrameMsgInfo(true, msg_id, msg_len, total_size, const_cast<uint8_t*>(buffer + Config::header_size));
  }
};

/*===========================================================================
 * Profile Configuration Type Aliases
 * Profiles are composed from HeaderConfig + PayloadConfig
 *===========================================================================*/

// Profile Standard: Basic + Default
// Frame: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
using ProfileBasicConfig = ProfileConfig<FrameHeaders::HEADER_BASIC_CONFIG, PayloadTypes::PAYLOAD_DEFAULT_CONFIG>;

// Profile Sensor: Tiny + Minimal
// Frame: [0x70] [MSG_ID] [PAYLOAD]
using ProfileSensorConfig = ProfileConfig<FrameHeaders::HEADER_TINY_CONFIG, PayloadTypes::PAYLOAD_MINIMAL_CONFIG>;

// Profile IPC: None + Minimal
// Frame: [MSG_ID] [PAYLOAD]
using ProfileIPCConfig = ProfileConfig<FrameHeaders::HEADER_NONE_CONFIG, PayloadTypes::PAYLOAD_MINIMAL_CONFIG>;

// Profile Bulk: Basic + Extended
// Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
using ProfileBulkConfig = ProfileConfig<FrameHeaders::HEADER_BASIC_CONFIG, PayloadTypes::PAYLOAD_EXTENDED_CONFIG>;

// Profile Network: Basic + ExtendedMultiSystemStream
// Frame: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
using ProfileNetworkConfig =
    ProfileConfig<FrameHeaders::HEADER_BASIC_CONFIG, PayloadTypes::PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG>;

/*===========================================================================
 * Buffer Reader/Writer Classes
 * These provide stateful iteration over buffers for encoding/decoding
 * multiple messages without manual offset tracking.
 *===========================================================================*/

/**
 * BufferReader - Iterate through a buffer parsing multiple frames.
 *
 * Usage:
 *   BufferReader<ProfileBasicConfig> reader(buffer, size);
 *   while (auto result = reader.next()) {
 *     // Process result.msg_id, result.msg_data, result.msg_len
 *   }
 *
 * For minimal profiles that need get_msg_length:
 *   BufferReader<ProfileSensorConfig> reader(buffer, size, get_message_length);
 */
template <typename Config>
class BufferReader {
 public:
  BufferReader(const uint8_t* buffer, size_t size)
      : buffer_(buffer), size_(size), offset_(0), get_msg_length_(nullptr) {}

  BufferReader(const uint8_t* buffer, size_t size, std::function<bool(uint8_t, size_t*)> get_msg_length)
      : buffer_(buffer), size_(size), offset_(0), get_msg_length_(get_msg_length) {}

  /**
   * Parse the next frame in the buffer.
   * Returns FrameMsgInfo with valid=true if successful, valid=false if no more frames.
   */
  FrameMsgInfo next() {
    if (offset_ >= size_) {
      return FrameMsgInfo();
    }

    FrameMsgInfo result;
    if constexpr (Config::has_length || Config::has_crc) {
      result = BufferParserWithCrc<Config>::parse(buffer_ + offset_, size_ - offset_);
    } else {
      result = BufferParserMinimal<Config>::parse(buffer_ + offset_, size_ - offset_, get_msg_length_);
    }

    if (result.valid && result.frame_size > 0) {
      offset_ += result.frame_size;
    }

    return result;
  }

  /**
   * Reset the reader to the beginning of the buffer.
   */
  void reset() { offset_ = 0; }

  /**
   * Get the current offset in the buffer.
   */
  size_t offset() const { return offset_; }

  /**
   * Get the remaining bytes in the buffer.
   */
  size_t remaining() const { return size_ > offset_ ? size_ - offset_ : 0; }

  /**
   * Check if there are more bytes to parse.
   */
  bool has_more() const { return offset_ < size_; }

 private:
  const uint8_t* buffer_;
  size_t size_;
  size_t offset_;
  std::function<bool(uint8_t, size_t*)> get_msg_length_;
};

/**
 * BufferWriter - Encode multiple frames into a buffer with automatic offset tracking.
 *
 * Usage:
 *   BufferWriter<ProfileBasicConfig> writer(buffer, sizeof(buffer));
 *   writer.write(msg1);
 *   writer.write(msg2);
 *   size_t total = writer.size();  // Total bytes written
 *
 * For profiles with extra header fields:
 *   BufferWriter<ProfileNetworkConfig> writer(buffer, sizeof(buffer));
 *   writer.write(msg, sequence, system_id, component_id);
 */
template <typename Config>
class BufferWriter {
 public:
  BufferWriter(uint8_t* buffer, size_t capacity) : buffer_(buffer), capacity_(capacity), offset_(0) {}

  /**
   * Write a message to the buffer.
   * Returns the number of bytes written, or 0 on failure.
   */
  template <typename T, typename = std::enable_if_t<std::is_base_of_v<MessageBase<T, T::MSG_ID, T::MAX_SIZE>, T>>>
  size_t write(const T& msg) {
    if constexpr (Config::has_length || Config::has_crc) {
      // Profiles with CRC use the full encoder signature
      size_t written = FrameEncoderWithCrc<Config>::encode(buffer_ + offset_, capacity_ - offset_, 0, 0, 0, T::MSG_ID,
                                                           msg.data(), T::MAX_SIZE);
      if (written > 0) {
        offset_ += written;
      }
      return written;
    } else {
      // Minimal profiles use the simple encoder
      size_t written = FrameEncoderMinimal<Config>::encode(buffer_ + offset_, capacity_ - offset_,
                                                           static_cast<uint8_t>(T::MSG_ID), msg.data(), T::MAX_SIZE);
      if (written > 0) {
        offset_ += written;
      }
      return written;
    }
  }

  /**
   * Write a message with sequence and addressing (for profiles that support it).
   */
  template <typename T, typename = std::enable_if_t<std::is_base_of_v<MessageBase<T, T::MSG_ID, T::MAX_SIZE>, T>>>
  size_t write(const T& msg, uint8_t seq, uint8_t sys_id = 0, uint8_t comp_id = 0) {
    static_assert(Config::has_seq || Config::has_sys_id || Config::has_comp_id,
                  "This profile does not support sequence/addressing fields");
    size_t written = FrameEncoderWithCrc<Config>::encode(buffer_ + offset_, capacity_ - offset_, seq, sys_id, comp_id,
                                                         T::MSG_ID, msg.data(), T::MAX_SIZE);
    if (written > 0) {
      offset_ += written;
    }
    return written;
  }

  /**
   * Reset the writer to the beginning of the buffer.
   */
  void reset() { offset_ = 0; }

  /**
   * Get the total number of bytes written.
   */
  size_t size() const { return offset_; }

  /**
   * Get the remaining capacity in the buffer.
   */
  size_t remaining() const { return capacity_ > offset_ ? capacity_ - offset_ : 0; }

  /**
   * Get pointer to the buffer.
   */
  uint8_t* data() { return buffer_; }
  const uint8_t* data() const { return buffer_; }

 private:
  uint8_t* buffer_;
  size_t capacity_;
  size_t offset_;
};

/* Convenience type aliases for BufferReader/Writer with standard profiles */
using ProfileBasicReader = BufferReader<ProfileBasicConfig>;
using ProfileBasicWriter = BufferWriter<ProfileBasicConfig>;
using ProfileSensorReader = BufferReader<ProfileSensorConfig>;
using ProfileSensorWriter = BufferWriter<ProfileSensorConfig>;
using ProfileIPCReader = BufferReader<ProfileIPCConfig>;
using ProfileIPCWriter = BufferWriter<ProfileIPCConfig>;
using ProfileBulkReader = BufferReader<ProfileBulkConfig>;
using ProfileBulkWriter = BufferWriter<ProfileBulkConfig>;
using ProfileNetworkReader = BufferReader<ProfileNetworkConfig>;
using ProfileNetworkWriter = BufferWriter<ProfileNetworkConfig>;

/**
 * AccumulatingReader - Unified parser for buffer and byte-by-byte streaming input.
 *
 * Handles partial messages across buffer boundaries and supports both:
 * - Buffer mode: add_data() for processing chunks of data
 * - Stream mode: push_byte() for byte-by-byte processing (e.g., UART)
 *
 * Template parameters:
 *   Config - The frame profile configuration (e.g., ProfileBasicConfig)
 *   BufferSize - Size of internal buffer for partial messages (default: 1024)
 *
 * Buffer mode usage:
 *   AccumulatingReader<ProfileBasicConfig> reader;
 *   reader.add_data(chunk1, chunk1_size);
 *   while (auto result = reader.next()) {
 *     // Process complete messages
 *   }
 *
 * Stream mode usage:
 *   AccumulatingReader<ProfileBasicConfig> reader;
 *   while (receiving) {
 *     uint8_t byte = read_byte();
 *     if (auto result = reader.push_byte(byte)) {
 *       // Process complete message
 *     }
 *   }
 *
 * For minimal profiles:
 *   AccumulatingReader<ProfileSensorConfig> reader(get_message_length);
 */
template <typename Config, size_t BufferSize = 1024>
class AccumulatingReader {
 public:
  /**
   * Parser state for streaming mode
   */
  enum class State : uint8_t {
    Idle = 0,           // No data, waiting for input
    LookingForStart1,   // Looking for first start byte
    LookingForStart2,   // Looking for second start byte
    CollectingHeader,   // Collecting header bytes to determine frame size
    CollectingPayload,  // Collecting payload + footer bytes
    BufferMode          // Processing external buffer via add_data/next
  };

  /**
   * Construct an AccumulatingReader with internal buffer for partial messages.
   */
  AccumulatingReader()
      : internal_data_len_(0),
        expected_frame_size_(0),
        state_(State::Idle),
        current_buffer_(nullptr),
        current_size_(0),
        current_offset_(0),
        get_msg_length_(nullptr) {}

  /**
   * Construct an AccumulatingReader with message length callback (for minimal profiles).
   */
  explicit AccumulatingReader(std::function<bool(uint8_t, size_t*)> get_msg_length)
      : internal_data_len_(0),
        expected_frame_size_(0),
        state_(State::Idle),
        current_buffer_(nullptr),
        current_size_(0),
        current_offset_(0),
        get_msg_length_(get_msg_length) {}

  // Default copy/move operations are fine with fixed array
  AccumulatingReader(const AccumulatingReader&) = default;
  AccumulatingReader& operator=(const AccumulatingReader&) = default;
  AccumulatingReader(AccumulatingReader&&) = default;
  AccumulatingReader& operator=(AccumulatingReader&&) = default;

  /**
   * Get the internal buffer size (template parameter).
   */
  static constexpr size_t buffer_size() { return BufferSize; }

  /*=========================================================================
   * Buffer Mode API - Process chunks of data
   *=========================================================================*/

  /**
   * Add a new buffer of data to process.
   * If there was a partial message from the previous buffer, data is appended
   * to the internal buffer to complete it.
   *
   * Note: Do not mix add_data() with push_byte() on the same reader instance.
   *
   * @param buffer Pointer to new data
   * @param size Size of new data
   */
  void add_data(const uint8_t* buffer, size_t size) {
    current_buffer_ = buffer;
    current_size_ = size;
    current_offset_ = 0;
    state_ = State::BufferMode;

    // If we have partial data in internal buffer, try to complete it
    if (internal_data_len_ > 0) {
      // Append as much as needed/possible from new buffer to internal buffer
      size_t space_available = BufferSize - internal_data_len_;
      size_t bytes_to_copy = (size < space_available) ? size : space_available;

      std::memcpy(internal_buffer_ + internal_data_len_, buffer, bytes_to_copy);
      internal_data_len_ += bytes_to_copy;
    }
  }

  /**
   * Parse the next frame (buffer mode).
   * Returns FrameMsgInfo with valid=true if successful, valid=false if no more complete frames.
   *
   * When returning a message completed from a partial, msg_data points to the internal buffer.
   * When returning a message from the current buffer, msg_data points into that buffer.
   */
  FrameMsgInfo next() {
    if (state_ != State::BufferMode) {
      return FrameMsgInfo();
    }

    // First, try to complete a partial message from the internal buffer
    size_t partial_len = internal_data_len_ > current_size_ ? internal_data_len_ - current_size_ : 0;
    if (internal_data_len_ > 0 && current_offset_ == 0) {
      // We have data in internal buffer that includes new data
      FrameMsgInfo result = parse_buffer(internal_buffer_, internal_data_len_);

      if (result.valid) {
        // Successfully parsed from internal buffer
        // Calculate how many bytes from the current buffer were consumed
        size_t bytes_from_current = result.frame_size > partial_len ? result.frame_size - partial_len : 0;
        current_offset_ = bytes_from_current;

        // Clear internal buffer state
        internal_data_len_ = 0;
        expected_frame_size_ = 0;

        return result;
      } else {
        // Still not enough data for a complete message
        // Keep partial state, wait for more data via add_data()
        return FrameMsgInfo();
      }
    }

    // Parse from current buffer
    if (current_buffer_ == nullptr || current_offset_ >= current_size_) {
      return FrameMsgInfo();
    }

    FrameMsgInfo result = parse_buffer(current_buffer_ + current_offset_, current_size_ - current_offset_);

    if (result.valid && result.frame_size > 0) {
      current_offset_ += result.frame_size;
      return result;
    }

    // Parse failed - might be partial message at end of buffer
    // Save remaining bytes to internal buffer for next add_data() call
    size_t remaining = current_size_ - current_offset_;
    if (remaining > 0 && remaining < BufferSize) {
      std::memcpy(internal_buffer_, current_buffer_ + current_offset_, remaining);
      internal_data_len_ = remaining;
      current_offset_ = current_size_;  // Mark current buffer as consumed
    }

    return FrameMsgInfo();
  }

  /*=========================================================================
   * Stream Mode API - Process byte-by-byte
   *=========================================================================*/

  /**
   * Push a single byte for parsing (stream mode).
   * Returns FrameMsgInfo with valid=true when a complete valid message is received.
   *
   * Note: Do not mix push_byte() with add_data() on the same reader instance.
   *
   * @param byte The byte to process
   * @return FrameMsgInfo with valid=true if a complete message was parsed
   */
  FrameMsgInfo push_byte(uint8_t byte) {
    // Initialize state on first byte if idle
    if (state_ == State::Idle || state_ == State::BufferMode) {
      state_ = State::LookingForStart1;
      internal_data_len_ = 0;
      expected_frame_size_ = 0;
    }

    switch (state_) {
      case State::LookingForStart1:
        return handle_looking_for_start1(byte);

      case State::LookingForStart2:
        return handle_looking_for_start2(byte);

      case State::CollectingHeader:
        return handle_collecting_header(byte);

      case State::CollectingPayload:
        return handle_collecting_payload(byte);

      default:
        state_ = State::LookingForStart1;
        return FrameMsgInfo();
    }
  }

  /*=========================================================================
   * Common API
   *=========================================================================*/

  /**
   * Check if there might be more data to parse (buffer mode only).
   */
  bool has_more() const {
    if (state_ != State::BufferMode) return false;
    return (internal_data_len_ > 0) || (current_buffer_ != nullptr && current_offset_ < current_size_);
  }

  /**
   * Check if there's a partial message waiting for more data.
   */
  bool has_partial() const { return internal_data_len_ > 0; }

  /**
   * Get the size of the partial message data (0 if none).
   */
  size_t partial_size() const { return internal_data_len_; }

  /**
   * Get current parser state (for debugging).
   */
  State state() const { return state_; }

  /**
   * Reset the reader, clearing any partial message data.
   */
  void reset() {
    internal_data_len_ = 0;
    expected_frame_size_ = 0;
    state_ = State::Idle;
    current_buffer_ = nullptr;
    current_size_ = 0;
    current_offset_ = 0;
  }

 private:
  /*=========================================================================
   * Stream Mode State Handlers
   *=========================================================================*/

  FrameMsgInfo handle_looking_for_start1(uint8_t byte) {
    if constexpr (Config::num_start_bytes == 0) {
      // No start bytes - this byte is the beginning of the frame
      internal_buffer_[0] = byte;
      internal_data_len_ = 1;

      // For minimal profiles without length, we need to check msg_id
      if constexpr (!Config::has_length && !Config::has_crc) {
        return handle_minimal_msg_id(byte);
      } else {
        state_ = State::CollectingHeader;
      }
    } else {
      if (byte == Config::computed_start_byte1()) {
        internal_buffer_[0] = byte;
        internal_data_len_ = 1;

        if constexpr (Config::num_start_bytes == 1) {
          state_ = State::CollectingHeader;
        } else {
          state_ = State::LookingForStart2;
        }
      }
      // Otherwise stay in LookingForStart1
    }
    return FrameMsgInfo();
  }

  FrameMsgInfo handle_looking_for_start2(uint8_t byte) {
    if (byte == Config::computed_start_byte2()) {
      internal_buffer_[internal_data_len_++] = byte;
      state_ = State::CollectingHeader;
    } else if (byte == Config::computed_start_byte1()) {
      // Might be start of new frame - restart
      internal_buffer_[0] = byte;
      internal_data_len_ = 1;
      // Stay in LookingForStart2
    } else {
      // Invalid - go back to looking for start
      state_ = State::LookingForStart1;
      internal_data_len_ = 0;
    }
    return FrameMsgInfo();
  }

  FrameMsgInfo handle_collecting_header(uint8_t byte) {
    if (internal_data_len_ >= BufferSize) {
      // Buffer overflow - reset
      state_ = State::LookingForStart1;
      internal_data_len_ = 0;
      return FrameMsgInfo();
    }

    internal_buffer_[internal_data_len_++] = byte;

    // Check if we have enough header bytes to determine frame size
    if (internal_data_len_ >= Config::header_size) {
      // For minimal profiles, we need the callback to determine length
      if constexpr (!Config::has_length && !Config::has_crc) {
        // msg_id is at header_size - 1 position
        uint8_t msg_id = internal_buffer_[Config::header_size - 1];
        size_t msg_len = 0;
        if (get_msg_length_ && get_msg_length_(msg_id, &msg_len)) {
          expected_frame_size_ = Config::header_size + msg_len;

          if (expected_frame_size_ > BufferSize) {
            // Too large - reset
            state_ = State::LookingForStart1;
            internal_data_len_ = 0;
            return FrameMsgInfo();
          }

          if (msg_len == 0) {
            // Zero-length message - complete!
            FrameMsgInfo result(true, msg_id, 0, expected_frame_size_, internal_buffer_ + Config::header_size);
            state_ = State::LookingForStart1;
            internal_data_len_ = 0;
            expected_frame_size_ = 0;
            return result;
          }

          state_ = State::CollectingPayload;
        } else {
          // Unknown message ID - reset
          state_ = State::LookingForStart1;
          internal_data_len_ = 0;
        }
      } else {
        // Calculate payload length from header
        size_t len_offset = Config::num_start_bytes;

        // Skip seq, sys_id, comp_id if present
        if constexpr (Config::has_seq) len_offset++;
        if constexpr (Config::has_sys_id) len_offset++;
        if constexpr (Config::has_comp_id) len_offset++;

        size_t payload_len = 0;
        if constexpr (Config::has_length) {
          if constexpr (Config::length_bytes == 1) {
            payload_len = internal_buffer_[len_offset];
          } else {
            payload_len = internal_buffer_[len_offset] | (static_cast<size_t>(internal_buffer_[len_offset + 1]) << 8);
          }
        }

        expected_frame_size_ = Config::overhead + payload_len;

        if (expected_frame_size_ > BufferSize) {
          // Too large - reset
          state_ = State::LookingForStart1;
          internal_data_len_ = 0;
          return FrameMsgInfo();
        }

        // Check if we already have the complete frame
        if (internal_data_len_ >= expected_frame_size_) {
          return validate_and_return();
        }

        state_ = State::CollectingPayload;
      }
    }

    return FrameMsgInfo();
  }

  FrameMsgInfo handle_collecting_payload(uint8_t byte) {
    if (internal_data_len_ >= BufferSize) {
      // Buffer overflow - reset
      state_ = State::LookingForStart1;
      internal_data_len_ = 0;
      return FrameMsgInfo();
    }

    internal_buffer_[internal_data_len_++] = byte;

    if (internal_data_len_ >= expected_frame_size_) {
      return validate_and_return();
    }

    return FrameMsgInfo();
  }

  FrameMsgInfo handle_minimal_msg_id(uint8_t msg_id) {
    size_t msg_len = 0;
    if (get_msg_length_ && get_msg_length_(msg_id, &msg_len)) {
      expected_frame_size_ = Config::header_size + msg_len;

      if (expected_frame_size_ > BufferSize) {
        state_ = State::LookingForStart1;
        internal_data_len_ = 0;
        return FrameMsgInfo();
      }

      if (msg_len == 0) {
        // Zero-length message - complete!
        FrameMsgInfo result(true, msg_id, 0, expected_frame_size_, internal_buffer_ + Config::header_size);
        state_ = State::LookingForStart1;
        internal_data_len_ = 0;
        expected_frame_size_ = 0;
        return result;
      }

      state_ = State::CollectingPayload;
    } else {
      // Unknown msg_id - stay looking for valid start
      state_ = State::LookingForStart1;
      internal_data_len_ = 0;
    }
    return FrameMsgInfo();
  }

  FrameMsgInfo validate_and_return() {
    FrameMsgInfo result = parse_buffer(internal_buffer_, internal_data_len_);

    // Reset state for next message
    state_ = State::LookingForStart1;
    internal_data_len_ = 0;
    expected_frame_size_ = 0;

    return result;
  }

  /*=========================================================================
   * Shared Parsing
   *=========================================================================*/

  FrameMsgInfo parse_buffer(const uint8_t* buffer, size_t size) {
    if constexpr (Config::has_length || Config::has_crc) {
      return BufferParserWithCrc<Config>::parse(buffer, size);
    } else {
      return BufferParserMinimal<Config>::parse(buffer, size, get_msg_length_);
    }
  }

  /*=========================================================================
   * Member Variables
   *=========================================================================*/

  uint8_t internal_buffer_[BufferSize];  // Internal buffer for partial messages (stack allocated)
  size_t internal_data_len_;             // Current data length in internal buffer
  size_t expected_frame_size_;           // Expected total frame size (0 if not yet known)
  State state_;                          // Current parser state

  // Buffer mode state
  const uint8_t* current_buffer_;  // Current external buffer being processed
  size_t current_size_;            // Size of current external buffer
  size_t current_offset_;          // Current position in external buffer

  std::function<bool(uint8_t, size_t*)> get_msg_length_;
};

/* Convenience type aliases for AccumulatingReader with standard profiles (default 1024 byte buffer) */
using ProfileBasicAccumulatingReader = AccumulatingReader<ProfileBasicConfig>;
using ProfileSensorAccumulatingReader = AccumulatingReader<ProfileSensorConfig>;
using ProfileIPCAccumulatingReader = AccumulatingReader<ProfileIPCConfig>;
using ProfileBulkAccumulatingReader = AccumulatingReader<ProfileBulkConfig>;
using ProfileNetworkAccumulatingReader = AccumulatingReader<ProfileNetworkConfig>;

}  // namespace FrameParsers
