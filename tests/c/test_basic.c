/**
 * Test entry point for basic message tests (C).
 *
 * Usage:
 *   test_runner encode <frame_format> <output_file>
 *   test_runner decode <frame_format> <input_file>
 *
 * Frame formats: profile_basic, profile_sensor, profile_ipc, profile_bulk, profile_network
 */

#include "include/basic_test_data.h"

int main(int argc, char* argv[]) { return run_test_main(&basic_test_config, argc, argv); }
