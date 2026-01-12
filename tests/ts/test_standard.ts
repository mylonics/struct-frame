/**
 * Test entry point for standard message tests (TypeScript).
 *
 * Usage:
 *   node test_standard.js encode <frame_format> <output_file>
 *   node test_standard.js decode <frame_format> <input_file>
 *
 * Frame formats: profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network
 */

import { runTestMain } from './include/test_codec';
import { stdTestConfig } from './include/standard_test_data';

process.exit(runTestMain(stdTestConfig));
