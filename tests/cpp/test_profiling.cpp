/**
 * Profiling test for struct-frame packed vs unpacked struct performance.
 * 
 * This test compares the encode/decode performance of:
 * - Packed structs (struct-frame's default approach with #pragma pack(1))
 * - Unpacked structs (naturally-aligned structs without packing)
 * 
 * The test runs 1000 iterations of each operation and reports timing differences
 * to help characterize memory access penalties on different platforms.
 */

#include <chrono>
#include <cstdio>
#include <cstring>

#include "../../generated/cpp/serialization_test.structframe.hpp"
#include "profiling_tests.hpp"

// Unpacked version of SerializationTestBasicTypesMessage
// Same fields but without #pragma pack(1), allowing natural alignment
struct BasicTypesMessageUnpacked {
    int8_t small_int;
    int16_t medium_int;
    int32_t regular_int;
    int64_t large_int;
    uint8_t small_uint;
    uint16_t medium_uint;
    uint32_t regular_uint;
    uint64_t large_uint;
    float single_precision;
    double double_precision;
    bool flag;
    char device_id[32];
    struct { uint8_t length; char data[128]; } description;
};

// Copy function: unpacked -> packed
void copy_to_packed(SerializationTestBasicTypesMessage& packed, const BasicTypesMessageUnpacked& unpacked) {
    packed.small_int = unpacked.small_int;
    packed.medium_int = unpacked.medium_int;
    packed.regular_int = unpacked.regular_int;
    packed.large_int = unpacked.large_int;
    packed.small_uint = unpacked.small_uint;
    packed.medium_uint = unpacked.medium_uint;
    packed.regular_uint = unpacked.regular_uint;
    packed.large_uint = unpacked.large_uint;
    packed.single_precision = unpacked.single_precision;
    packed.double_precision = unpacked.double_precision;
    packed.flag = unpacked.flag;
    std::memcpy(packed.device_id, unpacked.device_id, sizeof(packed.device_id));
    packed.description.length = unpacked.description.length;
    std::memcpy(packed.description.data, unpacked.description.data, sizeof(packed.description.data));
}

// Copy function: packed -> unpacked
void copy_to_unpacked(BasicTypesMessageUnpacked& unpacked, const SerializationTestBasicTypesMessage& packed) {
    unpacked.small_int = packed.small_int;
    unpacked.medium_int = packed.medium_int;
    unpacked.regular_int = packed.regular_int;
    unpacked.large_int = packed.large_int;
    unpacked.small_uint = packed.small_uint;
    unpacked.medium_uint = packed.medium_uint;
    unpacked.regular_uint = packed.regular_uint;
    unpacked.large_uint = packed.large_uint;
    unpacked.single_precision = packed.single_precision;
    unpacked.double_precision = packed.double_precision;
    unpacked.flag = packed.flag;
    std::memcpy(unpacked.device_id, packed.device_id, sizeof(unpacked.device_id));
    unpacked.description.length = packed.description.length;
    std::memcpy(unpacked.description.data, packed.description.data, sizeof(unpacked.description.data));
}

// High-resolution timing helper
using Clock = std::chrono::high_resolution_clock;
using Duration = std::chrono::duration<double, std::milli>;

int main() {
    printf("\n");
    printf("=============================================================\n");
    printf("STRUCT-FRAME PROFILING TEST: Packed vs Unpacked Performance\n");
    printf("=============================================================\n");
    printf("\n");
    printf("This test measures memory access penalties when using packed structs\n");
    printf("(struct-frame's approach) vs naturally-aligned unpacked structs.\n");
    printf("\n");
    printf("Test configuration:\n");
    printf("  Iterations per test: %zu\n", FrameParsers::ProfilingTests::PROFILE_ITERATIONS);
    printf("  Message type: SerializationTestBasicTypesMessage\n");
    printf("  Packed size: %zu bytes\n", sizeof(SerializationTestBasicTypesMessage));
    printf("  Unpacked size: %zu bytes\n", sizeof(BasicTypesMessageUnpacked));
    printf("\n");

    // Create test data
    SerializationTestBasicTypesMessage packed_msg{};
    packed_msg.small_int = 42;
    packed_msg.medium_int = 1000;
    packed_msg.regular_int = 123456;
    packed_msg.large_int = 9876543210LL;
    packed_msg.small_uint = 200;
    packed_msg.medium_uint = 50000;
    packed_msg.regular_uint = 4000000000U;
    packed_msg.large_uint = 9223372036854775807ULL;
    packed_msg.single_precision = 3.14159f;
    packed_msg.double_precision = 2.718281828459045;
    packed_msg.flag = true;
    std::strncpy(packed_msg.device_id, "DEVICE-001", 31);
    packed_msg.device_id[31] = '\0';
    packed_msg.description.length = 16;
    std::strncpy(packed_msg.description.data, "Basic test data", 127);

    // Create unpacked version with same data
    BasicTypesMessageUnpacked unpacked_msg{};
    copy_to_unpacked(unpacked_msg, packed_msg);

    // Buffer for encoding
    uint8_t buffer[4096];

    printf("-------------------------------------------------------------\n");
    printf("ENCODE TESTS (ProfileStandard)\n");
    printf("-------------------------------------------------------------\n");

    // Verify round-trip first
    bool roundtrip_ok = FrameParsers::ProfilingTests::verify_roundtrip<
        SerializationTestBasicTypesMessage, 
        FrameParsers::ProfileStandardConfig>(
            packed_msg, buffer, sizeof(buffer), FrameParsers::get_message_info);
    
    if (!roundtrip_ok) {
        printf("[FAIL] Round-trip verification failed!\n");
        return 1;
    }
    printf("  Round-trip verification: PASS\n\n");

    // Encode packed test
    auto start_packed_encode = Clock::now();
    auto encode_packed_result = FrameParsers::ProfilingTests::encode_packed_test<
        SerializationTestBasicTypesMessage, 
        FrameParsers::ProfileStandardConfig>(
            packed_msg, buffer, sizeof(buffer));
    auto end_packed_encode = Clock::now();
    Duration packed_encode_time = end_packed_encode - start_packed_encode;

    printf("  Encode Packed:   %8.3f ms (%zu iterations, %zu bytes)\n", 
           packed_encode_time.count(), 
           encode_packed_result.iterations, 
           encode_packed_result.bytes_total);

    // Encode unpacked test
    auto start_unpacked_encode = Clock::now();
    auto encode_unpacked_result = FrameParsers::ProfilingTests::encode_unpacked_test<
        SerializationTestBasicTypesMessage, 
        BasicTypesMessageUnpacked, 
        FrameParsers::ProfileStandardConfig>(
            packed_msg, unpacked_msg, buffer, sizeof(buffer), copy_to_packed);
    auto end_unpacked_encode = Clock::now();
    Duration unpacked_encode_time = end_unpacked_encode - start_unpacked_encode;

    printf("  Encode Unpacked: %8.3f ms (%zu iterations, %zu bytes)\n", 
           unpacked_encode_time.count(), 
           encode_unpacked_result.iterations, 
           encode_unpacked_result.bytes_total);

    // Calculate percentage difference for encode
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
    printf("DECODE TESTS (ProfileStandard)\n");
    printf("-------------------------------------------------------------\n");

    // Re-encode to get a valid frame in buffer
    size_t frame_size = FrameParsers::FrameEncoderWithCrc<FrameParsers::ProfileStandardConfig>::encode(
        buffer, sizeof(buffer), packed_msg);

    // Decode packed test
    auto start_packed_decode = Clock::now();
    auto decode_packed_result = FrameParsers::ProfilingTests::decode_packed_test<
        SerializationTestBasicTypesMessage, 
        FrameParsers::ProfileStandardConfig>(
            buffer, frame_size, FrameParsers::get_message_info);
    auto end_packed_decode = Clock::now();
    Duration packed_decode_time = end_packed_decode - start_packed_decode;

    printf("  Decode Packed:   %8.3f ms (%zu iterations, %zu bytes)\n", 
           packed_decode_time.count(), 
           decode_packed_result.iterations, 
           decode_packed_result.bytes_total);

    // Decode unpacked test
    auto start_unpacked_decode = Clock::now();
    auto decode_unpacked_result = FrameParsers::ProfilingTests::decode_unpacked_test<
        SerializationTestBasicTypesMessage, 
        BasicTypesMessageUnpacked, 
        FrameParsers::ProfileStandardConfig>(
            buffer, frame_size, FrameParsers::get_message_info, copy_to_unpacked);
    auto end_unpacked_decode = Clock::now();
    Duration unpacked_decode_time = end_unpacked_decode - start_unpacked_decode;

    printf("  Decode Unpacked: %8.3f ms (%zu iterations, %zu bytes)\n", 
           unpacked_decode_time.count(), 
           decode_unpacked_result.iterations, 
           decode_unpacked_result.bytes_total);

    // Calculate percentage difference for decode
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
    
    // Overall assessment
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

    // Return success
    bool all_success = encode_packed_result.success && 
                       encode_unpacked_result.success && 
                       decode_packed_result.success && 
                       decode_unpacked_result.success;
    
    if (all_success) {
        printf("[TEST PASSED] All profiling tests completed successfully.\n");
    } else {
        printf("[TEST FAILED] Some profiling tests failed.\n");
    }
    printf("\n");
    
    return all_success ? 0 : 1;
}
