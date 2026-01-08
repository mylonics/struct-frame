/* Frame Profiles - Pre-defined Header + Payload combinations */
/*
 * This file provides ready-to-use encode/parse functions for frame format profiles.
 * It uses C++ templates for maximum code reuse with zero runtime overhead.
 *
 * Standard Profiles:
 * - ProfileStandard: Basic + Default (General serial/UART)
 * - ProfileSensor: Tiny + Minimal (Low-bandwidth sensors)
 * - ProfileIPC: None + Minimal (Trusted inter-process communication)
 * - ProfileBulk: Basic + Extended (Large data transfers with package namespacing)
 * - ProfileNetwork: Basic + ExtendedMultiSystemStream (Multi-system networked communication)
 *
 * Each profile provides:
 * - Encoder: encode messages into a buffer
 * - BufferParser: parse/validate a complete frame in a buffer
 * - StreamParser: byte-by-byte streaming parser for serial/UART
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

    return FrameMsgInfo(true, msg_id, msg_len, const_cast<uint8_t*>(buffer + Config::header_size));
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

    return FrameMsgInfo(true, msg_id, msg_len, const_cast<uint8_t*>(buffer + Config::header_size));
  }
};

/*===========================================================================
 * Streaming Parsers (Byte-by-Byte)
 *===========================================================================*/

/**
 * Parser state for streaming parsers
 */
enum class StreamParserState : uint8_t {
  LookingForStart1 = 0,
  LookingForStart2 = 1,
  GettingHeader = 2,
  GettingPayload = 3,
  GettingFooter = 4
};

/**
 * Generic streaming parser for frames with length field and CRC.
 * Processes one byte at a time for use with serial/UART streams.
 */
template <typename Config>
class StreamParserWithCrc {
 public:
  StreamParserWithCrc(uint8_t* buffer, size_t buffer_size)
      : state_(StreamParserState::LookingForStart1),
        buffer_(buffer),
        buffer_max_size_(buffer_size),
        buffer_index_(0),
        packet_size_(0) {}

  void reset() {
    state_ = StreamParserState::LookingForStart1;
    buffer_index_ = 0;
    packet_size_ = 0;
  }

  /**
   * Parse a single byte.
   * Returns FrameMsgInfo with valid=true when a complete valid message is received.
   */
  FrameMsgInfo parse_byte(uint8_t byte) {
    FrameMsgInfo result;

    switch (state_) {
      case StreamParserState::LookingForStart1:
        if constexpr (Config::num_start_bytes == 0) {
          // No start bytes - go directly to header
          buffer_[0] = byte;
          buffer_index_ = 1;
          state_ = StreamParserState::GettingHeader;
        } else {
          if (byte == Config::computed_start_byte1()) {
            buffer_[0] = byte;
            buffer_index_ = 1;
            if constexpr (Config::num_start_bytes == 1) {
              state_ = StreamParserState::GettingHeader;
            } else {
              state_ = StreamParserState::LookingForStart2;
            }
          }
        }
        break;

      case StreamParserState::LookingForStart2:
        if (byte == Config::computed_start_byte2()) {
          buffer_[buffer_index_++] = byte;
          state_ = StreamParserState::GettingHeader;
        } else if (byte == Config::computed_start_byte1()) {
          // Restart - might be new frame
          buffer_[0] = byte;
          buffer_index_ = 1;
        } else {
          state_ = StreamParserState::LookingForStart1;
        }
        break;

      case StreamParserState::GettingHeader:
        if (buffer_index_ < buffer_max_size_) {
          buffer_[buffer_index_++] = byte;
        }

        // Check if we have enough header bytes to determine length
        if (buffer_index_ >= Config::header_size) {
          // Calculate payload length from header
          size_t header_fields_offset = Config::num_start_bytes;
          size_t len_offset = header_fields_offset;

          // Skip seq, sys_id, comp_id if present
          if constexpr (Config::has_seq) len_offset++;
          if constexpr (Config::has_sys_id) len_offset++;
          if constexpr (Config::has_comp_id) len_offset++;

          size_t payload_len = 0;
          if constexpr (Config::has_length) {
            if constexpr (Config::length_bytes == 1) {
              payload_len = buffer_[len_offset];
            } else {
              payload_len = buffer_[len_offset] | (static_cast<size_t>(buffer_[len_offset + 1]) << 8);
            }
          }

          packet_size_ = Config::overhead + payload_len;

          if (packet_size_ > buffer_max_size_) {
            // Frame too large for buffer
            state_ = StreamParserState::LookingForStart1;
          } else if (buffer_index_ >= packet_size_) {
            // Already have complete frame
            result = validate_frame();
            state_ = StreamParserState::LookingForStart1;
          } else {
            state_ = StreamParserState::GettingPayload;
          }
        }
        break;

      case StreamParserState::GettingPayload:
        if (buffer_index_ < buffer_max_size_) {
          buffer_[buffer_index_++] = byte;
        }

        if (buffer_index_ >= packet_size_) {
          result = validate_frame();
          state_ = StreamParserState::LookingForStart1;
        }
        break;

      default:
        state_ = StreamParserState::LookingForStart1;
        break;
    }

    return result;
  }

  /**
   * Get current parser state (for debugging)
   */
  StreamParserState state() const { return state_; }

 private:
  FrameMsgInfo validate_frame() {
    // Use the buffer parser to validate the complete frame
    return BufferParserWithCrc<Config>::parse(buffer_, packet_size_);
  }

  StreamParserState state_;
  uint8_t* buffer_;
  size_t buffer_max_size_;
  size_t buffer_index_;
  size_t packet_size_;
};

/**
 * Generic streaming parser for minimal frames (no length field, no CRC).
 * Requires a callback to determine message length from msg_id.
 */
template <typename Config>
class StreamParserMinimal {
 public:
  using MsgLengthCallback = std::function<bool(uint8_t msg_id, size_t* length)>;

  StreamParserMinimal(uint8_t* buffer, size_t buffer_size, MsgLengthCallback msg_length_cb = nullptr)
      : state_(StreamParserState::LookingForStart1),
        buffer_(buffer),
        buffer_max_size_(buffer_size),
        buffer_index_(0),
        packet_size_(0),
        msg_id_(0),
        get_msg_length_(std::move(msg_length_cb)) {}

  void reset() {
    state_ = StreamParserState::LookingForStart1;
    buffer_index_ = 0;
    packet_size_ = 0;
    msg_id_ = 0;
  }

  void set_msg_length_callback(MsgLengthCallback cb) { get_msg_length_ = std::move(cb); }

  /**
   * Parse a single byte.
   * Returns FrameMsgInfo with valid=true when a complete valid message is received.
   */
  FrameMsgInfo parse_byte(uint8_t byte) {
    FrameMsgInfo result;

    switch (state_) {
      case StreamParserState::LookingForStart1:
        if constexpr (Config::num_start_bytes == 0) {
          // No start bytes - this byte is the msg_id
          buffer_[0] = byte;
          buffer_index_ = 1;
          msg_id_ = byte;

          size_t msg_length = 0;
          if (get_msg_length_ && get_msg_length_(byte, &msg_length)) {
            packet_size_ = Config::header_size + msg_length;
            if (packet_size_ <= buffer_max_size_) {
              if (msg_length == 0) {
                // Zero-length message, we're done
                result = FrameMsgInfo(true, msg_id_, 0, buffer_ + Config::header_size);
                state_ = StreamParserState::LookingForStart1;
              } else {
                state_ = StreamParserState::GettingPayload;
              }
            } else {
              state_ = StreamParserState::LookingForStart1;
            }
          }
          // If callback fails or missing, stay in LookingForStart1
        } else {
          if (byte == Config::computed_start_byte1()) {
            buffer_[0] = byte;
            buffer_index_ = 1;
            if constexpr (Config::num_start_bytes == 1) {
              state_ = StreamParserState::GettingHeader;
            } else {
              state_ = StreamParserState::LookingForStart2;
            }
          }
        }
        break;

      case StreamParserState::LookingForStart2:
        if (byte == Config::computed_start_byte2()) {
          buffer_[buffer_index_++] = byte;
          state_ = StreamParserState::GettingHeader;
        } else if (byte == Config::computed_start_byte1()) {
          buffer_[0] = byte;
          buffer_index_ = 1;
        } else {
          state_ = StreamParserState::LookingForStart1;
        }
        break;

      case StreamParserState::GettingHeader:
        // For minimal frames, the next byte after start bytes is msg_id
        buffer_[buffer_index_++] = byte;
        msg_id_ = byte;

        {
          size_t msg_length = 0;
          if (get_msg_length_ && get_msg_length_(byte, &msg_length)) {
            packet_size_ = Config::header_size + msg_length;
            if (packet_size_ <= buffer_max_size_) {
              if (msg_length == 0) {
                // Zero-length message
                result = FrameMsgInfo(true, msg_id_, 0, buffer_ + Config::header_size);
                state_ = StreamParserState::LookingForStart1;
              } else {
                state_ = StreamParserState::GettingPayload;
              }
            } else {
              state_ = StreamParserState::LookingForStart1;
            }
          } else {
            // Unknown message ID
            state_ = StreamParserState::LookingForStart1;
          }
        }
        break;

      case StreamParserState::GettingPayload:
        if (buffer_index_ < buffer_max_size_) {
          buffer_[buffer_index_++] = byte;
        }

        if (buffer_index_ >= packet_size_) {
          size_t msg_len = packet_size_ - Config::header_size;
          result = FrameMsgInfo(true, msg_id_, msg_len, buffer_ + Config::header_size);
          state_ = StreamParserState::LookingForStart1;
        }
        break;

      default:
        state_ = StreamParserState::LookingForStart1;
        break;
    }

    return result;
  }

  StreamParserState state() const { return state_; }

 private:
  StreamParserState state_;
  uint8_t* buffer_;
  size_t buffer_max_size_;
  size_t buffer_index_;
  size_t packet_size_;
  uint8_t msg_id_;
  MsgLengthCallback get_msg_length_;
};

/*===========================================================================
 * Profile Configuration Type Aliases
 * Profiles are composed from HeaderConfig + PayloadConfig
 *===========================================================================*/

// Profile Standard: Basic + Default
// Frame: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
using ProfileStandardConfig = ProfileConfig<FrameHeaders::HEADER_BASIC_CONFIG, PayloadTypes::PAYLOAD_DEFAULT_CONFIG>;

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
 * Profile-Specific Type Aliases for Encoders and Parsers
 *===========================================================================*/

// Profile Standard (Basic + Default)
using ProfileStandardEncoder = FrameEncoderWithCrc<ProfileStandardConfig>;
using ProfileStandardBufferParser = BufferParserWithCrc<ProfileStandardConfig>;
using ProfileStandardStreamParser = StreamParserWithCrc<ProfileStandardConfig>;

// Profile Sensor (Tiny + Minimal)
using ProfileSensorEncoder = FrameEncoderMinimal<ProfileSensorConfig>;
using ProfileSensorBufferParser = BufferParserMinimal<ProfileSensorConfig>;
using ProfileSensorStreamParser = StreamParserMinimal<ProfileSensorConfig>;

// Profile IPC (None + Minimal)
using ProfileIPCEncoder = FrameEncoderMinimal<ProfileIPCConfig>;
using ProfileIPCBufferParser = BufferParserMinimal<ProfileIPCConfig>;
using ProfileIPCStreamParser = StreamParserMinimal<ProfileIPCConfig>;

// Profile Bulk (Basic + Extended)
using ProfileBulkEncoder = FrameEncoderWithCrc<ProfileBulkConfig>;
using ProfileBulkBufferParser = BufferParserWithCrc<ProfileBulkConfig>;
using ProfileBulkStreamParser = StreamParserWithCrc<ProfileBulkConfig>;

// Profile Network (Basic + ExtendedMultiSystemStream)
using ProfileNetworkEncoder = FrameEncoderWithCrc<ProfileNetworkConfig>;
using ProfileNetworkBufferParser = BufferParserWithCrc<ProfileNetworkConfig>;
using ProfileNetworkStreamParser = StreamParserWithCrc<ProfileNetworkConfig>;

/*===========================================================================
 * Convenience Functions
 * These are template functions that work with MessageBase-derived types.
 * The message type provides its own MSG_ID and MAX_SIZE at compile time.
 *===========================================================================*/

// Profile Standard (Basic + Default)
template <typename T, typename = std::enable_if_t<std::is_base_of_v<MessageBase<T, T::MSG_ID, T::MAX_SIZE>, T>>>
inline size_t encode_profile_standard(uint8_t* buffer, size_t buffer_size, const T& msg) {
  return ProfileStandardEncoder::encode(buffer, buffer_size, 0, 0, 0, T::MSG_ID, msg.data(), T::MAX_SIZE);
}

inline FrameMsgInfo parse_profile_standard_buffer(const uint8_t* buffer, size_t length) {
  return ProfileStandardBufferParser::parse(buffer, length);
}

// Profile Sensor (Tiny + Minimal)
template <typename T, typename = std::enable_if_t<std::is_base_of_v<MessageBase<T, T::MSG_ID, T::MAX_SIZE>, T>>>
inline size_t encode_profile_sensor(uint8_t* buffer, size_t buffer_size, const T& msg) {
  return ProfileSensorEncoder::encode(buffer, buffer_size, static_cast<uint8_t>(T::MSG_ID), msg.data(), T::MAX_SIZE);
}

inline FrameMsgInfo parse_profile_sensor_buffer(const uint8_t* buffer, size_t length,
                                                std::function<bool(uint8_t, size_t*)> get_msg_length) {
  return ProfileSensorBufferParser::parse(buffer, length, get_msg_length);
}

// Profile IPC (None + Minimal)
template <typename T, typename = std::enable_if_t<std::is_base_of_v<MessageBase<T, T::MSG_ID, T::MAX_SIZE>, T>>>
inline size_t encode_profile_ipc(uint8_t* buffer, size_t buffer_size, const T& msg) {
  return ProfileIPCEncoder::encode(buffer, buffer_size, static_cast<uint8_t>(T::MSG_ID), msg.data(), T::MAX_SIZE);
}

inline FrameMsgInfo parse_profile_ipc_buffer(const uint8_t* buffer, size_t length,
                                             std::function<bool(uint8_t, size_t*)> get_msg_length) {
  return ProfileIPCBufferParser::parse(buffer, length, get_msg_length);
}

// Profile Bulk (Basic + Extended)
template <typename T, typename = std::enable_if_t<std::is_base_of_v<MessageBase<T, T::MSG_ID, T::MAX_SIZE>, T>>>
inline size_t encode_profile_bulk(uint8_t* buffer, size_t buffer_size, const T& msg) {
  return ProfileBulkEncoder::encode(buffer, buffer_size, 0, 0, 0, T::MSG_ID, msg.data(), T::MAX_SIZE);
}

inline FrameMsgInfo parse_profile_bulk_buffer(const uint8_t* buffer, size_t length) {
  return ProfileBulkBufferParser::parse(buffer, length);
}

// Profile Network (Basic + ExtendedMultiSystemStream)
template <typename T, typename = std::enable_if_t<std::is_base_of_v<MessageBase<T, T::MSG_ID, T::MAX_SIZE>, T>>>
inline size_t encode_profile_network(uint8_t* buffer, size_t buffer_size, uint8_t sequence, uint8_t system_id,
                                     uint8_t component_id, const T& msg) {
  return ProfileNetworkEncoder::encode(buffer, buffer_size, sequence, system_id, component_id, T::MSG_ID, msg.data(),
                                       T::MAX_SIZE);
}

inline FrameMsgInfo parse_profile_network_buffer(const uint8_t* buffer, size_t length) {
  return ProfileNetworkBufferParser::parse(buffer, length);
}

}  // namespace FrameParsers
