/**
 * Test codec - Config-based encode/decode and test runner infrastructure for JavaScript.
 *
 * This file provides:
 * 1. TestConfig interface for test configuration
 * 2. Generic encode/decode functions that work with any test config
 * 3. Test runner utilities (file I/O, hex dump, CLI parsing)
 * 4. A unified runTestMain() function for entry points
 */

const fs = require('fs');
const {
  ProfileStandardAccumulatingReader,
  ProfileStandardWriter,
  ProfileSensorAccumulatingReader,
  ProfileSensorWriter,
  ProfileIPCAccumulatingReader,
  ProfileIPCWriter,
  ProfileBulkAccumulatingReader,
  ProfileBulkWriter,
  ProfileNetworkAccumulatingReader,
  ProfileNetworkWriter,
} = require('../../generated/js/frame-profiles');

/** Print hex dump of data (up to 64 bytes) */
function printHex(data) {
  const hexStr = data.length <= 64 ? data.toString('hex') : data.slice(0, 64).toString('hex') + '...';
  console.log(`  Hex (${data.length} bytes): ${hexStr}`);
}

/** Print usage help */
function printUsage(programName, formatsHelp) {
  console.log('Usage:');
  console.log(`  ${programName} encode <frame_format> <output_file>`);
  console.log(`  ${programName} decode <frame_format> <input_file>`);
  console.log(`\nFrame formats: ${formatsHelp}`);
}

/** Get writer for a profile format */
function getWriter(format, capacity) {
  const writers = {
    'profile_standard': () => new ProfileStandardWriter(capacity),
    'profile_sensor': () => new ProfileSensorWriter(capacity),
    'profile_ipc': () => new ProfileIPCWriter(capacity),
    'profile_bulk': () => new ProfileBulkWriter(capacity),
    'profile_network': () => new ProfileNetworkWriter(capacity),
  };

  const creator = writers[format];
  return creator ? creator() : null;
}

/** Get reader for a profile format */
function getReader(format, getMessageInfo) {
  const readers = {
    'profile_standard': () => new ProfileStandardAccumulatingReader(getMessageInfo, 4096),
    'profile_sensor': () => new ProfileSensorAccumulatingReader(getMessageInfo, 4096),
    'profile_ipc': () => new ProfileIPCAccumulatingReader(getMessageInfo, 4096),
    'profile_bulk': () => new ProfileBulkAccumulatingReader(getMessageInfo, 4096),
    'profile_network': () => new ProfileNetworkAccumulatingReader(getMessageInfo, 4096),
  };

  const creator = readers[format];
  return creator ? creator() : null;
}

/** Encode messages using the specified format */
function encodeMessages(config, format) {
  if (!config.supportsFormat(format)) {
    console.log(`  Unsupported format: ${format}`);
    return Buffer.alloc(0);
  }

  // Reset encoder state
  config.resetState();

  const writer = getWriter(format, config.bufferSize);
  if (!writer) {
    console.log(`  Unknown frame format: ${format}`);
    return Buffer.alloc(0);
  }

  for (let i = 0; i < config.messageCount; i++) {
    const written = config.encodeMessage(writer, i);
    if (written === 0) {
      console.log(`  Encoding failed for message ${i}`);
      return Buffer.alloc(0);
    }
  }

  if (config.testName.includes('Variable Flag')) {
    console.log(`Total: ${writer.size} bytes`);
  }

  return Buffer.from(writer.data());
}

/** Decode and validate messages using the specified format */
function decodeMessages(config, format, data) {
  if (!config.supportsFormat(format)) {
    console.log(`  Unsupported format: ${format}`);
    return 0;
  }

  // Reset validator state
  config.resetState();

  const msgOrder = config.getMsgIdOrder();

  // Split buffer into 3 chunks to test partial message handling
  const chunk1Size = Math.floor(data.length / 3);
  const chunk2Size = Math.floor(data.length / 3);
  const chunk3Size = data.length - chunk1Size - chunk2Size;

  const chunk1 = data.slice(0, chunk1Size);
  const chunk2 = data.slice(chunk1Size, chunk1Size + chunk2Size);
  const chunk3 = data.slice(chunk1Size + chunk2Size);

  const reader = getReader(format, config.getMessageInfo.bind(config));
  if (!reader) {
    console.log(`  Unknown frame format: ${format}`);
    return 0;
  }

  // Use AccumulatingReader pattern - add chunks and process
  const chunks = [chunk1, chunk2, chunk3];
  let messageCount = 0;

  for (const chunk of chunks) {
    reader.addData(chunk);

    while (true) {
      const result = reader.next();
      if (!result || !result.valid) break;

      if (messageCount >= config.messageCount) {
        console.log(`  Too many messages decoded: ${messageCount}`);
        return messageCount;
      }

      const expectedMsgId = msgOrder[messageCount];
      if (result.msg_id !== expectedMsgId) {
        console.log(`  Message ${messageCount} ID mismatch: expected ${expectedMsgId}, got ${result.msg_id}`);
        return messageCount;
      }

      if (!config.validateMessage(result, messageCount)) {
        console.log(`  Message ${messageCount} validation failed`);
        return messageCount;
      }

      messageCount++;
    }
  }

  if (messageCount !== config.messageCount) {
    console.log(`  Expected ${config.messageCount} messages, decoded ${messageCount}`);
    return messageCount;
  }

  if (reader.hasPartial && reader.hasPartial()) {
    console.log(`  Incomplete partial message: ${reader.partialSize()} bytes`);
    return messageCount;
  }

  return messageCount;
}

/** Run encode operation */
function runEncode(config, format, outputFile) {
  console.log(`[ENCODE] Format: ${format}`);

  let encodedData;
  try {
    encodedData = encodeMessages(config, format);
  } catch (error) {
    console.log(`[ENCODE] FAILED: Encoding error - ${error.message}`);
    console.error(error.stack);
    return 1;
  }

  if (!encodedData || encodedData.length === 0) {
    console.log('[ENCODE] FAILED: Empty encoded data');
    return 1;
  }

  try {
    fs.writeFileSync(outputFile, encodedData);
  } catch (error) {
    console.log(`[ENCODE] FAILED: Cannot create output file: ${outputFile} - ${error.message}`);
    return 1;
  }

  console.log(`[ENCODE] SUCCESS: Wrote ${encodedData.length} bytes to ${outputFile}`);
  return 0;
}

/** Run decode operation */
function runDecode(config, format, inputFile) {
  console.log(`[DECODE] Format: ${format}, File: ${inputFile}`);

  let data;
  try {
    data = fs.readFileSync(inputFile);
  } catch (error) {
    console.log(`[DECODE] FAILED: Cannot open input file: ${inputFile} - ${error.message}`);
    return 1;
  }

  if (data.length === 0) {
    console.log('[DECODE] FAILED: Empty file');
    return 1;
  }

  let messageCount;
  try {
    messageCount = decodeMessages(config, format, data);
  } catch (error) {
    console.log(`[DECODE] FAILED: Decoding error - ${error.message}`);
    printHex(data);
    console.error(error.stack);
    return 1;
  }

  if (messageCount === 0) {
    console.log('[DECODE] FAILED: No messages decoded');
    printHex(data);
    return 1;
  }

  if (messageCount < config.messageCount) {
    console.log(`[DECODE] FAILED: ${messageCount} messages validated before error`);
    printHex(data);
    return 1;
  }

  console.log(`[DECODE] SUCCESS: ${messageCount} messages validated correctly`);
  return 0;
}

/** Main entry point */
function runTestMain(config) {
  const args = process.argv.slice(2);

  if (args.length !== 3) {
    printUsage(process.argv[1], config.formatsHelp);
    return 1;
  }

  const mode = args[0];
  const format = args[1];
  const filePath = args[2];

  console.log(`\n[TEST START] ${config.testName} ${format} ${mode}`);

  let result;
  if (mode === 'encode') {
    result = runEncode(config, format, filePath);
  } else if (mode === 'decode') {
    result = runDecode(config, format, filePath);
  } else {
    console.log(`Unknown mode: ${mode}`);
    result = 1;
  }

  const status = result === 0 ? 'PASS' : 'FAIL';
  console.log(`[TEST END] ${config.testName} ${format} ${mode}: ${status}\n`);

  return result;
}

module.exports = {
  printHex,
  printUsage,
  encodeMessages,
  decodeMessages,
  runEncode,
  runDecode,
  runTestMain,
};
