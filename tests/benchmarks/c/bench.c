// Tier D shared-schema benchmark for C (sibling of tests/benchmarks/cpp/bench.cpp).
// Self-contained: emits tests/benchmarks/results/c.json matching schema.json.
#define _POSIX_C_SOURCE 200809L

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifndef _WIN32
#include <sys/utsname.h>
#endif

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

static void fletcher(const uint8_t* d, size_t n, uint8_t* o1, uint8_t* o2) {
  unsigned a = 0, b = 0;
  for (size_t i = 0; i < n; i++) {
    a = (a + d[i]) & 0xff;
    b = (b + a) & 0xff;
  }
  *o1 = (uint8_t)a;
  *o2 = (uint8_t)b;
}

static size_t encode(const char* profile, uint8_t type, size_t payload_len,
                     int network, uint8_t seq, uint8_t* out) {
  size_t b = 2;
  out[0] = 0x90;
  out[1] = type;
  if (network) {
    out[b++] = seq;
    out[b++] = 1;
    out[b++] = 42;
    out[b++] = payload_len & 0xff;
    out[b++] = (payload_len >> 8) & 0xff;
    out[b++] = 7;
    out[b++] = 3;
  } else if (strcmp(profile, "bulk") == 0) {
    out[b++] = payload_len & 0xff;
    out[b++] = (payload_len >> 8) & 0xff;
    out[b++] = 7;
    out[b++] = 3;
  } else {
    out[b++] = payload_len & 0xff;
    out[b++] = 3;
  }
  for (size_t i = 0; i < payload_len; i++) {
    out[b++] = (uint8_t)((i * 31 + payload_len) & 0xff);
  }
  uint8_t c1, c2;
  fletcher(out + 2, b - 2, &c1, &c2);
  out[b++] = c1;
  out[b++] = c2;
  return b;
}

static size_t decode(const uint8_t* f) {
  size_t off = 2, len = 0;
  int p = f[1] - 0x70;
  if (p == 8) {
    off += 3;
    len = f[off] | (f[off + 1] << 8);
    off += 4;
  } else if (p == 4) {
    len = f[off] | (f[off + 1] << 8);
    off += 4;
  } else {
    len = f[off];
    off += 2;
  }
  uint8_t c1, c2;
  fletcher(f + 2, off + len - 2, &c1, &c2);
  if (f[off + len] != c1 || f[off + len + 1] != c2) {
    fprintf(stderr, "bad crc\n");
    exit(2);
  }
  return len;
}

struct scen {
  const char* name;
  const char* profile;
  uint8_t type;
  size_t len;
  int network;
};

static struct scen scens[] = {
  {"standard", "standard", 0x71, 32,  0},
  {"bulk",     "bulk",     0x74, 512, 0},
  {"network",  "network",  0x78, 96,  1},
};

static void run(FILE* fp, struct scen* s, const char* op, int iters, int comma) {
  uint8_t frame[2048];
  uint8_t frames[8][2048];
  size_t flen[8];
  for (int i = 0; i < 8; i++) {
    flen[i] = encode(s->profile, s->type, s->len, s->network,
                     (uint8_t)i, frames[i]);
  }
  uint64_t* lat = (uint64_t*)calloc((size_t)iters, sizeof(uint64_t));
  size_t bytes = 0;
  uint64_t start = now_ns();
  for (int i = 0; i < iters; i++) {
    uint64_t t = now_ns();
    if (strcmp(op, "encode") == 0) {
      bytes += encode(s->profile, s->type, s->len, s->network,
                      (uint8_t)i, frame);
    } else {
      decode(frames[i & 7]);
      bytes += flen[i & 7];
    }
    lat[i] = now_ns() - t;
  }
  double dur = (now_ns() - start) / 1e9;
  if (dur <= 0) dur = 1e-9;
  uint64_t max = 0;
  for (int i = 0; i < iters; i++) {
    if (lat[i] > max) max = lat[i];
  }
  uint64_t p50 = pct(lat, iters, 0.50);
  uint64_t p95 = pct(lat, iters, 0.95);
  uint64_t p99 = pct(lat, iters, 0.99);
  fprintf(fp,
          "%s{\"name\":\"%s_%s\",\"profile\":\"%s\",\"operation\":\"%s\","
          "\"msg_count\":%d,\"bytes_total\":%zu,\"duration_s\":%.9f,"
          "\"msg_per_sec\":%.3f,\"mb_per_sec\":%.3f,"
          "\"latency_ns\":{\"p50\":%llu,\"p95\":%llu,\"p99\":%llu,\"max\":%llu}}",
          comma ? "," : "", s->name, op, s->profile, op,
          iters, bytes, dur, iters / dur, bytes / dur / 1e6,
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
          "\"runner_version\":\"tier-d-1\",\"timestamp\":\"%s\","
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
