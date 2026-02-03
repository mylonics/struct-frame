/**
 * Profile runner (JavaScript).
 * Low-level encoding and decoding for message providers.
 *
 * This file matches the C++ profile_runner.hpp structure.
 */

const {
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
} = require('../../generated/js/frame-profiles');

// Buffer size for readers
const BUFFER_SIZE = 16384;

const writerClasses = {
  'standard': ProfileStandardWriter,
  'sensor': ProfileSensorWriter,
  'ipc': ProfileIPCWriter,
  'bulk': ProfileBulkWriter,
  'network': ProfileNetworkWriter,
};

const readerClasses = {
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
function encode(msgProvider, profile, buffer) {
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
function parse(msgProvider, getMsgInfo, profile, buffer) {
  const ReaderClass = readerClasses[profile];
  if (!ReaderClass) return 0;

  const reader = new ReaderClass(getMsgInfo, BUFFER_SIZE);
  reader.addData(buffer);

  let messageCount = 0;

  while (true) {
    const result = reader.next();
    if (!result || !result.valid) break;

    const expected = msgProvider.getMessage(messageCount);
    const msgClass = expected.constructor;

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
function getProfileOps(msgProvider, getMsgInfo, profile) {
  return {
    encode: (buffer) => encode(msgProvider, profile, buffer),
    parse: (buffer) => parse(msgProvider, getMsgInfo, profile, buffer),
  };
}

module.exports = {
  encode,
  parse,
  getProfileOps,
};
