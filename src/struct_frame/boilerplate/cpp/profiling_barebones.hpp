/* Struct-frame boilerplate: Barebones profiling (no std, no heap) */
/*
 * This file provides barebones structs and pack/unpack functions for profiling
 * packed vs unpacked struct access performance. No struct-frame, no std library,
 * no heap allocations.
 *
 * Usage:
 *   // In your test file:
 *   #include "profiling_barebones.hpp"
 *   
 *   // Create messages and buffers (caller-provided)
 *   BarebonesTests::PackedMessage packed_msgs[1000];
 *   BarebonesTests::UnpackedMessage unpacked_msgs[1000];
 *   uint8_t buffer[256 * 1000];
 *   
 *   // Initialize messages
 *   for (size_t i = 0; i < 1000; i++) {
 *       BarebonesTests::init_packed_message(packed_msgs[i], i);
 *       BarebonesTests::copy_packed_to_unpacked(unpacked_msgs[i], packed_msgs[i]);
 *   }
 *   
 *   // Time encode packed
 *   auto start = get_time();
 *   size_t offset = 0;
 *   for (size_t i = 0; i < 1000; i++) {
 *       offset += BarebonesTests::pack_packed(buffer + offset, packed_msgs[i]);
 *   }
 *   auto packed_time = get_time() - start;
 */

#pragma once

#include <cstddef>
#include <cstdint>

namespace BarebonesTests {

// Volatile sink to prevent compiler optimizations (no std)
inline volatile uint8_t g_barebones_sink = 0;

/**
 * Force the compiler to not optimize out buffer contents.
 * Computes a simple checksum and stores to volatile sink.
 */
inline void do_not_optimize_buffer(const uint8_t* buffer, size_t size) {
    uint8_t sum = 0;
    for (size_t i = 0; i < size; i++) {
        sum ^= buffer[i];
    }
    g_barebones_sink ^= sum;
}

// =============================================================================
// Packed struct (struct-frame style with #pragma pack(1))
// =============================================================================
#pragma pack(push, 1)
struct PackedMessage {
    uint8_t msg_id;
    uint32_t timestamp;
    int16_t value1;
    int32_t value2;
    float value3;
    double value4;
    uint8_t flags;
    char name[32];
};
#pragma pack(pop)

// =============================================================================
// Unpacked struct (natural alignment)
// =============================================================================
struct UnpackedMessage {
    uint8_t msg_id;
    uint32_t timestamp;
    int16_t value1;
    int32_t value2;
    float value3;
    double value4;
    uint8_t flags;
    char name[32];
};

// Wire format size (same as packed struct size)
static constexpr size_t WIRE_FORMAT_SIZE = sizeof(PackedMessage);

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
// Initialize a packed message with test data
// =============================================================================
inline void init_packed_message(PackedMessage& msg, size_t index) {
    msg.msg_id = static_cast<uint8_t>(index & 0xFF);
    msg.timestamp = static_cast<uint32_t>(index * 1000);
    msg.value1 = static_cast<int16_t>(index);
    msg.value2 = static_cast<int32_t>(index * 100);
    msg.value3 = static_cast<float>(index) * 1.5f;
    msg.value4 = static_cast<double>(index) * 2.5;
    msg.flags = static_cast<uint8_t>(index % 256);
    
    // Simple name initialization without snprintf
    const char* prefix = "Msg_";
    size_t j = 0;
    while (prefix[j] && j < sizeof(msg.name) - 1) {
        msg.name[j] = prefix[j];
        j++;
    }
    // Add index as simple decimal
    size_t temp = index;
    char digits[16];
    size_t digit_count = 0;
    do {
        digits[digit_count++] = '0' + (temp % 10);
        temp /= 10;
    } while (temp > 0 && digit_count < 16);
    
    // Reverse digits into name
    while (digit_count > 0 && j < sizeof(msg.name) - 1) {
        msg.name[j++] = digits[--digit_count];
    }
    // Null terminate and fill rest
    while (j < sizeof(msg.name)) {
        msg.name[j++] = '\0';
    }
}

// =============================================================================
// Copy functions
// =============================================================================
inline void copy_packed_to_unpacked(UnpackedMessage& unpacked, const PackedMessage& packed) {
    unpacked.msg_id = packed.msg_id;
    unpacked.timestamp = packed.timestamp;
    unpacked.value1 = packed.value1;
    unpacked.value2 = packed.value2;
    unpacked.value3 = packed.value3;
    unpacked.value4 = packed.value4;
    unpacked.flags = packed.flags;
    mem_copy(unpacked.name, packed.name, sizeof(unpacked.name));
}

inline void copy_unpacked_to_packed(PackedMessage& packed, const UnpackedMessage& unpacked) {
    packed.msg_id = unpacked.msg_id;
    packed.timestamp = unpacked.timestamp;
    packed.value1 = unpacked.value1;
    packed.value2 = unpacked.value2;
    packed.value3 = unpacked.value3;
    packed.value4 = unpacked.value4;
    packed.flags = unpacked.flags;
    mem_copy(packed.name, unpacked.name, sizeof(packed.name));
}

// =============================================================================
// Pack functions (struct -> buffer)
// =============================================================================
inline size_t pack_packed(uint8_t* buffer, const PackedMessage& msg) {
    // Direct copy - packed struct matches wire format exactly
    mem_copy(buffer, &msg, sizeof(PackedMessage));
    return sizeof(PackedMessage);
}

inline size_t pack_unpacked(uint8_t* buffer, const UnpackedMessage& msg) {
    // Field-by-field packing to wire format (simulates what you'd do without packed structs)
    size_t offset = 0;
    mem_copy(buffer + offset, &msg.msg_id, sizeof(msg.msg_id)); offset += sizeof(msg.msg_id);
    mem_copy(buffer + offset, &msg.timestamp, sizeof(msg.timestamp)); offset += sizeof(msg.timestamp);
    mem_copy(buffer + offset, &msg.value1, sizeof(msg.value1)); offset += sizeof(msg.value1);
    mem_copy(buffer + offset, &msg.value2, sizeof(msg.value2)); offset += sizeof(msg.value2);
    mem_copy(buffer + offset, &msg.value3, sizeof(msg.value3)); offset += sizeof(msg.value3);
    mem_copy(buffer + offset, &msg.value4, sizeof(msg.value4)); offset += sizeof(msg.value4);
    mem_copy(buffer + offset, &msg.flags, sizeof(msg.flags)); offset += sizeof(msg.flags);
    mem_copy(buffer + offset, msg.name, sizeof(msg.name)); offset += sizeof(msg.name);
    return offset;
}

// =============================================================================
// Unpack functions (buffer -> struct)
// =============================================================================
inline void unpack_packed(const uint8_t* buffer, PackedMessage& msg) {
    // Direct copy - packed struct matches wire format exactly
    mem_copy(&msg, buffer, sizeof(PackedMessage));
}

inline void unpack_unpacked(const uint8_t* buffer, UnpackedMessage& msg) {
    // Field-by-field unpacking from wire format
    size_t offset = 0;
    mem_copy(&msg.msg_id, buffer + offset, sizeof(msg.msg_id)); offset += sizeof(msg.msg_id);
    mem_copy(&msg.timestamp, buffer + offset, sizeof(msg.timestamp)); offset += sizeof(msg.timestamp);
    mem_copy(&msg.value1, buffer + offset, sizeof(msg.value1)); offset += sizeof(msg.value1);
    mem_copy(&msg.value2, buffer + offset, sizeof(msg.value2)); offset += sizeof(msg.value2);
    mem_copy(&msg.value3, buffer + offset, sizeof(msg.value3)); offset += sizeof(msg.value3);
    mem_copy(&msg.value4, buffer + offset, sizeof(msg.value4)); offset += sizeof(msg.value4);
    mem_copy(&msg.flags, buffer + offset, sizeof(msg.flags)); offset += sizeof(msg.flags);
    mem_copy(msg.name, buffer + offset, sizeof(msg.name)); offset += sizeof(msg.name);
}

// =============================================================================
// Verify functions
// =============================================================================
inline bool verify_packed(const PackedMessage& original, const PackedMessage& decoded) {
    return original.msg_id == decoded.msg_id &&
           original.timestamp == decoded.timestamp &&
           original.value1 == decoded.value1 &&
           original.value2 == decoded.value2 &&
           original.flags == decoded.flags;
}

inline bool verify_unpacked(const UnpackedMessage& original, const UnpackedMessage& decoded) {
    return original.msg_id == decoded.msg_id &&
           original.timestamp == decoded.timestamp &&
           original.value1 == decoded.value1 &&
           original.value2 == decoded.value2 &&
           original.flags == decoded.flags;
}

}  // namespace BarebonesTests
