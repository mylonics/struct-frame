/* Struct-frame boilerplate: Profiling and verification tests */
/*
 * This file provides built-in profiling and verification tests for the struct-frame SDK.
 * These tests can be run on the target system to:
 * 1. Profile encode/decode performance comparing packed vs unpacked struct access
 * 2. Verify round-trip encode/decode correctness
 *
 * The main purpose is to characterize memory access penalties when using packed structs
 * (which is the core approach of struct-frame) vs unpacked/naturally-aligned structs.
 * These penalties can vary across different platforms.
 *
 * Usage:
 *   // Define an unpacked version of your message for comparison
 *   struct MyMessageUnpacked {
 *     uint32_t field1;
 *     uint8_t field2;
 *     uint16_t field3;
 *     // ... same fields as MyMessage but without packing
 *   };
 *
 *   // Time profiling - measure 1000 iterations of encode/decode
 *   auto start = get_time();
 *   ProfilingTests::encode_packed_test<MyMessage>(msg, buffer, sizeof(buffer));
 *   auto packed_time = get_time() - start;
 *
 *   start = get_time();
 *   ProfilingTests::encode_unpacked_test<MyMessage, MyMessageUnpacked>(msg, unpacked_msg, buffer, sizeof(buffer));
 *   auto unpacked_time = get_time() - start;
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
 *
 * The tests compare:
 * - Packed struct: Direct access to packed (#pragma pack(1)) structs
 * - Unpacked struct: Access to naturally-aligned structs (compiler default)
 *
 * This helps characterize any memory access penalties from unaligned access
 * that may occur on different platforms when using packed structs.
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
 * Uses direct memory access to the packed struct.
 *
 * @tparam T Message type derived from MessageBase (must be packed with #pragma pack(1))
 * @tparam Config Frame profile configuration
 * @param msg Reference to packed message to encode
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
 * Deserializes directly into a packed struct.
 *
 * @tparam T Message type derived from MessageBase (must be packed with #pragma pack(1))
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

    // Deserialize the message directly into packed struct
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
 * Encode from an unpacked struct PROFILE_ITERATIONS times.
 * This version reads fields from an unpacked (naturally-aligned) struct
 * and copies them to the packed struct for encoding.
 *
 * The unpacked struct should have the same fields as the packed struct
 * but without #pragma pack(1), allowing the compiler to add natural alignment.
 *
 * @tparam TPacked Packed message type derived from MessageBase
 * @tparam TUnpacked Unpacked version of the message (same fields, no packing)
 * @tparam Config Frame profile configuration
 * @param packed_msg Reference to packed message (destination for copy)
 * @param unpacked_msg Reference to unpacked message (source for copy)
 * @param buffer Output buffer
 * @param buffer_size Size of output buffer
 * @param copy_func Function to copy fields from unpacked to packed: void(TPacked&, const TUnpacked&)
 * @return ProfileResult with iteration count, bytes processed, and success status
 */
template <typename TPacked, typename TUnpacked, typename Config, typename CopyFunc>
ProfileResult encode_unpacked_test(TPacked& packed_msg, const TUnpacked& unpacked_msg, 
                                   uint8_t* buffer, size_t buffer_size, CopyFunc copy_func) {
  static_assert(std::is_base_of_v<MessageBase<TPacked, TPacked::MSG_ID, TPacked::MAX_SIZE, TPacked::MAGIC1, TPacked::MAGIC2>, TPacked>,
                "Packed message type must derive from MessageBase");

  ProfileResult result{0, 0, true};

  for (size_t i = 0; i < PROFILE_ITERATIONS; i++) {
    // Copy from unpacked to packed struct (simulates reading from unpacked struct)
    copy_func(packed_msg, unpacked_msg);
    
    size_t written = 0;

    // Encode the packed message
    if constexpr (Config::has_length || Config::has_crc) {
      written = FrameEncoderWithCrc<Config>::encode(buffer, buffer_size, packed_msg);
    } else {
      written = FrameEncoderMinimal<Config>::encode(buffer, buffer_size, packed_msg);
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
 * Decode into an unpacked struct PROFILE_ITERATIONS times.
 * This version deserializes into a packed struct and then copies
 * the fields to an unpacked (naturally-aligned) struct.
 *
 * @tparam TPacked Packed message type derived from MessageBase
 * @tparam TUnpacked Unpacked version of the message (same fields, no packing)
 * @tparam Config Frame profile configuration
 * @tparam GetMsgInfo Function type for get_message_info callback
 * @tparam CopyFunc Function type for copying: void(TUnpacked&, const TPacked&)
 * @param buffer Input buffer containing encoded frame
 * @param buffer_size Size of encoded frame
 * @param get_message_info Callback to get message info for parsing
 * @param copy_func Function to copy fields from packed to unpacked: void(TUnpacked&, const TPacked&)
 * @return ProfileResult with iteration count, bytes processed, and success status
 */
template <typename TPacked, typename TUnpacked, typename Config, typename GetMsgInfo, typename CopyFunc>
ProfileResult decode_unpacked_test(const uint8_t* buffer, size_t buffer_size, 
                                   GetMsgInfo get_message_info, CopyFunc copy_func) {
  static_assert(std::is_base_of_v<MessageBase<TPacked, TPacked::MSG_ID, TPacked::MAX_SIZE, TPacked::MAGIC1, TPacked::MAGIC2>, TPacked>,
                "Packed message type must derive from MessageBase");

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

    // Deserialize into packed struct first
    TPacked decoded_packed{};
    size_t bytes_read = decoded_packed.deserialize(frame_info);

    if (bytes_read == 0) {
      result.success = false;
      break;
    }

    // Copy from packed to unpacked struct (simulates writing to unpacked struct)
    TUnpacked decoded_unpacked{};
    copy_func(decoded_unpacked, decoded_packed);

    result.bytes_total += bytes_read;
    result.iterations++;

    // Prevent compiler from optimizing away the decode
    do_not_optimize(decoded_unpacked);
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

/*===========================================================================
 * Profiling Suite
 * Convenience functions for running multiple profiling tests
 *===========================================================================*/

/**
 * Result structure for packed-only profiling suite
 */
struct PackedProfilingResult {
  ProfileResult encode_packed;
  ProfileResult decode_packed;
  bool roundtrip_verified;
};

/**
 * Run packed struct profiling tests.
 * Tests encode/decode performance using the packed struct directly.
 *
 * @tparam T Message type derived from MessageBase (packed with #pragma pack(1))
 * @tparam Config Frame profile configuration
 * @tparam GetMsgInfo Function type for get_message_info callback
 * @param msg Message to profile
 * @param buffer Working buffer
 * @param buffer_size Size of working buffer
 * @param get_message_info Callback to get message info for parsing
 * @return PackedProfilingResult with encode/decode results
 */
template <typename T, typename Config, typename GetMsgInfo>
PackedProfilingResult run_packed_profiling(const T& msg, uint8_t* buffer, size_t buffer_size,
                                           GetMsgInfo get_message_info) {
  PackedProfilingResult result;

  // First verify round-trip works
  result.roundtrip_verified = verify_roundtrip<T, Config>(msg, buffer, buffer_size, get_message_info);

  if (!result.roundtrip_verified) {
    result.encode_packed = {0, 0, false};
    result.decode_packed = {0, 0, false};
    return result;
  }

  // Run encode profiling test
  result.encode_packed = encode_packed_test<T, Config>(msg, buffer, buffer_size);

  // Re-encode for decode test (ensure buffer has valid frame)
  size_t frame_size = 0;
  if constexpr (Config::has_length || Config::has_crc) {
    frame_size = FrameEncoderWithCrc<Config>::encode(buffer, buffer_size, msg);
  } else {
    frame_size = FrameEncoderMinimal<Config>::encode(buffer, buffer_size, msg);
  }

  // Run decode profiling test
  result.decode_packed = decode_packed_test<T, Config>(buffer, frame_size, get_message_info);

  return result;
}

/**
 * Result structure for full packed vs unpacked profiling comparison
 */
struct PackedVsUnpackedResult {
  ProfileResult encode_packed;
  ProfileResult decode_packed;
  ProfileResult encode_unpacked;
  ProfileResult decode_unpacked;
  bool roundtrip_verified;
};

/**
 * Run full packed vs unpacked profiling comparison.
 * Compares performance of:
 * - Packed: Direct access to packed struct (struct-frame default)
 * - Unpacked: Access through naturally-aligned struct with field-by-field copy
 *
 * This helps characterize memory access penalties on different platforms.
 *
 * @tparam TPacked Packed message type derived from MessageBase
 * @tparam TUnpacked Unpacked version of the message (same fields, no #pragma pack)
 * @tparam Config Frame profile configuration
 * @tparam GetMsgInfo Function type for get_message_info callback
 * @tparam CopyToPackedFunc Function type: void(TPacked&, const TUnpacked&)
 * @tparam CopyToUnpackedFunc Function type: void(TUnpacked&, const TPacked&)
 * @param packed_msg Packed message to profile
 * @param unpacked_msg Unpacked message with same field values
 * @param buffer Working buffer
 * @param buffer_size Size of working buffer
 * @param get_message_info Callback to get message info for parsing
 * @param copy_to_packed Function to copy from unpacked to packed
 * @param copy_to_unpacked Function to copy from packed to unpacked
 * @return PackedVsUnpackedResult with all profiling results
 */
template <typename TPacked, typename TUnpacked, typename Config, typename GetMsgInfo,
          typename CopyToPackedFunc, typename CopyToUnpackedFunc>
PackedVsUnpackedResult run_packed_vs_unpacked_profiling(
    TPacked& packed_msg, const TUnpacked& unpacked_msg,
    uint8_t* buffer, size_t buffer_size,
    GetMsgInfo get_message_info,
    CopyToPackedFunc copy_to_packed,
    CopyToUnpackedFunc copy_to_unpacked) {

  PackedVsUnpackedResult result;

  // First verify round-trip works
  result.roundtrip_verified = verify_roundtrip<TPacked, Config>(packed_msg, buffer, buffer_size, get_message_info);

  if (!result.roundtrip_verified) {
    result.encode_packed = {0, 0, false};
    result.decode_packed = {0, 0, false};
    result.encode_unpacked = {0, 0, false};
    result.decode_unpacked = {0, 0, false};
    return result;
  }

  // Run packed encode test
  result.encode_packed = encode_packed_test<TPacked, Config>(packed_msg, buffer, buffer_size);

  // Re-encode for decode tests
  size_t frame_size = 0;
  if constexpr (Config::has_length || Config::has_crc) {
    frame_size = FrameEncoderWithCrc<Config>::encode(buffer, buffer_size, packed_msg);
  } else {
    frame_size = FrameEncoderMinimal<Config>::encode(buffer, buffer_size, packed_msg);
  }

  // Run packed decode test
  result.decode_packed = decode_packed_test<TPacked, Config>(buffer, frame_size, get_message_info);

  // Run unpacked encode test
  result.encode_unpacked = encode_unpacked_test<TPacked, TUnpacked, Config>(
      packed_msg, unpacked_msg, buffer, buffer_size, copy_to_packed);

  // Re-encode for unpacked decode test
  if constexpr (Config::has_length || Config::has_crc) {
    frame_size = FrameEncoderWithCrc<Config>::encode(buffer, buffer_size, packed_msg);
  } else {
    frame_size = FrameEncoderMinimal<Config>::encode(buffer, buffer_size, packed_msg);
  }

  // Run unpacked decode test
  result.decode_unpacked = decode_unpacked_test<TPacked, TUnpacked, Config>(
      buffer, frame_size, get_message_info, copy_to_unpacked);

  return result;
}

}  // namespace ProfilingTests
}  // namespace FrameParsers
