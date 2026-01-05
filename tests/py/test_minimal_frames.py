#!/usr/bin/env python3
"""
Test minimal frame parsing - validates parsing of frames without length field

This test uses the auto-generated get_msg_length function from the proto definitions.
"""

import sys
import os

# Add generated code path to sys.path
generated_path = os.path.join(os.path.dirname(__file__), '..', 'generated', 'py')
sys.path.insert(0, generated_path)

try:
    from parser import Parser, HeaderType, PayloadType
    # Import the auto-generated get_msg_length function
    from serialization_test_sf import get_msg_length, serialization_test_definitions
except ImportError as e:
    print(f"[TEST START]")
    print(f"Failed to import parser or generated messages: {e}")
    print(f"Make sure to generate the frame parsers first.")
    print(f"[TEST END]")
    sys.exit(1)


# Use actual message IDs and sizes from the generated proto
# Message IDs: 201 (BasicTypesMessage), 203 (ComprehensiveArrayMessage), 204 (SerializationTestMessage)
# The get_msg_length function is auto-generated and knows the sizes of these messages


def test_basic_minimal():
    """Test BasicMinimal frame encoding and parsing"""
    print("Testing BasicMinimal frame...")
    
    parser = Parser(
        get_msg_length=get_msg_length,
        enabled_headers=[HeaderType.BASIC],
        enabled_payloads=[PayloadType.MINIMAL]
    )
    
    # Use real message ID from proto: 204 (SerializationTestMessage)
    msg_id = 204
    msg_size = get_msg_length(msg_id)  # Auto-generated function knows the size
    msg_data = bytes(range(min(msg_size, 256)))[:msg_size]  # Create data matching the message size
    
    # Encode
    frame = parser.encode(msg_id, msg_data, HeaderType.BASIC, PayloadType.MINIMAL)
    
    # Parse
    parser.reset()
    result = None
    for byte in frame:
        result = parser.parse_byte(byte)
        if result.valid:
            break
    
    if not result or not result.valid:
        print(f"  ERROR: Failed to parse BasicMinimal frame")
        return False
    
    if result.header_type != HeaderType.BASIC:
        print(f"  ERROR: Wrong header type: {result.header_type}")
        return False
    
    if result.payload_type != PayloadType.MINIMAL:
        print(f"  ERROR: Wrong payload type: {result.payload_type}")
        return False
    
    if result.msg_id != msg_id:
        print(f"  ERROR: Wrong msg_id: {result.msg_id}")
        return False
    
    if result.msg_data != msg_data:
        print(f"  ERROR: Data mismatch")
        return False
    
    print(f"  SUCCESS: BasicMinimal works correctly")
    return True


def test_tiny_minimal():
    """Test TinyMinimal frame encoding and parsing"""
    print("Testing TinyMinimal frame...")
    
    parser = Parser(
        get_msg_length=get_msg_length,
        enabled_headers=[HeaderType.TINY],
        enabled_payloads=[PayloadType.MINIMAL]
    )
    
    # Use real message ID from proto: 203 (ComprehensiveArrayMessage)
    msg_id = 203
    msg_size = get_msg_length(msg_id)
    msg_data = bytes(range(min(msg_size, 256)))[:msg_size]
    
    # Encode
    frame = parser.encode(msg_id, msg_data, HeaderType.TINY, PayloadType.MINIMAL)
    
    # Parse
    parser.reset()
    result = None
    for byte in frame:
        result = parser.parse_byte(byte)
        if result.valid:
            break
    
    if not result or not result.valid:
        print(f"  ERROR: Failed to parse TinyMinimal frame")
        return False
    
    if result.header_type != HeaderType.TINY:
        print(f"  ERROR: Wrong header type: {result.header_type}")
        return False
    
    if result.payload_type != PayloadType.MINIMAL:
        print(f"  ERROR: Wrong payload type: {result.payload_type}")
        return False
    
    if result.msg_id != msg_id:
        print(f"  ERROR: Wrong msg_id: {result.msg_id}")
        return False
    
    if result.msg_data != msg_data:
        print(f"  ERROR: Data mismatch")
        return False
    
    print(f"  SUCCESS: TinyMinimal works correctly")
    return True


def test_none_minimal():
    """Test NoneMinimal frame encoding and parsing"""
    print("Testing NoneMinimal frame...")
    
    parser = Parser(
        get_msg_length=get_msg_length,
        enabled_headers=[HeaderType.NONE],
        enabled_payloads=[PayloadType.MINIMAL],
        default_payload_type=PayloadType.MINIMAL
    )
    
    # Use real message ID from proto: 201 (BasicTypesMessage)
    msg_id = 201
    msg_size = get_msg_length(msg_id)
    msg_data = bytes(range(min(msg_size, 256)))[:msg_size]
    
    # Encode
    frame = parser.encode(msg_id, msg_data, HeaderType.NONE, PayloadType.MINIMAL)
    
    # Parse
    parser.reset()
    result = None
    for byte in frame:
        result = parser.parse_byte(byte)
        if result.valid:
            break
    
    if not result or not result.valid:
        print(f"  ERROR: Failed to parse NoneMinimal frame")
        return False
    
    if result.header_type != HeaderType.NONE:
        print(f"  ERROR: Wrong header type: {result.header_type}")
        return False
    
    if result.payload_type != PayloadType.MINIMAL:
        print(f"  ERROR: Wrong payload type: {result.payload_type}")
        return False
    
    if result.msg_id != msg_id:
        print(f"  ERROR: Wrong msg_id: {result.msg_id}")
        return False
    
    if result.msg_data != msg_data:
        print(f"  ERROR: Data mismatch")
        return False
    
    print(f"  SUCCESS: NoneMinimal works correctly")
    return True


def test_mixed_minimal_stream():
    """Test parsing stream with multiple minimal frame types"""
    print("Testing mixed minimal frame stream...")
    
    parser = Parser(
        get_msg_length=get_msg_length,
        enabled_headers=[HeaderType.BASIC, HeaderType.TINY],
        enabled_payloads=[PayloadType.MINIMAL]
    )
    
    # Create multiple frames using real message IDs from proto
    msg_id_1 = 204  # SerializationTestMessage
    size_1 = get_msg_length(msg_id_1)
    
    msg_id_2 = 203  # ComprehensiveArrayMessage
    size_2 = get_msg_length(msg_id_2)
    
    msg_id_3 = 201  # BasicTypesMessage
    size_3 = get_msg_length(msg_id_3)
    
    frames = [
        parser.encode(msg_id_1, bytes(range(min(size_1, 256)))[:size_1], HeaderType.BASIC, PayloadType.MINIMAL),
        parser.encode(msg_id_2, bytes(range(min(size_2, 256)))[:size_2], HeaderType.TINY, PayloadType.MINIMAL),
        parser.encode(msg_id_3, bytes(range(min(size_3, 256)))[:size_3], HeaderType.BASIC, PayloadType.MINIMAL),
    ]
    
    stream = b''.join(frames)
    
    # Parse stream
    parser.reset()
    results = []
    for byte in stream:
        result = parser.parse_byte(byte)
        if result.valid:
            results.append(result)
    
    if len(results) != len(frames):
        print(f"  ERROR: Expected {len(frames)} frames, got {len(results)}")
        return False
    
    # Verify each result
    expected = [
        (HeaderType.BASIC, msg_id_1, size_1),
        (HeaderType.TINY, msg_id_2, size_2),
        (HeaderType.BASIC, msg_id_3, size_3),
    ]
    
    for i, (result, (exp_header, exp_id, exp_len)) in enumerate(zip(results, expected)):
        if result.header_type != exp_header:
            print(f"  ERROR: Frame {i}: wrong header type")
            return False
        if result.msg_id != exp_id:
            print(f"  ERROR: Frame {i}: wrong msg_id")
            return False
        if result.msg_len != exp_len:
            print(f"  ERROR: Frame {i}: wrong length")
            return False
    
    print(f"  SUCCESS: Mixed stream parsed correctly")
    return True


def test_callback_required():
    """Test that minimal frames fail without callback"""
    print("Testing minimal frame without callback (should fail gracefully)...")
    
    # Parser without callback
    parser = Parser(
        # No callback!
        enabled_headers=[HeaderType.TINY],
        enabled_payloads=[PayloadType.MINIMAL]
    )
    
    # Use a real message ID from proto
    msg_id = 204
    # Create frame manually: [0x70 = Tiny+Minimal] [msg_id] [data]
    msg_data = bytes(range(20))
    frame = bytes([0x70, msg_id]) + msg_data
    
    # Try to parse
    result = None
    for byte in frame:
        result = parser.parse_byte(byte)
        if result.valid:
            break
    
    if result and result.valid:
        print(f"  ERROR: Frame should not parse without callback")
        return False
    
    print(f"  SUCCESS: Parser correctly rejects minimal frame without callback")
    return True


def test_variable_sizes():
    """Test minimal frames with different message sizes from proto"""
    print("Testing minimal frames with variable message sizes...")
    
    parser = Parser(
        get_msg_length=get_msg_length,
        enabled_headers=[HeaderType.BASIC],
        enabled_payloads=[PayloadType.MINIMAL]
    )
    
    # Use real message IDs from proto with different sizes
    test_cases = [
        (201, get_msg_length(201)),  # BasicTypesMessage
        (203, get_msg_length(203)),  # ComprehensiveArrayMessage
        (204, get_msg_length(204)),  # SerializationTestMessage
    ]
    
    for msg_id, expected_len in test_cases:
        msg_data = bytes(range(min(expected_len, 256)))[:expected_len]
        frame = parser.encode(msg_id, msg_data, HeaderType.BASIC, PayloadType.MINIMAL)
        
        parser.reset()
        result = None
        for byte in frame:
            result = parser.parse_byte(byte)
            if result.valid:
                break
        
        if not result or not result.valid:
            print(f"  ERROR: Failed for msg_id={msg_id}, len={expected_len}")
            return False
        
        if result.msg_len != expected_len:
            print(f"  ERROR: msg_id={msg_id}: expected len={expected_len}, got {result.msg_len}")
            return False
    
    print(f"  SUCCESS: All message sizes handled correctly")
    return True


def main():
    print("[TEST START]")
    print("Minimal Frame Parsing Test Suite")
    print("=" * 60)
    
    tests = [
        test_basic_minimal,
        test_tiny_minimal,
        test_none_minimal,
        test_mixed_minimal_stream,
        test_callback_required,
        test_variable_sizes,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("[TEST END]")
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
