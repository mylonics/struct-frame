/**
 * Test entry point for standard message tests (C++).
 *
 * Usage:
 *   test_runner encode <frame_format> <output_file>
 *   test_runner decode <frame_format> <input_file>
 *
 * Frame formats: profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network
 */

#include "include/standard_test_data.hpp"
#include "include/test_codec.hpp"

int main(int argc, char* argv[]) { return TestCodec::run_test_main<TestMessagesData::Config>(argc, argv); }
