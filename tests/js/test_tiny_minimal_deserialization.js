/**
 * Tiny Minimal frame format deserialization test for JavaScript.
 */
"use strict";

const fs = require('fs');
const path = require('path');

// TinyMinimal constants
const TINY_MINIMAL_START_BYTE = 0x70;
const TINY_MINIMAL_HEADER_SIZE = 2;
const TINY_MINIMAL_FOOTER_SIZE = 0;

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

function validateTinyMinimal(buffer, expected) {
  if (buffer.length < TINY_MINIMAL_HEADER_SIZE + TINY_MINIMAL_FOOTER_SIZE) {
    console.log('  Data too short');
    return false;
  }

  if (buffer[0] !== TINY_MINIMAL_START_BYTE) {
    console.log('  Invalid start byte');
    return false;
  }

  if (buffer[1] !== 204) {
    console.log('  Invalid message ID');
    return false;
  }

  // No CRC validation for minimal format

  const magicNumber = buffer.readUInt32LE(TINY_MINIMAL_HEADER_SIZE);
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

    if (!validateTinyMinimal(binaryData, expected)) {
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
  console.log('\n[TEST START] JavaScript Tiny Minimal Deserialization');

  const args = process.argv.slice(2);
  if (args.length !== 1) {
    console.log('  Usage: ' + process.argv[1] + ' <binary_file>');
    console.log('[TEST END] JavaScript Tiny Minimal Deserialization: FAIL\n');
    return false;
  }

  try {
    const success = readAndValidateTestData(args[0]);

    console.log('[TEST END] JavaScript Tiny Minimal Deserialization: ' + (success ? 'PASS' : 'FAIL') + '\n');
    return success;
  } catch (error) {
    printFailureDetails('Exception: ' + error);
    console.log('[TEST END] JavaScript Tiny Minimal Deserialization: FAIL\n');
    return false;
  }
}

if (require.main === module) {
  const success = main();
  process.exit(success ? 0 : 1);
}

module.exports.main = main;
