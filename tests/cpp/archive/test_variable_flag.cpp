/**
 * Test entry point for variable flag truncation tests (C++).
 *
 * This test validates that messages with option variable = true properly
 * truncate unused array space, while non-variable messages do not.
 *
 * Usage:
 *   test_variable_flag encode <frame_format> <output_file>
 *   test_variable_flag decode <frame_format> <input_file>
 *
 * Frame formats: profile_bulk (only profile that supports extended features)
 */

#include "include/test_codec.hpp"
#include "include/variable_flag_test_data.hpp"

int main(int argc, char* argv[]) { return TestCodec::run_test_main<VariableFlagTestData::Config>(argc, argv); }
