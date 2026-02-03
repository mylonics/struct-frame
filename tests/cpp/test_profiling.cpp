/**
 * Struct-Frame-Generic Profiling Test
 * 
 * This test uses struct-frame's boilerplate profiling code with hardcoded
 * packed and unpacked message types. It encodes 1000 messages into buffers,
 * times the operation, then decodes all 1000 messages.
 * 
 * This demonstrates the struct-frame encode/decode performance comparing:
 * - Packed structs (struct-frame's default approach with #pragma pack(1))
 * - Unpacked structs (naturally-aligned structs requiring field-by-field copy)
 * 
 * The core structs and functions are in profiling_generic.hpp
 * This file only handles timing and output.
 */

#include <chrono>
#include <cstdio>

#include "profiling_generic.hpp"

// Number of iterations
static constexpr size_t ITERATIONS = 1000;

// Buffer size for all encoded messages (frame overhead + message size per iteration)
static constexpr size_t BUFFER_SIZE = 128 * ITERATIONS;

// High-resolution timing
using Clock = std::chrono::high_resolution_clock;
using Duration = std::chrono::duration<double, std::milli>;

int main() {
    printf("\n");
    printf("=============================================================\n");
    printf("STRUCT-FRAME-GENERIC PROFILING TEST\n");
    printf("=============================================================\n");
    printf("\n");
    printf("This test uses struct-frame encoding/decoding with hardcoded\n");
    printf("packed and unpacked message types.\n");
    printf("\n");
    printf("Test configuration:\n");
    printf("  Messages to encode/decode: %zu\n", ITERATIONS);
    printf("  Packed message size: %zu bytes\n", sizeof(GenericTests::TestMessagePacked));
    printf("  Unpacked message size: %zu bytes\n", sizeof(GenericTests::TestMessageUnpacked));
    printf("\n");

    // Allocate buffers and messages on stack (static for large arrays)
    static uint8_t packed_buffer[BUFFER_SIZE];
    static uint8_t unpacked_buffer[BUFFER_SIZE];
    static GenericTests::TestMessagePacked packed_msgs[ITERATIONS];
    static GenericTests::TestMessageUnpacked unpacked_msgs[ITERATIONS];

    // Initialize test messages using boilerplate functions
    for (size_t i = 0; i < ITERATIONS; i++) {
        GenericTests::init_packed_message(packed_msgs[i], i);
        GenericTests::copy_to_unpacked(unpacked_msgs[i], packed_msgs[i]);
    }

    printf("-------------------------------------------------------------\n");
    printf("ENCODE TESTS (Encode %zu messages using ProfileStandard)\n", ITERATIONS);
    printf("-------------------------------------------------------------\n");

    // Encode packed - encode all 1000 messages into buffer
    auto start_packed_encode = Clock::now();
    size_t packed_offset = 0;
    for (size_t i = 0; i < ITERATIONS; i++) {
        size_t written = FrameParsers::FrameEncoderWithCrc<FrameParsers::ProfileStandardConfig>::encode(
            packed_buffer + packed_offset, BUFFER_SIZE - packed_offset, packed_msgs[i]);
        if (written == 0) {
            printf("  [FAIL] Packed encode failed at message %zu\n", i);
            return 1;
        }
        packed_offset += written;
    }
    auto end_packed_encode = Clock::now();
    Duration packed_encode_time = end_packed_encode - start_packed_encode;
    GenericTests::do_not_optimize_buffer(packed_buffer, packed_offset);

    printf("  Encode Packed:   %8.3f ms (%zu bytes total)\n", packed_encode_time.count(), packed_offset);

    // Encode unpacked - copy to packed then encode
    auto start_unpacked_encode = Clock::now();
    size_t unpacked_offset = 0;
    GenericTests::TestMessagePacked temp_packed{};
    for (size_t i = 0; i < ITERATIONS; i++) {
        GenericTests::copy_to_packed(temp_packed, unpacked_msgs[i]);
        size_t written = FrameParsers::FrameEncoderWithCrc<FrameParsers::ProfileStandardConfig>::encode(
            unpacked_buffer + unpacked_offset, BUFFER_SIZE - unpacked_offset, temp_packed);
        if (written == 0) {
            printf("  [FAIL] Unpacked encode failed at message %zu\n", i);
            return 1;
        }
        unpacked_offset += written;
    }
    auto end_unpacked_encode = Clock::now();
    Duration unpacked_encode_time = end_unpacked_encode - start_unpacked_encode;
    GenericTests::do_not_optimize_buffer(unpacked_buffer, unpacked_offset);

    printf("  Encode Unpacked: %8.3f ms (%zu bytes total)\n", unpacked_encode_time.count(), unpacked_offset);

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
    printf("DECODE TESTS (Decode %zu messages using ProfileStandard)\n", ITERATIONS);
    printf("-------------------------------------------------------------\n");

    // Decode packed - parse all 1000 frames from buffer
    static GenericTests::TestMessagePacked decoded_packed[ITERATIONS];
    auto start_packed_decode = Clock::now();
    size_t read_offset = 0;
    for (size_t i = 0; i < ITERATIONS; i++) {
        auto frame_info = FrameParsers::BufferParserWithCrc<FrameParsers::ProfileStandardConfig>::parse(
            packed_buffer + read_offset, packed_offset - read_offset, GenericTests::get_test_message_info);
        if (!frame_info.valid) {
            printf("  [FAIL] Packed decode parse failed at message %zu\n", i);
            return 1;
        }
        size_t bytes_read = decoded_packed[i].deserialize(frame_info);
        if (bytes_read == 0) {
            printf("  [FAIL] Packed decode deserialize failed at message %zu\n", i);
            return 1;
        }
        read_offset += frame_info.frame_size;
    }
    auto end_packed_decode = Clock::now();
    Duration packed_decode_time = end_packed_decode - start_packed_decode;
    GenericTests::do_not_optimize_buffer(reinterpret_cast<uint8_t*>(decoded_packed), sizeof(decoded_packed));

    printf("  Decode Packed:   %8.3f ms\n", packed_decode_time.count());

    // Decode unpacked - parse then copy to unpacked
    static GenericTests::TestMessageUnpacked decoded_unpacked[ITERATIONS];
    auto start_unpacked_decode = Clock::now();
    read_offset = 0;
    for (size_t i = 0; i < ITERATIONS; i++) {
        auto frame_info = FrameParsers::BufferParserWithCrc<FrameParsers::ProfileStandardConfig>::parse(
            unpacked_buffer + read_offset, unpacked_offset - read_offset, GenericTests::get_test_message_info);
        if (!frame_info.valid) {
            printf("  [FAIL] Unpacked decode parse failed at message %zu\n", i);
            return 1;
        }
        GenericTests::TestMessagePacked temp_decoded{};
        size_t bytes_read = temp_decoded.deserialize(frame_info);
        if (bytes_read == 0) {
            printf("  [FAIL] Unpacked decode deserialize failed at message %zu\n", i);
            return 1;
        }
        GenericTests::copy_to_unpacked(decoded_unpacked[i], temp_decoded);
        read_offset += frame_info.frame_size;
    }
    auto end_unpacked_decode = Clock::now();
    Duration unpacked_decode_time = end_unpacked_decode - start_unpacked_decode;
    GenericTests::do_not_optimize_buffer(reinterpret_cast<uint8_t*>(decoded_unpacked), sizeof(decoded_unpacked));

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
        if (!GenericTests::verify_packed(packed_msgs[i], decoded_packed[i])) {
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
