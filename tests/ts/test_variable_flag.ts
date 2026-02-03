/**
 * Test entry point for variable flag tests (TypeScript).
 */

import { MESSAGE_COUNT, getMessage, checkMessage } from './include/variable_flag_messages';
import { get_message_info } from '../generated/ts/serialization_test.structframe';
import { run } from './include/test_harness';

const TEST_NAME = 'VariableFlagMessages';
const PROFILES = 'bulk';

process.exit(run(MESSAGE_COUNT, getMessage, checkMessage, get_message_info, TEST_NAME, PROFILES));
