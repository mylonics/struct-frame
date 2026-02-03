/* Struct-frame boilerplate: Generic profiling (no std, no heap) */
/*
 * This file provides hardcoded packed and unpacked message types for profiling
 * struct-frame encode/decode performance. No std library, no heap allocations.
 *
 * Usage:
 *   // In your test file:
 *   #include "profiling_generic.hpp"
 *   
 *   // Create messages and buffers (caller-provided)
 *   GenericTests::TestMessagePacked packed_msgs[1000];
 *   GenericTests::TestMessageUnpacked unpacked_msgs[1000];
 *   uint8_t buffer[256 * 1000];
 *   
 *   // Initialize messages
 *   for (size_t i = 0; i < 1000; i++) {
 *       GenericTests::init_packed_message(packed_msgs[i], i);
 *       GenericTests::copy_to_unpacked(unpacked_msgs[i], packed_msgs[i]);
 *   }
 *   
 *   // Time encode using struct-frame
 *   auto start = get_time();
 *   size_t offset = 0;
 *   for (size_t i = 0; i < 1000; i++) {
 *       offset += FrameParsers::FrameEncoderWithCrc<Config>::encode(buffer + offset, ...);
 *   }
 *   auto time = get_time() - start;
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
// =============================================================================
#pragma pack(push, 1)
struct TestMessagePacked : public FrameParsers::MessageBase<TestMessagePacked, 0x01, 64, 0xAA, 0x55> {
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
// =============================================================================
struct TestMessageUnpacked {
    uint8_t msg_type;
    uint32_t sequence;
    int16_t sensor_value;
    int32_t counter;
    float temperature;
    double pressure;
    uint8_t status;
    char label[16];
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

// =============================================================================
// Copy functions
// =============================================================================
inline void copy_to_packed(TestMessagePacked& packed, const TestMessageUnpacked& unpacked) {
    packed.msg_type = unpacked.msg_type;
    packed.sequence = unpacked.sequence;
    packed.sensor_value = unpacked.sensor_value;
    packed.counter = unpacked.counter;
    packed.temperature = unpacked.temperature;
    packed.pressure = unpacked.pressure;
    packed.status = unpacked.status;
    mem_copy(packed.label, unpacked.label, sizeof(packed.label));
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
// Verify functions
// =============================================================================
inline bool verify_packed(const TestMessagePacked& original, const TestMessagePacked& decoded) {
    return original.sequence == decoded.sequence &&
           original.counter == decoded.counter &&
           original.msg_type == decoded.msg_type;
}

inline bool verify_unpacked(const TestMessageUnpacked& original, const TestMessageUnpacked& decoded) {
    return original.sequence == decoded.sequence &&
           original.counter == decoded.counter &&
           original.msg_type == decoded.msg_type;
}

}  // namespace GenericTests
