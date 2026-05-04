/**
 * Test entry point for standard message tests (TypeScript).
 */

import { MESSAGE_COUNT, getMessage, checkMessage } from './include/standard_messages';
import { getMessageInfo } from '../generated/ts/serialization-test.structframe';
import { run } from './include/test_harness';

const TEST_NAME = 'StandardMessages';
const PROFILES = 'standard, sensor, ipc, bulk, network';

process.exit(run(MESSAGE_COUNT, getMessage, checkMessage, getMessageInfo, TEST_NAME, PROFILES));
