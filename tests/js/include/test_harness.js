/**
 * Test harness (JavaScript).
 * High-level test setup, CLI parsing, file I/O, and test execution.
 *
 * This file matches the C++ test_harness.hpp structure.
 */

const fs = require('fs');
const { encode, parse, BUFFER_SIZE } = require('./profile_runner');

function printUsage(programName, profileHelp) {
  console.log('Usage:');
  console.log(`  ${programName} encode <profile> <output_file>`);
  console.log(`  ${programName} decode <profile> <input_file>`);
  console.log(`  ${programName} both <profile>`);
  console.log(`\nProfiles: ${profileHelp}`);
}

function writeFile(path, data) {
  try {
    fs.writeFileSync(path, data);
    return true;
  } catch {
    return false;
  }
}

function readFile(path) {
  try {
    return fs.readFileSync(path);
  } catch {
    return Buffer.alloc(0);
  }
}

function runEncode(messageCount, getMessage, profile, outputFile) {
  const buffer = Buffer.alloc(BUFFER_SIZE);
  const bytesWritten = encode(messageCount, getMessage, profile, buffer);

  if (bytesWritten === 0 || !writeFile(outputFile, buffer.subarray(0, bytesWritten))) {
    console.log('[ENCODE] FAILED');
    return 1;
  }

  console.log(`[ENCODE] SUCCESS: Wrote ${bytesWritten} bytes to ${outputFile}`);
  return 0;
}

function runDecode(messageCount, checkMessage, getMsgInfo, profile, inputFile) {
  const buffer = readFile(inputFile);
  if (buffer.length === 0) {
    console.log('[DECODE] FAILED: Cannot read file');
    return 1;
  }

  const count = parse(messageCount, checkMessage, getMsgInfo, profile, buffer);
  if (count !== messageCount) {
    console.log(`[DECODE] FAILED: ${count} of ${messageCount} messages validated`);
    return 1;
  }

  console.log(`[DECODE] SUCCESS: ${count} messages validated`);
  return 0;
}

function runBoth(messageCount, getMessage, checkMessage, getMsgInfo, profile) {
  const buffer = Buffer.alloc(BUFFER_SIZE);
  const bytesWritten = encode(messageCount, getMessage, profile, buffer);

  if (bytesWritten === 0) {
    console.log('[BOTH] FAILED: Encoding error');
    return 1;
  }

  console.log(`[BOTH] Encoded ${bytesWritten} bytes`);

  const count = parse(messageCount, checkMessage, getMsgInfo, profile, buffer.subarray(0, bytesWritten));
  if (count !== messageCount) {
    console.log(`[BOTH] FAILED: ${count} of ${messageCount} messages validated`);
    return 1;
  }

  console.log(`[BOTH] SUCCESS: ${count} messages round-trip validated`);
  return 0;
}

/**
 * Main entry point for test programs.
 */
function run(messageCount, getMessage, checkMessage, getMsgInfo, testName, profileHelp) {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    printUsage(process.argv[1], profileHelp);
    return 1;
  }

  const mode = args[0];
  const profile = args[1];
  const filePath = args[2] || '';

  if (!['encode', 'decode', 'both'].includes(mode)) {
    console.log(`Unknown mode: ${mode}`);
    printUsage(process.argv[1], profileHelp);
    return 1;
  }

  if ((mode === 'encode' || mode === 'decode') && !filePath) {
    console.log(`Mode '${mode}' requires a file argument`);
    printUsage(process.argv[1], profileHelp);
    return 1;
  }

  console.log(`\n[TEST START] ${testName} ${profile} ${mode}`);

  let result;

  if (mode === 'encode') {
    result = runEncode(messageCount, getMessage, profile, filePath);
  } else if (mode === 'decode') {
    result = runDecode(messageCount, checkMessage, getMsgInfo, profile, filePath);
  } else {
    result = runBoth(messageCount, getMessage, checkMessage, getMsgInfo, profile);
  }

  const status = result === 0 ? 'PASS' : 'FAIL';
  console.log(`[TEST END] ${testName} ${profile} ${mode}: ${status}\n`);

  return result;
}

module.exports = {
  run,
};
