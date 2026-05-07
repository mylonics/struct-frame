/**
 * Test entry point for standard message tests (JavaScript).
 */

const { MESSAGE_COUNT, getMessage, checkMessage, checkEnumToString } = require('./include/standard_messages');
const { getMessageInfo } = require('../generated/js/serialization-test.structframe');
const { run } = require('./include/test_harness');

const TEST_NAME = 'StandardMessages';
const PROFILES = 'standard, sensor, ipc, bulk, network';

// Verify enum-to-string (reverse lookup) before running the main test suite
if (!checkEnumToString()) {
  console.error('[FAIL] JavaScript enum-to-string reverse lookup check failed');
  process.exit(1);
}

process.exit(run(MESSAGE_COUNT, getMessage, checkMessage, getMessageInfo, TEST_NAME, PROFILES));
