// Tier D benchmark for C++: runs the generated message types and the real frame_profiles.hpp
// writer/reader against tests/benchmarks/schema/bench.sf. Build with -I<generated cpp dir>
// (run_all.py does this). Emits results matching schema.json.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <string>
#include <vector>

#include "bench.structframe.hpp"
#include "frame_profiles.hpp"

using namespace structframe;
using namespace structframe::bench;

static constexpr int kBatch = 64;
static constexpr int kWarmupBatches = 20;
static volatile uint64_t g_sink;  // keeps the optimiser from discarding measured work

// Tell the compiler the bytes at p are used, so it cannot drop an encode whose output is
// never read again (which made the minimal-profile encodes look free).
static inline void escape(const void* p) {
#if defined(__GNUC__) || defined(__clang__)
  asm volatile("" : : "g"(p) : "memory");
#else
  g_sink += reinterpret_cast<uintptr_t>(p) & 1;
#endif
}

static uint64_t now_ns() {
  return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                   std::chrono::steady_clock::now().time_since_epoch())
                                   .count());
}

static uint64_t pct(std::vector<uint64_t>& v, double q) {
  std::sort(v.begin(), v.end());
  size_t i = static_cast<size_t>((v.size() - 1) * q);
  return v[std::min(i, v.size() - 1)];
}

template <typename Config, typename Msg>
static size_t encode_once(const Msg& msg, uint8_t seq, uint8_t* out, size_t cap) {
  BufferWriter<Config> w(out, cap);
  size_t n;
  if constexpr (Config::has_seq) {
    n = w.write(msg, seq, 1, 42);
  } else {
    n = w.write(msg);
  }
  if (n == 0) {
    std::fprintf(stderr, "encode failed\n");
    std::exit(2);
  }
  escape(out);
  return n;
}

template <typename Config, typename Msg>
static size_t decode_once(const uint8_t* frame, size_t len) {
  BufferReader<Config, MessageInfo (*)(uint16_t)> reader(frame, len, get_message_info);
  FrameMsgInfo info = reader.next();
  if (!info.valid) {
    std::fprintf(stderr, "decode failed\n");
    std::exit(3);
  }
  Msg m;
  m.deserialize(info);
  g_sink += m.data[0];
  return len;
}

template <typename Config, typename Msg>
static std::string run(const char* name, const char* op, int iters) {
  Msg msg;
  for (size_t i = 0; i < sizeof(msg.data); i++) msg.data[i] = static_cast<uint8_t>(i * 31);
  static uint8_t frames[8][2048];
  size_t flen[8];
  static uint8_t frame[2048];
  for (int i = 0; i < 8; i++) flen[i] = encode_once<Config>(msg, static_cast<uint8_t>(i), frames[i], sizeof frames[i]);
  bool is_encode = std::strcmp(op, "encode") == 0;
  auto one = [&](int i) -> size_t {
    return is_encode ? encode_once<Config>(msg, static_cast<uint8_t>(i), frame, sizeof frame)
                     : decode_once<Config, Msg>(frames[i & 7], flen[i & 7]);
  };

  for (int i = 0; i < kWarmupBatches * kBatch; i++) g_sink += one(i);

  int batches = std::max(1, iters / kBatch);
  std::vector<uint64_t> lat(static_cast<size_t>(batches));
  size_t bytes = 0;
  uint64_t start = now_ns();
  for (int b = 0; b < batches; b++) {
    uint64_t t = now_ns();
    for (int j = 0; j < kBatch; j++) bytes += one(b * kBatch + j);
    lat[static_cast<size_t>(b)] = (now_ns() - t) / kBatch;
  }
  double dur = std::max((now_ns() - start) / 1e9, 1e-9);
  int count = batches * kBatch;
  uint64_t max = *std::max_element(lat.begin(), lat.end());
  uint64_t p50 = pct(lat, 0.50), p95 = pct(lat, 0.95), p99 = pct(lat, 0.99);
  char buf[512];
  std::snprintf(buf, sizeof buf,
                "{\"name\":\"%s_%s\",\"profile\":\"%s\",\"operation\":\"%s\",\"msg_count\":%d,"
                "\"bytes_total\":%zu,\"duration_s\":%.9f,\"msg_per_sec\":%.3f,\"mb_per_sec\":%.3f,"
                "\"latency_ns\":{\"p50\":%llu,\"p95\":%llu,\"p99\":%llu,\"max\":%llu}}",
                name, op, name, op, count, bytes, dur, count / dur, bytes / dur / 1e6,
                static_cast<unsigned long long>(p50), static_cast<unsigned long long>(p95),
                static_cast<unsigned long long>(p99), static_cast<unsigned long long>(max));
  return buf;
}

template <typename Config, typename Msg>
static void both(std::vector<std::string>& out, const char* name, int iters) {
  out.push_back(run<Config, Msg>(name, "encode", iters));
  out.push_back(run<Config, Msg>(name, "decode", iters));
}

int main(int argc, char** argv) {
  int iters = std::getenv("BENCH_ITERATIONS") ? std::atoi(std::getenv("BENCH_ITERATIONS")) : 50000;
  std::string out_path = "tests/benchmarks/results/cpp.json";
  for (int i = 1; i < argc; i++) {
    if (!std::strcmp(argv[i], "--iterations") && i + 1 < argc) iters = std::atoi(argv[++i]);
    else if (!std::strcmp(argv[i], "--output") && i + 1 < argc) out_path = argv[++i];
  }
  std::vector<std::string> scenarios;
  both<ProfileStandardConfig, Small>(scenarios, "standard", iters);
  both<ProfileBulkConfig, Large>(scenarios, "bulk", iters);
  both<ProfileNetworkConfig, Medium>(scenarios, "network", iters);
  both<ProfileSensorConfig, Small>(scenarios, "sensor", iters);
  both<ProfileIPCConfig, Small>(scenarios, "ipc", iters);

  std::FILE* fp = std::fopen(out_path.c_str(), "w");
  if (!fp) {
    std::perror(out_path.c_str());
    return 1;
  }
  char ts[64];
  std::time_t t = std::time(nullptr);
  std::strftime(ts, sizeof ts, "%Y-%m-%dT%H:%M:%SZ", std::gmtime(&t));
#ifdef _WIN32
  const char* os = "Windows";
#elif defined(__APPLE__)
  const char* os = "Darwin";
#else
  const char* os = "Linux";
#endif
  std::fprintf(fp,
               "{\"schema_version\":\"1\",\"language\":\"cpp\",\"runner_version\":\"tier-d-2-generated\","
               "\"timestamp\":\"%s\",\"host\":{\"os\":\"%s\",\"arch\":\"unknown\",\"cpu\":\"unknown\"},"
               "\"scenarios\":[",
               ts, os);
  for (size_t i = 0; i < scenarios.size(); i++) std::fprintf(fp, "%s%s", i ? "," : "", scenarios[i].c_str());
  std::fprintf(fp, "]}\n");
  std::fclose(fp);
  return 0;
}
