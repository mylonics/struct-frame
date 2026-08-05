/**
 * Cross-language x cross-version wire-evolution file I/O (C).
 * See tests/cpp/test_wire_evolution_file_io.cpp for the full rationale.
 *
 * Usage:
 *   test_wire_evolution_file_io encode v1 <file>
 *   test_wire_evolution_file_io encode v2 <file>
 *   test_wire_evolution_file_io decode v1 <file>
 *   test_wire_evolution_file_io decode v2 <file>
 *
 * Canonical values must match every other language's file_io helper:
 * header=0x1234, seq=42, crc_seed=0xDEADBEEF.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "wire_evolution_v1.structframe.h"
#include "wire_evolution_v2.structframe.h"

static const uint16_t kHeader = 0x1234;
static const uint8_t kSeq = 42;
static const uint32_t kCrcSeed = 0xDEADBEEF;

static int do_encode(const char* version, const char* path) {
  FILE* f = fopen(path, "wb");
  if (!f) {
    fprintf(stderr, "[ENCODE] FAILED: cannot open %s for writing\n", path);
    return 1;
  }
  uint8_t buf[16];
  size_t n;
  if (strcmp(version, "v1") == 0) {
    WireEvolutionV1BaseExtensionMessage msg;
    memset(&msg, 0, sizeof(msg));
    msg.header = kHeader;
    msg.seq = kSeq;
    n = WireEvolutionV1BaseExtensionMessage_serialize(&msg, buf);
  } else if (strcmp(version, "v2") == 0) {
    WireEvolutionV2BaseExtensionMessage msg;
    memset(&msg, 0, sizeof(msg));
    msg.header = kHeader;
    msg.seq = kSeq;
    msg.crc_seed = kCrcSeed;
    n = WireEvolutionV2BaseExtensionMessage_serialize(&msg, buf);
  } else {
    fprintf(stderr, "[ENCODE] FAILED: unknown version '%s'\n", version);
    fclose(f);
    return 1;
  }
  fwrite(buf, 1, n, f);
  fclose(f);
  printf("[ENCODE] SUCCESS: wrote %zu bytes (%s) to %s\n", n, version, path);
  return 0;
}

static int do_decode(const char* version, const char* path) {
  FILE* f = fopen(path, "rb");
  if (!f) {
    fprintf(stderr, "[DECODE] FAILED: cannot open %s for reading\n", path);
    return 1;
  }
  uint8_t buf[16];
  size_t n = fread(buf, 1, sizeof(buf), f);
  fclose(f);

  if (strcmp(version, "v1") == 0) {
    WireEvolutionV1BaseExtensionMessage msg;
    size_t r = WireEvolutionV1BaseExtensionMessage_deserialize(buf, n, &msg);
    if (r == 0) {
      fprintf(stderr, "[DECODE] FAILED: deserialize returned 0\n");
      return 1;
    }
    if (msg.header != kHeader || msg.seq != kSeq) {
      fprintf(stderr, "[DECODE] FAILED: header=0x%04x (expected 0x%04x) seq=%u (expected %u)\n",
              msg.header, kHeader, msg.seq, kSeq);
      return 1;
    }
    printf("[DECODE] SUCCESS: v1 header=0x%04x seq=%u\n", msg.header, msg.seq);
    return 0;
  } else if (strcmp(version, "v2") == 0) {
    WireEvolutionV2BaseExtensionMessage msg;
    size_t r = WireEvolutionV2BaseExtensionMessage_deserialize(buf, n, &msg);
    if (r == 0) {
      fprintf(stderr, "[DECODE] FAILED: deserialize returned 0\n");
      return 1;
    }
    if (msg.header != kHeader || msg.seq != kSeq) {
      fprintf(stderr, "[DECODE] FAILED: header=0x%04x (expected 0x%04x) seq=%u (expected %u)\n",
              msg.header, kHeader, msg.seq, kSeq);
      return 1;
    }
    /* 4242 is crc_seed's schema [default = ...]; an older sender never
     * transmits this field, so a short input must decode to the default,
     * not zero. */
    uint32_t expected_crc = (n >= WIRE_EVOLUTION_V2_BASE_EXTENSION_MESSAGE_BASE_SIZE + 4) ? kCrcSeed : 4242;
    if (msg.crc_seed != expected_crc) {
      fprintf(stderr, "[DECODE] FAILED: crc_seed=0x%08x (expected 0x%08x for %zu-byte input)\n",
              msg.crc_seed, expected_crc, n);
      return 1;
    }
    printf("[DECODE] SUCCESS: v2 header=0x%04x seq=%u crc_seed=0x%08x (from %zu bytes)\n",
           msg.header, msg.seq, msg.crc_seed, n);
    return 0;
  }
  fprintf(stderr, "[DECODE] FAILED: unknown version '%s'\n", version);
  return 1;
}

int main(int argc, char** argv) {
  if (argc != 4) {
    fprintf(stderr, "Usage: %s <encode|decode> <v1|v2> <file>\n", argv[0]);
    return 2;
  }
  const char* mode = argv[1];
  const char* version = argv[2];
  const char* path = argv[3];

  if (strcmp(mode, "encode") == 0) return do_encode(version, path);
  if (strcmp(mode, "decode") == 0) return do_decode(version, path);
  fprintf(stderr, "Unknown mode: %s\n", mode);
  return 2;
}
