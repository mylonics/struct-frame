"use strict";
/**
 * Negative tests for struct-frame TypeScript parser
 *
 * Tests error handling for:
 * - Corrupted CRC/checksum
 * - Truncated frames
 * - Invalid start bytes
 * - Malformed data
 */
Object.defineProperty(exports, "__esModule", { value: true });
var frame_profiles_1 = require("../generated/ts/frame-profiles");
var serialization_test_structframe_1 = require("../generated/ts/serialization_test.structframe");
// Test result tracking
var testsRun = 0;
var testsPassed = 0;
var testsFailed = 0;
function testResult(name, passed) {
    testsRun++;
    if (passed) {
        console.log("  [TEST] ".concat(name, "... PASS"));
        testsPassed++;
    }
    else {
        console.log("  [TEST] ".concat(name, "... FAIL"));
        testsFailed++;
    }
}
function createTestMessage() {
    var msg = new serialization_test_structframe_1.SerializationTestBasicTypesMessage();
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
function testCorruptedCrc() {
    var msg = createTestMessage();
    var writer = new frame_profiles_1.ProfileStandardWriter(1024);
    writer.write(msg);
    var buffer = writer.data();
    var bytesWritten = writer.size();
    if (bytesWritten < 4)
        return false;
    // Corrupt the CRC (last 2 bytes)
    buffer[bytesWritten - 1] ^= 0xFF;
    buffer[bytesWritten - 2] ^= 0xFF;
    // Try to parse - should fail
    var reader = new frame_profiles_1.ProfileStandardReader(buffer.subarray(0, bytesWritten), serialization_test_structframe_1.get_message_info);
    var result = reader.next();
    return !result.valid; // Expect failure
}
/**
 * Test: Parser rejects truncated frame
 */
function testTruncatedFrame() {
    var msg = createTestMessage();
    var writer = new frame_profiles_1.ProfileStandardWriter(1024);
    writer.write(msg);
    var buffer = writer.data();
    var bytesWritten = writer.size();
    if (bytesWritten < 10)
        return false;
    // Truncate the frame
    var truncatedSize = bytesWritten - 5;
    // Try to parse - should fail
    var reader = new frame_profiles_1.ProfileStandardReader(buffer.subarray(0, truncatedSize), serialization_test_structframe_1.get_message_info);
    var result = reader.next();
    return !result.valid; // Expect failure
}
/**
 * Test: Parser rejects frame with invalid start bytes
 */
function testInvalidStartBytes() {
    var msg = createTestMessage();
    var writer = new frame_profiles_1.ProfileStandardWriter(1024);
    writer.write(msg);
    var buffer = writer.data();
    var bytesWritten = writer.size();
    if (bytesWritten < 2)
        return false;
    // Corrupt start bytes
    buffer[0] = 0xDE;
    buffer[1] = 0xAD;
    // Try to parse - should fail
    var reader = new frame_profiles_1.ProfileStandardReader(buffer.subarray(0, bytesWritten), serialization_test_structframe_1.get_message_info);
    var result = reader.next();
    return !result.valid; // Expect failure
}
/**
 * Test: Parser handles zero-length buffer
 */
function testZeroLengthBuffer() {
    var buffer = new Uint8Array(0);
    var reader = new frame_profiles_1.ProfileStandardReader(buffer, serialization_test_structframe_1.get_message_info);
    var result = reader.next();
    return !result.valid; // Expect failure
}
/**
 * Test: Parser handles corrupted length field
 */
function testCorruptedLength() {
    var msg = createTestMessage();
    var writer = new frame_profiles_1.ProfileStandardWriter(1024);
    writer.write(msg);
    var buffer = writer.data();
    var bytesWritten = writer.size();
    if (bytesWritten < 4)
        return false;
    // Corrupt length field (byte 2)
    buffer[2] = 0xFF;
    // Try to parse - should fail
    var reader = new frame_profiles_1.ProfileStandardReader(buffer.subarray(0, bytesWritten), serialization_test_structframe_1.get_message_info);
    var result = reader.next();
    return !result.valid; // Expect failure
}
/**
 * Test: Streaming parser rejects corrupted CRC
 */
function testStreamingCorruptedCrc() {
    var msg = createTestMessage();
    var writer = new frame_profiles_1.ProfileStandardWriter(1024);
    writer.write(msg);
    var buffer = writer.data();
    var bytesWritten = writer.size();
    if (bytesWritten < 4)
        return false;
    // Corrupt CRC
    buffer[bytesWritten - 1] ^= 0xFF;
    // Try streaming parse
    var reader = new frame_profiles_1.ProfileStandardAccumulatingReader(serialization_test_structframe_1.get_message_info, 1024);
    // Feed byte by byte
    for (var i = 0; i < bytesWritten; i++) {
        reader.pushByte(buffer[i]);
    }
    var result = reader.next();
    return !result.valid; // Expect failure
}
/**
 * Test: Streaming parser handles garbage data
 */
function testStreamingGarbage() {
    var reader = new frame_profiles_1.ProfileStandardAccumulatingReader(serialization_test_structframe_1.get_message_info, 1024);
    // Feed garbage bytes
    var garbage = new Uint8Array([0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56, 0x78, 0x9A]);
    for (var _i = 0, garbage_1 = garbage; _i < garbage_1.length; _i++) {
        var byte = garbage_1[_i];
        reader.pushByte(byte);
    }
    var result = reader.next();
    return !result.valid; // Expect no valid frame
}
/**
 * Test: Bulk profile with corrupted CRC
 */
function testBulkProfileCorruptedCrc() {
    var msg = createTestMessage();
    var writer = new frame_profiles_1.ProfileBulkWriter(1024);
    writer.write(msg);
    var buffer = writer.data();
    var bytesWritten = writer.size();
    if (bytesWritten < 4)
        return false;
    // Corrupt the CRC (last 2 bytes)
    buffer[bytesWritten - 1] ^= 0xFF;
    buffer[bytesWritten - 2] ^= 0xFF;
    // Try to parse - should fail
    var reader = new frame_profiles_1.ProfileBulkReader(buffer.subarray(0, bytesWritten), serialization_test_structframe_1.get_message_info);
    var result = reader.next();
    return !result.valid; // Expect failure
}
function main() {
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
    console.log("Tests run:    ".concat(testsRun));
    console.log("Tests passed: ".concat(testsPassed));
    console.log("Tests failed: ".concat(testsFailed));
    console.log('========================================\n');
    return testsFailed > 0 ? 1 : 0;
}
process.exit(main());
