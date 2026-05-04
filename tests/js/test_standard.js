/**
 * Test entry point for standard message tests (JavaScript).
 */

const { MESSAGE_COUNT, getMessage, checkMessage } = require('./include/standard_messages');
const { getMessageInfo } = require('../generated/js/serialization-test.structframe');
const { run } = require('./include/test_harness');

const TEST_NAME = 'StandardMessages';
const PROFILES = 'standard, sensor, ipc, bulk, network';

process.exit(run(MESSAGE_COUNT, getMessage, checkMessage, getMessageInfo, TEST_NAME, PROFILES));
