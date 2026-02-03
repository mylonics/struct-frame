/**
 * Test entry point for standard message tests (JavaScript).
 */

const { MESSAGE_COUNT, getMessage, checkMessage } = require('./include/standard_messages');
const { get_message_info } = require('../generated/js/serialization_test.structframe');
const { run } = require('./include/test_harness');

const TEST_NAME = 'StandardMessages';
const PROFILES = 'standard, sensor, ipc, bulk, network';

process.exit(run(MESSAGE_COUNT, getMessage, checkMessage, get_message_info, TEST_NAME, PROFILES));
