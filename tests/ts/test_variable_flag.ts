/**
 * Test entry point for variable flag tests (TypeScript).
 */

import { MESSAGE_COUNT, getMessage, checkMessage } from './include/variable_flag_messages';
import { getMessageInfo } from '../generated/ts/serialization-test.structframe';
import { run } from './include/test_harness';

const TEST_NAME = 'VariableFlagMessages';
const PROFILES = 'bulk';

process.exit(run(MESSAGE_COUNT, getMessage, checkMessage, getMessageInfo, TEST_NAME, PROFILES));
