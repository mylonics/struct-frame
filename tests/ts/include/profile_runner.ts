/**
 * Profile runner (TypeScript).
 * Low-level encoding and decoding for message providers.
 *
 * This file matches the C++ profile_runner.hpp structure.
 * ProfileRunner has NO knowledge of message types - all message-specific
 * logic is handled via callbacks (getMessage, checkMessage).
 */

import {
  BufferWriter,
  AccumulatingReader,
  ProfileStandardConfig,
  ProfileSensorConfig,
  ProfileIPCConfig,
  ProfileBulkConfig,
  ProfileNetworkConfig,
  FrameProfileConfig,
  MessageInfo,
} from '../../generated/ts/frame-profiles';

import { FrameMsgInfo } from '../../generated/ts/frame-base';

// Buffer size for readers
const BUFFER_SIZE = 16384;

export type GetMsgInfoFn = (msgId: number) => MessageInfo | undefined;
export type GetMsgFn = (index: number) => any;
export type CheckMsgFn = (index: number, info: FrameMsgInfo) => boolean;

const profileConfigs: { [key: string]: FrameProfileConfig } = {
  'standard': ProfileStandardConfig,
  'sensor': ProfileSensorConfig,
  'ipc': ProfileIPCConfig,
  'bulk': ProfileBulkConfig,
  'network': ProfileNetworkConfig,
};

/**
 * Encode all messages to buffer using BufferWriter.
 * Returns total bytes written.
 */
export function encode(messageCount: number, getMessage: GetMsgFn, profile: string, buffer: Buffer): number {
  const config = profileConfigs[profile];
  if (!config) return 0;

  const writer = new BufferWriter(config, buffer.length);

  for (let i = 0; i < messageCount; i++) {
    const msg = getMessage(i);
    writer.write(msg);
  }

  const data = writer.data();
  // Copy Uint8Array to Buffer
  for (let i = 0; i < data.length; i++) {
    buffer[i] = data[i];
  }
  return writer.size;
}

/**
 * Parse all messages from buffer using AccumulatingReader.
 * Uses checkMessage callback to validate each decoded message.
 * Returns the number of messages that matched (messageCount if all pass).
 */
export function parse(messageCount: number, checkMessage: CheckMsgFn, getMsgInfo: GetMsgInfoFn, profile: string, buffer: Buffer): number {
  const config = profileConfigs[profile];
  if (!config) return 0;

  const reader = new AccumulatingReader(config, getMsgInfo, BUFFER_SIZE);
  reader.addData(buffer);

  let count = 0;

  while (true) {
    const result = reader.next();
    if (!result || !result.valid) break;

    // Use callback to check if message matches expected
    if (!checkMessage(count, result)) break;

    count++;
  }

  return count;
}
