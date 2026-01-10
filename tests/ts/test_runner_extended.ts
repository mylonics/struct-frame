/**
 * Test runner entry point for TypeScript - Extended message ID and payload tests.
 * 
 * Usage:
 *   node test_runner_extended.js encode <frame_format> <output_file>
 *   node test_runner_extended.js decode <frame_format> <input_file>
 * 
 * Frame formats (extended profiles only): profile_bulk, profile_network
 */
import * as fs from 'fs';
import { encodeExtendedMessages, decodeExtendedMessages } from './test_codec_extended';

function printUsage(): void {
  console.log('Usage:');
  console.log('  node test_runner_extended.js encode <frame_format> <output_file>');
  console.log('  node test_runner_extended.js decode <frame_format> <input_file>');
  console.log('\nFrame formats (extended profiles): profile_bulk, profile_network');
}

function printHex(data: Buffer): void {
  const hexStr = data.length <= 64 ? data.toString('hex') : data.slice(0, 64).toString('hex') + '...';
  console.log(`  Hex (${data.length} bytes): ${hexStr}`);
}

function runEncode(formatName: string, outputFile: string): number {
  console.log(`[ENCODE] Format: ${formatName}`);

  let encodedData: Buffer;
  try {
    encodedData = encodeExtendedMessages(formatName);
  } catch (error) {
    console.log(`[ENCODE] FAILED: Encoding error - ${(error as Error).message}`);
    console.error((error as Error).stack);
    return 1;
  }

  if (!encodedData || encodedData.length === 0) {
    console.log('[ENCODE] FAILED: Empty encoded data');
    return 1;
  }

  try {
    fs.writeFileSync(outputFile, encodedData);
  } catch (error) {
    console.log(`[ENCODE] FAILED: Cannot create output file: ${outputFile} - ${(error as Error).message}`);
    return 1;
  }

  console.log(`[ENCODE] SUCCESS: Wrote ${encodedData.length} bytes to ${outputFile}`);
  return 0;
}

function runDecode(formatName: string, inputFile: string): number {
  console.log(`[DECODE] Format: ${formatName}, File: ${inputFile}`);

  let data: Buffer;
  try {
    data = fs.readFileSync(inputFile);
  } catch (error) {
    console.log(`[DECODE] FAILED: Cannot open input file: ${inputFile} - ${(error as Error).message}`);
    return 1;
  }

  if (data.length === 0) {
    console.log('[DECODE] FAILED: Empty file');
    return 1;
  }

  let result: { success: boolean; messageCount: number };
  try {
    result = decodeExtendedMessages(formatName, data);
  } catch (error) {
    console.log(`[DECODE] FAILED: Decoding error - ${(error as Error).message}`);
    printHex(data);
    console.error((error as Error).stack);
    return 1;
  }

  if (!result.success) {
    console.log('[DECODE] FAILED: Validation error');
    printHex(data);
    return 1;
  }

  console.log(`[DECODE] SUCCESS: ${result.messageCount} messages validated correctly`);
  return 0;
}

function main(): number {
  const args = process.argv.slice(2);

  if (args.length !== 3) {
    printUsage();
    return 1;
  }

  const mode = args[0];
  const formatName = args[1];
  const filePath = args[2];

  console.log(`\n[TEST START] TypeScript Extended ${formatName} ${mode}`);

  let result: number;
  if (mode === 'encode') {
    result = runEncode(formatName, filePath);
  } else if (mode === 'decode') {
    result = runDecode(formatName, filePath);
  } else {
    console.log(`Unknown mode: ${mode}`);
    printUsage();
    result = 1;
  }

  const status = result === 0 ? 'PASS' : 'FAIL';
  console.log(`[TEST END] TypeScript Extended ${formatName} ${mode}: ${status}\n`);

  return result;
}

// Run main
process.exit(main());
