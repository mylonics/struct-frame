#!/usr/bin/env python3
"""
Test minimal frame parsing - validates parsing of frames without length field
"""

import sys
import os

# Add generated code path to sys.path
generated_path = os.path.join(os.path.dirname(__file__), '..', 'generated', 'py')
sys.path.insert(0, generated_path)

try:
    from parser import Parser, HeaderType, PayloadType
except ImportError as e:
    print(f"[TEST START]")
    print(f"Failed to import parser: {e}")
    print(f"Make sure to generate the frame parsers first.")
    print(f"[TEST END]")
    sys.exit(1)


# Define message sizes for testing
MESSAGE_SIZES = {
    1: 10,
    2: 20,
    3: 5,
    4: 100,
}

def get_msg_length(msg_id: int) -> int:
    """Callback for minimal frame parsing"""
    return MESSAGE_SIZES.get(msg_id, 0)


def test_basic_minimal():
    """Test BasicMinimal frame encoding and parsing"""
    print("Testing BasicMinimal frame...")
    
    parser = Parser(
        get_msg_length=get_msg_length,
        enabled_headers=[HeaderType.BASIC],
        enabled_payloads=[PayloadType.MINIMAL]
    )
    
    msg_id = 1
    msg_data = bytes(range(10))
    
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
    
    msg_id = 3
    msg_data = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE])
    
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
    
    msg_id = 3
    msg_data = bytes([0x11, 0x22, 0x33, 0x44, 0x55])
    
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
    
    # Create multiple frames
    frames = [
        parser.encode(1, bytes(range(10)), HeaderType.BASIC, PayloadType.MINIMAL),
        parser.encode(3, bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE]), HeaderType.TINY, PayloadType.MINIMAL),
        parser.encode(2, bytes(range(20)), HeaderType.BASIC, PayloadType.MINIMAL),
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
        (HeaderType.BASIC, 1, 10),
        (HeaderType.TINY, 3, 5),
        (HeaderType.BASIC, 2, 20),
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
    
    # Create frame manually: [0x70 = Tiny+Minimal] [0x03 = msg_id] [data]
    frame = bytes([0x70, 0x03, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE])
    
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
    """Test minimal frames with different message sizes"""
    print("Testing minimal frames with variable message sizes...")
    
    parser = Parser(
        get_msg_length=get_msg_length,
        enabled_headers=[HeaderType.BASIC],
        enabled_payloads=[PayloadType.MINIMAL]
    )
    
    test_cases = [
        (1, 10),   # 10 bytes
        (2, 20),   # 20 bytes
        (3, 5),    # 5 bytes
        (4, 100),  # 100 bytes
    ]
    
    for msg_id, expected_len in test_cases:
        msg_data = bytes(range(expected_len))
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
