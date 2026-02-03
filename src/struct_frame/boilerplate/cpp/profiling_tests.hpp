/* Struct-frame boilerplate: Profiling and verification tests */
/*
 * This file provides built-in profiling and verification tests for the struct-frame SDK.
 * These tests can be run on the target system to:
 * 1. Profile encode/decode performance with packed vs aligned memory access
 * 2. Verify round-trip encode/decode correctness
 *
 * Usage:
 *   // Time profiling - measure 1000 iterations of encode/decode
 *   auto start = get_time();
 *   ProfilingTests::encode_packed_test<MyMessage>(buffer, sizeof(buffer));
 *   auto elapsed = get_time() - start;
 *
 *   // Round-trip verification
 *   bool success = ProfilingTests::verify_roundtrip<MyMessage, ProfileStandard>(msg, buffer, sizeof(buffer));
 */

#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <new>
#include <type_traits>

#include "frame_base.hpp"
#include "frame_profiles.hpp"

namespace FrameParsers {
namespace ProfilingTests {

// Number of iterations for profiling tests
static constexpr size_t PROFILE_ITERATIONS = 1000;

// Volatile sink to prevent compiler optimizations
// This is used to ensure the compiler doesn't optimize away our test code
inline volatile uint8_t g_sink = 0;

/**
 * Force the compiler to not optimize out a value.
 * Uses volatile writes to prevent dead code elimination.
 */
template <typename T>
inline void do_not_optimize(const T& value) {
  const volatile T* vp = &value;
  g_sink ^= static_cast<uint8_t>(reinterpret_cast<uintptr_t>(vp) & 0xFF);
}

/**
 * Force the compiler to not optimize out buffer contents.
 * Computes a simple checksum and stores to volatile sink.
 */
inline void do_not_optimize_buffer(const uint8_t* buffer, size_t size) {
  uint8_t sum = 0;
  for (size_t i = 0; i < size; i++) {
    sum ^= buffer[i];
  }
  g_sink ^= sum;
}

/*===========================================================================
 * Time Profiling Tests
 * These tests run PROFILE_ITERATIONS encode/decode operations.
 * The user is responsible for timing before and after each call.
 *===========================================================================*/

/**
 * Result structure for profiling tests
 */
struct ProfileResult {
  size_t iterations;     // Number of iterations completed
  size_t bytes_total;    // Total bytes processed
  bool success;          // True if all iterations succeeded
};

/**
 * Encode a packed struct message PROFILE_ITERATIONS times.
 * Uses direct memory copy for packed struct encoding.
 *
 * @tparam T Message type derived from MessageBase (must be packed)
 * @tparam Config Frame profile configuration
 * @param msg Reference to message to encode
 * @param buffer Output buffer
 * @param buffer_size Size of output buffer
 * @return ProfileResult with iteration count, bytes processed, and success status
 */
template <typename T, typename Config>
ProfileResult encode_packed_test(const T& msg, uint8_t* buffer, size_t buffer_size) {
  static_assert(std::is_base_of_v<MessageBase<T, T::MSG_ID, T::MAX_SIZE, T::MAGIC1, T::MAGIC2>, T>,
                "Message type must derive from MessageBase");

  ProfileResult result{0, 0, true};

  for (size_t i = 0; i < PROFILE_ITERATIONS; i++) {
    size_t written = 0;

    // Use the appropriate encoder based on config
    if constexpr (Config::has_length || Config::has_crc) {
      written = FrameEncoderWithCrc<Config>::encode(buffer, buffer_size, msg);
    } else {
      written = FrameEncoderMinimal<Config>::encode(buffer, buffer_size, msg);
    }

    if (written == 0) {
      result.success = false;
      break;
    }

    result.bytes_total += written;
    result.iterations++;

    // Prevent compiler from optimizing away the encode
    do_not_optimize_buffer(buffer, written);
  }

  return result;
}

/**
 * Decode a packed struct message PROFILE_ITERATIONS times.
 * Uses direct memory copy for packed struct deserialization.
 *
 * @tparam T Message type derived from MessageBase (must be packed)
 * @tparam Config Frame profile configuration
 * @tparam GetMsgInfo Function type for get_message_info callback
 * @param buffer Input buffer containing encoded frame
 * @param buffer_size Size of encoded frame
 * @param get_message_info Callback to get message info for parsing
 * @return ProfileResult with iteration count, bytes processed, and success status
 */
template <typename T, typename Config, typename GetMsgInfo>
ProfileResult decode_packed_test(const uint8_t* buffer, size_t buffer_size, GetMsgInfo get_message_info) {
  static_assert(std::is_base_of_v<MessageBase<T, T::MSG_ID, T::MAX_SIZE, T::MAGIC1, T::MAGIC2>, T>,
                "Message type must derive from MessageBase");

  ProfileResult result{0, 0, true};

  for (size_t i = 0; i < PROFILE_ITERATIONS; i++) {
    FrameMsgInfo frame_info;

    // Parse the frame
    if constexpr (Config::has_length || Config::has_crc) {
      frame_info = BufferParserWithCrc<Config>::parse(buffer, buffer_size, get_message_info);
    } else {
      frame_info = BufferParserMinimal<Config>::parse(buffer, buffer_size, get_message_info);
    }

    if (!frame_info.valid) {
      result.success = false;
      break;
    }

    // Deserialize the message using direct copy (packed)
    T decoded_msg{};
    size_t bytes_read = decoded_msg.deserialize(frame_info);

    if (bytes_read == 0) {
      result.success = false;
      break;
    }

    result.bytes_total += bytes_read;
    result.iterations++;

    // Prevent compiler from optimizing away the decode
    do_not_optimize(decoded_msg);
  }

  return result;
}

/**
 * Encode a message with aligned memory access PROFILE_ITERATIONS times.
 * This version copies to an aligned buffer first, then encodes.
 *
 * @tparam T Message type derived from MessageBase
 * @tparam Config Frame profile configuration
 * @param msg Reference to message to encode
 * @param buffer Output buffer
 * @param buffer_size Size of output buffer
 * @return ProfileResult with iteration count, bytes processed, and success status
 */
template <typename T, typename Config>
ProfileResult encode_aligned_test(const T& msg, uint8_t* buffer, size_t buffer_size) {
  static_assert(std::is_base_of_v<MessageBase<T, T::MSG_ID, T::MAX_SIZE, T::MAGIC1, T::MAGIC2>, T>,
                "Message type must derive from MessageBase");

  ProfileResult result{0, 0, true};

  // Create an aligned copy of the message
  alignas(alignof(std::max_align_t)) uint8_t aligned_storage[sizeof(T)];

  for (size_t i = 0; i < PROFILE_ITERATIONS; i++) {
    // Copy to aligned storage first
    std::memcpy(aligned_storage, &msg, sizeof(T));

    // Encode from aligned storage
    const T* aligned_msg = reinterpret_cast<const T*>(aligned_storage);
    size_t written = 0;

    if constexpr (Config::has_length || Config::has_crc) {
      written = FrameEncoderWithCrc<Config>::encode(buffer, buffer_size, *aligned_msg);
    } else {
      written = FrameEncoderMinimal<Config>::encode(buffer, buffer_size, *aligned_msg);
    }

    if (written == 0) {
      result.success = false;
      break;
    }

    result.bytes_total += written;
    result.iterations++;

    // Prevent compiler from optimizing away the encode
    do_not_optimize_buffer(buffer, written);
  }

  return result;
}

/**
 * Decode a message with aligned memory access PROFILE_ITERATIONS times.
 * This version deserializes to an aligned buffer.
 *
 * @tparam T Message type derived from MessageBase
 * @tparam Config Frame profile configuration
 * @tparam GetMsgInfo Function type for get_message_info callback
 * @param buffer Input buffer containing encoded frame
 * @param buffer_size Size of encoded frame
 * @param get_message_info Callback to get message info for parsing
 * @return ProfileResult with iteration count, bytes processed, and success status
 */
template <typename T, typename Config, typename GetMsgInfo>
ProfileResult decode_aligned_test(const uint8_t* buffer, size_t buffer_size, GetMsgInfo get_message_info) {
  static_assert(std::is_base_of_v<MessageBase<T, T::MSG_ID, T::MAX_SIZE, T::MAGIC1, T::MAGIC2>, T>,
                "Message type must derive from MessageBase");

  ProfileResult result{0, 0, true};

  // Aligned storage for decoded message
  alignas(alignof(std::max_align_t)) uint8_t aligned_storage[sizeof(T)];

  for (size_t i = 0; i < PROFILE_ITERATIONS; i++) {
    FrameMsgInfo frame_info;

    // Parse the frame
    if constexpr (Config::has_length || Config::has_crc) {
      frame_info = BufferParserWithCrc<Config>::parse(buffer, buffer_size, get_message_info);
    } else {
      frame_info = BufferParserMinimal<Config>::parse(buffer, buffer_size, get_message_info);
    }

    if (!frame_info.valid) {
      result.success = false;
      break;
    }

    // Deserialize to aligned storage
    T* aligned_msg = reinterpret_cast<T*>(aligned_storage);
    new (aligned_msg) T{};  // Placement new for proper initialization
    size_t bytes_read = aligned_msg->deserialize(frame_info);

    if (bytes_read == 0) {
      result.success = false;
      break;
    }

    result.bytes_total += bytes_read;
    result.iterations++;

    // Prevent compiler from optimizing away the decode
    do_not_optimize(*aligned_msg);
  }

  return result;
}

/*===========================================================================
 * Round-Trip Verification Tests
 * These tests encode a message, decode it, and verify the result matches.
 *===========================================================================*/

/**
 * Verify round-trip encoding and decoding of a message.
 * Encodes the message, decodes it, and compares the result.
 *
 * @tparam T Message type derived from MessageBase
 * @tparam Config Frame profile configuration
 * @tparam GetMsgInfo Function type for get_message_info callback
 * @param msg Message to verify
 * @param buffer Working buffer for encoding
 * @param buffer_size Size of working buffer
 * @param get_message_info Callback to get message info for parsing
 * @return true if round-trip succeeded and decoded message matches original
 */
template <typename T, typename Config, typename GetMsgInfo>
bool verify_roundtrip(const T& msg, uint8_t* buffer, size_t buffer_size, GetMsgInfo get_message_info) {
  static_assert(std::is_base_of_v<MessageBase<T, T::MSG_ID, T::MAX_SIZE, T::MAGIC1, T::MAGIC2>, T>,
                "Message type must derive from MessageBase");

  // Encode the message
  size_t written = 0;
  if constexpr (Config::has_length || Config::has_crc) {
    written = FrameEncoderWithCrc<Config>::encode(buffer, buffer_size, msg);
  } else {
    written = FrameEncoderMinimal<Config>::encode(buffer, buffer_size, msg);
  }

  if (written == 0) {
    return false;
  }

  // Parse the frame
  FrameMsgInfo frame_info;
  if constexpr (Config::has_length || Config::has_crc) {
    frame_info = BufferParserWithCrc<Config>::parse(buffer, written, get_message_info);
  } else {
    frame_info = BufferParserMinimal<Config>::parse(buffer, written, get_message_info);
  }

  if (!frame_info.valid) {
    return false;
  }

  // Verify message ID
  if (frame_info.msg_id != T::MSG_ID) {
    return false;
  }

  // Deserialize the message
  T decoded_msg{};
  size_t bytes_read = decoded_msg.deserialize(frame_info);

  if (bytes_read == 0) {
    return false;
  }

  // Compare using byte-by-byte comparison (works for any message type)
  return std::memcmp(&msg, &decoded_msg, sizeof(T)) == 0;
}

/**
 * Run full profiling suite for a message type.
 * Returns a summary of encode/decode performance for both packed and aligned access.
 *
 * @tparam T Message type derived from MessageBase
 * @tparam Config Frame profile configuration
 * @tparam GetMsgInfo Function type for get_message_info callback
 * @param msg Message to profile
 * @param buffer Working buffer
 * @param buffer_size Size of working buffer
 * @param get_message_info Callback to get message info for parsing
 * @return Array of 4 ProfileResults: [encode_packed, decode_packed, encode_aligned, decode_aligned]
 */
template <typename T, typename Config, typename GetMsgInfo>
struct ProfilingSuiteResult {
  ProfileResult encode_packed;
  ProfileResult decode_packed;
  ProfileResult encode_aligned;
  ProfileResult decode_aligned;
  bool roundtrip_verified;
};

template <typename T, typename Config, typename GetMsgInfo>
ProfilingSuiteResult<T, Config, GetMsgInfo> run_profiling_suite(const T& msg, uint8_t* buffer, size_t buffer_size,
                                                                GetMsgInfo get_message_info) {
  ProfilingSuiteResult<T, Config, GetMsgInfo> result;

  // First verify round-trip works
  result.roundtrip_verified = verify_roundtrip<T, Config>(msg, buffer, buffer_size, get_message_info);

  if (!result.roundtrip_verified) {
    // If round-trip fails, profiling results will be invalid
    result.encode_packed = {0, 0, false};
    result.decode_packed = {0, 0, false};
    result.encode_aligned = {0, 0, false};
    result.decode_aligned = {0, 0, false};
    return result;
  }

  // Run encode profiling tests
  result.encode_packed = encode_packed_test<T, Config>(msg, buffer, buffer_size);

  // Re-encode for decode tests (ensure buffer has valid frame)
  size_t frame_size = 0;
  if constexpr (Config::has_length || Config::has_crc) {
    frame_size = FrameEncoderWithCrc<Config>::encode(buffer, buffer_size, msg);
  } else {
    frame_size = FrameEncoderMinimal<Config>::encode(buffer, buffer_size, msg);
  }

  // Run decode profiling tests
  result.decode_packed = decode_packed_test<T, Config>(buffer, frame_size, get_message_info);

  // Run aligned tests
  result.encode_aligned = encode_aligned_test<T, Config>(msg, buffer, buffer_size);

  // Re-encode for aligned decode test
  if constexpr (Config::has_length || Config::has_crc) {
    frame_size = FrameEncoderWithCrc<Config>::encode(buffer, buffer_size, msg);
  } else {
    frame_size = FrameEncoderMinimal<Config>::encode(buffer, buffer_size, msg);
  }

  result.decode_aligned = decode_aligned_test<T, Config>(buffer, frame_size, get_message_info);

  return result;
}

}  // namespace ProfilingTests
}  // namespace FrameParsers
