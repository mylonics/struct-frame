/**
 * Profile runner (TypeScript).
 * Low-level encoding and decoding for message providers.
 *
 * This file matches the C++ profile_runner.hpp structure.
 * ProfileRunner has NO knowledge of message types - all message-specific
 * logic is handled via callbacks (getMessage, checkMessage).
 */

import {
  ProfileStandardWriter,
  ProfileSensorWriter,
  ProfileIPCWriter,
  ProfileBulkWriter,
  ProfileNetworkWriter,
  ProfileStandardAccumulatingReader,
  ProfileSensorAccumulatingReader,
  ProfileIPCAccumulatingReader,
  ProfileBulkAccumulatingReader,
  ProfileNetworkAccumulatingReader,
  MessageInfo,
} from '../../generated/ts/frame-profiles';

import { FrameMsgInfo } from '../../generated/ts/frame-base';

// Buffer size for readers
const BUFFER_SIZE = 16384;

export type GetMsgInfoFn = (msgId: number) => MessageInfo | undefined;
export type GetMsgFn = (index: number) => any;
export type CheckMsgFn = (index: number, info: FrameMsgInfo) => boolean;

const writerClasses: { [key: string]: new (size: number) => any } = {
  'standard': ProfileStandardWriter,
  'sensor': ProfileSensorWriter,
  'ipc': ProfileIPCWriter,
  'bulk': ProfileBulkWriter,
  'network': ProfileNetworkWriter,
};

const readerClasses: { [key: string]: new (getMsgInfo: GetMsgInfoFn, bufSize: number) => any } = {
  'standard': ProfileStandardAccumulatingReader,
  'sensor': ProfileSensorAccumulatingReader,
  'ipc': ProfileIPCAccumulatingReader,
  'bulk': ProfileBulkAccumulatingReader,
  'network': ProfileNetworkAccumulatingReader,
};

/**
 * Encode all messages to buffer using BufferWriter.
 * Returns total bytes written.
 */
export function encode(messageCount: number, getMessage: GetMsgFn, profile: string, buffer: Buffer): number {
  const WriterClass = writerClasses[profile];
  if (!WriterClass) return 0;

  const writer = new WriterClass(buffer.length);

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
  const ReaderClass = readerClasses[profile];
  if (!ReaderClass) return 0;

  const reader = new ReaderClass(getMsgInfo, BUFFER_SIZE);
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
