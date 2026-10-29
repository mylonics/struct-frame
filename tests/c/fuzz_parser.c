/*
 * LibFuzzer entry point for the C accumulating-reader parser.
 *
 * Build with:
 *   clang -O1 -g -fsanitize=fuzzer,address,undefined \
 *         -I src/struct_frame/boilerplate/c \
 *         tests/c/fuzz_parser.c -o fuzz_parser
 *
 * Run with:
 *   ./fuzz_parser -max_len=4096 -runs=100000
 *
 * The fuzzer feeds arbitrary bytes to the streaming parser for every
 * supported profile. It does not assert semantic properties itself; it relies
 * on the sanitizers (ASan/UBSan) to catch crashes and out-of-bounds reads, and
 * on libFuzzer's per-input timeout to catch a parser that livelocks instead of
 * eventually reporting no valid frame.
 *
 * This file does not depend on any generated .sf code — it exercises only
 * the hand-written parser runtime, which is the most security-sensitive
 * part of the C surface.
 */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#include "frame_base.h"
#include "frame_headers.h"
#include "frame_profiles.h"

/* Real message table, identical to tests/fuzz/corpus.py, so seed frames from
 * tests/fuzz/make_seed_corpus.py pass the checksum and reach the deeper parser paths. */
static bool fuzz_get_message_info(uint16_t msg_id, message_info_t* info) {
    static const struct { uint16_t id; size_t size; uint8_t m1, m2; } T[] = {
        {1, 8, 11, 22}, {2, 32, 33, 44}, {3, 100, 55, 66}, {4, 1, 77, 88}, {5, 200, 99, 111},
    };
    for (size_t i = 0; i < sizeof(T) / sizeof(T[0]); i++) {
        if (T[i].id == msg_id) {
            info->size = info->base_size = info->min_size = T[i].size;
            info->magic1 = T[i].m1;
            info->magic2 = T[i].m2;
            return true;
        }
    }
    return false;
}

static void fuzz_one_profile(const profile_config_t* cfg,
                             const uint8_t* data, size_t size) {
    uint8_t internal[1024];
    accumulating_reader_t reader;
    accumulating_reader_init(&reader, cfg, internal, sizeof(internal),
                             fuzz_get_message_info);

    /* Feed the input in two slices to also exercise the cross-buffer
     * accumulation path, which is the historically-buggy code path. */
    size_t mid = size / 2;
    accumulating_reader_add_data(&reader, data, mid);
    for (int guard = 0; guard < 100000; guard++) {
        frame_msg_info_t msg;
        if (!accumulating_reader_try_next(&reader, &msg)) break;
    }
    accumulating_reader_add_data(&reader, data + mid, size - mid);
    for (int guard = 0; guard < 100000; guard++) {
        frame_msg_info_t msg;
        if (!accumulating_reader_try_next(&reader, &msg)) break;
    }
}

int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    if (size == 0) return 0;
    /* Exercise every shipped profile. */
    fuzz_one_profile(&PROFILE_STANDARD_CONFIG, data, size);
    fuzz_one_profile(&PROFILE_SENSOR_CONFIG,   data, size);
    fuzz_one_profile(&PROFILE_IPC_CONFIG,      data, size);
    fuzz_one_profile(&PROFILE_BULK_CONFIG,     data, size);
    fuzz_one_profile(&PROFILE_NETWORK_CONFIG,  data, size);
    return 0;
}
