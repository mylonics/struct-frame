/**
 * Test entry point for basic message tests (JavaScript).
 *
 * Usage:
 *   node test_basic.js encode <frame_format> <output_file>
 *   node test_basic.js decode <frame_format> <input_file>
 *
 * Frame formats: profile_basic, profile_sensor, profile_ipc, profile_bulk, profile_network
 */

const { runTestMain } = require('./include/test_codec');
const { basicTestConfig } = require('./include/basic_test_data');

process.exit(runTestMain(basicTestConfig));
