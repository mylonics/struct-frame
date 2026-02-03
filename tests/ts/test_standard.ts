/**
 * Test entry point for standard message tests (TypeScript).
 */

import { MESSAGE_COUNT, getMessage, checkMessage } from './include/standard_messages';
import { get_message_info } from '../generated/ts/serialization_test.structframe';
import { run } from './include/test_harness';

const TEST_NAME = 'StandardMessages';
const PROFILES = 'standard, sensor, ipc, bulk, network';

process.exit(run(MESSAGE_COUNT, getMessage, checkMessage, get_message_info, TEST_NAME, PROFILES));
