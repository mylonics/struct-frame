/**
 * Profile runner (JavaScript).
 * Low-level encoding and decoding for message providers.
 *
 * This file matches the C++ profile_runner.hpp structure.
 * ProfileRunner has NO knowledge of message types - all message-specific
 * logic is handled via callbacks (getMessage, checkMessage).
 */

const {
  BufferWriter,
  AccumulatingReader,
  ProfileStandardConfig,
  ProfileSensorConfig,
  ProfileIPCConfig,
  ProfileBulkConfig,
  ProfileNetworkConfig,
} = require('../../generated/js/frame-profiles');

// Buffer size for readers
const BUFFER_SIZE = 16384;

const profileConfigs = {
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
function encode(messageCount, getMessage, profile, buffer) {
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
function parse(messageCount, checkMessage, getMsgInfo, profile, buffer) {
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

module.exports = {
  encode,
  parse,
  BUFFER_SIZE,
};
