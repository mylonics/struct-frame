/**
 * Test entry point for variable flag tests (JavaScript).
 */

const { MESSAGE_COUNT, getMessage, checkMessage } = require('./include/variable_flag_messages');
const { get_message_info } = require('../generated/js/serialization_test.structframe');
const { run } = require('./include/test_harness');

const TEST_NAME = 'VariableFlagMessages';
const PROFILES = 'bulk';

process.exit(run(MESSAGE_COUNT, getMessage, checkMessage, get_message_info, TEST_NAME, PROFILES));
