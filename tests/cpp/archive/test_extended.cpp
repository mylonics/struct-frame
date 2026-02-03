/**
 * Test entry point for extended message ID and payload tests (C++).
 *
 * Usage:
 *   test_runner_extended encode <frame_format> <output_file>
 *   test_runner_extended decode <frame_format> <input_file>
 *
 * Frame formats (extended profiles only): profile_bulk, profile_network
 */

#include "include/extended_test_data.hpp"
#include "include/test_codec.hpp"

int main(int argc, char* argv[]) { return TestCodec::run_test_main<ExtendedTestMessages::Config>(argc, argv); }
