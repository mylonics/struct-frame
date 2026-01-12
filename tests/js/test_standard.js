/**
 * Test entry point for standard message tests (JavaScript).
 *
 * Usage:
 *   node test_standard.js encode <frame_format> <output_file>
 *   node test_standard.js decode <frame_format> <input_file>
 *
 * Frame formats: profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network
 */

const { runTestMain } = require('./include/test_codec');
const { stdTestConfig } = require('./include/standard_test_data');

process.exit(runTestMain(stdTestConfig));
