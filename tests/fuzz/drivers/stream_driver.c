/* Stream driver: stream_driver <profile> <stream.bin> <chunk>
 * Feeds the file through accumulating_reader_t in <chunk>-byte slices and prints one
 * "<msg_id> <payload_len> <fnv1a>" line per valid frame. Uses the same message table as
 * tests/fuzz/corpus.py. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "frame_base.h"
#include "frame_headers.h"
#include "frame_profiles.h"

static const struct { uint16_t id; size_t size; uint8_t m1, m2; } TABLE[] = {
    {1, 8, 11, 22}, {2, 32, 33, 44}, {3, 100, 55, 66}, {4, 1, 77, 88}, {5, 200, 99, 111},
};

static bool get_info(uint16_t id, message_info_t* info) {
    for (size_t i = 0; i < sizeof(TABLE) / sizeof(TABLE[0]); i++) {
        if (TABLE[i].id == id) {
            info->size = info->base_size = info->min_size = TABLE[i].size;
            info->magic1 = TABLE[i].m1;
            info->magic2 = TABLE[i].m2;
            return true;
        }
    }
    return false;
}

static uint32_t fnv1a(const uint8_t* d, size_t n) {
    uint32_t h = 0x811C9DC5u;
    for (size_t i = 0; i < n; i++) h = (h ^ d[i]) * 0x01000193u;
    return h;
}

static const profile_config_t* pick(const char* name) {
    if (!strcmp(name, "standard")) return &PROFILE_STANDARD_CONFIG;
    if (!strcmp(name, "sensor")) return &PROFILE_SENSOR_CONFIG;
    if (!strcmp(name, "ipc")) return &PROFILE_IPC_CONFIG;
    if (!strcmp(name, "bulk")) return &PROFILE_BULK_CONFIG;
    if (!strcmp(name, "network")) return &PROFILE_NETWORK_CONFIG;
    return NULL;
}

int main(int argc, char** argv) {
    if (argc != 4) return 64;
    const profile_config_t* cfg = pick(argv[1]);
    if (!cfg) return 64;
    size_t chunk = (size_t)strtoull(argv[3], NULL, 10);
    FILE* f = fopen(argv[2], "rb");
    if (!f) return 65;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t* data = (uint8_t*)malloc((size_t)n + 1);
    if (fread(data, 1, (size_t)n, f) != (size_t)n) return 66;
    fclose(f);

    uint8_t internal[1024];
    accumulating_reader_t reader;
    accumulating_reader_init(&reader, cfg, internal, sizeof(internal), get_info);
    for (size_t pos = 0; pos < (size_t)n; pos += chunk) {
        size_t len = (size_t)n - pos < chunk ? (size_t)n - pos : chunk;
        accumulating_reader_add_data(&reader, data + pos, len);
        for (int guard = 0; guard < 1000000; guard++) {
            frame_msg_info_t m;
            if (!accumulating_reader_try_next(&reader, &m)) break;
            if (m.valid) printf("%u %zu %u\n", m.msg_id, m.msg_len, fnv1a(m.msg_data, m.msg_len));
        }
    }
    return 0;
}
