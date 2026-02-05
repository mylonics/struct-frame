/* Struct-frame boilerplate: Generic profiling (no std, no heap) */
/*
 * This file provides hardcoded packed and unpacked message types for profiling
 * struct-frame encode/decode performance. No std library, no heap allocations.
 *
 * Usage:
 *   #include "profiling_generic.hpp"
 *
 *   GenericTests::init_all_messages();
 *   auto enc_result = GenericTests::encode_packed();
 *   GenericTests::do_not_optimize_packed_buffer();
 *   auto dec_result = GenericTests::decode_packed();
 *   GenericTests::do_not_optimize_decoded_packed();
 *   bool ok = GenericTests::verify_packed_results();
 */

#pragma once

#include <cstddef>
#include <cstdint>

#include "frame_base.hpp"
#include "frame_profiles.hpp"

namespace GenericTests {

// Volatile sink to prevent compiler optimizations (no std)
inline volatile uint8_t g_generic_sink = 0;

/**
 * Force the compiler to not optimize out buffer contents.
 * Computes a simple checksum and stores to volatile sink.
 */
inline void do_not_optimize_buffer(const uint8_t* buffer, size_t size) {
  uint8_t sum = 0;
  for (size_t i = 0; i < size; i++) {
    sum ^= buffer[i];
  }
  g_generic_sink ^= sum;
}

// =============================================================================
// Memory copy helper (no std::memcpy dependency)
// =============================================================================
inline void mem_copy(void* dest, const void* src, size_t size) {
  uint8_t* d = static_cast<uint8_t*>(dest);
  const uint8_t* s = static_cast<const uint8_t*>(src);
  for (size_t i = 0; i < size; i++) {
    d[i] = s[i];
  }
}

// =============================================================================
// Hardcoded Packed Message (struct-frame style)
// Wire format size: 40 bytes (1+4+2+4+4+8+1+16)
// =============================================================================
#pragma pack(push, 1)
struct TestMessagePacked : public FrameParsers::MessageBase<TestMessagePacked, 0x01, 40, 0xAA, 0x55> {
  uint8_t msg_type;
  uint32_t sequence;
  int16_t sensor_value;
  int32_t counter;
  float temperature;
  double pressure;
  uint8_t status;
  char label[16];

  size_t serialize(uint8_t* buffer, size_t max_size) const {
    if (max_size < sizeof(*this)) return 0;
    mem_copy(buffer, this, sizeof(*this));
    return sizeof(*this);
  }

  size_t deserialize(const FrameParsers::FrameMsgInfo& info) {
    if (info.msg_len < sizeof(*this)) return 0;
    mem_copy(this, info.msg_data, sizeof(*this));
    return sizeof(*this);
  }
};
#pragma pack(pop)

// =============================================================================
// Hardcoded Unpacked Message (natural alignment)
// Wire format size matches packed struct (40 bytes)
// Uses IS_VARIABLE=true so encoder calls serialize() instead of memcpy(data())
// =============================================================================
struct TestMessageUnpacked : public FrameParsers::MessageBase<TestMessageUnpacked, 0x01, 40, 0xAA, 0x55> {
  // Mark as variable so encoder uses serialize() instead of raw memcpy
  static constexpr bool IS_VARIABLE = true;

  uint8_t msg_type;
  uint32_t sequence;
  int16_t sensor_value;
  int32_t counter;
  float temperature;
  double pressure;
  uint8_t status;
  char label[16];

  // Wire format size (same as packed struct)
  static constexpr size_t WIRE_SIZE = 40;

  // Required for variable messages - return serialized size
  constexpr size_t serialized_size() const { return WIRE_SIZE; }

  // Serialize directly to wire buffer (field-by-field, no intermediate packed struct)
  size_t serialize(uint8_t* buffer) const {
    size_t offset = 0;

    buffer[offset] = msg_type;
    offset += 1;
    mem_copy(buffer + offset, &sequence, 4);
    offset += 4;
    mem_copy(buffer + offset, &sensor_value, 2);
    offset += 2;
    mem_copy(buffer + offset, &counter, 4);
    offset += 4;
    mem_copy(buffer + offset, &temperature, 4);
    offset += 4;
    mem_copy(buffer + offset, &pressure, 8);
    offset += 8;
    buffer[offset] = status;
    offset += 1;
    mem_copy(buffer + offset, label, 16);
    offset += 16;

    return WIRE_SIZE;
  }

  // Deserialize directly from wire buffer (field-by-field, no intermediate packed struct)
  size_t deserialize(const FrameParsers::FrameMsgInfo& info) {
    if (info.msg_len < WIRE_SIZE) return 0;
    const uint8_t* data = info.msg_data;
    size_t offset = 0;

    msg_type = data[offset];
    offset += 1;
    mem_copy(&sequence, data + offset, 4);
    offset += 4;
    mem_copy(&sensor_value, data + offset, 2);
    offset += 2;
    mem_copy(&counter, data + offset, 4);
    offset += 4;
    mem_copy(&temperature, data + offset, 4);
    offset += 4;
    mem_copy(&pressure, data + offset, 8);
    offset += 8;
    status = data[offset];
    offset += 1;
    mem_copy(label, data + offset, 16);
    offset += 16;

    return WIRE_SIZE;
  }
};

// =============================================================================
// Initialize a packed message with test data
// =============================================================================
inline void init_packed_message(TestMessagePacked& msg, size_t index) {
  msg.msg_type = static_cast<uint8_t>(index & 0xFF);
  msg.sequence = static_cast<uint32_t>(index);
  msg.sensor_value = static_cast<int16_t>(index * 10);
  msg.counter = static_cast<int32_t>(index * 100);
  msg.temperature = static_cast<float>(index) * 0.5f + 20.0f;
  msg.pressure = static_cast<double>(index) * 0.1 + 1000.0;
  msg.status = static_cast<uint8_t>(index % 4);

  // Simple label initialization without snprintf
  const char* prefix = "Msg_";
  size_t j = 0;
  while (prefix[j] && j < sizeof(msg.label) - 1) {
    msg.label[j] = prefix[j];
    j++;
  }
  // Add index as simple decimal (variable digits)
  size_t temp = index;
  char digits[16];
  size_t digit_count = 0;
  do {
    digits[digit_count++] = '0' + (temp % 10);
    temp /= 10;
  } while (temp > 0 && digit_count < 16);

  // Reverse digits into label
  while (digit_count > 0 && j < sizeof(msg.label) - 1) {
    msg.label[j++] = digits[--digit_count];
  }
  // Null terminate and fill rest
  while (j < sizeof(msg.label)) {
    msg.label[j++] = '\0';
  }
}

inline void copy_to_unpacked(TestMessageUnpacked& unpacked, const TestMessagePacked& packed) {
  unpacked.msg_type = packed.msg_type;
  unpacked.sequence = packed.sequence;
  unpacked.sensor_value = packed.sensor_value;
  unpacked.counter = packed.counter;
  unpacked.temperature = packed.temperature;
  unpacked.pressure = packed.pressure;
  unpacked.status = packed.status;
  mem_copy(unpacked.label, packed.label, sizeof(unpacked.label));
}

// =============================================================================
// Message info function for parsing
// =============================================================================
inline FrameParsers::MessageInfo get_test_message_info(uint16_t msg_id) {
  if (msg_id == TestMessagePacked::MSG_ID) {
    return {sizeof(TestMessagePacked), TestMessagePacked::MAGIC1, TestMessagePacked::MAGIC2};
  }
  return {0, 0, 0};
}

// =============================================================================
// Encode/Decode Result Structure
// =============================================================================
struct EncodeDecodeResult {
  bool success;
  size_t total_bytes;
  size_t failed_at;  // Index where failure occurred (if any)
};

// =============================================================================
// Test Configuration and Buffers
// =============================================================================

// Default test configuration
static constexpr size_t DEFAULT_ITERATIONS = 400;
static constexpr size_t DEFAULT_RUNS = 1000;
static constexpr size_t DEFAULT_BUFFER_SIZE = 128 * DEFAULT_ITERATIONS;

// Default profile configuration
using DefaultConfig = FrameParsers::ProfileStandardConfig;

// Static test buffers and message arrays
inline uint8_t* get_packed_buffer() {
  static uint8_t buffer[DEFAULT_BUFFER_SIZE];
  return buffer;
}

inline uint8_t* get_unpacked_buffer() {
  static uint8_t buffer[DEFAULT_BUFFER_SIZE];
  return buffer;
}

inline TestMessagePacked* get_packed_messages() {
  static TestMessagePacked messages[DEFAULT_ITERATIONS];
  return messages;
}

inline TestMessageUnpacked* get_unpacked_messages() {
  static TestMessageUnpacked messages[DEFAULT_ITERATIONS];
  return messages;
}

inline TestMessagePacked* get_decoded_packed() {
  static TestMessagePacked messages[DEFAULT_ITERATIONS];
  return messages;
}

inline TestMessageUnpacked* get_decoded_unpacked() {
  static TestMessageUnpacked messages[DEFAULT_ITERATIONS];
  return messages;
}

/**
 * Initialize all test messages with test data.
 * @param count Number of messages to initialize (default: DEFAULT_ITERATIONS)
 */
inline void init_all_messages(size_t count = DEFAULT_ITERATIONS) {
  TestMessagePacked* packed = get_packed_messages();
  TestMessageUnpacked* unpacked = get_unpacked_messages();
  for (size_t i = 0; i < count; i++) {
    init_packed_message(packed[i], i);
    copy_to_unpacked(unpacked[i], packed[i]);
  }
}

// =============================================================================
// Convenience Functions - use default buffers/arrays
// =============================================================================

// Track encoded sizes for decode functions
inline size_t& get_packed_encoded_size() {
  static size_t size = 0;
  return size;
}

inline size_t& get_unpacked_encoded_size() {
  static size_t size = 0;
  return size;
}

/**
 * Encode all packed messages using default buffers.
 * Stores encoded size for later decode.
 */
inline EncodeDecodeResult encode_packed() {
  uint8_t* buffer = get_packed_buffer();
  const TestMessagePacked* messages = get_packed_messages();
  size_t offset = 0;
  for (size_t i = 0; i < DEFAULT_ITERATIONS; i++) {
    size_t written = FrameParsers::FrameEncoderWithCrc<DefaultConfig>::encode(
        buffer + offset, DEFAULT_BUFFER_SIZE - offset, messages[i]);
    if (written == 0) {
      return {false, offset, i};
    }
    offset += written;
  }
  get_packed_encoded_size() = offset;
  return {true, offset, DEFAULT_ITERATIONS};
}

/**
 * Encode all unpacked messages using default buffers.
 * Serializes directly from unpacked struct to wire buffer (no intermediate copy).
 * Stores encoded size for later decode.
 */
inline EncodeDecodeResult encode_unpacked() {
  uint8_t* buffer = get_unpacked_buffer();
  const TestMessageUnpacked* messages = get_unpacked_messages();
  size_t offset = 0;
  for (size_t i = 0; i < DEFAULT_ITERATIONS; i++) {
    size_t written = FrameParsers::FrameEncoderWithCrc<DefaultConfig>::encode(
        buffer + offset, DEFAULT_BUFFER_SIZE - offset, messages[i]);
    if (written == 0) {
      return {false, offset, i};
    }
    offset += written;
  }
  get_unpacked_encoded_size() = offset;
  return {true, offset, DEFAULT_ITERATIONS};
}

/**
 * Decode packed buffer to packed messages using default buffers.
 * Uses size from previous encode_packed() call.
 */
inline EncodeDecodeResult decode_packed() {
  const uint8_t* buffer = get_packed_buffer();
  size_t buffer_size = get_packed_encoded_size();
  TestMessagePacked* messages = get_decoded_packed();
  size_t offset = 0;
  for (size_t i = 0; i < DEFAULT_ITERATIONS; i++) {
    auto frame_info = FrameParsers::BufferParserWithCrc<DefaultConfig>::parse(buffer + offset, buffer_size - offset,
                                                                              get_test_message_info);
    if (!frame_info.valid) {
      return {false, offset, i};
    }
    size_t bytes_read = messages[i].deserialize(frame_info);
    if (bytes_read == 0) {
      return {false, offset, i};
    }
    offset += frame_info.frame_size;
  }
  return {true, offset, DEFAULT_ITERATIONS};
}

/**
 * Decode unpacked buffer to unpacked messages using default buffers.
 * Deserializes directly from wire buffer to unpacked struct (no intermediate copy).
 * Uses size from previous encode_unpacked() call.
 */
inline EncodeDecodeResult decode_unpacked() {
  const uint8_t* buffer = get_unpacked_buffer();
  size_t buffer_size = get_unpacked_encoded_size();
  TestMessageUnpacked* messages = get_decoded_unpacked();
  size_t offset = 0;
  for (size_t i = 0; i < DEFAULT_ITERATIONS; i++) {
    auto frame_info = FrameParsers::BufferParserWithCrc<DefaultConfig>::parse(buffer + offset, buffer_size - offset,
                                                                              get_test_message_info);
    if (!frame_info.valid) {
      return {false, offset, i};
    }
    size_t bytes_read = messages[i].deserialize(frame_info);
    if (bytes_read == 0) {
      return {false, offset, i};
    }
    offset += frame_info.frame_size;
  }
  return {true, offset, DEFAULT_ITERATIONS};
}

// =============================================================================
// Verification
// =============================================================================

inline bool verify_packed(const TestMessagePacked& original, const TestMessagePacked& decoded) {
  return original.sequence == decoded.sequence && original.counter == decoded.counter &&
         original.msg_type == decoded.msg_type;
}

inline bool verify_unpacked(const TestMessageUnpacked& original, const TestMessageUnpacked& decoded) {
  return original.sequence == decoded.sequence && original.counter == decoded.counter &&
         original.msg_type == decoded.msg_type;
}

/**
 * Verify decoded packed messages match originals.
 */
inline bool verify_packed_results() {
  const TestMessagePacked* original = get_packed_messages();
  const TestMessagePacked* decoded = get_decoded_packed();
  for (size_t i = 0; i < DEFAULT_ITERATIONS; i++) {
    if (!verify_packed(original[i], decoded[i])) {
      return false;
    }
  }
  return true;
}

/**
 * Verify decoded unpacked messages match originals.
 */
inline bool verify_unpacked_results() {
  const TestMessageUnpacked* original = get_unpacked_messages();
  const TestMessageUnpacked* decoded = get_decoded_unpacked();
  for (size_t i = 0; i < DEFAULT_ITERATIONS; i++) {
    if (!verify_unpacked(original[i], decoded[i])) {
      return false;
    }
  }
  return true;
}

/**
 * Prevent compiler from optimizing away packed buffer.
 * Call after encode_packed() to ensure the encode isn't optimized out.
 */
inline void do_not_optimize_packed_buffer() { do_not_optimize_buffer(get_packed_buffer(), get_packed_encoded_size()); }

/**
 * Prevent compiler from optimizing away unpacked buffer.
 * Call after encode_unpacked() to ensure the encode isn't optimized out.
 */
inline void do_not_optimize_unpacked_buffer() {
  do_not_optimize_buffer(get_unpacked_buffer(), get_unpacked_encoded_size());
}

/**
 * Prevent compiler from optimizing away decoded packed messages.
 * Call after decode_packed() to ensure the decode isn't optimized out.
 */
inline void do_not_optimize_decoded_packed() {
  do_not_optimize_buffer(reinterpret_cast<uint8_t*>(get_decoded_packed()),
                         sizeof(TestMessagePacked) * DEFAULT_ITERATIONS);
}

/**
 * Prevent compiler from optimizing away decoded unpacked messages.
 * Call after decode_unpacked() to ensure the decode isn't optimized out.
 */
inline void do_not_optimize_decoded_unpacked() {
  do_not_optimize_buffer(reinterpret_cast<uint8_t*>(get_decoded_unpacked()),
                         sizeof(TestMessageUnpacked) * DEFAULT_ITERATIONS);
}

// =============================================================================
// Profiling Test Results Structure
// =============================================================================
struct ProfilingResults {
  bool success;                      // Overall test success
  size_t total_messages;             // Total messages encoded/decoded
  double packed_encode_seconds;      // Total time for packed encode
  double unpacked_encode_seconds;    // Total time for unpacked encode
  double packed_decode_seconds;      // Total time for packed decode
  double unpacked_decode_seconds;    // Total time for unpacked decode
  double packed_encode_per_msg_seconds;    // Time per message for packed encode
  double unpacked_encode_per_msg_seconds;  // Time per message for unpacked encode
  double packed_decode_per_msg_seconds;    // Time per message for packed decode
  double unpacked_decode_per_msg_seconds;  // Time per message for unpacked decode
  double encode_diff_percent;        // Percentage difference (positive = packed slower)
  double decode_diff_percent;        // Percentage difference (positive = packed slower)
  double total_diff_percent;         // Overall percentage difference
};

// =============================================================================
// Run Profiling Test
// =============================================================================
/**
 * Run the complete profiling test with custom timing function.
 * 
 * @param get_current_time_seconds Function that returns current time in seconds.
 *                                  Should be monotonic and have sufficient resolution.
 * @param num_runs Number of times to run the test (default: DEFAULT_RUNS = 1000).
 * @return ProfilingResults struct with timing measurements and percentage differences.
 * 
 * Example usage:
 *   auto results = GenericTests::run_test([]() { return std::chrono::duration<double>(
 *       std::chrono::high_resolution_clock::now().time_since_epoch()).count(); });
 */
inline ProfilingResults run_test(double (*get_current_time_seconds)(), size_t num_runs = DEFAULT_RUNS) {
  ProfilingResults results = {};
  
  // Initialize all test messages once
  init_all_messages();
  
  // Accumulators for timing across all runs
  double total_packed_encode_time = 0.0;
  double total_unpacked_encode_time = 0.0;
  double total_packed_decode_time = 0.0;
  double total_unpacked_decode_time = 0.0;
  
  // Run the test num_runs times
  for (size_t run = 0; run < num_runs; run++) {
    // ---- ENCODE TESTS ----
    
    // Encode packed messages
    double packed_enc_start = get_current_time_seconds();
    EncodeDecodeResult packed_enc = encode_packed();
    do_not_optimize_packed_buffer();
    double packed_enc_end = get_current_time_seconds();
    total_packed_encode_time += (packed_enc_end - packed_enc_start);
    
    // Encode unpacked messages
    double unpacked_enc_start = get_current_time_seconds();
    EncodeDecodeResult unpacked_enc = encode_unpacked();
    do_not_optimize_unpacked_buffer();
    double unpacked_enc_end = get_current_time_seconds();
    total_unpacked_encode_time += (unpacked_enc_end - unpacked_enc_start);
    
    // Check encode success
    if (!packed_enc.success || !unpacked_enc.success) {
      results.success = false;
      return results;
    }
    
    // ---- DECODE TESTS ----
    
    // Decode packed messages
    double packed_dec_start = get_current_time_seconds();
    EncodeDecodeResult packed_dec = decode_packed();
    do_not_optimize_decoded_packed();
    double packed_dec_end = get_current_time_seconds();
    total_packed_decode_time += (packed_dec_end - packed_dec_start);
    
    // Decode unpacked messages
    double unpacked_dec_start = get_current_time_seconds();
    EncodeDecodeResult unpacked_dec = decode_unpacked();
    do_not_optimize_decoded_unpacked();
    double unpacked_dec_end = get_current_time_seconds();
    total_unpacked_decode_time += (unpacked_dec_end - unpacked_dec_start);
    
    // Check decode success
    if (!packed_dec.success || !unpacked_dec.success) {
      results.success = false;
      return results;
    }
    
    // ---- VERIFY RESULTS (only on first run to save time) ----
    if (run == 0) {
      bool packed_verified = verify_packed_results();
      bool unpacked_verified = verify_unpacked_results();
      
      if (!packed_verified || !unpacked_verified) {
        results.success = false;
        return results;
      }
    }
  }
  
  // Store total timing results
  results.packed_encode_seconds = total_packed_encode_time;
  results.unpacked_encode_seconds = total_unpacked_encode_time;
  results.packed_decode_seconds = total_packed_decode_time;
  results.unpacked_decode_seconds = total_unpacked_decode_time;
  
  // Calculate total messages processed
  results.total_messages = DEFAULT_ITERATIONS * num_runs;
  
  // Calculate per-message timings
  results.packed_encode_per_msg_seconds = total_packed_encode_time / results.total_messages;
  results.unpacked_encode_per_msg_seconds = total_unpacked_encode_time / results.total_messages;
  results.packed_decode_per_msg_seconds = total_packed_decode_time / results.total_messages;
  results.unpacked_decode_per_msg_seconds = total_unpacked_decode_time / results.total_messages;
  
  // ---- CALCULATE PERCENTAGE DIFFERENCES ----
  
  // Calculate encode difference (positive = packed slower)
  results.encode_diff_percent = results.unpacked_encode_seconds > 0
      ? ((results.packed_encode_seconds - results.unpacked_encode_seconds) / 
         results.unpacked_encode_seconds) * 100.0
      : 0.0;
  
  // Calculate decode difference (positive = packed slower)
  results.decode_diff_percent = results.unpacked_decode_seconds > 0
      ? ((results.packed_decode_seconds - results.unpacked_decode_seconds) / 
         results.unpacked_decode_seconds) * 100.0
      : 0.0;
  
  // Calculate total difference
  double total_packed = results.packed_encode_seconds + results.packed_decode_seconds;
  double total_unpacked = results.unpacked_encode_seconds + results.unpacked_decode_seconds;
  results.total_diff_percent = total_unpacked > 0
      ? ((total_packed - total_unpacked) / total_unpacked) * 100.0
      : 0.0;
  
  results.success = true;
  return results;
}

}  // namespace GenericTests

// =============================================================================
// USAGE EXAMPLE: Platform-Specific Timing Function
// =============================================================================
/*
 * Implement get_current_time_seconds() for your platform and pass it to run_test().
 * The function should return monotonic time in seconds with sufficient resolution.
 *
 * Example implementations:
 *
 * // Using std::chrono (C++11):
 * double get_time_chrono() {
 *   return std::chrono::duration<double>(
 *       std::chrono::high_resolution_clock::now().time_since_epoch()).count();
 * }
 *
 * // STM32 HAL:
 * double get_time_stm32() {
 *   return HAL_GetTick() / 1000.0;  // Convert ms to seconds
 * }
 *
 * // Arduino:
 * double get_time_arduino() {
 *   return micros() / 1000000.0;  // Convert us to seconds
 * }
 *
 * // POSIX:
 * double get_time_posix() {
 *   struct timespec ts;
 *   clock_gettime(CLOCK_MONOTONIC, &ts);
 *   return ts.tv_sec + ts.tv_nsec / 1000000000.0;
 * }
 *
 * // Usage:
 * auto results = GenericTests::run_test(get_time_chrono);
 * if (results.success) {
 *   printf("Encode: packed=%.3fms, unpacked=%.3fms, diff=%+.1f%%\n",
 *          results.packed_encode_seconds * 1000,
 *          results.unpacked_encode_seconds * 1000,
 *          results.encode_diff_percent);
 * }
 */
