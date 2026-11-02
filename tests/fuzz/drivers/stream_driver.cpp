// Stream driver: stream_driver <profile> <stream.bin> <chunk>
// Mirrors stream_driver.c; the message table matches tests/fuzz/corpus.py.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#include "frame_profiles.hpp"

using namespace structframe;

static MessageInfo get_info(uint16_t id) {
  switch (id) {
    case 1: return MessageInfo(8, 11, 22);
    case 2: return MessageInfo(32, 33, 44);
    case 3: return MessageInfo(100, 55, 66);
    case 4: return MessageInfo(1, 77, 88);
    case 5: return MessageInfo(200, 99, 111);
    default: return MessageInfo();
  }
}

static uint32_t fnv1a(const uint8_t* d, size_t n) {
  uint32_t h = 0x811C9DC5u;
  for (size_t i = 0; i < n; i++) h = (h ^ d[i]) * 0x01000193u;
  return h;
}

template <typename Config>
static void run(const std::vector<uint8_t>& data, size_t chunk) {
  AccumulatingReader<Config, 1024, MessageInfo (*)(uint16_t)> reader(get_info);
  for (size_t pos = 0; pos < data.size(); pos += chunk) {
    size_t len = data.size() - pos < chunk ? data.size() - pos : chunk;
    reader.add_data(data.data() + pos, len);
    FrameMsgInfo f;
    for (int guard = 0; guard < 1000000 && reader.try_next(f); guard++) {
      if (f.valid) std::printf("%u %zu %u\n", f.msg_id, f.msg_len, fnv1a(f.msg_data, f.msg_len));
    }
  }
}

int main(int argc, char** argv) {
  if (argc != 4) return 64;
  std::string profile = argv[1];
  size_t chunk = std::strtoull(argv[3], nullptr, 10);
  std::ifstream in(argv[2], std::ios::binary);
  std::vector<uint8_t> data((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
  if (profile == "standard") run<ProfileStandardConfig>(data, chunk);
  else if (profile == "sensor") run<ProfileSensorConfig>(data, chunk);
  else if (profile == "ipc") run<ProfileIPCConfig>(data, chunk);
  else if (profile == "bulk") run<ProfileBulkConfig>(data, chunk);
  else if (profile == "network") run<ProfileNetworkConfig>(data, chunk);
  else return 64;
  return 0;
}
