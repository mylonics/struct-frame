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
  BufferWriter,
  BufferReader,
  AccumulatingReader,
  ProfileStandardConfig,
  ProfileSensorConfig,
  ProfileBulkConfig,
  ProfileNetworkConfig,
} from '../generated/ts/frame-profiles';

import { FrameMsgStatus } from '../generated/ts/frame-base';

import {
  BasicTypesMessage,
  getMessageInfo
} from '../generated/ts/serialization-test.structframe';

import {
  PackageTestMessage,
  CrossPackageMessage,
  getMessageInfo as getPkgTestMessagesMessageInfo,
  PACKAGE_ID as PKG_TEST_MESSAGES_PACKAGE_ID,
} from '../generated/ts/pkg-test-messages.structframe';

import {
  ActionMessage,
  PACKAGE_ID as PKG_TEST_A_PACKAGE_ID,
} from '../generated/ts/pkg-test-a.structframe';

// Test result tracking
let testsRun = 0;
let testsPassed = 0;
let testsFailed = 0;

function createTestMessage(): BasicTypesMessage {
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
  msg.descriptionData = 'Test device';
  return msg;
}

function tryNextCompat(reader: any): any | null {
  if (typeof reader.tryNext === 'function') {
    return reader.tryNext();
  }
  const result = reader.next();
  return (result.valid || (result.frameSize ?? 0) > 0) ? result : null;
}

/**
 * Test: Parser rejects frame with corrupted CRC
 */
function testCorruptedCrc(): boolean {
  const msg = createTestMessage();
  
  const writer = new BufferWriter(ProfileStandardConfig, 1024);
  writer.write(msg);
  const buffer = writer.data();
  const bytesWritten = writer.size;
  
  if (bytesWritten < 4) return false;
  
  // Corrupt the CRC (last 2 bytes)
  buffer[bytesWritten - 1] ^= 0xFF;
  buffer[bytesWritten - 2] ^= 0xFF;
  
  // Try to parse - should fail
  const reader = new BufferReader(ProfileStandardConfig, buffer.subarray(0, bytesWritten), getMessageInfo);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser rejects truncated frame
 */
function testTruncatedFrame(): boolean {
  const msg = createTestMessage();
  
  const writer = new BufferWriter(ProfileStandardConfig, 1024);
  writer.write(msg);
  const buffer = writer.data();
  const bytesWritten = writer.size;
  
  if (bytesWritten < 10) return false;
  
  // Truncate the frame
  const truncatedSize = bytesWritten - 5;
  
  // Try to parse - should fail
  const reader = new BufferReader(ProfileStandardConfig, buffer.subarray(0, truncatedSize), getMessageInfo);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser rejects frame with invalid start bytes
 */
function testInvalidStartBytes(): boolean {
  const msg = createTestMessage();
  
  const writer = new BufferWriter(ProfileStandardConfig, 1024);
  writer.write(msg);
  const buffer = writer.data();
  const bytesWritten = writer.size;
  
  if (bytesWritten < 2) return false;
  
  // Corrupt start bytes
  buffer[0] = 0xDE;
  buffer[1] = 0xAD;
  
  // Try to parse - should fail
  const reader = new BufferReader(ProfileStandardConfig, buffer.subarray(0, bytesWritten), getMessageInfo);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser handles zero-length buffer
 */
function testZeroLengthBuffer(): boolean {
  const buffer = new Uint8Array(0);
  
  const reader = new BufferReader(ProfileStandardConfig, buffer, getMessageInfo);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Parser handles corrupted length field
 */
function testCorruptedLength(): boolean {
  const msg = createTestMessage();
  
  const writer = new BufferWriter(ProfileStandardConfig, 1024);
  writer.write(msg);
  const buffer = writer.data();
  const bytesWritten = writer.size;
  
  if (bytesWritten < 4) return false;
  
  // Corrupt length field (byte 2)
  buffer[2] = 0xFF;
  
  // Try to parse - should fail
  const reader = new BufferReader(ProfileStandardConfig, buffer.subarray(0, bytesWritten), getMessageInfo);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Streaming parser rejects corrupted CRC
 */
function testStreamingCorruptedCrc(): boolean {
  const msg = createTestMessage();
  
  const writer = new BufferWriter(ProfileStandardConfig, 1024);
  writer.write(msg);
  const buffer = writer.data();
  const bytesWritten = writer.size;
  
  if (bytesWritten < 4) return false;
  
  // Corrupt CRC
  buffer[bytesWritten - 1] ^= 0xFF;
  
  // Try streaming parse
  const reader = new AccumulatingReader(ProfileStandardConfig, getMessageInfo, 1024);
  
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
  const reader = new AccumulatingReader(ProfileStandardConfig, getMessageInfo, 1024);
  
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
  
  const writer = new BufferWriter(ProfileBulkConfig, 1024);
  writer.write(msg);
  const buffer = writer.data();
  const bytesWritten = writer.size;
  
  if (bytesWritten < 4) return false;
  
  // Corrupt the CRC (last 2 bytes)
  buffer[bytesWritten - 1] ^= 0xFF;
  buffer[bytesWritten - 2] ^= 0xFF;
  
  // Try to parse - should fail
  const reader = new BufferReader(ProfileBulkConfig, buffer.subarray(0, bytesWritten), getMessageInfo);
  const result = reader.next();
  
  return !result.valid;  // Expect failure
}

/**
 * Test: Multiple frames with corrupted middle frame
 */
function testMultipleCorruptedFrames(): boolean {
  // Create buffer with 3 messages
  const writer = new BufferWriter(ProfileStandardConfig, 4096);
  
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
  const reader = new BufferReader(ProfileStandardConfig, buffer.subarray(0, totalBytes), getMessageInfo);
  
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
  
  const writer = new BufferWriter(ProfileStandardConfig, 1024);
  writer.write(msg);
  const buffer = writer.data();
  const frameSize = writer.size;
  
  if (frameSize < 10) return false;
  
  const mid = Math.floor(frameSize / 2);
  
  const reader = new AccumulatingReader(ProfileStandardConfig, getMessageInfo, 1024);
  
  // Feed first half via addData, then call next() to save partial data to internal buffer
  reader.addData(buffer.subarray(0, mid));
  const partial = reader.next();
  if (partial.valid) return false;
  
  // Feed second half - adds to internal buffer completing the frame
  reader.addData(buffer.subarray(mid, frameSize));
  
  // Call next() once all data is present - should successfully decode the frame
  const result = reader.next();
  if (!result.valid) return false;
  if (result.msgId !== BasicTypesMessage._msgid) return false;

  const decoded = BasicTypesMessage.deserialize(result);
  if (decoded.smallInt !== msg.smallInt) return false;
  if (decoded.flag !== msg.flag) return false;

  if (reader.hasMore()) return false;

  return true;
}

/**
 * Test: Parser rejects frame with unknown message ID (CRC fails with wrong magic values).
 * ProfileStandard layout: [0x90][0x71][LEN][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * Corrupting byte 3 (msg_id) to 0xFF causes getMessageInfo to return {0,0,0} magic.
 */
function testInvalidMsgId(): boolean {
  const msg = createTestMessage();
  const writer = new BufferWriter(ProfileStandardConfig, 1024);
  writer.write(msg);
  const buffer = Buffer.from(writer.data());
  const frameSize = writer.size;

  if (frameSize < 5) return false;

  // Corrupt the msg_id byte (byte 3: [start1][start2][len][msg_id]...)
  // 0xFF is not a known message ID â†’ getMessageInfo returns {0,0,0} magic â†’ CRC fails
  buffer[3] = 0xFF;

  const reader = new BufferReader(ProfileStandardConfig, buffer.subarray(0, frameSize), getMessageInfo);
  const result = reader.next();
  return !result.valid;  // Expect failure: CRC mismatch due to wrong magic values
}

/**
 * Test: Minimal profile (no CRC) rejects a truncated frame.
 * ProfileSensor layout: [0x70][MSG_ID][PAYLOAD...]  (no CRC, no length field)
 * Parser uses getMessageInfo to determine expected payload size; truncated buffer â†’ rejected.
 */
function testMinimalProfileTruncatedFrame(): boolean {
  const msg = createTestMessage();
  const writer = new BufferWriter(ProfileSensorConfig, 1024);
  writer.write(msg);
  const buffer = writer.data();
  const frameSize = writer.size;

  if (frameSize <= 5) return false;

  // Provide fewer bytes than the full frame to trigger truncation error
  const truncated = frameSize - 5;
  const reader = new BufferReader(ProfileSensorConfig, buffer.subarray(0, truncated), getMessageInfo);
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
  const writer = new BufferWriter(ProfileNetworkConfig, 1024);
  // Encode with seq=1, sysId=5, compId=10
  writer.write(msg, { seq: 1, sysId: 5, compId: 10 });
  const buffer = Buffer.from(writer.data());
  const frameSize = writer.size;

  if (frameSize < 10) return false;

  // Corrupt sys_id (byte 3: [start1][start2][seq][sys_id]...)
  // sys_id is inside the CRC-protected region so CRC will fail
  buffer[3] ^= 0xFF;

  const reader = new BufferReader(ProfileNetworkConfig, buffer.subarray(0, frameSize), getMessageInfo);
  const result = reader.next();
  return !result.valid;  // Expect failure: corrupted sys_id invalidates CRC
}

/**
 * Test: Bulk profile rejects corrupted pkg_id byte.
 * ProfileBulk layout: [0x90][0x71][LEN][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * Corrupting pkg_id (byte 3) causes CRC failure.
 */
function testBulkCorruptedPkgId(): boolean {
  const msg = new PackageTestMessage();
  msg.createdAt = [{ seconds: BigInt(12345), nanoseconds: 67890 }];
  msg.currentStatus = 1; // Active
  msg.name = 'TestDevice';

  const writer = new BufferWriter(ProfileBulkConfig, 1024);
  writer.write(msg);
  const buffer = Buffer.from(writer.data());
  const frameSize = writer.size;

  if (frameSize < 6) return false;

  // Corrupt pkg_id byte (byte 3 for Bulk: [start1][start2][len][pkg_id][msg_id]...)
  buffer[3] ^= 0xFF;

  const reader = new BufferReader(ProfileBulkConfig, buffer.subarray(0, frameSize), getPkgTestMessagesMessageInfo);
  const result = reader.next();
  return !result.valid;  // Expect failure: corrupted pkg_id invalidates CRC
}

/**
 * Test: Network profile rejects corrupted pkg_id byte.
 * ProfileNetwork layout: [0x90][0x78][SEQ][SYS_ID][COMP_ID][LEN_LO][LEN_HI][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
 * Corrupting pkg_id (byte 7) causes CRC failure.
 */
function testNetworkCorruptedPkgId(): boolean {
  const msg = new PackageTestMessage();
  msg.createdAt = [{ seconds: BigInt(12345), nanoseconds: 67890 }];
  msg.currentStatus = 1; // Active
  msg.name = 'TestDevice';

  const writer = new BufferWriter(ProfileNetworkConfig, 1024);
  writer.write(msg, { seq: 1, sysId: 5, compId: 10 });
  const buffer = Buffer.from(writer.data());
  const frameSize = writer.size;

  if (frameSize < 10) return false;

  // Corrupt pkg_id byte (byte 7 for Network)
  buffer[7] ^= 0xFF;

  const reader = new BufferReader(ProfileNetworkConfig, buffer.subarray(0, frameSize), getPkgTestMessagesMessageInfo);
  const result = reader.next();
  return !result.valid;  // Expect failure: corrupted pkg_id invalidates CRC
}

/**
 * Test: Cross-package message rejection.
 * Encode a pkg_test_a message (pkgid=2) and try to parse it as pkg_test_messages (pkgid=1).
 * The parser should reject it because pkg_id won't match.
 */
function testCrossPackageRejection(): boolean {
  // Encode a pkg_test_a message (pkgid=2, msg_id=513)
  const msg = new ActionMessage();
  msg.action = 0; // Start
  msg.targetId = 42;
  msg.descriptionLength = 4;
  msg.descriptionData = 'test';

  const writer = new BufferWriter(ProfileBulkConfig, 1024);
  writer.write(msg);
  const buffer = Buffer.from(writer.data());
  const frameSize = writer.size;

  if (frameSize < 6) return false;

  // Try to parse with getPkgTestMessagesMessageInfo - the pkg_id (2) won't match pkg_test_messages (1)
  const reader = new BufferReader(ProfileBulkConfig, buffer.subarray(0, frameSize), getPkgTestMessagesMessageInfo);
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
 * Corrupting msg_id low byte (byte 4) changes the message type â†’ wrong magic â†’ CRC fails.
 */
function testBulkCorruptedMsgIdLowByte(): boolean {
  const msg = new PackageTestMessage();
  msg.createdAt = [{ seconds: BigInt(12345), nanoseconds: 67890 }];
  msg.currentStatus = 1; // Active
  msg.name = 'TestDevice';

  const writer = new BufferWriter(ProfileBulkConfig, 1024);
  writer.write(msg);
  const buffer = Buffer.from(writer.data());
  const frameSize = writer.size;

  if (frameSize < 6) return false;

  // Corrupt msg_id low byte (byte 4 for Bulk)
  buffer[4] ^= 0xFF;

  const reader = new BufferReader(ProfileBulkConfig, buffer.subarray(0, frameSize), getPkgTestMessagesMessageInfo);
  const result = reader.next();
  return !result.valid;  // Expect failure: wrong msg_id â†’ wrong magic â†’ CRC fails
}

/**
 * Test: BufferReader advances past a CRC-failed frame and decodes the next valid frame.
 * Catches the A2 stall: BufferReader was not advancing past CRC failures.
 */
function testBufferReaderSkipsCrcFailure(): boolean {
  const writer = new BufferWriter(ProfileStandardConfig, 2048);
  const msg = createTestMessage();
  writer.write(msg);
  const firstFrameEnd = writer.size;
  writer.write(msg);
  const total = writer.size;

  const buffer = Buffer.from(writer.data());
  buffer[firstFrameEnd - 1] ^= 0xFF;
  buffer[firstFrameEnd - 2] ^= 0xFF;

  const reader = new BufferReader(ProfileStandardConfig, buffer.subarray(0, total), getMessageInfo);

  const result1 = reader.next();
  if (result1.valid) return false;  // First frame must fail (CRC corrupted)

  const result2 = reader.next();
  return result2.valid;  // Second frame must succeed after skipping the bad one
}

/**
 * Test: AccumulatingReader buffer mode recovers after a CRC failure in addData path.
 * Catches the A3 stall: CRC-bad frames caused a permanent loop in buffer mode.
 */
function testBufferModeRecoversAfterCrcFailure(): boolean {
  const writer = new BufferWriter(ProfileStandardConfig, 1024);
  const msg = createTestMessage();
  writer.write(msg);
  const frameSize = writer.size;

  const badFrame = Buffer.from(writer.data().subarray(0, frameSize));
  badFrame[frameSize - 1] ^= 0xFF;
  badFrame[frameSize - 2] ^= 0xFF;

  const reader = new AccumulatingReader(ProfileStandardConfig, getMessageInfo, 1024);
  reader.addData(badFrame);
  const result1 = reader.next();
  if (result1.valid) return false;  // Must fail

  // Feed a valid frame â€” reader must not be stuck on the bad one
  const goodWriter = new BufferWriter(ProfileStandardConfig, 1024);
  goodWriter.write(msg);
  reader.addData(goodWriter.data().subarray(0, goodWriter.size));
  const result2 = reader.next();
  return result2.valid;
}

/**
 * Test: Stream mode recovers after garbage prefix and decodes a valid frame.
 */
function testStreamRecoversAfterGarbage(): boolean {
  const reader = new AccumulatingReader(ProfileStandardConfig, getMessageInfo, 1024);

  const garbage = new Uint8Array([0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56]);
  for (const byte of garbage) reader.pushByte(byte);

  const writer = new BufferWriter(ProfileStandardConfig, 1024);
  const msg = createTestMessage();
  writer.write(msg);
  const frameData = writer.data().subarray(0, writer.size);

  for (let i = 0; i < frameData.length; i++) {
    const r = reader.pushByte(frameData[i]);
    if (r.valid) return true;
  }
  return false;
}

/**
 * Test: After a CRC failure the reader continues and decodes the next valid frame,
 * and the buffer-exhausted signal (hasMore() === false) is only set after ALL frames
 * are consumed — not immediately after the CRC error.
 */
function testCrcErrorThenValidFrame(): boolean {
  const writer = new BufferWriter(ProfileStandardConfig, 4096);
  const msg = createTestMessage();

  // Frame 1: valid
  msg.smallInt = 1;
  writer.write(msg);

  // Frame 2: CRC-corrupted
  msg.smallInt = 2;
  writer.write(msg);
  const frame2End = writer.size;

  // Frame 3: valid
  msg.smallInt = 3;
  writer.write(msg);
  const total = writer.size;

  const buffer = Buffer.from(writer.data());
  buffer[frame2End - 1] ^= 0xFF;
  buffer[frame2End - 2] ^= 0xFF;

  const reader = new BufferReader(ProfileStandardConfig, buffer.subarray(0, total), getMessageInfo);

  // Frame 1 must decode successfully
  const result1 = reader.next();
  if (!result1.valid) return false;

  // Frame 2 must report a CRC failure — status MUST be CrcFailure, not None
  const result2 = reader.next();
  if (result2.valid) return false;
  if (result2.status !== FrameMsgStatus.CrcFailure) return false;

  // Reader must continue past the CRC error and decode frame 3
  const result3 = reader.next();
  if (!result3.valid) return false;

  // Buffer must now be fully consumed
  if (reader.hasMore()) return false;

  return true;
}

/**
 * Test: AccumulatingReader preserves CRC error status when the failed frame spans
 * two addData() calls (the internal-buffer reassembly path).
 * Bug: the internal-buffer CRC path returned status=None instead of status=CrcFailure,
 * hiding the error from callers.
 */
function testSplitBufferCrcErrorStatus(): boolean {
  const writer = new BufferWriter(ProfileStandardConfig, 4096);
  const msg = createTestMessage();

  // Frame 1: valid
  msg.smallInt = 1;
  writer.write(msg);

  // Frame 2: CRC-corrupted
  msg.smallInt = 2;
  writer.write(msg);
  const frame2End = writer.size;

  // Frame 3: valid
  msg.smallInt = 3;
  writer.write(msg);
  const total = writer.size;

  const buffer = Buffer.from(writer.data());
  buffer[frame2End - 1] ^= 0xFF;
  buffer[frame2End - 2] ^= 0xFF;

  // Split so that frame 2's two CRC bytes land in the second addData() call,
  // forcing frame 2 to be assembled across the internal accumulation buffer.
  const splitPoint = frame2End - 2;
  const chunk1 = buffer.subarray(0, splitPoint);
  const chunk2 = buffer.subarray(splitPoint, total);

  const reader = new AccumulatingReader(ProfileStandardConfig, getMessageInfo, 1024);

  reader.addData(chunk1);

  // Frame 1 must decode from the first chunk
  const result1 = reader.next();
  if (!result1.valid) return false;

  // Frame 2 is still incomplete (no CRC bytes yet) — partial data saved internally
  const partial = reader.next();
  if (partial.valid) return false;

  reader.addData(chunk2);

  // CRC bytes of frame 2 arrive — frame 2 is now complete but CRC-corrupted.
  // Status MUST be CrcFailure (not None) so the caller knows to keep draining.
  const result2 = reader.next();
  if (result2.valid) return false;
  if (result2.status !== FrameMsgStatus.CrcFailure) return false;

  // Frame 3 must still be decodable from the remainder of chunk2
  const result3 = reader.next();
  if (!result3.valid) return false;

  return true;
}

/**
 * Test: tryNext drain loop surfaces CRC/resync progress and still delivers
 * the following valid frame.
 */
function testTryNextDrainContract(): boolean {
  const writer = new BufferWriter(ProfileStandardConfig, 4096);
  const msg = createTestMessage();

  msg.smallInt = 1;
  writer.write(msg);
  const firstEnd = writer.size;

  msg.smallInt = 2;
  writer.write(msg);
  const total = writer.size;

  const buffer = Buffer.from(writer.data());
  buffer[firstEnd - 1] ^= 0xFF;
  buffer[firstEnd - 2] ^= 0xFF;

  const reader = new AccumulatingReader(ProfileStandardConfig, getMessageInfo, 4096);
  reader.addData(buffer.subarray(0, total));

  let validCount = 0;
  let sawCrcFailure = false;
  let frame;
  while ((frame = tryNextCompat(reader)) !== null) {
    if (frame.valid) {
      validCount++;
    } else if (frame.status === FrameMsgStatus.CrcFailure) {
      sawCrcFailure = true;
    }
  }

  if (!sawCrcFailure) return false;
  if (validCount !== 1) return false;
  if (reader.hasMore()) return false;
  if (reader.hasPartial()) return false;
  if (reader.partialSize() !== 0) return false;
  return true;
}

/**
 * Test: tryNext partial-pending contract.
 */
function testTryNextPartialPendingContract(): boolean {
  const writer = new BufferWriter(ProfileStandardConfig, 1024);
  const msg = createTestMessage();
  writer.write(msg);
  const buffer = writer.data();
  const frameSize = writer.size;

  if (frameSize < 10) return false;
  const mid = Math.floor(frameSize / 2);

  const reader = new AccumulatingReader(ProfileStandardConfig, getMessageInfo, 1024);
  reader.addData(buffer.subarray(0, mid));

  if (tryNextCompat(reader) !== null) return false;
  if (!reader.hasPartial()) return false;
  if (reader.partialSize() <= 0) return false;

  reader.addData(buffer.subarray(mid, frameSize));

  let validCount = 0;
  let frame;
  while ((frame = tryNextCompat(reader)) !== null) {
    if (frame.valid) validCount++;
  }

  if (validCount !== 1) return false;
  if (reader.hasPartial()) return false;
  if (reader.partialSize() !== 0) return false;
  return !reader.hasMore();
}

function main(): number {
  console.log('\n========================================');
  console.log('NEGATIVE TESTS - TypeScript Parser');
  console.log('========================================\n');
  
  // Define test matrix
  const tests: Array<[string, () => boolean]> = [
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
    ['Multiple frames: CRC error then valid frame', testCrcErrorThenValidFrame],
    ['Multiple frames: Corrupted middle frame', testMultipleCorruptedFrames],
    ['Split-buffer: CRC error status preserved', testSplitBufferCrcErrorStatus],
    ['TryNext drain: CRC/resync + valid', testTryNextDrainContract],
    ['TryNext partial pending contract', testTryNextPartialPendingContract],
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

