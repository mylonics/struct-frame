/**
 * Test entry point for extended message ID and payload tests (JavaScript).
 *
 * Usage:
 *   node test_extended.js encode <frame_format> <output_file>
 *   node test_extended.js decode <frame_format> <input_file>
 *
 * Frame formats (extended profiles only): profile_bulk, profile_network
 */

const { runTestMain } = require('./include/test_codec');
const { extTestConfig } = require('./include/extended_test_data');

process.exit(runTestMain(extTestConfig));
