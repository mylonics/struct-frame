#!/usr/bin/env python3
"""
Negative tests for struct-frame Python parser

Tests error handling for:
- Corrupted CRC/checksum
- Truncated frames
- Invalid start bytes
- Invalid message IDs
- Malformed data
"""

import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'generated', 'py'))

from struct_frame.generated.serialization_test import BasicTypesMessage as BasicTypesMessage, get_message_info
from frame_profiles import (
    ProfileStandardWriter,
    ProfileStandardReader,
    ProfileStandardAccumulatingReader,
    ProfileBulkWriter,
    ProfileBulkReader,
    ProfileSensorWriter,
    ProfileSensorReader,
    ProfileNetworkWriter,
    ProfileNetworkReader,
    ProfileNetworkAccumulatingReader,
    FrameMsgStatus,
)

# Test result tracking
tests_run = 0
tests_passed = 0
tests_failed = 0

def test_corrupted_crc():
    """Test: Parser rejects frame with corrupted CRC"""
    # Create a valid message
    msg = BasicTypesMessage()
    msg.small_int = 42
    msg.medium_int = 1000
    msg.regular_int = 100000
    msg.large_int = 1000000000
    msg.small_uint = 200
    msg.medium_uint = 50000
    msg.regular_uint = 3000000000
    msg.large_uint = 9000000000000000000
    msg.single_precision = 3.14159
    msg.double_precision = 2.71828
    msg.flag = True
    msg.device_id = b"DEVICE123"
    msg.description = b"Test device"
    
    # Encode message
    writer = ProfileStandardWriter(capacity=1024)
    writer.write(msg)
    buffer = bytearray(writer.data())
    bytes_written = writer.size()
    
    if bytes_written < 4:
        return False
    
    # Corrupt the CRC (last 2 bytes)
    buffer[bytes_written - 1] ^= 0xFF
    buffer[bytes_written - 2] ^= 0xFF
    
    # Try to parse - should fail
    reader = ProfileStandardReader(buffer=bytes(buffer[:bytes_written]), get_message_info=get_message_info)
    result = reader.next()
    
    return not result.valid  # Expect failure

def test_truncated_frame():
    """Test: Parser rejects truncated frame"""
    # Create a valid message
    msg = BasicTypesMessage()
    msg.small_int = 42
    msg.medium_int = 1000
    msg.regular_int = 100000
    msg.large_int = 1000000000
    msg.small_uint = 200
    msg.medium_uint = 50000
    msg.regular_uint = 3000000000
    msg.large_uint = 9000000000000000000
    msg.single_precision = 3.14159
    msg.double_precision = 2.71828
    msg.flag = True
    msg.device_id = b"DEVICE123"
    msg.description = b"Test device"
    
    # Encode message
    writer = ProfileStandardWriter(capacity=1024)
    writer.write(msg)
    buffer = bytearray(writer.data())
    bytes_written = writer.size()
    
    if bytes_written < 10:
        return False
    
    # Truncate the frame
    truncated_size = bytes_written - 5
    
    # Try to parse - should fail
    reader = ProfileStandardReader(buffer=bytes(buffer[:truncated_size]), get_message_info=get_message_info)
    result = reader.next()
    
    return not result.valid  # Expect failure

def test_invalid_start_bytes():
    """Test: Parser rejects frame with invalid start bytes"""
    # Create a valid message
    msg = BasicTypesMessage()
    msg.small_int = 42
    msg.medium_int = 1000
    msg.regular_int = 100000
    msg.large_int = 1000000000
    msg.small_uint = 200
    msg.medium_uint = 50000
    msg.regular_uint = 3000000000
    msg.large_uint = 9000000000000000000
    msg.single_precision = 3.14159
    msg.double_precision = 2.71828
    msg.flag = True
    msg.device_id = b"DEVICE123"
    msg.description = b"Test device"
    
    # Encode message
    writer = ProfileStandardWriter(capacity=1024)
    writer.write(msg)
    buffer = bytearray(writer.data())
    bytes_written = writer.size()
    
    if bytes_written < 2:
        return False
    
    # Corrupt start bytes
    buffer[0] = 0xDE
    buffer[1] = 0xAD
    
    # Try to parse - should fail
    reader = ProfileStandardReader(buffer=bytes(buffer[:bytes_written]), get_message_info=get_message_info)
    result = reader.next()
    
    return not result.valid  # Expect failure

def test_zero_length_buffer():
    """Test: Parser handles zero-length buffer"""
    reader = ProfileStandardReader(buffer=b'', get_message_info=get_message_info)
    result = reader.next()
    
    return not result.valid  # Expect failure

def test_corrupted_length():
    """Test: Parser handles corrupted length field"""
    # Create a valid message
    msg = BasicTypesMessage()
    msg.small_int = 42
    msg.medium_int = 1000
    msg.regular_int = 100000
    msg.large_int = 1000000000
    msg.small_uint = 200
    msg.medium_uint = 50000
    msg.regular_uint = 3000000000
    msg.large_uint = 9000000000000000000
    msg.single_precision = 3.14159
    msg.double_precision = 2.71828
    msg.flag = True
    msg.device_id = b"DEVICE123"
    msg.description = b"Test device"
    
    # Encode message
    writer = ProfileStandardWriter(capacity=1024)
    writer.write(msg)
    buffer = bytearray(writer.data())
    bytes_written = writer.size()
    
    if bytes_written < 4:
        return False
    
    # Corrupt length field (byte 2)
    buffer[2] = 0xFF
    
    # Try to parse - should fail
    reader = ProfileStandardReader(buffer=bytes(buffer[:bytes_written]), get_message_info=get_message_info)
    result = reader.next()
    
    return not result.valid  # Expect failure

def test_streaming_corrupted_crc():
    """Test: Streaming parser rejects corrupted CRC"""
    # Create a valid message
    msg = BasicTypesMessage()
    msg.small_int = 42
    msg.medium_int = 1000
    msg.regular_int = 100000
    msg.large_int = 1000000000
    msg.small_uint = 200
    msg.medium_uint = 50000
    msg.regular_uint = 3000000000
    msg.large_uint = 9000000000000000000
    msg.single_precision = 3.14159
    msg.double_precision = 2.71828
    msg.flag = True
    msg.device_id = b"DEVICE123"
    msg.description = b"Test device"
    
    # Encode message
    writer = ProfileStandardWriter(capacity=1024)
    writer.write(msg)
    buffer = bytearray(writer.data())
    bytes_written = writer.size()
    
    if bytes_written < 4:
        return False
    
    # Corrupt CRC
    buffer[bytes_written - 1] ^= 0xFF
    
    # Try streaming parse
    reader = ProfileStandardAccumulatingReader(get_message_info=get_message_info, buffer_size=1024)
    
    # Feed byte by byte
    for i in range(bytes_written):
        reader.push_byte(buffer[i])
    
    result = reader.next()
    return not result.valid  # Expect failure

def test_streaming_garbage():
    """Test: Streaming parser handles garbage data"""
    reader = ProfileStandardAccumulatingReader(get_message_info=get_message_info, buffer_size=1024)
    
    # Feed garbage bytes
    garbage = bytes([0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56, 0x78, 0x9A])
    
    for byte in garbage:
        reader.push_byte(byte)
    
    result = reader.next()
    return not result.valid  # Expect no valid frame

def test_multiple_corrupted_frames():
    """Test: Multiple frames with corrupted middle frame"""
    # Create buffer with 3 messages
    writer = ProfileStandardWriter(capacity=4096)
    
    msg1 = BasicTypesMessage()
    msg1.small_int = 1
    msg1.medium_int = 100
    msg1.regular_int = 10000
    msg1.large_int = 1000000
    msg1.small_uint = 2
    msg1.medium_uint = 200
    msg1.regular_uint = 20000
    msg1.large_uint = 2000000
    msg1.single_precision = 1.0
    msg1.double_precision = 1.0
    msg1.flag = True
    msg1.device_id = b"DEV1"
    msg1.description = b"First"
    
    bytes1 = writer.write(msg1)
    
    msg2 = BasicTypesMessage()
    msg2.small_int = 2
    msg2.medium_int = 200
    msg2.regular_int = 20000
    msg2.large_int = 2000000
    msg2.small_uint = 4
    msg2.medium_uint = 400
    msg2.regular_uint = 40000
    msg2.large_uint = 4000000
    msg2.single_precision = 2.0
    msg2.double_precision = 2.0
    msg2.flag = False
    msg2.device_id = b"DEV2"
    msg2.description = b"Second"
    
    bytes2_start = writer.size()
    bytes2 = writer.write(msg2)
    bytes2_end = writer.size()
    
    msg3 = BasicTypesMessage()
    msg3.small_int = 3
    msg3.medium_int = 300
    msg3.regular_int = 30000
    msg3.large_int = 3000000
    msg3.small_uint = 6
    msg3.medium_uint = 600
    msg3.regular_uint = 60000
    msg3.large_uint = 6000000
    msg3.single_precision = 3.0
    msg3.double_precision = 3.0
    msg3.flag = True
    msg3.device_id = b"DEV3"
    msg3.description = b"Third"
    
    bytes3 = writer.write(msg3)
    
    buffer = bytearray(writer.data())
    total_bytes = writer.size()
    
    # Corrupt second frame's CRC
    buffer[bytes2_end - 1] ^= 0xFF
    
    # Parse all frames
    reader = ProfileStandardReader(buffer=bytes(buffer[:total_bytes]), get_message_info=get_message_info)
    
    result1 = reader.next()
    if not result1.valid:
        return False  # First should be valid
    
    result2 = reader.next()
    return not result2.valid  # Second should be invalid

def test_bulk_profile_corrupted_crc():
    """Test: Bulk profile with corrupted CRC"""
    # Create a valid message
    msg = BasicTypesMessage()
    msg.small_int = 42
    msg.medium_int = 1000
    msg.regular_int = 100000
    msg.large_int = 1000000000
    msg.small_uint = 200
    msg.medium_uint = 50000
    msg.regular_uint = 3000000000
    msg.large_uint = 9000000000000000000
    msg.single_precision = 3.14159
    msg.double_precision = 2.71828
    msg.flag = True
    msg.device_id = b"DEVICE123"
    msg.description = b"Test device"
    
    # Encode message with bulk profile
    writer = ProfileBulkWriter(capacity=1024)
    writer.write(msg)
    buffer = bytearray(writer.data())
    bytes_written = writer.size()
    
    if bytes_written < 4:
        return False
    
    # Corrupt the CRC (last 2 bytes)
    buffer[bytes_written - 1] ^= 0xFF
    buffer[bytes_written - 2] ^= 0xFF
    
    # Try to parse - should fail
    reader = ProfileBulkReader(buffer=bytes(buffer[:bytes_written]), get_message_info=get_message_info)
    result = reader.next()
    
    return not result.valid  # Expect failure

def test_partial_frame_boundary():
    """Test: AccumulatingReader handles a frame fed in two separate add_data chunks"""
    msg = BasicTypesMessage()
    msg.small_int = 42
    msg.medium_int = 1000
    msg.regular_int = 100000
    msg.large_int = 1000000000
    msg.small_uint = 200
    msg.medium_uint = 50000
    msg.regular_uint = 3000000000
    msg.large_uint = 9000000000000000000
    msg.single_precision = 3.14159
    msg.double_precision = 2.71828
    msg.flag = True
    msg.device_id = b"DEVICE123"
    msg.description = b"Test device"
    
    # Encode message
    writer = ProfileStandardWriter(capacity=1024)
    writer.write(msg)
    buffer = bytes(writer.data())
    frame_size = writer.size()
    
    if frame_size < 10:
        return False
    
    mid = frame_size // 2
    
    # Create accumulating reader (buffer mode)
    reader = ProfileStandardAccumulatingReader(get_message_info=get_message_info, buffer_size=1024)
    
    # Feed first half via add_data, then call next() to save partial data to internal buffer
    reader.add_data(buffer[:mid])
    reader.next()  # Should return invalid but save partial data internally
    
    # Feed second half - adds to internal buffer completing the frame
    reader.add_data(buffer[mid:frame_size])
    
    # Call next() once all data is present - should successfully decode the frame
    result = reader.next()
    return result.valid  # Expect success after accumulating both halves


def _make_test_msg():
    """Helper: create a standard test message"""
    msg = BasicTypesMessage()
    msg.small_int = 42
    msg.medium_int = 1000
    msg.regular_int = 100000
    msg.large_int = 1000000000
    msg.small_uint = 200
    msg.medium_uint = 50000
    msg.regular_uint = 3000000000
    msg.large_uint = 9000000000000000000
    msg.single_precision = 3.14159
    msg.double_precision = 2.71828
    msg.flag = True
    msg.device_id = b"DEVICE123"
    msg.description = b"Test device"
    return msg


def test_invalid_msg_id():
    """Test: Parser rejects frame with unknown message ID (CRC fails with wrong magic values).
    ProfileStandard layout: [0x90][0x71][LEN][MSG_ID][PAYLOAD...][CRC1][CRC2]
    Corrupting byte 3 (msg_id) to 0xFF causes get_message_info to return {0,0,0} magic,
    so the CRC check fails.
    """
    msg = _make_test_msg()
    writer = ProfileStandardWriter(capacity=1024)
    writer.write(msg)
    buffer = bytearray(writer.data())
    frame_size = writer.size()

    if frame_size < 5:
        return False

    # Corrupt the msg_id byte (byte 3: [start1][start2][len][msg_id]...)
    # 0xFF is not a known message ID → get_message_info returns {0,0,0} magic → CRC fails
    buffer[3] = 0xFF

    reader = ProfileStandardReader(buffer=bytes(buffer[:frame_size]), get_message_info=get_message_info)
    result = reader.next()
    return not result.valid  # Expect failure: CRC mismatch due to wrong magic values


def test_minimal_profile_truncated_frame():
    """Test: Minimal profile (no CRC) rejects a truncated frame.
    ProfileSensor layout: [0x70][MSG_ID][PAYLOAD...]  (no CRC, no length field)
    Parser uses get_message_info to determine expected payload size; truncated buffer → rejected.
    """
    msg = _make_test_msg()
    writer = ProfileSensorWriter(capacity=1024)
    writer.write(msg)
    buffer = bytes(writer.data())
    frame_size = writer.size()

    if frame_size <= 5:
        return False

    # Provide fewer bytes than the full frame to trigger truncation error
    truncated = frame_size - 5

    reader = ProfileSensorReader(buffer=buffer[:truncated], get_message_info=get_message_info)
    result = reader.next()
    return not result.valid  # Expect failure: buffer too small for expected payload


def test_network_sysid_compid():
    """Test: Network profile validates sys_id/comp_id as part of CRC-protected header.
    ProfileNetwork layout: [0x90][0x78][SEQ][SYS_ID][COMP_ID][LEN_LO][LEN_HI][PKG_ID][MSG_ID][PAYLOAD...][CRC1][CRC2]
    sys_id is at byte 3 (within CRC region); corrupting it causes CRC failure.
    """
    msg = _make_test_msg()
    writer = ProfileNetworkWriter(capacity=1024)
    # Encode with seq=1, sys_id=5, comp_id=10
    writer.write(msg, seq=1, sys_id=5, comp_id=10)
    buffer = bytearray(writer.data())
    frame_size = writer.size()

    if frame_size < 10:
        return False

    # Corrupt sys_id (byte 3: [start1][start2][seq][sys_id]...)
    # sys_id is inside the CRC-protected region so CRC will fail
    buffer[3] ^= 0xFF

    reader = ProfileNetworkReader(buffer=bytes(buffer[:frame_size]), get_message_info=get_message_info)
    result = reader.next()
    return not result.valid  # Expect failure: corrupted sys_id invalidates CRC


def test_diagnostic_crc_failure():
    """Diagnostics: cnt_crc_failures is incremented when a frame's CRC is corrupted."""
    msg = _make_test_msg()
    writer = ProfileStandardWriter(capacity=1024)
    writer.write(msg)
    buffer = bytearray(writer.data())
    frame_size = writer.size()

    # Corrupt CRC (last 2 bytes)
    buffer[frame_size - 1] ^= 0xFF
    buffer[frame_size - 2] ^= 0xFF

    reader = ProfileStandardAccumulatingReader(get_message_info=get_message_info, buffer_size=1024)
    for b in buffer[:frame_size]:
        reader.push_byte(b)

    diag = reader.diagnostics
    return diag.cnt_crc_failures == 1 and diag.cnt_sync_recoveries >= 1


def test_diagnostic_sync_recovery():
    """Diagnostics: cnt_sync_recoveries increments when garbage bytes are fed."""
    reader = ProfileStandardAccumulatingReader(get_message_info=get_message_info, buffer_size=1024)

    # Feed clearly invalid bytes (not start bytes) so the parser stays in
    # LOOKING_FOR_START2 and triggers at least one sync recovery when it
    # sees an invalid second byte after a valid 0x90.
    reader.push_byte(0x90)   # valid start1 for ProfileStandard
    reader.push_byte(0xAB)   # invalid start2 → sync recovery

    diag = reader.diagnostics
    return diag.cnt_sync_recoveries >= 1


def test_diagnostic_len_error():
    """Diagnostics: cnt_len_errors is incremented when the header length field
    doesn't match the expected message struct size.

    ProfileStandard header: [0x90][0x71][LEN][MSG_ID][PAYLOAD...][CRC1][CRC2]
    We build a valid frame and then set LEN to a wrong value while keeping CRC
    consistent so the frame still parses as 'complete' and triggers the length
    mismatch check inside _handle_collecting_header.
    """
    msg = _make_test_msg()
    writer = ProfileStandardWriter(capacity=1024)
    writer.write(msg)
    original = bytes(writer.data()[:writer.size()])
    frame_size = writer.size()

    # Build a tampered frame: change the length byte (index 2) so it doesn't
    # match the actual payload size.  We use a smaller fake length so the frame
    # is still well within the buffer (no overflow).  The CRC will be wrong,
    # but cnt_len_errors is checked BEFORE CRC validation in the header state.
    tampered = bytearray(original)
    real_len = tampered[2]
    tampered[2] = (real_len + 1) & 0xFF  # length mismatch

    reader = ProfileStandardAccumulatingReader(get_message_info=get_message_info, buffer_size=1024)
    for b in tampered[:frame_size]:
        reader.push_byte(b)

    diag = reader.diagnostics
    return diag.cnt_len_errors == 1


def test_diagnostic_seq_gap():
    """Diagnostics: cnt_seq_gaps is incremented when a sequence number is skipped.

    ProfileNetwork carries an 8-bit sequence number.  Sending seq=0 followed by
    seq=5 should be detected as a gap (4 dropped packets).
    """
    msg = _make_test_msg()

    def encode(seq):
        w = ProfileNetworkWriter(capacity=1024)
        w.write(msg, seq=seq, sys_id=1, comp_id=1)
        return bytes(w.data()[:w.size()])

    frame0 = encode(0)
    frame5 = encode(5)   # skips seq 1-4 → gap

    reader = ProfileNetworkAccumulatingReader(get_message_info=get_message_info, buffer_size=1024)
    for b in frame0:
        reader.push_byte(b)
    for b in frame5:
        reader.push_byte(b)

    diag = reader.diagnostics
    return diag.cnt_seq_gaps == 1 and diag.cnt_crc_failures == 0


def test_diagnostic_reset():
    """Diagnostics: reset_diagnostics() clears all counters."""
    reader = ProfileStandardAccumulatingReader(get_message_info=get_message_info, buffer_size=1024)

    # Trigger a sync recovery
    reader.push_byte(0x90)
    reader.push_byte(0xAB)

    assert reader.diagnostics.cnt_sync_recoveries >= 1, "Expected sync recovery to be counted"

    reader.reset_diagnostics()
    diag = reader.diagnostics
    return (
        diag.cnt_crc_failures == 0
        and diag.cnt_sync_recoveries == 0
        and diag.cnt_len_errors == 0
        and diag.cnt_seq_gaps == 0
    )


def test_status_waiting_for_start():
    """FrameMsgStatus: push_byte returns WAITING_FOR_START when no start byte seen yet."""
    reader = ProfileStandardAccumulatingReader(get_message_info=get_message_info, buffer_size=1024)
    # 0x42 is not the start byte (0x90); parser stays in waiting state
    result = reader.push_byte(0x42)
    return result.status == FrameMsgStatus.WAITING_FOR_START


def test_status_collecting():
    """FrameMsgStatus: push_byte returns COLLECTING once a valid start byte is in progress."""
    reader = ProfileStandardAccumulatingReader(get_message_info=get_message_info, buffer_size=1024)
    # 0x90 is startByte1 — move to LookingForStart2
    result = reader.push_byte(0x90)
    return result.status == FrameMsgStatus.COLLECTING


def test_status_crc_failure():
    """FrameMsgStatus: push_byte returns CRC_FAILURE when a complete frame has bad CRC."""
    writer = ProfileStandardWriter(capacity=1024)
    msg = BasicTypesMessage()
    msg.uint8_field = 99
    writer.write(msg)
    buffer = bytearray(writer.data())
    frame_size = writer.size()

    # Corrupt the last byte (CRC)
    buffer[frame_size - 1] ^= 0xFF

    reader = ProfileStandardAccumulatingReader(get_message_info=get_message_info, buffer_size=1024)
    result = None
    for b in buffer[:frame_size]:
        result = reader.push_byte(b)
    return result is not None and result.status == FrameMsgStatus.CRC_FAILURE


def test_status_sync_recovery():
    """FrameMsgStatus: push_byte returns SYNC_RECOVERY when parser is forced to resync."""
    reader = ProfileStandardAccumulatingReader(get_message_info=get_message_info, buffer_size=1024)
    # Start a frame then send a byte that forces resync at LookingForStart2
    reader.push_byte(0x90)  # valid startByte1
    # 0x42 is neither startByte2 (0xAB) nor startByte1 (0x90) — triggers resync
    result = reader.push_byte(0x42)
    return result.status == FrameMsgStatus.SYNC_RECOVERY


def main():
    print("\n========================================")
    print("NEGATIVE TESTS - Python Parser")
    print("========================================\n")
    
    # Define test matrix
    tests = [
        ("Bulk profile: Corrupted CRC", test_bulk_profile_corrupted_crc),
        ("Corrupted CRC detection", test_corrupted_crc),
        ("Corrupted length field detection", test_corrupted_length),
        ("Diagnostics: CRC failure counter", test_diagnostic_crc_failure),
        ("Diagnostics: Length error counter", test_diagnostic_len_error),
        ("Diagnostics: Reset diagnostics", test_diagnostic_reset),
        ("Diagnostics: Sequence gap counter", test_diagnostic_seq_gap),
        ("Diagnostics: Sync recovery counter", test_diagnostic_sync_recovery),
        ("Invalid message ID rejection", test_invalid_msg_id),
        ("Invalid start bytes detection", test_invalid_start_bytes),
        ("Minimal profile: Truncated frame", test_minimal_profile_truncated_frame),
        ("Multiple frames: Corrupted middle frame", test_multiple_corrupted_frames),
        ("Network profile: SysId/CompId corruption", test_network_sysid_compid),
        ("Partial frame across buffer boundary", test_partial_frame_boundary),
        ("Status: COLLECTING during frame reception", test_status_collecting),
        ("Status: CRC_FAILURE on bad checksum", test_status_crc_failure),
        ("Status: SYNC_RECOVERY on forced resync", test_status_sync_recovery),
        ("Status: WAITING_FOR_START before first byte", test_status_waiting_for_start),
        ("Streaming: Corrupted CRC detection", test_streaming_corrupted_crc),
        ("Streaming: Garbage data handling", test_streaming_garbage),
        ("Truncated frame detection", test_truncated_frame),
        ("Zero-length buffer handling", test_zero_length_buffer),
    ]
    
    global tests_run, tests_passed, tests_failed
    
    print("Test Results Matrix:\n")
    print(f"{'Test Name':<50} {'Result':>6}")
    print(f"{'='*50} {'='*6}")
    
    # Run all tests from the matrix
    for name, test_func in tests:
        tests_run += 1
        passed = test_func()
        
        result = "PASS" if passed else "FAIL"
        print(f"{name:<50} {result:>6}")
        
        if passed:
            tests_passed += 1
        else:
            tests_failed += 1
    
    print("\n========================================")
    print(f"Summary: {tests_passed}/{tests_run} tests passed")
    print("========================================\n")
    
    return 1 if tests_failed > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
