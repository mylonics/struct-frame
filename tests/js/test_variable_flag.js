/**
 * Test entry point for variable flag tests (JavaScript).
 */

const VariableFlagMessages = require('./include/variable_flag_messages');
const { get_message_info } = require('../generated/js/serialization_test.structframe');
const { run } = require('./include/test_harness');

const TEST_NAME = 'VariableFlagMessages';
const PROFILES = 'bulk';

process.exit(run(VariableFlagMessages, get_message_info, TEST_NAME, PROFILES));
