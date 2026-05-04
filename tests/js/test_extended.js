/**
 * Test entry point for extended message tests (JavaScript).
 */

const { MESSAGE_COUNT, getMessage, checkMessage } = require('./include/extended_messages');
const { getMessageInfo } = require('../generated/js/extended-test.structframe');
const { run } = require('./include/test_harness');

const TEST_NAME = 'ExtendedMessages';
const PROFILES = 'bulk, network';

process.exit(run(MESSAGE_COUNT, getMessage, checkMessage, getMessageInfo, TEST_NAME, PROFILES));
