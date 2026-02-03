/**
 * Barebones Profiling Test - Pure struct access comparison (no struct-frame)
 * 
 * This test measures the raw performance difference between:
 * - Packed structs (#pragma pack(1)) - potential unaligned memory access
 * - Unpacked structs (natural alignment) - aligned memory access
 * 
 * This is a pure memory access test with no struct-frame involvement.
 * It helps characterize the memory access penalty on different platforms.
 * 
 * The core structs and pack/unpack functions are in profiling_barebones.hpp
 * This file only handles timing and output.
 */

#include <chrono>
#include <cstdio>

#include "profiling_barebones.hpp"

// Number of iterations for profiling
static constexpr size_t ITERATIONS = 1000;

// Buffer size for all messages
static constexpr size_t BUFFER_SIZE = BarebonesTests::WIRE_FORMAT_SIZE * ITERATIONS;

// High-resolution timing
using Clock = std::chrono::high_resolution_clock;
using Duration = std::chrono::duration<double, std::milli>;

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
    printf("  Packed struct size: %zu bytes\n", sizeof(BarebonesTests::PackedMessage));
    printf("  Unpacked struct size: %zu bytes\n", sizeof(BarebonesTests::UnpackedMessage));
    printf("  Wire format size: %zu bytes\n", BarebonesTests::WIRE_FORMAT_SIZE);
    printf("\n");

    // Allocate buffers and messages on stack (or heap for large arrays)
    static uint8_t packed_buffer[BUFFER_SIZE];
    static uint8_t unpacked_buffer[BUFFER_SIZE];
    static BarebonesTests::PackedMessage packed_msgs[ITERATIONS];
    static BarebonesTests::UnpackedMessage unpacked_msgs[ITERATIONS];
    
    // Initialize test data using boilerplate functions
    for (size_t i = 0; i < ITERATIONS; i++) {
        BarebonesTests::init_packed_message(packed_msgs[i], i);
        BarebonesTests::copy_packed_to_unpacked(unpacked_msgs[i], packed_msgs[i]);
    }

    printf("-------------------------------------------------------------\n");
    printf("ENCODE TESTS (Pack %zu messages into buffer)\n", ITERATIONS);
    printf("-------------------------------------------------------------\n");

    // Encode packed
    auto start_packed_encode = Clock::now();
    size_t packed_offset = 0;
    for (size_t i = 0; i < ITERATIONS; i++) {
        packed_offset += BarebonesTests::pack_packed(packed_buffer + packed_offset, packed_msgs[i]);
    }
    auto end_packed_encode = Clock::now();
    Duration packed_encode_time = end_packed_encode - start_packed_encode;
    BarebonesTests::do_not_optimize_buffer(packed_buffer, packed_offset);

    printf("  Encode Packed:   %8.3f ms (%zu bytes)\n", packed_encode_time.count(), packed_offset);

    // Encode unpacked
    auto start_unpacked_encode = Clock::now();
    size_t unpacked_offset = 0;
    for (size_t i = 0; i < ITERATIONS; i++) {
        unpacked_offset += BarebonesTests::pack_unpacked(unpacked_buffer + unpacked_offset, unpacked_msgs[i]);
    }
    auto end_unpacked_encode = Clock::now();
    Duration unpacked_encode_time = end_unpacked_encode - start_unpacked_encode;
    BarebonesTests::do_not_optimize_buffer(unpacked_buffer, unpacked_offset);

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
    static BarebonesTests::PackedMessage decoded_packed[ITERATIONS];
    auto start_packed_decode = Clock::now();
    size_t read_offset = 0;
    for (size_t i = 0; i < ITERATIONS; i++) {
        BarebonesTests::unpack_packed(packed_buffer + read_offset, decoded_packed[i]);
        read_offset += BarebonesTests::WIRE_FORMAT_SIZE;
    }
    auto end_packed_decode = Clock::now();
    Duration packed_decode_time = end_packed_decode - start_packed_decode;
    BarebonesTests::do_not_optimize_buffer(reinterpret_cast<uint8_t*>(decoded_packed), sizeof(decoded_packed));

    printf("  Decode Packed:   %8.3f ms\n", packed_decode_time.count());

    // Decode unpacked
    static BarebonesTests::UnpackedMessage decoded_unpacked[ITERATIONS];
    auto start_unpacked_decode = Clock::now();
    read_offset = 0;
    for (size_t i = 0; i < ITERATIONS; i++) {
        BarebonesTests::unpack_unpacked(unpacked_buffer + read_offset, decoded_unpacked[i]);
        read_offset += BarebonesTests::WIRE_FORMAT_SIZE;
    }
    auto end_unpacked_decode = Clock::now();
    Duration unpacked_decode_time = end_unpacked_decode - start_unpacked_decode;
    BarebonesTests::do_not_optimize_buffer(reinterpret_cast<uint8_t*>(decoded_unpacked), sizeof(decoded_unpacked));

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

    // Verify data integrity using boilerplate functions
    bool verified = true;
    for (size_t i = 0; i < ITERATIONS && verified; i++) {
        if (!BarebonesTests::verify_packed(packed_msgs[i], decoded_packed[i])) {
            verified = false;
        }
    }

    if (verified) {
        printf("[TEST PASSED] All %zu messages verified successfully.\n", ITERATIONS);
    } else {
        printf("[TEST FAILED] Data integrity check failed.\n");
    }
    printf("\n");

    return verified ? 0 : 1;
}
