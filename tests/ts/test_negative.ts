/**
 * Negative tests for struct-frame TypeScript parser
 * 
 * Tests error handling for:
 * - Corrupted CRC/checksum
 * - Truncated frames
 * - Invalid start bytes
 * - Malformed data
 */

import {
  ProfileStandardWriter,
  ProfileStandardReader,
  ProfileStandardAccumulatingReader,
  ProfileBulkWriter,
  ProfileBulkReader
} from '../generated/ts/frame-profiles';

import {
  SerializationTestBasicTypesMessage,
  get_message_info
} from '../generated/ts/serialization_test.structframe';

// Test result tracking
let testsRun = 0;
let testsPassed = 0;
let testsFailed = 0;

function testResult(name: string, passed: boolean): void {
  testsRun++;
  if (passed) {
    console.log(`  [TEST] ${name}... PASS`);
    testsPassed++;
  } else {
    console.log(`  [TEST] ${name}... FAIL`);
    testsFailed++;
  }
}

function createTestMessage(): SerializationTestBasicTypesMessage {
  const msg = new SerializationTestBasicTypesMessage();
  msg.small_int = 42;
  msg.medium_int = 1000;
  msg.regular_int = 100000;
  msg.large_int = BigInt(1000000000);
  msg.small_uint = 200;
  msg.medium_uint = 50000;
  msg.regular_uint = 3000000000;
  msg.large_uint = BigInt('9000000000000000000');
  msg.single_precision = 3.14159;
  msg.double_precision = 2.71828;
  msg.flag = true;
  msg.device_id = 'DEVICE123';
  msg.description = 'Test device';
  return msg;
}

/**
 * Test: Parser rejects frame with corrupted CRC
 */
function testCorruptedCrc(): boolean {
  const msg = createTestMessage();
  
  const writer = new ProfileStandardWriter(1024);
  writer.write(msg);
  const buffer = writer.data();
  const bytesWritten = writer.size();
  
  if (bytesWritten < 4) return false;
  
  // Corrupt the CRC (last 2 bytes)
  buffer[bytesWritten - 1] ^= 0xFF;
  buffer[bytesWritten - 2] ^= 0xFF;
  
  // Try to parse - should fail
  const reader = new ProfileStandardReader(buffer.subarray(0, bytesWritten), get_message_info);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser rejects truncated frame
 */
function testTruncatedFrame(): boolean {
  const msg = createTestMessage();
  
  const writer = new ProfileStandardWriter(1024);
  writer.write(msg);
  const buffer = writer.data();
  const bytesWritten = writer.size();
  
  if (bytesWritten < 10) return false;
  
  // Truncate the frame
  const truncatedSize = bytesWritten - 5;
  
  // Try to parse - should fail
  const reader = new ProfileStandardReader(buffer.subarray(0, truncatedSize), get_message_info);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser rejects frame with invalid start bytes
 */
function testInvalidStartBytes(): boolean {
  const msg = createTestMessage();
  
  const writer = new ProfileStandardWriter(1024);
  writer.write(msg);
  const buffer = writer.data();
  const bytesWritten = writer.size();
  
  if (bytesWritten < 2) return false;
  
  // Corrupt start bytes
  buffer[0] = 0xDE;
  buffer[1] = 0xAD;
  
  // Try to parse - should fail
  const reader = new ProfileStandardReader(buffer.subarray(0, bytesWritten), get_message_info);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser handles zero-length buffer
 */
function testZeroLengthBuffer(): boolean {
  const buffer = new Uint8Array(0);
  
  const reader = new ProfileStandardReader(buffer, get_message_info);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser handles corrupted length field
 */
function testCorruptedLength(): boolean {
  const msg = createTestMessage();
  
  const writer = new ProfileStandardWriter(1024);
  writer.write(msg);
  const buffer = writer.data();
  const bytesWritten = writer.size();
  
  if (bytesWritten < 4) return false;
  
  // Corrupt length field (byte 2)
  buffer[2] = 0xFF;
  
  // Try to parse - should fail
  const reader = new ProfileStandardReader(buffer.subarray(0, bytesWritten), get_message_info);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Streaming parser rejects corrupted CRC
 */
function testStreamingCorruptedCrc(): boolean {
  const msg = createTestMessage();
  
  const writer = new ProfileStandardWriter(1024);
  writer.write(msg);
  const buffer = writer.data();
  const bytesWritten = writer.size();
  
  if (bytesWritten < 4) return false;
  
  // Corrupt CRC
  buffer[bytesWritten - 1] ^= 0xFF;
  
  // Try streaming parse
  const reader = new ProfileStandardAccumulatingReader(get_message_info, 1024);
  
  // Feed byte by byte
  for (let i = 0; i < bytesWritten; i++) {
    reader.pushByte(buffer[i]);
  }
  
  const result = reader.next();
  return !result.valid;  // Expect failure
}

/**
 * Test: Streaming parser handles garbage data
 */
function testStreamingGarbage(): boolean {
  const reader = new ProfileStandardAccumulatingReader(get_message_info, 1024);
  
  // Feed garbage bytes
  const garbage = new Uint8Array([0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56, 0x78, 0x9A]);
  
  for (const byte of garbage) {
    reader.pushByte(byte);
  }
  
  const result = reader.next();
  return !result.valid;  // Expect no valid frame
}

/**
 * Test: Bulk profile with corrupted CRC
 */
function testBulkProfileCorruptedCrc(): boolean {
  const msg = createTestMessage();
  
  const writer = new ProfileBulkWriter(1024);
  writer.write(msg);
  const buffer = writer.data();
  const bytesWritten = writer.size();
  
  if (bytesWritten < 4) return false;
  
  // Corrupt the CRC (last 2 bytes)
  buffer[bytesWritten - 1] ^= 0xFF;
  buffer[bytesWritten - 2] ^= 0xFF;
  
  // Try to parse - should fail
  const reader = new ProfileBulkReader(buffer.subarray(0, bytesWritten), get_message_info);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

function main(): number {
  console.log('\n========================================');
  console.log('NEGATIVE TESTS - TypeScript Parser');
  console.log('========================================\n');
  
  console.log('Testing error handling for invalid frames:\n');
  
  testResult('Corrupted CRC detection', testCorruptedCrc());
  testResult('Truncated frame detection', testTruncatedFrame());
  testResult('Invalid start bytes detection', testInvalidStartBytes());
  testResult('Zero-length buffer handling', testZeroLengthBuffer());
  testResult('Corrupted length field detection', testCorruptedLength());
  testResult('Streaming: Corrupted CRC detection', testStreamingCorruptedCrc());
  testResult('Streaming: Garbage data handling', testStreamingGarbage());
  testResult('Bulk profile: Corrupted CRC', testBulkProfileCorruptedCrc());
  
  console.log('\n========================================');
  console.log('RESULTS');
  console.log('========================================');
  console.log(`Tests run:    ${testsRun}`);
  console.log(`Tests passed: ${testsPassed}`);
  console.log(`Tests failed: ${testsFailed}`);
  console.log('========================================\n');
  
  return testsFailed > 0 ? 1 : 0;
}

process.exit(main());
