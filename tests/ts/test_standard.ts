/**
 * Test entry point for standard message tests (TypeScript).
 */

import { MESSAGE_COUNT, getMessage, checkMessage, checkEnumToString, checkDiscriminatorNone, checkMultiOneof } from './include/standard_messages';
import { getMessageInfo } from '../generated/ts/serialization-test.structframe';
import { run } from './include/test_harness';

const TEST_NAME = 'StandardMessages';
const PROFILES = 'standard, sensor, ipc, bulk, network';

// Verify enum-to-string (reverse mapping) before running the main test suite
if (!checkEnumToString()) {
  console.error('[FAIL] TypeScript enum-to-string reverse mapping check failed');
  process.exit(1);
}

// Verify discriminator=none oneof round-trip
if (!checkDiscriminatorNone()) {
  console.error('[FAIL] TypeScript discriminator=none oneof check failed');
  process.exit(1);
}

// Verify multiple oneof fields in one message
if (!checkMultiOneof()) {
  console.error('[FAIL] TypeScript multi-oneof check failed');
  process.exit(1);
}

process.exit(run(MESSAGE_COUNT, getMessage, checkMessage, getMessageInfo, TEST_NAME, PROFILES));
