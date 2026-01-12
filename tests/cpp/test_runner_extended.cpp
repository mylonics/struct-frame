/**
 * Test runner entry point for C++ - Extended message ID and payload tests.
 *
 * Usage:
 *   test_runner_extended encode <frame_format> <output_file>
 *   test_runner_extended decode <frame_format> <input_file>
 *
 * Frame formats (extended profiles only): profile_bulk, profile_network
 */

#include "base/test_codec_extended.hpp"
#include "base/test_runner_common.hpp"

static const size_t MAX_BUFFER_SIZE = 8192;  // Larger for extended payloads
static const char* FORMATS_HELP = "profile_bulk, profile_network";

int main(int argc, char* argv[]) {
  if (argc != 4) {
    TestRunner::print_usage(argv[0], FORMATS_HELP);
    return 1;
  }

  return TestRunner::run_test(argv[1], argv[2], argv[3], "C++ Extended", MAX_BUFFER_SIZE, encode_extended_messages,
                              decode_extended_messages);
}
