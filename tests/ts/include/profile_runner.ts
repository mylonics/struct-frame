/**
 * Profile runner (TypeScript).
 * Low-level encoding and decoding for message providers.
 *
 * This file matches the C++ profile_runner.hpp structure.
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

// Buffer size for readers
const BUFFER_SIZE = 16384;

type GetMsgInfoFn = (msgId: number) => MessageInfo | undefined;
type GetMsgFn = (index: number) => any;

interface MessageProvider {
  MESSAGE_COUNT: number;
  getMessage: GetMsgFn;
}

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
export function encode(msgProvider: MessageProvider, profile: string, buffer: Buffer): number {
  const WriterClass = writerClasses[profile];
  if (!WriterClass) return 0;

  const writer = new WriterClass(buffer.length);

  for (let i = 0; i < msgProvider.MESSAGE_COUNT; i++) {
    const msg = msgProvider.getMessage(i);
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
 * Returns the number of messages that matched (MESSAGE_COUNT if all pass).
 */
export function parse(msgProvider: MessageProvider, getMsgInfo: GetMsgInfoFn, profile: string, buffer: Buffer): number {
  const ReaderClass = readerClasses[profile];
  if (!ReaderClass) return 0;

  const reader = new ReaderClass(getMsgInfo, BUFFER_SIZE);
  reader.addData(buffer);

  let messageCount = 0;

  while (true) {
    const result = reader.next();
    if (!result || !result.valid) break;

    const expected = msgProvider.getMessage(messageCount);
    const msgClass = expected.constructor as any;

    if (result.msg_id !== msgClass._msgid) break;

    const decoded = msgClass.deserialize(result);
    if (!decoded.equals(expected)) break;

    messageCount++;
  }

  return messageCount;
}

/**
 * Get encode and parse functions for a profile.
 */
export function getProfileOps(msgProvider: MessageProvider, getMsgInfo: GetMsgInfoFn, profile: string) {
  return {
    encode: (buffer: Buffer) => encode(msgProvider, profile, buffer),
    parse: (buffer: Buffer) => parse(msgProvider, getMsgInfo, profile, buffer),
  };
}
