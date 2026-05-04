/**
 * Test entry point for extended message tests (TypeScript).
 */

import { MESSAGE_COUNT, getMessage, checkMessage } from './include/extended_messages';
import { getMessageInfo } from '../generated/ts/extended-test.structframe';
import { run } from './include/test_harness';

const TEST_NAME = 'ExtendedMessages';
const PROFILES = 'bulk, network';

process.exit(run(MESSAGE_COUNT, getMessage, checkMessage, getMessageInfo, TEST_NAME, PROFILES));
