/**
 * Test entry point for extended message tests (TypeScript).
 */

import { MESSAGE_COUNT, getMessage, checkMessage } from './include/extended_messages';
import { get_message_info } from '../generated/ts/extended_test.structframe';
import { run } from './include/test_harness';

const TEST_NAME = 'ExtendedMessages';
const PROFILES = 'bulk, network';

process.exit(run(MESSAGE_COUNT, getMessage, checkMessage, get_message_info, TEST_NAME, PROFILES));
