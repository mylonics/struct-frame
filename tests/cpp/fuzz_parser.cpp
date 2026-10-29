// LibFuzzer entry point for the C++ AccumulatingReader.
//
//   clang++ -std=c++20 -O1 -g -fsanitize=fuzzer,address,undefined \
//       -I src/struct_frame/boilerplate/cpp tests/cpp/fuzz_parser.cpp -o fuzz_parser_cpp
//   python tests/fuzz/make_seed_corpus.py corpus && ./fuzz_parser_cpp -max_len=4096 corpus
//
// Uses the real message table from tests/fuzz/corpus.py so seed frames pass the checksum.
#include <cstddef>
#include <cstdint>

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

template <typename Config>
static void drive(const uint8_t* data, size_t size) {
  AccumulatingReader<Config, 1024, MessageInfo (*)(uint16_t)> reader(get_info);
  size_t mid = size / 2;
  const size_t cuts[3] = {0, mid, size};
  for (int i = 0; i < 2; i++) {
    reader.add_data(data + cuts[i], cuts[i + 1] - cuts[i]);
    FrameMsgInfo f;
    for (int guard = 0; guard < 100000 && reader.try_next(f); guard++) {
    }
  }
}

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
  if (size == 0) return 0;
  drive<ProfileStandardConfig>(data, size);
  drive<ProfileSensorConfig>(data, size);
  drive<ProfileIPCConfig>(data, size);
  drive<ProfileBulkConfig>(data, size);
  drive<ProfileNetworkConfig>(data, size);
  return 0;
}
