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

from struct_frame.generated.serialization_test import BasicTypesMessage, get_message_info
from struct_frame.frame_profiles import (
    FrameEncoderStandard, FrameParserStandard,
    AccumulatingReaderStandard
)

# Test result tracking
tests_run = 0
tests_passed = 0
tests_failed = 0

def test_result(name, passed):
    """Record and print test result"""
    global tests_run, tests_passed, tests_failed
    tests_run += 1
    if passed:
        print(f"  [TEST] {name}... PASS")
        tests_passed += 1
    else:
        print(f"  [TEST] {name}... FAIL")
        tests_failed += 1

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
    msg.device_id = "DEVICE123"
    msg.description = "Test device"
    
    # Encode message
    buffer = bytearray(1024)
    encoder = FrameEncoderStandard(buffer)
    bytes_written = msg.encode(encoder)
    
    if bytes_written < 4:
        return False
    
    # Corrupt the CRC (last 2 bytes)
    buffer[bytes_written - 1] ^= 0xFF
    buffer[bytes_written - 2] ^= 0xFF
    
    # Try to parse - should fail
    parser = FrameParserStandard(bytes(buffer[:bytes_written]))
    result = parser.next()
    
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
    msg.device_id = "DEVICE123"
    msg.description = "Test device"
    
    # Encode message
    buffer = bytearray(1024)
    encoder = FrameEncoderStandard(buffer)
    bytes_written = msg.encode(encoder)
    
    if bytes_written < 10:
        return False
    
    # Truncate the frame
    truncated_size = bytes_written - 5
    
    # Try to parse - should fail
    parser = FrameParserStandard(bytes(buffer[:truncated_size]))
    result = parser.next()
    
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
    msg.device_id = "DEVICE123"
    msg.description = "Test device"
    
    # Encode message
    buffer = bytearray(1024)
    encoder = FrameEncoderStandard(buffer)
    bytes_written = msg.encode(encoder)
    
    if bytes_written < 2:
        return False
    
    # Corrupt start bytes
    buffer[0] = 0xDE
    buffer[1] = 0xAD
    
    # Try to parse - should fail
    parser = FrameParserStandard(bytes(buffer[:bytes_written]))
    result = parser.next()
    
    return not result.valid  # Expect failure

def test_zero_length_buffer():
    """Test: Parser handles zero-length buffer"""
    parser = FrameParserStandard(b'')
    result = parser.next()
    
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
    msg.device_id = "DEVICE123"
    msg.description = "Test device"
    
    # Encode message
    buffer = bytearray(1024)
    encoder = FrameEncoderStandard(buffer)
    bytes_written = msg.encode(encoder)
    
    if bytes_written < 4:
        return False
    
    # Corrupt length field (byte 2)
    buffer[2] = 0xFF
    
    # Try to parse - should fail
    parser = FrameParserStandard(bytes(buffer[:bytes_written]))
    result = parser.next()
    
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
    msg.device_id = "DEVICE123"
    msg.description = "Test device"
    
    # Encode message
    buffer = bytearray(1024)
    encoder = FrameEncoderStandard(buffer)
    bytes_written = msg.encode(encoder)
    
    if bytes_written < 4:
        return False
    
    # Corrupt CRC
    buffer[bytes_written - 1] ^= 0xFF
    
    # Try streaming parse
    reader = AccumulatingReaderStandard(get_message_info)
    
    # Feed byte by byte
    for i in range(bytes_written):
        reader.push_byte(buffer[i])
    
    result = reader.next()
    return not result.valid  # Expect failure

def test_streaming_garbage():
    """Test: Streaming parser handles garbage data"""
    reader = AccumulatingReaderStandard(get_message_info)
    
    # Feed garbage bytes
    garbage = bytes([0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56, 0x78, 0x9A])
    
    for byte in garbage:
        reader.push_byte(byte)
    
    result = reader.next()
    return not result.valid  # Expect no valid frame

def test_multiple_corrupted_frames():
    """Test: Multiple frames with corrupted middle frame"""
    # Create buffer with 3 messages
    buffer = bytearray(4096)
    encoder = FrameEncoderStandard(buffer)
    
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
    msg1.device_id = "DEV1"
    msg1.description = "First"
    
    bytes1 = msg1.encode(encoder)
    
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
    msg2.device_id = "DEV2"
    msg2.description = "Second"
    
    encoder.offset = bytes1
    bytes2_start = bytes1
    bytes2 = msg2.encode(encoder)
    bytes2_end = encoder.offset
    
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
    msg3.device_id = "DEV3"
    msg3.description = "Third"
    
    bytes3 = msg3.encode(encoder)
    total_bytes = encoder.offset
    
    # Corrupt second frame's CRC
    buffer[bytes2_end - 1] ^= 0xFF
    
    # Parse all frames
    parser = FrameParserStandard(bytes(buffer[:total_bytes]))
    
    result1 = parser.next()
    if not result1.valid:
        return False  # First should be valid
    
    result2 = parser.next()
    return not result2.valid  # Second should be invalid

def main():
    print("\n========================================")
    print("NEGATIVE TESTS - Python Parser")
    print("========================================\n")
    
    print("Testing error handling for invalid frames:\n")
    
    test_result("Corrupted CRC detection", test_corrupted_crc())
    test_result("Truncated frame detection", test_truncated_frame())
    test_result("Invalid start bytes detection", test_invalid_start_bytes())
    test_result("Zero-length buffer handling", test_zero_length_buffer())
    test_result("Corrupted length field detection", test_corrupted_length())
    test_result("Streaming: Corrupted CRC detection", test_streaming_corrupted_crc())
    test_result("Streaming: Garbage data handling", test_streaming_garbage())
    test_result("Multiple frames: Corrupted middle frame", test_multiple_corrupted_frames())
    
    print("\n========================================")
    print("RESULTS")
    print("========================================")
    print(f"Tests run:    {tests_run}")
    print(f"Tests passed: {tests_passed}")
    print(f"Tests failed: {tests_failed}")
    print("========================================\n")
    
    return 1 if tests_failed > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
