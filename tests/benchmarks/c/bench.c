// Tier D benchmark for C: runs the generated serialize/deserialize code and the real
// frame_profiles.h encoder/parser against tests/benchmarks/schema/bench.sf.
// Build with -I<generated c dir> (run_all.py does this). Emits results matching schema.json.
#define _POSIX_C_SOURCE 200809L

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifndef _WIN32
#include <sys/utsname.h>
#endif

#include "bench.structframe.h"
#include "frame_profiles.h"

#define BATCH 64
#define WARMUP_BATCHES 20

static uint64_t now_ns(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (uint64_t)ts.tv_sec * 1000000000ull + ts.tv_nsec;
}

static int cmp_u64(const void* a, const void* b) {
  uint64_t x = *(const uint64_t*)a, y = *(const uint64_t*)b;
  return (x > y) - (x < y);
}

static uint64_t pct(uint64_t* v, int n, double q) {
  qsort(v, n, sizeof(uint64_t), cmp_u64);
  int i = (int)((n - 1) * q);
  if (i < 0) i = 0;
  if (i >= n) i = n - 1;
  return v[i];
}

struct scen {
  const char* name;
  const profile_config_t* cfg;
  uint16_t msg_id;
  size_t size;
  uint8_t magic1, magic2;
};

static const struct scen scens[] = {
  {"standard", &PROFILE_STANDARD_CONFIG, BENCH_SMALL_MSG_ID,  BENCH_SMALL_MAX_SIZE,
   BENCH_SMALL_MAGIC1,  BENCH_SMALL_MAGIC2},
  {"bulk",     &PROFILE_BULK_CONFIG,     BENCH_LARGE_MSG_ID,  BENCH_LARGE_MAX_SIZE,
   BENCH_LARGE_MAGIC1,  BENCH_LARGE_MAGIC2},
  {"network",  &PROFILE_NETWORK_CONFIG,  BENCH_MEDIUM_MSG_ID, BENCH_MEDIUM_MAX_SIZE,
   BENCH_MEDIUM_MAGIC1, BENCH_MEDIUM_MAGIC2},
  {"sensor",   &PROFILE_SENSOR_CONFIG,   BENCH_SMALL_MSG_ID,  BENCH_SMALL_MAX_SIZE,
   BENCH_SMALL_MAGIC1,  BENCH_SMALL_MAGIC2},
  {"ipc",      &PROFILE_IPC_CONFIG,      BENCH_SMALL_MSG_ID,  BENCH_SMALL_MAX_SIZE,
   BENCH_SMALL_MAGIC1,  BENCH_SMALL_MAGIC2},
};

// Sink that keeps the optimiser from discarding the work being measured.
static volatile uint64_t g_sink;

static size_t encode_once(const struct scen* s, const uint8_t* payload, uint8_t seq, uint8_t* out) {
  buffer_writer_t w;
  buffer_writer_init(&w, s->cfg, out, 2048);
  size_t n = buffer_writer_write(&w, s->msg_id, payload, s->size, seq, 1, 42, 0,
                                 s->magic1, s->magic2);
  if (n == 0) {
    fprintf(stderr, "encode failed\n");
    exit(2);
  }
  return n;
}

static size_t decode_once(const struct scen* s, const uint8_t* frame, size_t flen) {
  frame_msg_info_t info = profile_parse(s->cfg, frame, flen, bench_get_message_info);
  if (!info.valid) {
    fprintf(stderr, "decode failed\n");
    exit(3);
  }
  uint8_t sink;
  switch (s->msg_id) {
    case BENCH_SMALL_MSG_ID: {
      BenchSmall m;
      BenchSmall_deserialize(info.msg_data, info.msg_len, &m);
      sink = m.data[0];
      break;
    }
    case BENCH_LARGE_MSG_ID: {
      BenchLarge m;
      BenchLarge_deserialize(info.msg_data, info.msg_len, &m);
      sink = m.data[0];
      break;
    }
    default: {
      BenchMedium m;
      BenchMedium_deserialize(info.msg_data, info.msg_len, &m);
      sink = m.data[0];
      break;
    }
  }
  g_sink += sink;
  return flen;
}

static void run(FILE* fp, const struct scen* s, const char* op, int iters, int comma) {
  uint8_t payload[600];
  for (size_t i = 0; i < s->size; i++) payload[i] = (uint8_t)(i * 31);
  uint8_t frames[8][2048];
  size_t flen[8];
  uint8_t frame[2048];
  for (int i = 0; i < 8; i++) flen[i] = encode_once(s, payload, (uint8_t)i, frames[i]);
  int is_encode = strcmp(op, "encode") == 0;

  for (int i = 0; i < WARMUP_BATCHES * BATCH; i++) {
    if (is_encode) g_sink += encode_once(s, payload, (uint8_t)i, frame);
    else g_sink += decode_once(s, frames[i & 7], flen[i & 7]);
  }

  int batches = iters / BATCH;
  if (batches < 1) batches = 1;
  uint64_t* lat = (uint64_t*)calloc((size_t)batches, sizeof(uint64_t));
  size_t bytes = 0;
  uint64_t start = now_ns();
  for (int b = 0; b < batches; b++) {
    uint64_t t = now_ns();
    for (int j = 0; j < BATCH; j++) {
      int i = b * BATCH + j;
      if (is_encode) bytes += encode_once(s, payload, (uint8_t)i, frame);
      else bytes += decode_once(s, frames[i & 7], flen[i & 7]);
    }
    lat[b] = (now_ns() - t) / BATCH;
  }
  double dur = (now_ns() - start) / 1e9;
  if (dur <= 0) dur = 1e-9;
  int count = batches * BATCH;
  uint64_t max = 0;
  for (int i = 0; i < batches; i++) {
    if (lat[i] > max) max = lat[i];
  }
  uint64_t p50 = pct(lat, batches, 0.50);
  uint64_t p95 = pct(lat, batches, 0.95);
  uint64_t p99 = pct(lat, batches, 0.99);
  fprintf(fp,
          "%s{\"name\":\"%s_%s\",\"profile\":\"%s\",\"operation\":\"%s\","
          "\"msg_count\":%d,\"bytes_total\":%zu,\"duration_s\":%.9f,"
          "\"msg_per_sec\":%.3f,\"mb_per_sec\":%.3f,"
          "\"latency_ns\":{\"p50\":%llu,\"p95\":%llu,\"p99\":%llu,\"max\":%llu}}",
          comma ? "," : "", s->name, op, s->name, op,
          count, bytes, dur, count / dur, bytes / dur / 1e6,
          (unsigned long long)p50, (unsigned long long)p95,
          (unsigned long long)p99, (unsigned long long)max);
  free(lat);
}

int main(int argc, char** argv) {
  int iters = getenv("BENCH_ITERATIONS")
                  ? atoi(getenv("BENCH_ITERATIONS"))
                  : 50000;
  const char* out = "tests/benchmarks/results/c.json";
  for (int i = 1; i < argc; i++) {
    if (!strcmp(argv[i], "--iterations") && i + 1 < argc) {
      iters = atoi(argv[++i]);
    } else if (!strcmp(argv[i], "--output") && i + 1 < argc) {
      out = argv[++i];
    }
  }
  FILE* fp = fopen(out, "w");
  if (!fp) {
    perror(out);
    return 1;
  }
  time_t t = time(NULL);
  char ts[64];
  strftime(ts, sizeof ts, "%Y-%m-%dT%H:%M:%SZ", gmtime(&t));
  char os[128] = "unknown", arch[128] = "unknown";
#ifndef _WIN32
  struct utsname u;
  if (uname(&u) == 0) {
    snprintf(os, sizeof os, "%.63s", u.sysname);
    snprintf(arch, sizeof arch, "%.63s", u.machine);
  }
#endif
  fprintf(fp,
          "{\"schema_version\":\"1\",\"language\":\"c\","
          "\"runner_version\":\"tier-d-2-generated\",\"timestamp\":\"%s\","
          "\"host\":{\"os\":\"%s\",\"arch\":\"%s\",\"cpu\":\"unknown\"},"
          "\"scenarios\":[",
          ts, os, arch);
  int comma = 0;
  for (size_t i = 0; i < sizeof(scens) / sizeof(scens[0]); i++) {
    run(fp, &scens[i], "encode", iters, comma++);
    run(fp, &scens[i], "decode", iters, comma++);
  }
  fprintf(fp, "]}\n");
  fclose(fp);
  return 0;
}
