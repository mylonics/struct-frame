/**
 * Test entry point for standard message tests (TypeScript).
 */

import { MESSAGE_COUNT, getMessage, checkMessage, checkEnumToString } from './include/standard_messages';
import { getMessageInfo } from '../generated/ts/serialization-test.structframe';
import { run } from './include/test_harness';

const TEST_NAME = 'StandardMessages';
const PROFILES = 'standard, sensor, ipc, bulk, network';

// Verify enum-to-string (reverse mapping) before running the main test suite
if (!checkEnumToString()) {
  console.error('[FAIL] TypeScript enum-to-string reverse mapping check failed');
  process.exit(1);
}

process.exit(run(MESSAGE_COUNT, getMessage, checkMessage, getMessageInfo, TEST_NAME, PROFILES));
