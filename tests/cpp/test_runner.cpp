/**
 * Test runner entry point for C++.
 *
 * Usage:
 *   test_runner encode <frame_format> <output_file>
 *   test_runner decode <frame_format> <input_file>
 *
 * Frame formats: profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network
 */

#include "base/test_codec.hpp"
#include "base/test_runner_common.hpp"

static const size_t MAX_BUFFER_SIZE = 4096;
static const char* FORMATS_HELP = "profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network";

int main(int argc, char* argv[]) {
  if (argc != 4) {
    TestRunner::print_usage(argv[0], FORMATS_HELP);
    return 1;
  }

  return TestRunner::run_test(argv[1], argv[2], argv[3], "C++", MAX_BUFFER_SIZE, encode_test_messages,
                              decode_test_messages);
}
