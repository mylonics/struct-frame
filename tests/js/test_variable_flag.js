/**
 * Test entry point for variable flag truncation tests (JavaScript).
 *
 * This test validates that messages with option variable = true properly
 * truncate unused array space, while non-variable messages do not.
 *
 * Usage:
 *   node test_variable_flag.js encode <frame_format> <output_file>
 *   node test_variable_flag.js decode <frame_format> <input_file>
 *
 * Frame formats: profile_bulk (only profile that supports extended features)
 */

const { runTestMain } = require('./include/test_codec');
const { variableFlagTestConfig } = require('./include/variable_flag_test_data');

process.exit(runTestMain(variableFlagTestConfig));
