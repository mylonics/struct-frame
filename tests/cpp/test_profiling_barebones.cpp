/**
 * Barebones Profiling Test - Pure struct access comparison (no struct-frame)
 * 
 * This test measures the raw performance difference between:
 * - Packed structs (#pragma pack(1)) - potential unaligned memory access
 * - Unpacked structs (natural alignment) - aligned memory access
 * 
 * This is a pure memory access test with no struct-frame involvement.
 * It helps characterize the memory access penalty on different platforms.
 */

#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>

// Number of iterations for profiling
static constexpr size_t ITERATIONS = 1000;

// Buffer size for all messages
static constexpr size_t BUFFER_SIZE = 256 * ITERATIONS;

// Volatile sink to prevent compiler optimizations
static volatile uint8_t g_sink = 0;

// Prevent compiler from optimizing away buffer contents
inline void do_not_optimize_buffer(const uint8_t* buffer, size_t size) {
    uint8_t sum = 0;
    for (size_t i = 0; i < size; i++) {
        sum ^= buffer[i];
    }
    g_sink ^= sum;
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

// High-resolution timing
using Clock = std::chrono::high_resolution_clock;
using Duration = std::chrono::duration<double, std::milli>;

// =============================================================================
// Pack functions (struct -> buffer)
// =============================================================================
inline size_t pack_packed(uint8_t* buffer, const PackedMessage& msg) {
    // Direct memcpy - packed struct matches wire format exactly
    std::memcpy(buffer, &msg, sizeof(PackedMessage));
    return sizeof(PackedMessage);
}

inline size_t pack_unpacked(uint8_t* buffer, const UnpackedMessage& msg) {
    // Field-by-field packing to wire format (simulates what you'd do without packed structs)
    size_t offset = 0;
    std::memcpy(buffer + offset, &msg.msg_id, sizeof(msg.msg_id)); offset += sizeof(msg.msg_id);
    std::memcpy(buffer + offset, &msg.timestamp, sizeof(msg.timestamp)); offset += sizeof(msg.timestamp);
    std::memcpy(buffer + offset, &msg.value1, sizeof(msg.value1)); offset += sizeof(msg.value1);
    std::memcpy(buffer + offset, &msg.value2, sizeof(msg.value2)); offset += sizeof(msg.value2);
    std::memcpy(buffer + offset, &msg.value3, sizeof(msg.value3)); offset += sizeof(msg.value3);
    std::memcpy(buffer + offset, &msg.value4, sizeof(msg.value4)); offset += sizeof(msg.value4);
    std::memcpy(buffer + offset, &msg.flags, sizeof(msg.flags)); offset += sizeof(msg.flags);
    std::memcpy(buffer + offset, msg.name, sizeof(msg.name)); offset += sizeof(msg.name);
    return offset;
}

// =============================================================================
// Unpack functions (buffer -> struct)
// =============================================================================
inline void unpack_packed(const uint8_t* buffer, PackedMessage& msg) {
    // Direct memcpy - packed struct matches wire format exactly
    std::memcpy(&msg, buffer, sizeof(PackedMessage));
}

inline void unpack_unpacked(const uint8_t* buffer, UnpackedMessage& msg) {
    // Field-by-field unpacking from wire format
    size_t offset = 0;
    std::memcpy(&msg.msg_id, buffer + offset, sizeof(msg.msg_id)); offset += sizeof(msg.msg_id);
    std::memcpy(&msg.timestamp, buffer + offset, sizeof(msg.timestamp)); offset += sizeof(msg.timestamp);
    std::memcpy(&msg.value1, buffer + offset, sizeof(msg.value1)); offset += sizeof(msg.value1);
    std::memcpy(&msg.value2, buffer + offset, sizeof(msg.value2)); offset += sizeof(msg.value2);
    std::memcpy(&msg.value3, buffer + offset, sizeof(msg.value3)); offset += sizeof(msg.value3);
    std::memcpy(&msg.value4, buffer + offset, sizeof(msg.value4)); offset += sizeof(msg.value4);
    std::memcpy(&msg.flags, buffer + offset, sizeof(msg.flags)); offset += sizeof(msg.flags);
    std::memcpy(msg.name, buffer + offset, sizeof(msg.name)); offset += sizeof(msg.name);
}

int main() {
    printf("\n");
    printf("=============================================================\n");
    printf("BAREBONES PROFILING TEST: Packed vs Unpacked Struct Access\n");
    printf("=============================================================\n");
    printf("\n");
    printf("This test measures raw memory access performance difference\n");
    printf("between packed and unpacked structs (no struct-frame involved).\n");
    printf("\n");
    printf("Test configuration:\n");
    printf("  Iterations: %zu\n", ITERATIONS);
    printf("  Packed struct size: %zu bytes\n", sizeof(PackedMessage));
    printf("  Unpacked struct size: %zu bytes\n", sizeof(UnpackedMessage));
    printf("  Wire format size: %zu bytes\n", sizeof(PackedMessage));
    printf("\n");

    // Allocate buffers for all messages
    uint8_t* packed_buffer = new uint8_t[BUFFER_SIZE];
    uint8_t* unpacked_buffer = new uint8_t[BUFFER_SIZE];

    // Create test data
    PackedMessage packed_msgs[ITERATIONS];
    UnpackedMessage unpacked_msgs[ITERATIONS];
    
    for (size_t i = 0; i < ITERATIONS; i++) {
        packed_msgs[i].msg_id = static_cast<uint8_t>(i & 0xFF);
        packed_msgs[i].timestamp = static_cast<uint32_t>(i * 1000);
        packed_msgs[i].value1 = static_cast<int16_t>(i);
        packed_msgs[i].value2 = static_cast<int32_t>(i * 100);
        packed_msgs[i].value3 = static_cast<float>(i) * 1.5f;
        packed_msgs[i].value4 = static_cast<double>(i) * 2.5;
        packed_msgs[i].flags = static_cast<uint8_t>(i % 256);
        snprintf(packed_msgs[i].name, sizeof(packed_msgs[i].name), "Message_%zu", i);

        unpacked_msgs[i].msg_id = packed_msgs[i].msg_id;
        unpacked_msgs[i].timestamp = packed_msgs[i].timestamp;
        unpacked_msgs[i].value1 = packed_msgs[i].value1;
        unpacked_msgs[i].value2 = packed_msgs[i].value2;
        unpacked_msgs[i].value3 = packed_msgs[i].value3;
        unpacked_msgs[i].value4 = packed_msgs[i].value4;
        unpacked_msgs[i].flags = packed_msgs[i].flags;
        std::memcpy(unpacked_msgs[i].name, packed_msgs[i].name, sizeof(unpacked_msgs[i].name));
    }

    printf("-------------------------------------------------------------\n");
    printf("ENCODE TESTS (Pack %zu messages into buffer)\n", ITERATIONS);
    printf("-------------------------------------------------------------\n");

    // Encode packed
    auto start_packed_encode = Clock::now();
    size_t packed_offset = 0;
    for (size_t i = 0; i < ITERATIONS; i++) {
        packed_offset += pack_packed(packed_buffer + packed_offset, packed_msgs[i]);
    }
    auto end_packed_encode = Clock::now();
    Duration packed_encode_time = end_packed_encode - start_packed_encode;
    do_not_optimize_buffer(packed_buffer, packed_offset);

    printf("  Encode Packed:   %8.3f ms (%zu bytes)\n", packed_encode_time.count(), packed_offset);

    // Encode unpacked
    auto start_unpacked_encode = Clock::now();
    size_t unpacked_offset = 0;
    for (size_t i = 0; i < ITERATIONS; i++) {
        unpacked_offset += pack_unpacked(unpacked_buffer + unpacked_offset, unpacked_msgs[i]);
    }
    auto end_unpacked_encode = Clock::now();
    Duration unpacked_encode_time = end_unpacked_encode - start_unpacked_encode;
    do_not_optimize_buffer(unpacked_buffer, unpacked_offset);

    printf("  Encode Unpacked: %8.3f ms (%zu bytes)\n", unpacked_encode_time.count(), unpacked_offset);

    double encode_diff_pct = 0.0;
    if (unpacked_encode_time.count() > 0) {
        encode_diff_pct = ((packed_encode_time.count() - unpacked_encode_time.count()) / 
                          unpacked_encode_time.count()) * 100.0;
    }

    printf("\n  Encode Performance Difference:\n");
    if (encode_diff_pct > 0) {
        printf("    Packed is %.1f%% SLOWER than unpacked\n", encode_diff_pct);
    } else if (encode_diff_pct < 0) {
        printf("    Packed is %.1f%% FASTER than unpacked\n", -encode_diff_pct);
    } else {
        printf("    No significant difference\n");
    }

    printf("\n-------------------------------------------------------------\n");
    printf("DECODE TESTS (Unpack %zu messages from buffer)\n", ITERATIONS);
    printf("-------------------------------------------------------------\n");

    // Decode packed
    PackedMessage decoded_packed[ITERATIONS];
    auto start_packed_decode = Clock::now();
    size_t read_offset = 0;
    for (size_t i = 0; i < ITERATIONS; i++) {
        unpack_packed(packed_buffer + read_offset, decoded_packed[i]);
        read_offset += sizeof(PackedMessage);
    }
    auto end_packed_decode = Clock::now();
    Duration packed_decode_time = end_packed_decode - start_packed_decode;
    do_not_optimize_buffer(reinterpret_cast<uint8_t*>(decoded_packed), sizeof(decoded_packed));

    printf("  Decode Packed:   %8.3f ms\n", packed_decode_time.count());

    // Decode unpacked
    UnpackedMessage decoded_unpacked[ITERATIONS];
    auto start_unpacked_decode = Clock::now();
    read_offset = 0;
    for (size_t i = 0; i < ITERATIONS; i++) {
        unpack_unpacked(unpacked_buffer + read_offset, decoded_unpacked[i]);
        read_offset += sizeof(PackedMessage);  // Wire format size
    }
    auto end_unpacked_decode = Clock::now();
    Duration unpacked_decode_time = end_unpacked_decode - start_unpacked_decode;
    do_not_optimize_buffer(reinterpret_cast<uint8_t*>(decoded_unpacked), sizeof(decoded_unpacked));

    printf("  Decode Unpacked: %8.3f ms\n", unpacked_decode_time.count());

    double decode_diff_pct = 0.0;
    if (unpacked_decode_time.count() > 0) {
        decode_diff_pct = ((packed_decode_time.count() - unpacked_decode_time.count()) / 
                          unpacked_decode_time.count()) * 100.0;
    }

    printf("\n  Decode Performance Difference:\n");
    if (decode_diff_pct > 0) {
        printf("    Packed is %.1f%% SLOWER than unpacked\n", decode_diff_pct);
    } else if (decode_diff_pct < 0) {
        printf("    Packed is %.1f%% FASTER than unpacked\n", -decode_diff_pct);
    } else {
        printf("    No significant difference\n");
    }

    printf("\n=============================================================\n");
    printf("SUMMARY\n");
    printf("=============================================================\n");
    printf("\n");
    printf("  %-20s %10s %10s %10s\n", "Operation", "Packed", "Unpacked", "Diff %%");
    printf("  %-20s %10s %10s %10s\n", "--------------------", "----------", "----------", "----------");
    printf("  %-20s %8.3f ms %8.3f ms %+9.1f%%\n", 
           "Encode", packed_encode_time.count(), unpacked_encode_time.count(), encode_diff_pct);
    printf("  %-20s %8.3f ms %8.3f ms %+9.1f%%\n", 
           "Decode", packed_decode_time.count(), unpacked_decode_time.count(), decode_diff_pct);
    printf("\n");

    double total_packed = packed_encode_time.count() + packed_decode_time.count();
    double total_unpacked = unpacked_encode_time.count() + unpacked_decode_time.count();
    double total_diff_pct = ((total_packed - total_unpacked) / total_unpacked) * 100.0;

    printf("  Overall: Packed structs are ");
    if (total_diff_pct > 1.0) {
        printf("%.1f%% SLOWER than unpacked\n", total_diff_pct);
    } else if (total_diff_pct < -1.0) {
        printf("%.1f%% FASTER than unpacked\n", -total_diff_pct);
    } else {
        printf("approximately EQUAL to unpacked (%.1f%%)\n", total_diff_pct);
    }
    printf("\n");

    // Verify data integrity
    bool verified = true;
    for (size_t i = 0; i < ITERATIONS && verified; i++) {
        if (decoded_packed[i].msg_id != packed_msgs[i].msg_id ||
            decoded_packed[i].timestamp != packed_msgs[i].timestamp ||
            decoded_packed[i].value1 != packed_msgs[i].value1 ||
            decoded_packed[i].value2 != packed_msgs[i].value2) {
            verified = false;
        }
    }

    if (verified) {
        printf("[TEST PASSED] All %zu messages verified successfully.\n", ITERATIONS);
    } else {
        printf("[TEST FAILED] Data integrity check failed.\n");
    }
    printf("\n");

    delete[] packed_buffer;
    delete[] unpacked_buffer;

    return verified ? 0 : 1;
}
