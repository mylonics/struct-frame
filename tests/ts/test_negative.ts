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
  ProfileBulkReader,
  ProfileSensorWriter,
  ProfileSensorReader,
  ProfileNetworkWriter,
  ProfileNetworkReader
} from '../generated/ts/frame-profiles';

import {
  BasicTypesMessage,
  get_message_info
} from '../generated/ts/serialization-test.structframe';

// Test result tracking
let testsRun = 0;
let testsPassed = 0;
let testsFailed = 0;

function createTestMessage(): BasicTypesMessage {
  const msg = new BasicTypesMessage();
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
  msg.description_data = 'Test device';
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
  const bytesWritten = writer.size;
  
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
  const bytesWritten = writer.size;
  
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
  const bytesWritten = writer.size;
  
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
  const bytesWritten = writer.size;
  
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
  const bytesWritten = writer.size;
  
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
  const bytesWritten = writer.size;
  
  if (bytesWritten < 4) return false;
  
  // Corrupt the CRC (last 2 bytes)
  buffer[bytesWritten - 1] ^= 0xFF;
  buffer[bytesWritten - 2] ^= 0xFF;
  
  // Try to parse - should fail
  const reader = new ProfileBulkReader(buffer.subarray(0, bytesWritten), get_message_info);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Multiple frames with corrupted middle frame
 */
function testMultipleCorruptedFrames(): boolean {
  // Create buffer with 3 messages
  const writer = new ProfileStandardWriter(4096);
  
  const msg1 = createTestMessage();
  msg1.small_int = 1;
  writer.write(msg1);
  const bytes1End = writer.size;
  
  const msg2 = createTestMessage();
  msg2.small_int = 2;
  writer.write(msg2);
  const bytes2End = writer.size;
  
  const msg3 = createTestMessage();
  msg3.small_int = 3;
  writer.write(msg3);
  
  const buffer = writer.data();
  const totalBytes = writer.size;
  
  // Corrupt second frame's CRC (last byte before third frame)
  buffer[bytes2End - 1] ^= 0xFF;
  
  // Parse all frames
  const reader = new ProfileStandardReader(buffer.subarray(0, totalBytes), get_message_info);
  
  const result1 = reader.next();
  if (!result1.valid) return false;  // First should be valid
  
  const result2 = reader.next();
  return !result2.valid;  // Second should be invalid
}

/**
 * Test: AccumulatingReader handles a frame fed in two separate addData chunks
 */
function testPartialFrameBoundary(): boolean {
  const msg = createTestMessage();
  
  const writer = new ProfileStandardWriter(1024);
  writer.write(msg);
  const buffer = writer.data();
  const frameSize = writer.size;
  
  if (frameSize < 10) return false;
  
  const mid = Math.floor(frameSize / 2);
  
  const reader = new ProfileStandardAccumulatingReader(get_message_info, 1024);
  
  // Feed first half via addData, then call next() to save partial data to internal buffer
  reader.addData(buffer.subarray(0, mid));
  reader.next();  // Should return invalid but save partial data internally
  
  // Feed second half - adds to internal buffer completing the frame
  reader.addData(buffer.subarray(mid, frameSize));
  
  // Call next() once all data is present - should successfully decode the frame
  const result = reader.next();
  return result.valid;  // Expect success after accumulating both halves
}

/**
 * Test: Parser rejects frame with unknown message ID (CRC fails with wrong magic values).
 * ProfileStandard layout: [0x90][0x71][LEN][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * Corrupting byte 3 (msg_id) to 0xFF causes get_message_info to return {0,0,0} magic.
 */
function testInvalidMsgId(): boolean {
  const msg = createTestMessage();
  const writer = new ProfileStandardWriter(1024);
  writer.write(msg);
  const buffer = Buffer.from(writer.data());
  const frameSize = writer.size;

  if (frameSize < 5) return false;

  // Corrupt the msg_id byte (byte 3: [start1][start2][len][msg_id]...)
  // 0xFF is not a known message ID → get_message_info returns {0,0,0} magic → CRC fails
  buffer[3] = 0xFF;

  const reader = new ProfileStandardReader(buffer.subarray(0, frameSize), get_message_info);
  const result = reader.next();
  return !result.valid;  // Expect failure: CRC mismatch due to wrong magic values
}

/**
 * Test: Minimal profile (no CRC) rejects a truncated frame.
 * ProfileSensor layout: [0x70][MSG_ID][PAYLOAD...]  (no CRC, no length field)
 * Parser uses get_message_info to determine expected payload size; truncated buffer → rejected.
 */
function testMinimalProfileTruncatedFrame(): boolean {
  const msg = createTestMessage();
  const writer = new ProfileSensorWriter(1024);
  writer.write(msg);
  const buffer = writer.data();
  const frameSize = writer.size;

  if (frameSize <= 5) return false;

  // Provide fewer bytes than the full frame to trigger truncation error
  const truncated = frameSize - 5;
  const reader = new ProfileSensorReader(buffer.subarray(0, truncated), get_message_info);
  const result = reader.next();
  return !result.valid;  // Expect failure: buffer too small for expected payload
}

/**
 * Test: Network profile validates sys_id/comp_id as part of CRC-protected header.
 * ProfileNetwork layout: [0x90][0x78][SEQ][SYS_ID][COMP_ID][LEN_LO][LEN_HI][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * sys_id is at byte 3 (within CRC region); corrupting it causes CRC failure.
 */
function testNetworkSysIdCompId(): boolean {
  const msg = createTestMessage();
  const writer = new ProfileNetworkWriter(1024);
  // Encode with seq=1, sysId=5, compId=10
  writer.write(msg, { seq: 1, sysId: 5, compId: 10 });
  const buffer = Buffer.from(writer.data());
  const frameSize = writer.size;

  if (frameSize < 10) return false;

  // Corrupt sys_id (byte 3: [start1][start2][seq][sys_id]...)
  // sys_id is inside the CRC-protected region so CRC will fail
  buffer[3] ^= 0xFF;

  const reader = new ProfileNetworkReader(buffer.subarray(0, frameSize), get_message_info);
  const result = reader.next();
  return !result.valid;  // Expect failure: corrupted sys_id invalidates CRC
}

function main(): number {
  console.log('\n========================================');
  console.log('NEGATIVE TESTS - TypeScript Parser');
  console.log('========================================\n');
  
  // Define test matrix
  const tests: Array<[string, () => boolean]> = [
    ['Bulk profile: Corrupted CRC', testBulkProfileCorruptedCrc],
    ['Corrupted CRC detection', testCorruptedCrc],
    ['Corrupted length field detection', testCorruptedLength],
    ['Invalid message ID rejection', testInvalidMsgId],
    ['Invalid start bytes detection', testInvalidStartBytes],
    ['Minimal profile: Truncated frame', testMinimalProfileTruncatedFrame],
    ['Multiple frames: Corrupted middle frame', testMultipleCorruptedFrames],
    ['Network profile: SysId/CompId corruption', testNetworkSysIdCompId],
    ['Partial frame across buffer boundary', testPartialFrameBoundary],
    ['Streaming: Corrupted CRC detection', testStreamingCorruptedCrc],
    ['Streaming: Garbage data handling', testStreamingGarbage],
    ['Truncated frame detection', testTruncatedFrame],
    ['Zero-length buffer handling', testZeroLengthBuffer],
  ];
  
  console.log('Test Results Matrix:\n');
  console.log(`${'Test Name'.padEnd(50)} ${'Result'.padStart(6)}`);
  console.log(`${'='.repeat(50)} ${'='.repeat(6)}`);
  
  // Run all tests from the matrix
  for (const [name, testFunc] of tests) {
    testsRun++;
    const passed = testFunc();
    
    const result = passed ? 'PASS' : 'FAIL';
    console.log(`${name.padEnd(50)} ${result.padStart(6)}`);
    
    if (passed) {
      testsPassed++;
    } else {
      testsFailed++;
    }
  }
  
  console.log('\n========================================');
  console.log(`Summary: ${testsPassed}/${testsRun} tests passed`);
  console.log('========================================\n');
  
  return testsFailed > 0 ? 1 : 0;
}

process.exit(main());
