/**
 * Test entry point for basic message tests (TypeScript).
 *
 * Usage:
 *   node test_basic.js encode <frame_format> <output_file>
 *   node test_basic.js decode <frame_format> <input_file>
 *
 * Frame formats: profile_basic, profile_sensor, profile_ipc, profile_bulk, profile_network
 */

import { runTestMain } from './include/test_codec';
import { basicTestConfig } from './include/basic_test_data';

process.exit(runTestMain(basicTestConfig));
