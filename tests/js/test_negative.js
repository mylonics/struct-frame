/**
 * Negative tests for struct-frame JavaScript parser
 * 
 * Tests error handling for:
 * - Corrupted CRC/checksum
 * - Truncated frames
 * - Invalid start bytes
 * - Malformed data
 */

const {
  ProfileStandardWriter,
  ProfileStandardReader,
  ProfileStandardAccumulatingReader,
  ProfileBulkWriter,
  ProfileBulkReader,
  ProfileSensorWriter,
  ProfileSensorReader,
  ProfileNetworkWriter,
  ProfileNetworkReader
} = require('../generated/js/frame-profiles');

const {
  BasicTypesMessage,
  getMessageInfo
} = require('../generated/js/serialization-test.structframe');

const {
  PackageTestMessage,
  CrossPackageMessage,
  getMessageInfo: getPkgTestMessagesMessageInfo,
  PACKAGE_ID: PKG_TEST_MESSAGES_PACKAGE_ID,
} = require('../generated/js/pkg-test-messages.structframe');

const {
  ActionMessage,
  PACKAGE_ID: PKG_TEST_A_PACKAGE_ID,
} = require('../generated/js/pkg-test-a.structframe');

// Test result tracking
let testsRun = 0;
let testsPassed = 0;
let testsFailed = 0;

function createTestMessage() {
  const msg = new BasicTypesMessage();
  msg.smallInt = 42;
  msg.mediumInt = 1000;
  msg.regularInt = 100000;
  msg.largeInt = BigInt(1000000000);
  msg.smallUint = 200;
  msg.mediumUint = 50000;
  msg.regularUint = 3000000000;
  msg.largeUint = BigInt('9000000000000000000');
  msg.singlePrecision = 3.14159;
  msg.doublePrecision = 2.71828;
  msg.flag = true;
  msg.deviceId = 'DEVICE123';
  msg.description = 'Test device';
  return msg;
}

/**
 * Test: Parser rejects frame with corrupted CRC
 */
function testCorruptedCrc() {
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
  const reader = new ProfileStandardReader(buffer.subarray(0, bytesWritten), getMessageInfo);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser rejects truncated frame
 */
function testTruncatedFrame() {
  const msg = createTestMessage();
  
  const writer = new ProfileStandardWriter(1024);
  writer.write(msg);
  const buffer = writer.data();
  const bytesWritten = writer.size;
  
  if (bytesWritten < 10) return false;
  
  // Truncate the frame
  const truncatedSize = bytesWritten - 5;
  
  // Try to parse - should fail
  const reader = new ProfileStandardReader(buffer.subarray(0, truncatedSize), getMessageInfo);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser rejects frame with invalid start bytes
 */
function testInvalidStartBytes() {
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
  const reader = new ProfileStandardReader(buffer.subarray(0, bytesWritten), getMessageInfo);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser handles zero-length buffer
 */
function testZeroLengthBuffer() {
  const buffer = new Uint8Array(0);
  
  const reader = new ProfileStandardReader(buffer, getMessageInfo);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser handles corrupted length field
 */
function testCorruptedLength() {
  const msg = createTestMessage();
  
  const writer = new ProfileStandardWriter(1024);
  writer.write(msg);
  const buffer = writer.data();
  const bytesWritten = writer.size;
  
  if (bytesWritten < 4) return false;
  
  // Corrupt length field (byte 2)
  buffer[2] = 0xFF;
  
  // Try to parse - should fail
  const reader = new ProfileStandardReader(buffer.subarray(0, bytesWritten), getMessageInfo);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Streaming parser rejects corrupted CRC
 */
function testStreamingCorruptedCrc() {
  const msg = createTestMessage();
  
  const writer = new ProfileStandardWriter(1024);
  writer.write(msg);
  const buffer = writer.data();
  const bytesWritten = writer.size;
  
  if (bytesWritten < 4) return false;
  
  // Corrupt CRC
  buffer[bytesWritten - 1] ^= 0xFF;
  
  // Try streaming parse
  const reader = new ProfileStandardAccumulatingReader(getMessageInfo, 1024);
  
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
function testStreamingGarbage() {
  const reader = new ProfileStandardAccumulatingReader(getMessageInfo, 1024);
  
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
function testBulkProfileCorruptedCrc() {
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
  const reader = new ProfileBulkReader(buffer.subarray(0, bytesWritten), getMessageInfo);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Multiple frames with corrupted middle frame
 */
function testMultipleCorruptedFrames() {
  // Create buffer with 3 messages
  const writer = new ProfileStandardWriter(4096);
  
  const msg1 = createTestMessage();
  msg1.smallInt = 1;
  writer.write(msg1);
  const bytes1End = writer.size;
  
  const msg2 = createTestMessage();
  msg2.smallInt = 2;
  writer.write(msg2);
  const bytes2End = writer.size;
  
  const msg3 = createTestMessage();
  msg3.smallInt = 3;
  writer.write(msg3);
  
  const buffer = writer.data();
  const totalBytes = writer.size;
  
  // Corrupt second frame's CRC (last byte before third frame)
  buffer[bytes2End - 1] ^= 0xFF;
  
  // Parse all frames
  const reader = new ProfileStandardReader(buffer.subarray(0, totalBytes), getMessageInfo);
  
  const result1 = reader.next();
  if (!result1.valid) return false;  // First should be valid
  
  const result2 = reader.next();
  return !result2.valid;  // Second should be invalid
}

/**
 * Test: AccumulatingReader handles a frame fed in two separate addData chunks
 */
function testPartialFrameBoundary() {
  const msg = createTestMessage();
  
  const writer = new ProfileStandardWriter(1024);
  writer.write(msg);
  const buffer = writer.data();
  const frameSize = writer.size;
  
  if (frameSize < 10) return false;
  
  const mid = Math.floor(frameSize / 2);
  
  const reader = new ProfileStandardAccumulatingReader(getMessageInfo, 1024);
  
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
 * Corrupting byte 3 (msg_id) to 0xFF causes getMessageInfo to return {0,0,0} magic.
 */
function testInvalidMsgId() {
  const msg = createTestMessage();
  const writer = new ProfileStandardWriter(1024);
  writer.write(msg);
  const buffer = Buffer.from(writer.data());
  const frameSize = writer.size;

  if (frameSize < 5) return false;

  // Corrupt the msg_id byte (byte 3: [start1][start2][len][msg_id]...)
  // 0xFF is not a known message ID → getMessageInfo returns {0,0,0} magic → CRC fails
  buffer[3] = 0xFF;

  const reader = new ProfileStandardReader(buffer.subarray(0, frameSize), getMessageInfo);
  const result = reader.next();
  return !result.valid;  // Expect failure: CRC mismatch due to wrong magic values
}

/**
 * Test: Minimal profile (no CRC) rejects a truncated frame.
 * ProfileSensor layout: [0x70][MSG_ID][PAYLOAD...]  (no CRC, no length field)
 * Parser uses getMessageInfo to determine expected payload size; truncated buffer → rejected.
 */
function testMinimalProfileTruncatedFrame() {
  const msg = createTestMessage();
  const writer = new ProfileSensorWriter(1024);
  writer.write(msg);
  const buffer = writer.data();
  const frameSize = writer.size;

  if (frameSize <= 5) return false;

  // Provide fewer bytes than the full frame to trigger truncation error
  const truncated = frameSize - 5;
  const reader = new ProfileSensorReader(buffer.subarray(0, truncated), getMessageInfo);
  const result = reader.next();
  return !result.valid;  // Expect failure: buffer too small for expected payload
}

/**
 * Test: Network profile validates sys_id/comp_id as part of CRC-protected header.
 * ProfileNetwork layout: [0x90][0x78][SEQ][SYS_ID][COMP_ID][LEN_LO][LEN_HI][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * sys_id is at byte 3 (within CRC region); corrupting it causes CRC failure.
 */
function testNetworkSysIdCompId() {
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

  const reader = new ProfileNetworkReader(buffer.subarray(0, frameSize), getMessageInfo);
  const result = reader.next();
  return !result.valid;  // Expect failure: corrupted sys_id invalidates CRC
}

/**
 * Test: Bulk profile rejects corrupted pkg_id byte.
 * ProfileBulk layout: [0x90][0x71][LEN][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * Corrupting pkg_id (byte 3) causes CRC failure.
 */
function testBulkCorruptedPkgId() {
  const msg = new PackageTestMessage();
  msg.createdAt = [{ seconds: BigInt(12345), nanoseconds: 67890 }];
  msg.currentStatus = 1; // Active
  msg.name = 'TestDevice';

  const writer = new ProfileBulkWriter(1024);
  writer.write(msg);
  const buffer = Buffer.from(writer.data());
  const frameSize = writer.size;

  if (frameSize < 6) return false;

  // Corrupt pkg_id byte (byte 3 for Bulk: [start1][start2][len][pkg_id][msg_id]...)
  buffer[3] ^= 0xFF;

  const reader = new ProfileBulkReader(buffer.subarray(0, frameSize), getPkgTestMessagesMessageInfo);
  const result = reader.next();
  return !result.valid;  // Expect failure: corrupted pkg_id invalidates CRC
}

/**
 * Test: Network profile rejects corrupted pkg_id byte.
 * ProfileNetwork layout: [0x90][0x78][SEQ][SYS_ID][COMP_ID][LEN_LO][LEN_HI][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * Corrupting pkg_id (byte 7) causes CRC failure.
 */
function testNetworkCorruptedPkgId() {
  const msg = new PackageTestMessage();
  msg.createdAt = [{ seconds: BigInt(12345), nanoseconds: 67890 }];
  msg.currentStatus = 1; // Active
  msg.name = 'TestDevice';

  const writer = new ProfileNetworkWriter(1024);
  writer.write(msg, { seq: 1, sysId: 5, compId: 10 });
  const buffer = Buffer.from(writer.data());
  const frameSize = writer.size;

  if (frameSize < 10) return false;

  // Corrupt pkg_id byte (byte 7 for Network)
  buffer[7] ^= 0xFF;

  const reader = new ProfileNetworkReader(buffer.subarray(0, frameSize), getPkgTestMessagesMessageInfo);
  const result = reader.next();
  return !result.valid;  // Expect failure: corrupted pkg_id invalidates CRC
}

/**
 * Test: Cross-package message rejection.
 * Encode a pkg_test_a message (pkgid=2) and try to parse it as pkg_test_messages (pkgid=1).
 * The parser should reject it because pkg_id won't match.
 */
function testCrossPackageRejection() {
  // Encode a pkg_test_a message (pkgid=2, msg_id=513)
  const msg = new ActionMessage();
  msg.action = 0; // Start
  msg.targetId = 42;
  msg.descriptionLength = 4;
  msg.descriptionData = 'test';

  const writer = new ProfileBulkWriter(1024);
  writer.write(msg);
  const buffer = Buffer.from(writer.data());
  const frameSize = writer.size;

  if (frameSize < 6) return false;

  // Try to parse with getPkgTestMessagesMessageInfo - the pkg_id (2) won't match pkg_test_messages (1)
  const reader = new ProfileBulkReader(buffer.subarray(0, frameSize), getPkgTestMessagesMessageInfo);
  const result = reader.next();

  // The frame may parse as valid at the frame level, but the msg_id should be 513 (pkg_test_a)
  // not a pkg_test_messages ID. Check that the msg_id doesn't belong to pkg_test_messages.
  if (!result.valid) return true;  // If parsing failed, that's good

  // If parsing succeeded, verify it's NOT a pkg_test_messages message
  const expectedPkgId = (result.msgId >> 8) & 0xFF;
  return expectedPkgId !== PKG_TEST_MESSAGES_PACKAGE_ID;
}

/**
 * Test: Bulk profile rejects corrupted msg_id low byte.
 * ProfileBulk layout: [0x90][0x71][LEN][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * Corrupting msg_id low byte (byte 4) changes the message type → wrong magic → CRC fails.
 */
function testBulkCorruptedMsgIdLowByte() {
  const msg = new PackageTestMessage();
  msg.createdAt = [{ seconds: BigInt(12345), nanoseconds: 67890 }];
  msg.currentStatus = 1; // Active
  msg.name = 'TestDevice';

  const writer = new ProfileBulkWriter(1024);
  writer.write(msg);
  const buffer = Buffer.from(writer.data());
  const frameSize = writer.size;

  if (frameSize < 6) return false;

  // Corrupt msg_id low byte (byte 4 for Bulk)
  buffer[4] ^= 0xFF;

  const reader = new ProfileBulkReader(buffer.subarray(0, frameSize), getPkgTestMessagesMessageInfo);
  const result = reader.next();
  return !result.valid;  // Expect failure: wrong msg_id → wrong magic → CRC fails
}

/**
 * Test: BufferReader advances past a CRC-failed frame and decodes the next valid frame.
 * Catches the A2 stall: BufferReader was not advancing past CRC failures.
 */
function testBufferReaderSkipsCrcFailure() {
  const writer = new ProfileStandardWriter(2048);
  const msg = createTestMessage();
  writer.write(msg);
  const firstFrameEnd = writer.size;
  writer.write(msg);
  const total = writer.size;

  const buffer = Buffer.from(writer.data());
  buffer[firstFrameEnd - 1] ^= 0xFF;
  buffer[firstFrameEnd - 2] ^= 0xFF;

  const reader = new ProfileStandardReader(buffer.subarray(0, total), getMessageInfo);

  const result1 = reader.next();
  if (result1.valid) return false;  // First frame must fail (CRC corrupted)

  const result2 = reader.next();
  return result2.valid;  // Second frame must succeed after skipping the bad one
}

/**
 * Test: AccumulatingReader buffer mode recovers after a CRC failure in addData path.
 * Catches the A3 stall: CRC-bad frames caused a permanent loop in buffer mode.
 */
function testBufferModeRecoversAfterCrcFailure() {
  const writer = new ProfileStandardWriter(1024);
  const msg = createTestMessage();
  writer.write(msg);
  const frameSize = writer.size;

  const badFrame = Buffer.from(writer.data().subarray(0, frameSize));
  badFrame[frameSize - 1] ^= 0xFF;
  badFrame[frameSize - 2] ^= 0xFF;

  const reader = new ProfileStandardAccumulatingReader(getMessageInfo, 1024);
  reader.addData(badFrame);
  const result1 = reader.next();
  if (result1.valid) return false;  // Must fail

  // Feed a valid frame — reader must not be stuck on the bad one
  const goodWriter = new ProfileStandardWriter(1024);
  goodWriter.write(msg);
  reader.addData(goodWriter.data().subarray(0, goodWriter.size));
  const result2 = reader.next();
  return result2.valid;
}

/**
 * Test: Stream mode recovers after garbage prefix and decodes a valid frame.
 */
function testStreamRecoversAfterGarbage() {
  const reader = new ProfileStandardAccumulatingReader(getMessageInfo, 1024);

  const garbage = new Uint8Array([0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56]);
  for (const byte of garbage) reader.pushByte(byte);

  const writer = new ProfileStandardWriter(1024);
  const msg = createTestMessage();
  writer.write(msg);
  const frameData = writer.data().subarray(0, writer.size);

  for (let i = 0; i < frameData.length; i++) {
    const r = reader.pushByte(frameData[i]);
    if (r.valid) return true;
  }
  return false;
}

function main() {
  console.log('\n========================================');
  console.log('NEGATIVE TESTS - JavaScript Parser');
  console.log('========================================\n');
  
  // Define test matrix
  const tests = [
    ['Buffer mode: recovers after CRC failure', testBufferModeRecoversAfterCrcFailure],
    ['Buffer reader: skips CRC-failed frame', testBufferReaderSkipsCrcFailure],
    ['Bulk profile: Corrupted CRC', testBulkProfileCorruptedCrc],
    ['Bulk profile: Corrupted pkg_id', testBulkCorruptedPkgId],
    ['Bulk profile: Corrupted msg_id low byte', testBulkCorruptedMsgIdLowByte],
    ['Corrupted CRC detection', testCorruptedCrc],
    ['Corrupted length field detection', testCorruptedLength],
    ['Cross-package message rejection', testCrossPackageRejection],
    ['Invalid message ID rejection', testInvalidMsgId],
    ['Invalid start bytes detection', testInvalidStartBytes],
    ['Minimal profile: Truncated frame', testMinimalProfileTruncatedFrame],
    ['Multiple frames: Corrupted middle frame', testMultipleCorruptedFrames],
    ['Network profile: Corrupted pkg_id', testNetworkCorruptedPkgId],
    ['Network profile: SysId/CompId corruption', testNetworkSysIdCompId],
    ['Partial frame across buffer boundary', testPartialFrameBoundary],
    ['Stream mode: recovers after garbage prefix', testStreamRecoversAfterGarbage],
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
