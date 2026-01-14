/**
 * Test entry point for variable flag truncation tests (TypeScript).
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

import { runTestMain } from './include/test_codec';
import { variableFlagTestConfig } from './include/variable_flag_test_data';

process.exit(runTestMain(variableFlagTestConfig));
