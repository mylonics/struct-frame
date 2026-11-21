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
 * - BufferReader: iterate through multiple frames in a buffer
 * - BufferWriter: encode multiple frames with automatic offset tracking
 * - AccumulatingReader: unified parser supporting both buffer chunks and byte-by-byte streaming
 */

#pragma once

#include <type_traits>

#include "frame_base.hpp"
#include "frame_headers.hpp"
#include "payload_types.hpp"
#include "sf_system_info.hpp"

/* System frames (payload type 9, start byte 0x79) carry struct-frame's own messages next to
 * the application's. Define SF_DISABLE_SYSTEM_FRAMES to compile the reader support out. */
#ifndef SF_DISABLE_SYSTEM_FRAMES
#define SF_SYSTEM_FRAMES_ENABLED 1
#else
#define SF_SYSTEM_FRAMES_ENABLED 0
#endif

namespace structframe {

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
template <headers::HeaderConfig Header, payloads::PayloadConfig Payload>
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
      return headers::PAYLOAD_TYPE_BASE + static_cast<uint8_t>(Payload.payload_type);
    } else {
      return Header.start_byte2;
    }
  }

  /* Compute start byte1 dynamically for Tiny header (single byte encodes payload type) */
  static constexpr uint8_t computed_start_byte1() {
    if constexpr (Header.encodes_payload_type && Header.num_start_bytes == 1) {
      return headers::PAYLOAD_TYPE_BASE + static_cast<uint8_t>(Payload.payload_type);
    } else {
      return Header.start_byte1;
    }
  }

  /* System frames travel with this profile's header when it carries the payload type in a
   * start byte (Basic and Tiny headers). SystemConfig is their profile. */
  static constexpr bool supports_system_frames =
      SF_SYSTEM_FRAMES_ENABLED && Header.encodes_payload_type && Header.num_start_bytes >= 1;
  using SystemConfig = ProfileConfig<Header, payloads::PAYLOAD_SYSTEM_CONFIG>;
};

/*===========================================================================
 * Generic Frame Encoder/Parser Templates
 *===========================================================================*/

/**
 * Generic frame encoder for frames with CRC
 */
template <typename Config>
class FrameEncoderWithCrc {
 private:
  // Helper to detect if T has IS_VARIABLE member and it's true
  template <typename U>
  static constexpr bool is_variable_message() {
    if constexpr (requires { U::IS_VARIABLE; }) {
      return U::IS_VARIABLE;
    } else {
      return false;
    }
  }

 public:
  /**
   * Encode a message object.
   * Message must be derived from MessageBase and have MSG_ID, MAX_SIZE, MAGIC1, MAGIC2.
   * For variable messages (with IS_VARIABLE=true), uses serialize() for variable-length encoding.
   */
  template <FramedMessage T>
  static size_t encode(uint8_t* buffer, size_t buffer_size, const T& msg, uint8_t seq = 0, uint8_t sys_id = 0,
                       uint8_t comp_id = 0) {
    // Determine if this is a variable message
    constexpr bool is_variable = is_variable_message<T>();

    // Get the actual payload size (variable messages use serialized_size(), others use MAX_SIZE)
    size_t payload_size;
    if constexpr (is_variable) {
      payload_size = msg.serialized_size();
    } else {
      payload_size = T::MAX_SIZE;
    }

    // A profile without a package-id byte carries only a 1-byte message id.
    // Fail rather than silently truncating a larger (package-qualified) id.
    if constexpr (!Config::has_pkg_id) {
      if constexpr (T::MSG_ID > 0xFF) {
        return 0;
      }
    }

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

    // Write length field (use actual payload size for variable messages)
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
      buffer[idx++] = static_cast<uint8_t>((T::MSG_ID >> 8) & 0xFF);  // pkg_id (high byte)
    }
    buffer[idx++] = static_cast<uint8_t>(T::MSG_ID & 0xFF);  // msg_id (low byte)

    // Write payload (use serialize for variable messages, memcpy for fixed)
    if constexpr (is_variable) {
      size_t written = msg.serialize(buffer + idx);
      idx += written;
    } else {
      // Not msg.data(): a message field or oneof named `data` would hide that member.
      std::memcpy(buffer + idx, reinterpret_cast<const uint8_t*>(&msg), payload_size);
      idx += payload_size;
    }

    // Calculate and write CRC (extension-aware)
    if constexpr (Config::has_crc) {
      size_t crc_len = idx - crc_start;
      size_t effective_base = crc_len;
      if constexpr (Config::has_length) {
        if (T::BASE_SIZE <= payload_size) {
          effective_base = (crc_len - payload_size) + T::BASE_SIZE;
        }
      }
      FrameChecksum ck = fletcher_checksum_ext(buffer + crc_start, effective_base, crc_len, T::MAGIC1, T::MAGIC2);
      buffer[idx++] = ck.byte1;
      buffer[idx++] = ck.byte2;
    }

    return idx;
  }

  template <typename Buffer, FramedMessage T>
  static size_t encode(Buffer& buffer, const T& msg, uint8_t seq = 0, uint8_t sys_id = 0, uint8_t comp_id = 0) {
    return encode(buffer.data(), buffer.size(), msg, seq, sys_id, comp_id);
  }
};

/**
 * Generic frame encoder for minimal frames (no length, no CRC)
 */
template <typename Config>
class FrameEncoderMinimal {
 private:
  // Helper to detect if T has IS_VARIABLE member and it's true
  template <typename U>
  static constexpr bool is_variable_message() {
    if constexpr (requires { U::IS_VARIABLE; }) {
      return U::IS_VARIABLE;
    } else {
      return false;
    }
  }

 public:
  /**
   * Encode a message object.
   * Message must be derived from MessageBase and have MSG_ID, MAX_SIZE.
   * NOTE: Minimal profiles do NOT support variable-length encoding!
   * Variable messages are always encoded at MAX_SIZE for minimal profiles
   * because the parser has no length field and cannot determine message boundaries.
   */
  template <FramedMessage T>
  static size_t encode(uint8_t* buffer, size_t buffer_size, const T& msg) {
    // Minimal profiles ALWAYS use MAX_SIZE (no variable-length support)
    constexpr size_t payload_size = T::MAX_SIZE;

    // A profile without a package-id byte carries only a 1-byte message id.
    // Fail rather than silently truncating a larger (package-qualified) id.
    if constexpr (!Config::has_pkg_id) {
      if constexpr (T::MSG_ID > 0xFF) {
        return 0;
      }
    }

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
    buffer[idx++] = static_cast<uint8_t>(T::MSG_ID);

    if constexpr (is_variable_message<T>() && sizeof(T) != payload_size) {
      // Variable oneofs carry a wire-only length prefix that is not stored in the struct,
      // so the struct is smaller than MAX_SIZE: copying MAX_SIZE bytes would over-read it.
      // Serialize and zero-pad out to MAX_SIZE instead.
      size_t written = msg.serialize(buffer + idx);
      if (written > payload_size) {
        return 0;
      }
      std::memset(buffer + idx + written, 0, payload_size - written);
    } else {
      // Fixed messages and array-only variable messages: the in-memory struct is already
      // the MAX_SIZE wire layout (arrays are stored as count + full-capacity data).
      // Not msg.data(): a message field or oneof named `data` would hide that member.
      std::memcpy(buffer + idx, reinterpret_cast<const uint8_t*>(&msg), payload_size);
    }
    idx += payload_size;

    return idx;
  }

  template <typename Buffer, FramedMessage T>
  static size_t encode(Buffer& buffer, const T& msg) {
    return encode(buffer.data(), buffer.size(), msg);
  }
};

/**
 * Generic buffer parser for frames with CRC
 */
template <typename Config>
class BufferParserWithCrc {
 public:
  /**
   * Parse a frame with CRC using a callable to get message info.
   * @tparam GetMessageInfoFn Callable type (function pointer, lambda, or functor) with signature MessageInfo(uint16_t)
   * @param buffer Pointer to data buffer
   * @param length Size of buffer
   * @param get_message_info Callable that returns MessageInfo for a given message ID
   * @return FrameMsgInfo with valid=true if successful
   */
  template <typename GetMessageInfoFn>
  static FrameMsgInfo parse(const uint8_t* buffer, size_t length, GetMessageInfoFn get_message_info) {
    if (length < Config::overhead) {
      FrameMsgInfo r;
      r.status = FrameMsgStatus::Collecting;
      return r;
    }

    size_t idx = 0;

    // Verify start bytes (use computed values for dynamic payload type encoding)
    if constexpr (Config::num_start_bytes >= 1) {
      if (buffer[idx++] != Config::computed_start_byte1()) {
        FrameMsgInfo r;
        r.status = FrameMsgStatus::WaitingForStart;
        return r;
      }
    }
    if constexpr (Config::num_start_bytes >= 2) {
      if (buffer[idx++] != Config::computed_start_byte2()) {
        FrameMsgInfo r;
        r.status = FrameMsgStatus::WaitingForStart;
        return r;
      }
    }

    size_t crc_start = idx;

    // Optional fields before length
    uint8_t sequence = 0, system_id = 0, component_id = 0, package_id = 0;
    if constexpr (Config::has_seq) sequence = buffer[idx++];
    if constexpr (Config::has_sys_id) system_id = buffer[idx++];
    if constexpr (Config::has_comp_id) component_id = buffer[idx++];

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
      package_id = buffer[idx];
      msg_id = static_cast<uint16_t>(buffer[idx++]) << 8;  // pkg_id (high byte)
    }
    msg_id |= buffer[idx++];  // msg_id (low byte)

    // Verify total size
    size_t total_size = Config::overhead + msg_len;
    if (length < total_size) {
      FrameMsgInfo r;
      r.status = FrameMsgStatus::Collecting;
      return r;
    }

    // Verify CRC (extension-aware).
    // Magic bytes are obtained from the callback when one is provided.
    // Without a callback (GetMessageInfoFn == nullptr_t), magic1=magic2=0 is used —
    // CRC verification will succeed only for messages encoded with zero magic bytes.
    if constexpr (Config::has_crc) {
      size_t crc_len = total_size - crc_start - Config::footer_size;

      uint8_t magic1 = 0, magic2 = 0;
      size_t effective_base = crc_len;
      if constexpr (!std::is_same_v<GetMessageInfoFn, std::nullptr_t>) {
        if (!is_null_callback(get_message_info)) {
          auto info = get_message_info(msg_id);
          if (info) {
            magic1 = info.magic1;
            magic2 = info.magic2;
            if constexpr (Config::has_length) {
              if (info.base_size <= msg_len) {
                effective_base = (crc_len - msg_len) + info.base_size;
              }
            }
          }
        }
      }

      FrameChecksum ck = fletcher_checksum_ext(buffer + crc_start, effective_base, crc_len, magic1, magic2);
      if (ck.byte1 != buffer[total_size - 2] || ck.byte2 != buffer[total_size - 1]) {
        return FrameMsgInfo(false, msg_id, msg_len, total_size,
                            buffer + Config::header_size, buffer,
                            FrameMsgStatus::CrcFailure);
      }
    }

    FrameMsgInfo result(true, msg_id, msg_len, total_size, buffer + Config::header_size, buffer);
    result.sequence = sequence;
    result.system_id = system_id;
    result.component_id = component_id;
    result.package_id = package_id;
    return result;
  }

  template <typename Buffer, typename GetMessageInfoFn = std::nullptr_t>
  static FrameMsgInfo parse(const Buffer& buffer, GetMessageInfoFn get_message_info = nullptr) {
    return parse(buffer.data(), buffer.size(), get_message_info);
  }
};

/**
 * Generic frame parser for minimal frames (requires get_message_info callback)
 * @tparam GetMessageInfoFn Callable type that takes uint16_t and returns MessageInfo
 */
template <typename Config>
class BufferParserMinimal {
 public:
  /**
   * Parse a minimal frame using a callable to get message info.
   * @tparam GetMessageInfoFn Callable type (function pointer, lambda, or functor) with signature MessageInfo(uint16_t)
   * @param buffer Pointer to data buffer
   * @param length Size of buffer
   * @param get_message_info Callable that returns MessageInfo for a given message ID
   * @return FrameMsgInfo with valid=true if successful
   */
  template <typename GetMessageInfoFn>
  static FrameMsgInfo parse(const uint8_t* buffer, size_t length, GetMessageInfoFn get_message_info) {
    if (length < Config::header_size) {
      FrameMsgInfo r;
      r.status = FrameMsgStatus::Collecting;
      return r;
    }

    size_t idx = 0;

    // Verify start bytes (use computed values for dynamic payload type encoding)
    if constexpr (Config::num_start_bytes >= 1) {
      if (buffer[idx++] != Config::computed_start_byte1()) {
        FrameMsgInfo r;
        r.status = FrameMsgStatus::WaitingForStart;
        return r;
      }
    }
    if constexpr (Config::num_start_bytes >= 2) {
      if (buffer[idx++] != Config::computed_start_byte2()) {
        FrameMsgInfo r;
        r.status = FrameMsgStatus::WaitingForStart;
        return r;
      }
    }

    // Read message ID
    uint8_t msg_id = buffer[idx];

    // Get message info from callback
    if constexpr (!std::is_same_v<GetMessageInfoFn, std::nullptr_t>) {
      if (!is_null_callback(get_message_info)) {
        auto info = get_message_info(msg_id);
        if (!info) {
          // Unknown message ID — this position is not a frame start. Report
          // WaitingForStart (matching the C parser) so readers resync by
          // scanning forward instead of stalling.
          FrameMsgInfo r;
          r.status = FrameMsgStatus::WaitingForStart;
          return r;
        }
        size_t msg_len = info.size;
        size_t total_size = Config::header_size + msg_len;
        if (length < total_size) {
          FrameMsgInfo r;
          r.status = FrameMsgStatus::Collecting;
          return r;
        }
        return FrameMsgInfo(true, msg_id, msg_len, total_size,
                            buffer + Config::header_size, buffer);
      }
    }

    // No callback — cannot determine message length; report WaitingForStart
    FrameMsgInfo r;
    r.status = FrameMsgStatus::WaitingForStart;
    return r;
  }

  template <typename Buffer, typename GetMessageInfoFn = std::nullptr_t>
  static FrameMsgInfo parse(const Buffer& buffer, GetMessageInfoFn get_message_info = nullptr) {
    return parse(buffer.data(), buffer.size(), get_message_info);
  }
};

/*===========================================================================
 * Profile Configuration Type Aliases
 * Profiles are composed from HeaderConfig + PayloadConfig
 *===========================================================================*/

// Profile Standard: Basic + Default
// Frame: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
using ProfileStandardConfig = ProfileConfig<headers::HEADER_BASIC_CONFIG, payloads::PAYLOAD_DEFAULT_CONFIG>;

// Profile Sensor: Tiny + Minimal
// Frame: [0x70] [MSG_ID] [PAYLOAD]
using ProfileSensorConfig = ProfileConfig<headers::HEADER_TINY_CONFIG, payloads::PAYLOAD_MINIMAL_CONFIG>;

// Profile IPC: None + Minimal
// Frame: [MSG_ID] [PAYLOAD]
using ProfileIPCConfig = ProfileConfig<headers::HEADER_NONE_CONFIG, payloads::PAYLOAD_MINIMAL_CONFIG>;

// Profile Bulk: Basic + Extended
// Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
using ProfileBulkConfig = ProfileConfig<headers::HEADER_BASIC_CONFIG, payloads::PAYLOAD_EXTENDED_CONFIG>;

// Profile Network: Basic + ExtendedMultiSystemStream
// Frame: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
using ProfileNetworkConfig =
    ProfileConfig<headers::HEADER_BASIC_CONFIG, payloads::PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG>;

/*===========================================================================
 * System frames - encode, and helpers shared by the readers
 *===========================================================================*/

namespace system_frames {

/* True when data starts with the start bytes of a system frame of SysConfig. */
template <typename SysConfig>
inline bool is_system_start(const uint8_t* data, size_t size) {
  if (size < 1 || data[0] != SysConfig::computed_start_byte1()) return false;
  if constexpr (SysConfig::num_start_bytes >= 2) {
    return size >= 2 && data[1] == SysConfig::computed_start_byte2();
  } else {
    return true;
  }
}

/* Check the header of a candidate system frame: 1 when the system message id is known and
 * the length fits it, 0 when not, -1 while the header is incomplete. */
template <typename SysConfig>
inline int header_check(const uint8_t* data, size_t size) {
  if (size < SysConfig::header_size) return -1;
  constexpr size_t off = SysConfig::num_start_bytes + 3;  // after SEQ, SYS, COMP
  size_t length = static_cast<size_t>(data[off]) | (static_cast<size_t>(data[off + 1]) << 8);
  MessageInfo info = message_info(data[SysConfig::header_size - 1]);
  return (info && length >= info.min_size && length <= info.size) ? 1 : 0;
}

/* Parse a frame known to start with system start bytes. */
template <typename SysConfig>
inline FrameMsgInfo parse(const uint8_t* data, size_t size) {
  FrameMsgInfo result;
  if (header_check<SysConfig>(data, size) == 0) {
    result.status = FrameMsgStatus::WaitingForStart;
  } else {
    result = BufferParserWithCrc<SysConfig>::parse(data, size, &message_info);
  }
  result.is_system = true;
  return result;
}

/* Index of the next byte in buf[begin, end) that can start an application frame (sb1) or a
 * system frame (sys_sb1, when with_system), or end when there is none. */
inline size_t find_start(const uint8_t* buf, size_t begin, size_t end, uint8_t sb1, bool with_system,
                         uint8_t sys_sb1) {
  if (begin >= end) return end;
  const void* p = std::memchr(buf + begin, static_cast<int>(sb1), end - begin);
  size_t nxt = p ? static_cast<size_t>(static_cast<const uint8_t*>(p) - buf) : end;
  if (with_system && sys_sb1 != sb1 && nxt > begin) {
    const void* q = std::memchr(buf + begin, static_cast<int>(sys_sb1), nxt - begin);
    if (q) nxt = static_cast<size_t>(static_cast<const uint8_t*>(q) - buf);
  }
  return nxt;
}

/**
 * Encode a system frame for the header of Config: system message system_msg_id with its
 * serialized fixed fields and an optional raw tail (Ping, Pong, LinkTestData, RpcRequest,
 * RpcResponse). Returns the frame size, or 0 when the message is unknown, fixed_size is not
 * its fixed size, the tail is too long or the buffer too small.
 */
template <typename Config>
inline size_t encode(uint8_t* buffer, size_t buffer_size, uint8_t system_msg_id, const uint8_t* fixed,
                     size_t fixed_size, const uint8_t* tail = nullptr, size_t tail_size = 0, uint8_t seq = 0,
                     uint8_t sys_id = 0, uint8_t comp_id = 0) {
  static_assert(Config::supports_system_frames,
                "this profile cannot carry system frames (it needs a Basic or Tiny header)");
  using Sys = typename Config::SystemConfig;
  MessageInfo info = message_info(system_msg_id);
  if (!info || fixed_size != info.min_size || tail_size > info.size - info.min_size) return 0;
  size_t payload_size = fixed_size + tail_size;
  size_t total = Sys::overhead + payload_size;
  if (buffer_size < total) return 0;
  size_t idx = 0;
  buffer[idx++] = Sys::computed_start_byte1();
  if constexpr (Sys::num_start_bytes >= 2) buffer[idx++] = Sys::computed_start_byte2();
  size_t crc_start = idx;
  buffer[idx++] = seq;
  buffer[idx++] = sys_id;
  buffer[idx++] = comp_id;
  buffer[idx++] = static_cast<uint8_t>(payload_size & 0xFF);
  buffer[idx++] = static_cast<uint8_t>((payload_size >> 8) & 0xFF);
  buffer[idx++] = system_msg_id;
  if (fixed_size > 0 && fixed != buffer + idx) std::memmove(buffer + idx, fixed, fixed_size);
  idx += fixed_size;
  if (tail_size > 0 && tail != buffer + idx) std::memmove(buffer + idx, tail, tail_size);
  idx += tail_size;
  FrameChecksum ck = fletcher_checksum(buffer + crc_start, idx - crc_start, info.magic1, info.magic2);
  buffer[idx++] = ck.byte1;
  buffer[idx++] = ck.byte2;
  return idx;
}

/* Encode a generated sf_system message (structframe::sf_system::Ping, ...) as a system frame. */
template <typename Config, FramedMessage T>
inline size_t encode(uint8_t* buffer, size_t buffer_size, const T& msg, const uint8_t* tail = nullptr,
                     size_t tail_size = 0, uint8_t seq = 0, uint8_t sys_id = 0, uint8_t comp_id = 0) {
  return encode<Config>(buffer, buffer_size, static_cast<uint8_t>(T::MSG_ID),
                        reinterpret_cast<const uint8_t*>(&msg), T::MAX_SIZE, tail, tail_size, seq, sys_id,
                        comp_id);
}

/* The tail of a valid system frame (the bytes after the message's fixed fields). */
inline const uint8_t* tail(const FrameMsgInfo& frame, size_t& tail_size) {
  tail_size = 0;
  if (!frame.valid || !frame.is_system) return nullptr;
  MessageInfo info = message_info(frame.msg_id);
  if (!info || frame.msg_len < info.min_size) return nullptr;
  tail_size = frame.msg_len - info.min_size;
  return frame.msg_data + info.min_size;
}

}  // namespace system_frames

/*===========================================================================
 * Buffer Reader/Writer Classes
 * These provide stateful iteration over buffers for encoding/decoding
 * multiple messages without manual offset tracking.
 *===========================================================================*/

/**
 * BufferReader - Iterate through a buffer parsing multiple frames.
 *
 * Usage:
 *   BufferReader<ProfileStandardConfig> reader(buffer, size);
 *   while (auto result = reader.next()) {
 *     // Process result.msg_id, result.msg_data, result.msg_len
 *   }
 *
 * For minimal profiles that need get_message_info:
 *   BufferReader<ProfileSensorConfig, decltype(&get_msg_info)> reader(buffer, size, get_msg_info);
 *   // Or with lambda:
 *   auto getter = [](uint16_t id) { return get_message_info(id); };
 *   BufferReader<ProfileSensorConfig, decltype(getter)> reader(buffer, size, getter);
 *
 * @tparam Config Frame profile configuration
 * @tparam GetMessageInfoFn Callable type for minimal profiles (default: nullptr_t for non-minimal)
 */
template <typename Config, typename GetMessageInfoFn = std::nullptr_t>
class BufferReader {
 public:
  BufferReader(const uint8_t* buffer, size_t size) : buffer_(buffer), size_(size), offset_(0), get_message_info_{} {}

  BufferReader(const uint8_t* buffer, size_t size, GetMessageInfoFn get_message_info)
      : buffer_(buffer), size_(size), offset_(0), get_message_info_(get_message_info) {}

  template <typename Buffer>
  explicit BufferReader(const Buffer& buffer) : BufferReader(buffer.data(), buffer.size()) {}

  template <typename Buffer>
  BufferReader(const Buffer& buffer, GetMessageInfoFn get_message_info)
      : BufferReader(buffer.data(), buffer.size(), get_message_info) {}

  /**
   * Parse the next frame in the buffer.
   * Returns FrameMsgInfo with valid=true if successful, valid=false if no more frames.
   * System frames are returned (is_system) only after set_deliver_system_frames(true).
   */
  FrameMsgInfo next() {
    for (;;) {
      FrameMsgInfo result = next_frame();
      if (result.valid && result.is_system && !deliver_system_frames_) continue;
      return result;
    }
  }

  /** Return system frames from next() instead of skipping them. */
  void set_deliver_system_frames(bool deliver) { deliver_system_frames_ = deliver; }

 private:
  FrameMsgInfo next_frame() {
    if (offset_ >= size_) {
      return FrameMsgInfo();
    }

    FrameMsgInfo result = parse_frame(buffer_ + offset_, size_ - offset_);

    if (result.frame_size > 0) {
      // Advance past complete frames (valid or CRC-failed)
      offset_ += result.frame_size;
    } else if (result.status == FrameMsgStatus::WaitingForStart) {
      // Head byte is not a frame start — scan forward to next start byte,
      // reporting SyncRecovery so try_next() keeps advancing.
      size_t old_offset = offset_;
      if constexpr (Config::num_start_bytes >= 1) {
        offset_ = system_frames::find_start(buffer_, offset_ + 1, size_, Config::computed_start_byte1(),
                                            Config::supports_system_frames,
                                            Config::SystemConfig::computed_start_byte1());
      } else {
        // No start bytes (e.g. IPC profile): advance one byte and retry so a
        // single unknown msg_id doesn't discard the rest of the buffer.
        offset_ += 1;
      }
      result.status = FrameMsgStatus::SyncRecovery;
      result.frame_size = offset_ - old_offset;
    }
    // Collecting: leave offset unchanged — frame is incomplete (normal end-of-buffer)

    return result;
  }

 public:
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

  /**
   * Try to parse the next frame. Returns true while forward progress is made
   * (valid frame, CRC-failed frame, or skipped resync bytes). Returns false
   * when the buffer is drained or only a trailing partial frame remains.
   *
   * Canonical drain loop:
   *   FrameMsgInfo f;
   *   while (reader.try_next(f)) {
   *       if (f.valid) handle(f);  // else CrcFailure or SyncRecovery
   *   }
   */
  bool try_next(FrameMsgInfo& out) {
    out = next();
    return out.valid || out.frame_size > 0;
  }

 private:
  FrameMsgInfo parse_frame(const uint8_t* buffer, size_t size) const {
    if constexpr (Config::supports_system_frames) {
      if (system_frames::is_system_start<typename Config::SystemConfig>(buffer, size)) {
        return system_frames::parse<typename Config::SystemConfig>(buffer, size);
      }
    }
    if constexpr (Config::has_length || Config::has_crc) {
      return BufferParserWithCrc<Config>::parse(buffer, size, get_message_info_);
    } else {
      return BufferParserMinimal<Config>::parse(buffer, size, get_message_info_);
    }
  }

  const uint8_t* buffer_;
  size_t size_;
  size_t offset_;
  GetMessageInfoFn get_message_info_;
  bool deliver_system_frames_ = false;
};

/**
 * BufferWriter - Encode multiple frames into a buffer with automatic offset tracking.
 *
 * Usage:
 *   BufferWriter<ProfileStandardConfig> writer(buffer, sizeof(buffer));
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

  template <typename Buffer>
  explicit BufferWriter(Buffer& buffer) : BufferWriter(buffer.data(), buffer.size()) {}

  /**
   * Write a message to the buffer.
   * Returns the number of bytes written, or 0 on failure.
   */
  template <FramedMessage T>
  size_t write(const T& msg) {
    if constexpr (Config::has_length || Config::has_crc) {
      // Profiles with CRC use the full encoder signature
      size_t written = FrameEncoderWithCrc<Config>::encode(buffer_ + offset_, capacity_ - offset_, msg);
      if (written > 0) {
        offset_ += written;
      }
      return written;
    } else {
      // Minimal profiles use the simple encoder
      size_t written = FrameEncoderMinimal<Config>::encode(buffer_ + offset_, capacity_ - offset_, msg);
      if (written > 0) {
        offset_ += written;
      }
      return written;
    }
  }

  /**
   * Write a message with sequence and addressing (for profiles that support it).
   */
  template <FramedMessage T>
  size_t write(const T& msg, uint8_t seq, uint8_t sys_id = 0, uint8_t comp_id = 0) {
    static_assert(Config::has_seq || Config::has_sys_id || Config::has_comp_id,
                  "This profile does not support sequence/addressing fields");
    size_t written =
        FrameEncoderWithCrc<Config>::encode(buffer_ + offset_, capacity_ - offset_, msg, seq, sys_id, comp_id);
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
using ProfileStandardReader = BufferReader<ProfileStandardConfig>;
using ProfileStandardWriter = BufferWriter<ProfileStandardConfig>;
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
 *   Config - The frame profile configuration (e.g., ProfileStandardConfig)
 *   BufferSize - Size of internal buffer for partial messages (default: 1024)
 *   GetMessageInfoFn - Type of the message-info callback (the generated
 *     get_message_info, a function pointer or a lambda). Every profile with a
 *     checksum or without a length field needs it.
 *
 * The Profile*AccumulatingReader aliases below take the generated function directly:
 *   ProfileStandardAccumulatingReader reader(mypkg::get_message_info);
 *
 * Buffer mode usage:
 *   reader.add_data(chunk1, chunk1_size);
 *   FrameMsgInfo result;
 *   while (reader.try_next(result)) {
 *     if (result.valid) { ... }   // else a corrupt frame was skipped
 *   }
 *
 * Stream mode usage:
 *   while (receiving) {
 *     if (auto result = reader.push_byte(read_byte())) {
 *       // Process complete message
 *     }
 *   }
 */
template <typename Config, size_t BufferSize = 1024, typename GetMessageInfoFn = std::nullptr_t>
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
   *
   * Only usable without a callback for profiles that carry no checksum: the
   * checksum of a CRC profile includes per-message magic bytes that only the
   * message-info callback can supply, so such a reader would reject every real
   * frame. Pass the callback (see the class comment) for CRC profiles.
   */
  AccumulatingReader()
      : internal_data_len_(0),
        bytes_appended_to_internal_(0),
        expected_frame_size_(0),
        state_(State::Idle),
        current_buffer_(nullptr),
        current_size_(0),
        current_offset_(0),
        get_message_info_{},
        diagnostics_{},
        last_seq_(0),
        last_seq_valid_(false) {
    // A default-constructed function pointer is null, which is no better than no callback.
    static_assert(!Config::has_crc || std::is_class_v<GetMessageInfoFn>,
                  "A CRC profile needs the message-info callback (its checksum includes per-message "
                  "magic bytes): construct the reader with it, e.g. "
                  "ProfileStandardAccumulatingReader reader(mypkg::get_message_info)");
  }

  /**
   * Construct an AccumulatingReader with message info callback (for minimal profiles).
   */
  explicit AccumulatingReader(GetMessageInfoFn get_message_info)
      : internal_data_len_(0),
        bytes_appended_to_internal_(0),
        expected_frame_size_(0),
        state_(State::Idle),
        current_buffer_(nullptr),
        current_size_(0),
        current_offset_(0),
        get_message_info_(get_message_info),
        diagnostics_{},
        last_seq_(0),
        last_seq_valid_(false) {}

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
    bytes_appended_to_internal_ = 0;

    // If we have partial data in internal buffer, try to complete it
    if (internal_data_len_ > 0) {
      // Append as much as needed/possible from new buffer to internal buffer
      size_t space_available = BufferSize - internal_data_len_;
      size_t bytes_to_copy = (size < space_available) ? size : space_available;

      std::memcpy(internal_buffer_ + internal_data_len_, buffer, bytes_to_copy);
      internal_data_len_ += bytes_to_copy;
      bytes_appended_to_internal_ = bytes_to_copy;
    }
  }

  template <typename Buffer>
  void add_data(const Buffer& buffer) {
    add_data(buffer.data(), buffer.size());
  }

  /**
   * Parse the next frame (buffer mode).
   * Returns FrameMsgInfo with valid=true if successful, valid=false if no more complete frames.
   *
   * When returning a message completed from a partial, msg_data points to the internal buffer.
   * When returning a message from the current buffer, msg_data points into that buffer.
   *
   * System frames are returned (is_system) only after set_deliver_system_frames(true);
   * otherwise they are counted (cnt_system_frames) and skipped.
   */
  FrameMsgInfo next() {
    for (;;) {
      FrameMsgInfo result = next_frame();
      if (result.valid && result.is_system) {
        count_system_frame(result);
        if (!deliver_system_frames_) continue;
      }
      return result;
    }
  }

  /** Return system frames from next()/push_byte() instead of only counting them. */
  void set_deliver_system_frames(bool deliver) { deliver_system_frames_ = deliver; }

 private:
  using Sys = typename Config::SystemConfig;
  static constexpr bool kSystemFrames = Config::supports_system_frames;

  static size_t find_start(const uint8_t* buf, size_t begin, size_t end) {
    return system_frames::find_start(buf, begin, end, Config::computed_start_byte1(), kSystemFrames,
                                     Sys::computed_start_byte1());
  }

  static bool is_system_frame(const uint8_t* data, size_t size) {
    if constexpr (kSystemFrames) {
      return system_frames::is_system_start<Sys>(data, size);
    } else {
      (void)data; (void)size;
      return false;
    }
  }

  void count_system_frame(const FrameMsgInfo& frame) {
    diagnostics_.cnt_system_frames++;
    if (last_sys_seq_valid_ && frame.sequence != static_cast<uint8_t>(last_sys_seq_ + 1)) {
      diagnostics_.cnt_seq_gaps++;
    }
    last_sys_seq_ = frame.sequence;
    last_sys_seq_valid_ = true;
  }

  FrameMsgInfo next_frame() {
    if (state_ != State::BufferMode) {
      return with_diagnostics(FrameMsgInfo());
    }

    // Full-wedge escape: new data arrived but nothing could be appended because
    // the internal buffer is full. The buffered bytes can never complete —
    // discard them so parsing continues from the current buffer instead of
    // stalling forever.
    if (internal_data_len_ > 0 && current_offset_ == 0 &&
        bytes_appended_to_internal_ == 0 && current_size_ > current_offset_) {
      diagnostics_.cnt_sync_recoveries++;
      diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(internal_data_len_);
      internal_data_len_ = 0;
      expected_frame_size_ = 0;
      // fall through to current-buffer parsing below
    }

    // First, try to complete a partial message from the internal buffer.
    // partial_len = bytes in internal buffer that came from a PREVIOUS add_data call
    // (i.e., before bytes_appended_to_internal_ were added this call).
    if (internal_data_len_ > 0 && current_offset_ == 0) {
      size_t partial_len = internal_data_len_ - bytes_appended_to_internal_;
      FrameMsgInfo result = parse_frame(internal_buffer_, internal_data_len_);

      if (result.valid) {
        record_frame_diagnostics(internal_buffer_, true);
        // How many bytes from the *current* buffer were consumed to complete this frame
        size_t bytes_from_current = result.frame_size > partial_len ? result.frame_size - partial_len : 0;
        current_offset_ = bytes_from_current;
        internal_data_len_ = 0;
        bytes_appended_to_internal_ = 0;
        expected_frame_size_ = 0;
        return with_diagnostics(result);
      }

      if (result.frame_size > 0) {
        // Complete but invalid frame (CRC failure) — count it and skip
        diagnostics_.cnt_crc_failures++;
        diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(result.frame_size);
        diagnostics_.cnt_sync_recoveries++;
        record_frame_diagnostics(internal_buffer_, false);
        size_t bytes_from_current = result.frame_size > partial_len ? result.frame_size - partial_len : 0;
        current_offset_ = bytes_from_current;
        internal_data_len_ = 0;
        bytes_appended_to_internal_ = 0;
        expected_frame_size_ = 0;
        return with_diagnostics(result);
      }

      // Garbage prefix saved as a partial (WaitingForStart), or a frame that
      // can never complete because its claimed size exceeds the internal
      // buffer (still collecting with the buffer full): resync inside the
      // internal buffer instead of waiting forever.
      if (result.status == FrameMsgStatus::WaitingForStart ||
          internal_data_len_ >= BufferSize ||
          claims_oversize_frame(internal_buffer_, internal_data_len_)) {
        size_t discard = internal_data_len_;
        if (result.is_system && result.status == FrameMsgStatus::WaitingForStart) {
          diagnostics_.cnt_system_rejected++;
        }
        if constexpr (Config::num_start_bytes >= 1) {
          discard = find_start(internal_buffer_, 1, internal_data_len_);
        } else {
          // No start bytes (e.g. IPC): advance one byte and retry.
          discard = 1;
        }
        diagnostics_.cnt_sync_recoveries++;
        diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(discard);
        size_t keep = internal_data_len_ - discard;
        if (keep > 0) {
          std::memmove(internal_buffer_, internal_buffer_ + discard, keep);
        }
        // Only the portion of the discard that reached into this cycle's
        // appended bytes reduces the appended count.
        if (discard > partial_len) {
          bytes_appended_to_internal_ -= (discard - partial_len);
        }
        internal_data_len_ = keep;
        FrameMsgInfo r;
        r.status = FrameMsgStatus::SyncRecovery;
        r.frame_size = discard;
        return with_diagnostics(r);
      }

      // Still not enough data for a complete message — wait for next add_data()
      return with_diagnostics(FrameMsgInfo());
    }

    // Parse from current buffer
    if (current_buffer_ == nullptr || current_offset_ >= current_size_) {
      return with_diagnostics(FrameMsgInfo());
    }

    FrameMsgInfo result = parse_frame(current_buffer_ + current_offset_, current_size_ - current_offset_);

    if (result.valid && result.frame_size > 0) {
      record_frame_diagnostics(current_buffer_ + current_offset_, true);
      current_offset_ += result.frame_size;
      return with_diagnostics(result);
    }

    if (!result.valid && result.frame_size > 0) {
      // Complete frame with bad CRC — count it, skip it, let caller call next() again
      diagnostics_.cnt_crc_failures++;
      diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(result.frame_size);
      diagnostics_.cnt_sync_recoveries++;
      record_frame_diagnostics(current_buffer_ + current_offset_, false);
      current_offset_ += result.frame_size;
      return with_diagnostics(result);
    }

    if (result.status == FrameMsgStatus::WaitingForStart) {
      // Head byte is not a start byte — scan forward for the next one,
      // reporting SyncRecovery so try_next() keeps draining.
      size_t old_offset = current_offset_;
      if (result.is_system) {
        diagnostics_.cnt_system_rejected++;
      }
      if constexpr (Config::num_start_bytes >= 1) {
        current_offset_ = find_start(current_buffer_, current_offset_ + 1, current_size_);
      } else {
        // No start bytes (e.g. IPC profile): advance one byte and retry so a
        // single unknown msg_id doesn't discard the rest of the buffer.
        current_offset_ += 1;
      }
      FrameMsgInfo r;
      r.status = FrameMsgStatus::SyncRecovery;
      r.frame_size = current_offset_ - old_offset;
      diagnostics_.cnt_sync_recoveries++;
      diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(r.frame_size);
      return with_diagnostics(r);
    }

    // A header that claims a frame larger than the internal buffer can never complete:
    // resync past its start byte now rather than buffering good data behind it.
    if constexpr (Config::num_start_bytes >= 1) {
      if (claims_oversize_frame(current_buffer_ + current_offset_, current_size_ - current_offset_)) {
        size_t old_offset = current_offset_;
        current_offset_ = find_start(current_buffer_, current_offset_ + 1, current_size_);
        FrameMsgInfo r;
        r.status = FrameMsgStatus::SyncRecovery;
        r.frame_size = current_offset_ - old_offset;
        diagnostics_.cnt_sync_recoveries++;
        diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(r.frame_size);
        return with_diagnostics(r);
      }
    }

    // Collecting — save remaining bytes to internal buffer for next add_data() call
    size_t remaining = current_size_ - current_offset_;
    if (remaining > 0 && remaining < BufferSize) {
      std::memcpy(internal_buffer_, current_buffer_ + current_offset_, remaining);
      internal_data_len_ = remaining;
      bytes_appended_to_internal_ = 0;
      current_offset_ = current_size_;
    } else if (remaining >= BufferSize) {
      // Partial too large to buffer — discard with diagnostics.
      diagnostics_.cnt_sync_recoveries++;
      diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(remaining);
      current_offset_ = current_size_;
    }

    return with_diagnostics(FrameMsgInfo());
  }

 public:
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
    FrameMsgInfo result = push_byte_inner(byte);
    if (result.valid && result.is_system) {
      count_system_frame(result);
      if (!deliver_system_frames_) {
        FrameMsgInfo hidden;
        hidden.status = FrameMsgStatus::WaitingForStart;
        return with_diagnostics(hidden);
      }
    }
    return result;
  }

 private:
  FrameMsgInfo push_byte_inner(uint8_t byte) {
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
        if constexpr (kSystemFrames) {
          if (collecting_system_) return handle_collecting_header<Sys>(byte);
        }
        return handle_collecting_header<Config>(byte);

      case State::CollectingPayload:
        return handle_collecting_payload(byte);

      default:
        state_ = State::LookingForStart1;
        return with_diagnostics(FrameMsgInfo());
    }
  }

 public:
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
   * Try to parse the next frame. Returns true while forward progress is made
   * (valid frame, CRC-failed frame, or skipped resync bytes). Returns false
   * when the current buffer is exhausted or only a trailing partial is pending.
   *
   * Canonical drain loop:
   *   FrameMsgInfo f;
   *   while (reader.try_next(f)) {
   *       if (f.valid) handle(f);  // else CrcFailure or SyncRecovery
   *   }
   *   if (reader.has_partial()) { // incomplete frame; feed more data }
   */
  bool try_next(FrameMsgInfo& out) {
    out = next();
    return out.valid || out.frame_size > 0;
  }

  /**
   * Get current parser state (for debugging).
   */
  State state() const { return state_; }

  /**
   * Return a snapshot of the current diagnostic counters.
   *
   * Counters accumulate over the reader's lifetime. Call reset_diagnostics()
   * to clear them.
   */
  ParserDiagnostics diagnostics() const { return diagnostics_; }

  /**
   * Reset all diagnostic counters to zero.
   */
  void reset_diagnostics() {
    diagnostics_ = ParserDiagnostics{};
  }

  /**
   * Reset the reader, clearing any partial message data.
   */
  void reset() {
    internal_data_len_ = 0;
    bytes_appended_to_internal_ = 0;
    expected_frame_size_ = 0;
    state_ = State::Idle;
    current_buffer_ = nullptr;
    current_size_ = 0;
    current_offset_ = 0;
    last_seq_ = 0;
    last_seq_valid_ = false;
    last_sys_seq_ = 0;
    last_sys_seq_valid_ = false;
    collecting_system_ = false;
  }

 private:
  // True when the header at the start of data claims a frame that cannot fit in the internal
  // buffer (typically a corrupted length field). Only profiles with a length field carry such a
  // claim.
  static bool claims_oversize_frame(const uint8_t* data, size_t size) {
    if (is_system_frame(data, size)) return claims_oversize_frame_as<Sys>(data, size);
    return claims_oversize_frame_as<Config>(data, size);
  }

  template <typename C>
  static bool claims_oversize_frame_as(const uint8_t* data, size_t size) {
    if constexpr (!C::has_length) {
      (void)data; (void)size;
      return false;
    } else {
      if (size < C::header_size) return false;
      size_t off = C::num_start_bytes;
      if constexpr (C::has_seq) off++;
      if constexpr (C::has_sys_id) off++;
      if constexpr (C::has_comp_id) off++;
      size_t payload_len = (C::length_bytes == 1)
          ? data[off]
          : static_cast<size_t>(data[off] | (data[off + 1] << 8));
      return C::overhead + payload_len > BufferSize;
    }
  }

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
      bool is_user = byte == Config::computed_start_byte1();
      if (is_user || (kSystemFrames && byte == Sys::computed_start_byte1())) {
        internal_buffer_[0] = byte;
        internal_data_len_ = 1;
        // A Basic header shares its first byte with system frames: the second byte
        // decides. A Tiny header's only byte decides now.
        collecting_system_ = !is_user;

        if constexpr (Config::num_start_bytes == 1) {
          state_ = State::CollectingHeader;
        } else {
          state_ = State::LookingForStart2;
        }
      } else {
        // No start byte found yet
        FrameMsgInfo r;
        r.status = FrameMsgStatus::WaitingForStart;
        return with_diagnostics(r);
      }
    }
    FrameMsgInfo r;
    r.status = FrameMsgStatus::Collecting;
    return with_diagnostics(r);
  }

  FrameMsgInfo handle_looking_for_start2(uint8_t byte) {
    if (byte == Config::computed_start_byte2() || (kSystemFrames && byte == Sys::computed_start_byte2())) {
      internal_buffer_[internal_data_len_++] = byte;
      collecting_system_ = byte != Config::computed_start_byte2();
      state_ = State::CollectingHeader;
    } else if (byte == Config::computed_start_byte1()) {
      // Might be start of new frame - restart
      internal_buffer_[0] = byte;
      internal_data_len_ = 1;
      // Stay in LookingForStart2
    } else {
      // Invalid byte - lost sync; discard and restart
      diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(internal_data_len_ + 1);
      diagnostics_.cnt_sync_recoveries++;
      state_ = State::LookingForStart1;
      internal_data_len_ = 0;
      FrameMsgInfo r;
      r.status = FrameMsgStatus::SyncRecovery;
      return with_diagnostics(r);
    }
    FrameMsgInfo r;
    r.status = FrameMsgStatus::Collecting;
    return with_diagnostics(r);
  }

  // C is the profile of the frame being collected: Config, or Sys for a system frame.
  template <typename C>
  FrameMsgInfo handle_collecting_header(uint8_t byte) {
    constexpr bool system = !std::is_same_v<C, Config>;
    if (internal_data_len_ >= BufferSize) {
      // Buffer overflow - reset
      diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(internal_data_len_ + 1);
      diagnostics_.cnt_sync_recoveries++;
      state_ = State::LookingForStart1;
      internal_data_len_ = 0;
      FrameMsgInfo r;
      r.status = FrameMsgStatus::SyncRecovery;
      return with_diagnostics(r);
    }

    internal_buffer_[internal_data_len_++] = byte;

    // Check if we have enough header bytes to determine frame size
    if (internal_data_len_ >= C::header_size) {
      if constexpr (system) {
        if (system_frames::header_check<Sys>(internal_buffer_, internal_data_len_) != 1) {
          // Not a system frame after all: resync without collecting a payload.
          diagnostics_.cnt_system_rejected++;
          diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(internal_data_len_);
          diagnostics_.cnt_sync_recoveries++;
          state_ = State::LookingForStart1;
          internal_data_len_ = 0;
          collecting_system_ = false;
          FrameMsgInfo r;
          r.status = FrameMsgStatus::SyncRecovery;
          return with_diagnostics(r);
        }
      }
      // For minimal profiles, we need the callback to determine length
      if constexpr (!C::has_length && !C::has_crc) {
        // msg_id is at header_size - 1 position
        uint8_t msg_id = internal_buffer_[Config::header_size - 1];
        if (get_message_info_) {
          auto info = lookup_message_info(msg_id);
          if (info) {
            size_t msg_len = info.size;
            expected_frame_size_ = Config::header_size + msg_len;

            if (expected_frame_size_ > BufferSize) {
              // Too large - reset
              diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(internal_data_len_);
              diagnostics_.cnt_sync_recoveries++;
              state_ = State::LookingForStart1;
              internal_data_len_ = 0;
              FrameMsgInfo r;
              r.status = FrameMsgStatus::SyncRecovery;
              return with_diagnostics(r);
            }

          if (msg_len == 0) {
            // Zero-length message - complete!
            FrameMsgInfo result(true, msg_id, 0, expected_frame_size_, internal_buffer_ + Config::header_size);
            state_ = State::LookingForStart1;
            internal_data_len_ = 0;
            expected_frame_size_ = 0;
            return with_diagnostics(result);
          }

          state_ = State::CollectingPayload;
        } else {
          // Unknown message ID - reset
          diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(internal_data_len_);
          diagnostics_.cnt_sync_recoveries++;
          state_ = State::LookingForStart1;
          internal_data_len_ = 0;
          FrameMsgInfo r;
          r.status = FrameMsgStatus::SyncRecovery;
          return with_diagnostics(r);
        }
      } else {
        // Unknown message ID - reset
        diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(internal_data_len_);
        diagnostics_.cnt_sync_recoveries++;
        state_ = State::LookingForStart1;
        internal_data_len_ = 0;
        FrameMsgInfo r;
        r.status = FrameMsgStatus::SyncRecovery;
        return with_diagnostics(r);
      }
    } else {
      // Calculate payload length from header
      size_t len_offset = C::num_start_bytes;

      // Skip seq, sys_id, comp_id if present
      if constexpr (C::has_seq) len_offset++;
      if constexpr (C::has_sys_id) len_offset++;
      if constexpr (C::has_comp_id) len_offset++;

      size_t payload_len = 0;
      if constexpr (C::has_length) {
        if constexpr (C::length_bytes == 1) {
          payload_len = internal_buffer_[len_offset];
        } else {
          payload_len = internal_buffer_[len_offset] | (static_cast<size_t>(internal_buffer_[len_offset + 1]) << 8);
        }
      }

      // Check for length mismatch against expected message struct size
      if constexpr (C::has_length && !system) {
        if (get_message_info_) {
          uint16_t full_msg_id = 0;
          if constexpr (Config::has_pkg_id) {
            full_msg_id = static_cast<uint16_t>(internal_buffer_[Config::header_size - 2]) << 8;
          }
          full_msg_id |= internal_buffer_[Config::header_size - 1];
          auto info = lookup_message_info(full_msg_id);
          // Valid frames may carry anywhere from min_size (variable messages /
          // truncated extensions) up to size bytes — only count outside that range.
          if (info && (payload_len > info.size || payload_len < info.min_size)) {
            diagnostics_.cnt_len_errors++;
          }
        }
      }

      expected_frame_size_ = C::overhead + payload_len;

      if (expected_frame_size_ > BufferSize) {
        // Too large - reset
        diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(internal_data_len_);
        diagnostics_.cnt_sync_recoveries++;
        state_ = State::LookingForStart1;
        internal_data_len_ = 0;
        FrameMsgInfo r;
        r.status = FrameMsgStatus::SyncRecovery;
        return with_diagnostics(r);
      }

      // Check if we already have the complete frame
      if (internal_data_len_ >= expected_frame_size_) {
        return with_diagnostics(validate_and_return());
      }

      state_ = State::CollectingPayload;
    }
    }

    FrameMsgInfo r;
    r.status = FrameMsgStatus::Collecting;
    return with_diagnostics(r);
  }

  FrameMsgInfo handle_collecting_payload(uint8_t byte) {
    if (internal_data_len_ >= BufferSize) {
    // Buffer overflow - reset
    diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(internal_data_len_ + 1);
    diagnostics_.cnt_sync_recoveries++;
    state_ = State::LookingForStart1;
    internal_data_len_ = 0;
    FrameMsgInfo r;
    r.status = FrameMsgStatus::SyncRecovery;
    return with_diagnostics(r);
    }

    internal_buffer_[internal_data_len_++] = byte;

    if (internal_data_len_ >= expected_frame_size_) {
      return with_diagnostics(validate_and_return());
    }

    FrameMsgInfo r;
    r.status = FrameMsgStatus::Collecting;
    return with_diagnostics(r);
  }

  FrameMsgInfo handle_minimal_msg_id(uint8_t msg_id) {
    if (get_message_info_) {
      auto info = lookup_message_info(msg_id);
      if (info) {
        size_t msg_len = info.size;
        expected_frame_size_ = Config::header_size + msg_len;

        if (expected_frame_size_ > BufferSize) {
          diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(internal_data_len_);
          diagnostics_.cnt_sync_recoveries++;
          state_ = State::LookingForStart1;
          internal_data_len_ = 0;
          FrameMsgInfo r;
          r.status = FrameMsgStatus::SyncRecovery;
          return with_diagnostics(r);
        }

        if (msg_len == 0) {
          // Zero-length message - complete!
          FrameMsgInfo result(true, msg_id, 0, expected_frame_size_, internal_buffer_ + Config::header_size);
          state_ = State::LookingForStart1;
          internal_data_len_ = 0;
          expected_frame_size_ = 0;
          return with_diagnostics(result);
        }

        state_ = State::CollectingPayload;
        FrameMsgInfo r;
        r.status = FrameMsgStatus::Collecting;
        return with_diagnostics(r);
      } else {
        // Unknown msg_id - stay looking for valid start
        diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(internal_data_len_);
        diagnostics_.cnt_sync_recoveries++;
        state_ = State::LookingForStart1;
        internal_data_len_ = 0;
        FrameMsgInfo r;
        r.status = FrameMsgStatus::SyncRecovery;
        return with_diagnostics(r);
      }
    } else {
      // Unknown msg_id - stay looking for valid start
      diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(internal_data_len_);
      diagnostics_.cnt_sync_recoveries++;
      state_ = State::LookingForStart1;
      internal_data_len_ = 0;
      FrameMsgInfo r;
      r.status = FrameMsgStatus::SyncRecovery;
      return with_diagnostics(r);
    }
  }

  FrameMsgInfo validate_and_return() {
    FrameMsgInfo result = parse_frame(internal_buffer_, internal_data_len_);

    // Reset state for next message
    state_ = State::LookingForStart1;
    internal_data_len_ = 0;
    expected_frame_size_ = 0;
    bool was_system = collecting_system_;
    collecting_system_ = false;

    if (result.valid && result.is_system) {
      // sequence gaps of system frames are counted by count_system_frame()
    } else if (result.valid) {
      // Check for sequence gap on profiles that carry a sequence number
      if constexpr (Config::has_seq) {
        uint8_t seq = internal_buffer_[Config::num_start_bytes];
        if (last_seq_valid_) {
          uint8_t expected_seq = static_cast<uint8_t>(last_seq_ + 1);
          if (seq != expected_seq) {
            diagnostics_.cnt_seq_gaps++;
          }
        }
        last_seq_ = seq;
        last_seq_valid_ = true;
      }
    } else {
      // Invalid frame — count CRC failures and sync recoveries
      if (Config::has_crc || was_system) {
        diagnostics_.cnt_crc_failures++;
        result.status = FrameMsgStatus::CrcFailure;
      }
      diagnostics_.cnt_failed_bytes += static_cast<uint32_t>(result.frame_size);
      diagnostics_.cnt_sync_recoveries++;
    }

    return result;
  }

  FrameMsgInfo with_diagnostics(FrameMsgInfo result) {
    result.diagnostics = &diagnostics_;
    return result;
  }

  /**
   * Record per-frame diagnostics for a complete frame consumed in buffer mode,
   * matching the stream-mode (push_byte) counter semantics:
   *  - cnt_len_errors when the header length is outside [min_size, size]
   *  - cnt_seq_gaps on valid frames for profiles that carry a sequence number
   * frame_start points at the first byte of the frame (start bytes included).
   */
  void record_frame_diagnostics(const uint8_t* frame_start, bool valid) {
    if (is_system_frame(frame_start, Config::num_start_bytes)) {
      return;  // counted by count_system_frame(); the header was already validated
    }
    if constexpr (Config::has_length) {
      if (get_message_info_) {
        size_t len_offset = Config::num_start_bytes;
        if constexpr (Config::has_seq) len_offset++;
        if constexpr (Config::has_sys_id) len_offset++;
        if constexpr (Config::has_comp_id) len_offset++;
        size_t payload_len;
        if constexpr (Config::length_bytes == 1) {
          payload_len = frame_start[len_offset];
        } else {
          payload_len = frame_start[len_offset] | (static_cast<size_t>(frame_start[len_offset + 1]) << 8);
        }
        uint16_t full_msg_id = 0;
        if constexpr (Config::has_pkg_id) {
          full_msg_id = static_cast<uint16_t>(frame_start[Config::header_size - 2]) << 8;
        }
        full_msg_id |= frame_start[Config::header_size - 1];
        auto info = lookup_message_info(full_msg_id);
        if (info && (payload_len > info.size || payload_len < info.min_size)) {
          diagnostics_.cnt_len_errors++;
        }
      }
    }
    if (valid) {
      if constexpr (Config::has_seq) {
        uint8_t seq = frame_start[Config::num_start_bytes];
        if (last_seq_valid_) {
          if (seq != static_cast<uint8_t>(last_seq_ + 1)) {
            diagnostics_.cnt_seq_gaps++;
          }
        }
        last_seq_ = seq;
        last_seq_valid_ = true;
      }
    }
  }

  /*=========================================================================
   * Shared Parsing
   *=========================================================================*/

  FrameMsgInfo parse_frame(const uint8_t* buffer, size_t size) const {
    if constexpr (kSystemFrames) {
      if (system_frames::is_system_start<Sys>(buffer, size)) {
        return system_frames::parse<Sys>(buffer, size);
      }
    }
    if constexpr (Config::has_length || Config::has_crc) {
      return BufferParserWithCrc<Config>::parse(buffer, size, get_message_info_);
    } else {
      return BufferParserMinimal<Config>::parse(buffer, size, get_message_info_);
    }
  }

  /*=========================================================================
   * Member Variables
   *=========================================================================*/

  uint8_t internal_buffer_[BufferSize];       // Internal buffer for partial messages (stack allocated)
  size_t internal_data_len_;                  // Current data length in internal buffer
  size_t bytes_appended_to_internal_;         // Bytes copied from current buffer into internal buffer this add_data() call
  size_t expected_frame_size_;                // Expected total frame size (0 if not yet known)
  State state_;                          // Current parser state

  // Buffer mode state
  const uint8_t* current_buffer_;  // Current external buffer being processed
  size_t current_size_;            // Size of current external buffer
  size_t current_offset_;          // Current position in external buffer

  /**
   * Look up message info through the configured callback. With the default
   * (std::nullptr_t) callback type there is nothing to call, so return an empty,
   * invalid MessageInfo; this keeps readers for profiles that carry a length
   * (which need no callback) compilable.
   */
  auto lookup_message_info(uint16_t id) const {
    if constexpr (std::is_same_v<GetMessageInfoFn, std::nullptr_t>) {
      (void)id;
      return MessageInfo();
    } else {
      return get_message_info_(id);
    }
  }

  GetMessageInfoFn get_message_info_;

  // Diagnostic counters (stream mode)
  ParserDiagnostics diagnostics_;
  uint8_t last_seq_;        // Last seen sequence number
  bool last_seq_valid_;     // Whether last_seq_ holds a valid value

  // System frames: delivered or only counted; their sequence numbers are tracked separately.
  bool deliver_system_frames_ = false;
  uint8_t last_sys_seq_ = 0;
  bool last_sys_seq_valid_ = false;
  bool collecting_system_ = false;  // stream mode: the frame being collected is a system frame
};

/**
 * Factory function to create AccumulatingReader with proper template deduction
 * for minimal profiles that require a get_message_info callable.
 *
 * Usage:
 *   auto reader = make_accumulating_reader<ProfileSensorConfig>(get_message_info);
 */
template <typename Config, size_t BufferSize = 1024, typename GetMessageInfoFn>
auto make_accumulating_reader(GetMessageInfoFn get_message_info) {
  return AccumulatingReader<Config, BufferSize, GetMessageInfoFn>(get_message_info);
}

/**
 * Factory function to create BufferReader with proper template deduction
 * for minimal profiles that require a get_message_info callable.
 *
 * Usage:
 *   auto reader = make_buffer_reader<ProfileSensorConfig>(buffer, size, get_message_info);
 */
template <typename Config, typename GetMessageInfoFn>
auto make_buffer_reader(const uint8_t* buffer, size_t size, GetMessageInfoFn get_message_info) {
  return BufferReader<Config, GetMessageInfoFn>(buffer, size, get_message_info);
}

/* Type of the generated get_message_info functions (structframe::<pkg>::get_message_info). */
using MessageInfoFn = MessageInfo (*)(uint16_t);

/* AccumulatingReader for a profile, constructed with the generated message-info function:
 *   ProfileStandardAccumulatingReader reader(mypkg::get_message_info);
 *   ProfileReader<ProfileBulkConfig, 4096> big_reader(mypkg::get_message_info);
 * The aliases use a 1024-byte buffer. */
template <typename Config, size_t BufferSize = 1024>
using ProfileReader = AccumulatingReader<Config, BufferSize, MessageInfoFn>;

using ProfileStandardAccumulatingReader = ProfileReader<ProfileStandardConfig>;
using ProfileSensorAccumulatingReader = ProfileReader<ProfileSensorConfig>;
using ProfileIPCAccumulatingReader = ProfileReader<ProfileIPCConfig>;
using ProfileBulkAccumulatingReader = ProfileReader<ProfileBulkConfig>;
using ProfileNetworkAccumulatingReader = ProfileReader<ProfileNetworkConfig>;

}  // namespace structframe
