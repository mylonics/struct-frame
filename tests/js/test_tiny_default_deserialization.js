/**
 * Tiny Default frame format deserialization test for JavaScript.
 */
"use strict";

const fs = require('fs');
const path = require('path');

// TinyDefault constants
const TINY_DEFAULT_START_BYTE = 0x71;
const TINY_DEFAULT_HEADER_SIZE = 3;
const TINY_DEFAULT_FOOTER_SIZE = 2;

function printFailureDetails(label) {
  console.log('\n============================================================');
  console.log('FAILURE DETAILS: ' + label);
  console.log('============================================================\n');
}

function loadExpectedValues() {
  try {
    const jsonPath = path.join(__dirname, '../../expected_values.json');
    const data = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));
    return data.serialization_test;
  } catch (error) {
    console.log('Error loading expected values: ' + error);
    return null;
  }
}

function validateTinyDefault(buffer, expected) {
  if (buffer.length < TINY_DEFAULT_HEADER_SIZE + TINY_DEFAULT_FOOTER_SIZE) {
    console.log('  Data too short');
    return false;
  }

  if (buffer[0] !== TINY_DEFAULT_START_BYTE) {
    console.log('  Invalid start byte');
    return false;
  }

  if (buffer[2] !== 204) {
    console.log('  Invalid message ID');
    return false;
  }

  // Validate checksum
  const msgLen = buffer.length - TINY_DEFAULT_HEADER_SIZE - TINY_DEFAULT_FOOTER_SIZE;
  let byte1 = buffer[1];  // length byte
  let byte2 = buffer[1];
  byte1 = (byte1 + buffer[2]) % 256;  // msg_id
  byte2 = (byte2 + byte1) % 256;
  for (let i = 0; i < msgLen; i++) {
    byte1 = (byte1 + buffer[TINY_DEFAULT_HEADER_SIZE + i]) & 0xFF;
    byte2 = (byte2 + byte1) & 0xFF;
  }
  
  if (byte1 !== buffer[buffer.length - 2] || byte2 !== buffer[buffer.length - 1]) {
    console.log('  Checksum mismatch');
    return false;
  }

  const magicNumber = buffer.readUInt32LE(TINY_DEFAULT_HEADER_SIZE);
  if (magicNumber !== expected.magic_number) {
    console.log('  Magic number mismatch');
    return false;
  }

  console.log('  [OK] Data validated successfully');
  return true;
}

function readAndValidateTestData(filename) {
  try {
    if (!fs.existsSync(filename)) {
      console.log('  Error: file not found: ' + filename);
      return false;
    }

    const binaryData = fs.readFileSync(filename);

    if (binaryData.length === 0) {
      printFailureDetails('Empty file');
      return false;
    }

    const expected = loadExpectedValues();
    if (!expected) {
      return false;
    }

    if (!validateTinyDefault(binaryData, expected)) {
      console.log('  Validation failed');
      return false;
    }

    return true;
  } catch (error) {
    printFailureDetails('Read data exception: ' + error);
    return false;
  }
}

function main() {
  console.log('\n[TEST START] JavaScript Tiny Default Deserialization');

  const args = process.argv.slice(2);
  if (args.length !== 1) {
    console.log('  Usage: ' + process.argv[1] + ' <binary_file>');
    console.log('[TEST END] JavaScript Tiny Default Deserialization: FAIL\n');
    return false;
  }

  try {
    const success = readAndValidateTestData(args[0]);

    console.log('[TEST END] JavaScript Tiny Default Deserialization: ' + (success ? 'PASS' : 'FAIL') + '\n');
    return success;
  } catch (error) {
    printFailureDetails('Exception: ' + error);
    console.log('[TEST END] JavaScript Tiny Default Deserialization: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

module.exports.main = main;
