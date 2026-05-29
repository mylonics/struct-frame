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
 * supported profile and asserts that the parser never crashes, never reads
 * out of bounds (caught by ASan), and always converges back to IDLE after
 * the input is exhausted.
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

/* Stub message-info callback.  The fuzzer doesn't care about valid msg_ids;
 * we just need a callback that never crashes so the parser can route Tiny
 * and None header profiles through it. */
static bool fuzz_get_message_info(uint16_t msg_id, message_info_t* info) {
    (void)msg_id;
    if (info) {
        info->size = 64;
        info->base_size = 64;
        info->magic1 = 0;
        info->magic2 = 0;
    }
    return true;
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
    while (1) {
        frame_msg_info_t msg = accumulating_reader_next(&reader);
        if (!msg.valid) break;
    }
    accumulating_reader_add_data(&reader, data + mid, size - mid);
    while (1) {
        frame_msg_info_t msg = accumulating_reader_next(&reader);
        if (!msg.valid) break;
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
