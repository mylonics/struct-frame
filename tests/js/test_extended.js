/**
 * Test entry point for extended message tests (JavaScript).
 */

const ExtendedMessages = require('./include/extended_messages');
const { get_message_info } = require('../generated/js/extended_test.structframe');
const { run } = require('./include/test_harness');

const TEST_NAME = 'ExtendedMessages';
const PROFILES = 'bulk, network';

process.exit(run(ExtendedMessages, get_message_info, TEST_NAME, PROFILES));
