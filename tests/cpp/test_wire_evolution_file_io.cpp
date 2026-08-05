/**
 * Cross-language x cross-version wire-evolution file I/O.
 *
 * Minimal CLI so another language's process can drive this binary via real
 * subprocess + file interchange, instead of every wire-evolution-interop
 * scenario only ever running in-process within a single language (which is
 * what test_wire_evolution_interop.* do in every language today -- see
 * tests/README.md and tests/test_wire_evolution_interop.py). This exists
 * specifically so tests/test_wire_evolution_cross_lang.py can prove that a
 * v1 frame encoded by one language is correctly read (with the extension
 * filled with its schema default) by another language's v2 decoder, and
 * vice versa.
 *
 * Usage:
 *   test_wire_evolution_file_io encode v1 <file>
 *   test_wire_evolution_file_io encode v2 <file>
 *   test_wire_evolution_file_io decode v1 <file>
 *   test_wire_evolution_file_io decode v2 <file>
 *
 * The canonical message is BaseExtensionMessage: v1 has {header, seq}; v2
 * adds the {crc_seed} extension field (extensions_start=3). Encode always
 * uses fixed canonical values (header=0x1234, seq=42, crc_seed=0xDEADBEEF)
 * so the caller can assert on known output.
 */
#include <cstdint>
#include <cstdio>
#include <cstring>

#include "../generated/cpp/wire_evolution_v1.structframe.hpp"
#include "../generated/cpp/wire_evolution_v2.structframe.hpp"

using namespace structframe;

static constexpr uint16_t kHeader = 0x1234;
static constexpr uint8_t kSeq = 42;
static constexpr uint32_t kCrcSeed = 0xDEADBEEF;

static int do_encode(const char* version, const char* path) {
  FILE* f = fopen(path, "wb");
  if (!f) {
    fprintf(stderr, "[ENCODE] FAILED: cannot open %s for writing\n", path);
    return 1;
  }
  uint8_t buf[16];
  size_t n;
  if (std::strcmp(version, "v1") == 0) {
    wire_evolution_v1::BaseExtensionMessage msg{};
    msg.header = kHeader;
    msg.seq = kSeq;
    n = msg.serialize(buf);
  } else if (std::strcmp(version, "v2") == 0) {
    wire_evolution_v2::BaseExtensionMessage msg{};
    msg.header = kHeader;
    msg.seq = kSeq;
    msg.crc_seed = kCrcSeed;
    n = msg.serialize(buf);
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

  if (std::strcmp(version, "v1") == 0) {
    wire_evolution_v1::BaseExtensionMessage msg{};
    size_t r = msg.deserialize(buf, n);
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
  } else if (std::strcmp(version, "v2") == 0) {
    wire_evolution_v2::BaseExtensionMessage msg{};
    size_t r = msg.deserialize(buf, n);
    if (r == 0) {
      fprintf(stderr, "[DECODE] FAILED: deserialize returned 0\n");
      return 1;
    }
    if (msg.header != kHeader || msg.seq != kSeq) {
      fprintf(stderr, "[DECODE] FAILED: header=0x%04x (expected 0x%04x) seq=%u (expected %u)\n",
              msg.header, kHeader, msg.seq, kSeq);
      return 1;
    }
    // A legacy (v1-sized, 3-byte) frame decoded as v2 must fill the extension
    // with its schema default (4242, not zero); a genuine v2-sized (7-byte)
    // frame must preserve the transmitted value.
    uint32_t expected_crc = (n >= wire_evolution_v2::BaseExtensionMessage::BASE_SIZE + 4) ? kCrcSeed : 4242;
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

  if (std::strcmp(mode, "encode") == 0) return do_encode(version, path);
  if (std::strcmp(mode, "decode") == 0) return do_decode(version, path);
  fprintf(stderr, "Unknown mode: %s\n", mode);
  return 2;
}
