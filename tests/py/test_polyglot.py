#!/usr/bin/env python3
"""
Test polyglot parser - tests the ability to parse multiple frame types in same stream
"""

import sys
import os

# Add generated code path to sys.path
generated_path = os.path.join(os.path.dirname(__file__), '..', 'generated', 'py')
sys.path.insert(0, generated_path)

try:
    import polyglot_parser
    import basic_default
    import tiny_default
    import basic_minimal
    import tiny_minimal
    
    PolyglotParser = polyglot_parser.PolyglotParser
    PolyglotParserResult = polyglot_parser.PolyglotParserResult
    BasicDefault = basic_default.BasicDefault
    TinyDefault = tiny_default.TinyDefault
    BasicMinimal = basic_minimal.BasicMinimal
    TinyMinimal = tiny_minimal.TinyMinimal
except ImportError as e:
    print(f"[TEST START]")
    print(f"Failed to import frame parsers: {e}")
    print(f"Make sure to generate the frame parsers first.")
    print(f"[TEST END]")
    sys.exit(1)


def test_polyglot_basic_frame():
    """Test that polyglot parser can detect and parse a Basic frame"""
    print("Testing polyglot parser with Basic frame (0x90 0x71)...")
    
    # Create a BasicDefault parser and encode a test message
    basic_parser = BasicDefault()
    test_msg_id = 42
    test_data = b"Hello Basic!"
    encoded = basic_parser.encode(test_msg_id, test_data)
    
    print(f"  Encoded Basic frame: {' '.join(f'{b:02X}' for b in encoded)}")
    
    # Parse with polyglot parser
    polyglot = PolyglotParser()
    result = None
    for byte in encoded:
        result = polyglot.parse_byte(byte)
        if result.valid:
            break
    
    if not result or not result.valid:
        print(f"  ERROR: Failed to parse Basic frame")
        return False
    
    if result.frame_type != "basic":
        print(f"  ERROR: Expected frame_type='basic', got '{result.frame_type}'")
        return False
    
    if result.payload_type != 1:  # Default payload type
        print(f"  ERROR: Expected payload_type=1, got {result.payload_type}")
        return False
    
    if result.msg_id != test_msg_id:
        print(f"  ERROR: Expected msg_id={test_msg_id}, got {result.msg_id}")
        return False
    
    if result.msg_data != test_data:
        print(f"  ERROR: Data mismatch")
        return False
    
    print(f"  SUCCESS: Detected {result.format_name}, msg_id={result.msg_id}")
    return True


def test_polyglot_tiny_frame():
    """Test that polyglot parser can detect and parse a Tiny frame"""
    print("Testing polyglot parser with Tiny frame (0x71)...")
    
    # Create a TinyDefault parser and encode a test message
    tiny_parser = TinyDefault()
    test_msg_id = 99
    test_data = b"Hello Tiny!"
    encoded = tiny_parser.encode(test_msg_id, test_data)
    
    print(f"  Encoded Tiny frame: {' '.join(f'{b:02X}' for b in encoded)}")
    
    # Parse with polyglot parser
    polyglot = PolyglotParser()
    result = None
    for byte in encoded:
        result = polyglot.parse_byte(byte)
        if result.valid:
            break
    
    if not result or not result.valid:
        print(f"  ERROR: Failed to parse Tiny frame")
        return False
    
    if result.frame_type != "tiny":
        print(f"  ERROR: Expected frame_type='tiny', got '{result.frame_type}'")
        return False
    
    if result.payload_type != 1:  # Default payload type
        print(f"  ERROR: Expected payload_type=1, got {result.payload_type}")
        return False
    
    if result.msg_id != test_msg_id:
        print(f"  ERROR: Expected msg_id={test_msg_id}, got {result.msg_id}")
        return False
    
    if result.msg_data != test_data:
        print(f"  ERROR: Data mismatch")
        return False
    
    print(f"  SUCCESS: Detected {result.format_name}, msg_id={result.msg_id}")
    return True


def test_polyglot_mixed_stream():
    """Test that polyglot parser can handle mixed frame types in same stream"""
    print("Testing polyglot parser with mixed frame stream...")
    
    # Create messages with different frame types
    basic_parser = BasicDefault()
    tiny_parser = TinyDefault()
    
    # Encode multiple messages
    basic_msg1 = basic_parser.encode(10, b"Basic1")
    tiny_msg1 = tiny_parser.encode(20, b"Tiny1")
    basic_msg2 = basic_parser.encode(30, b"Basic2")
    tiny_msg2 = tiny_parser.encode(40, b"Tiny2")
    
    # Concatenate into a single stream
    stream = basic_msg1 + tiny_msg1 + basic_msg2 + tiny_msg2
    
    print(f"  Stream length: {len(stream)} bytes")
    
    # Parse the stream
    polyglot = PolyglotParser()
    results = []
    for byte in stream:
        result = polyglot.parse_byte(byte)
        if result.valid:
            results.append(result)
    
    if len(results) != 4:
        print(f"  ERROR: Expected 4 messages, got {len(results)}")
        return False
    
    # Verify frame types
    expected = [
        ("basic", 1, 10),
        ("tiny", 1, 20),
        ("basic", 1, 30),
        ("tiny", 1, 40),
    ]
    
    for i, (result, expected_vals) in enumerate(zip(results, expected)):
        exp_type, exp_payload, exp_id = expected_vals
        if result.frame_type != exp_type:
            print(f"  ERROR: Message {i}: Expected frame_type='{exp_type}', got '{result.frame_type}'")
            return False
        if result.payload_type != exp_payload:
            print(f"  ERROR: Message {i}: Expected payload_type={exp_payload}, got {result.payload_type}")
            return False
        if result.msg_id != exp_id:
            print(f"  ERROR: Message {i}: Expected msg_id={exp_id}, got {result.msg_id}")
            return False
    
    print(f"  SUCCESS: Parsed {len(results)} messages correctly")
    return True


def test_polyglot_minimal_frames():
    """Test polyglot parser with minimal frame types (no CRC)"""
    print("Testing polyglot parser with minimal frames...")
    
    # These frames have no CRC, so they're more challenging
    basic_minimal = BasicMinimal()
    tiny_minimal = TinyMinimal()
    
    # Encode messages
    basic_msg = basic_minimal.encode(15, b"BMin")
    tiny_msg = tiny_minimal.encode(25, b"TMin")
    
    # Parse with polyglot
    polyglot = PolyglotParser()
    
    # Parse basic minimal
    result = None
    for byte in basic_msg:
        result = polyglot.parse_byte(byte)
        if result.valid:
            break
    
    if not result or not result.valid:
        print(f"  ERROR: Failed to parse BasicMinimal frame")
        return False
    
    if result.frame_type != "basic" or result.payload_type != 0:
        print(f"  ERROR: BasicMinimal not detected correctly")
        return False
    
    # Reset and parse tiny minimal
    polyglot.reset()
    result = None
    for byte in tiny_msg:
        result = polyglot.parse_byte(byte)
        if result.valid:
            break
    
    if not result or not result.valid:
        print(f"  ERROR: Failed to parse TinyMinimal frame")
        return False
    
    if result.frame_type != "tiny" or result.payload_type != 0:
        print(f"  ERROR: TinyMinimal not detected correctly")
        return False
    
    print(f"  SUCCESS: Parsed minimal frames correctly")
    return True


def main():
    print("[TEST START]")
    print("Polyglot Parser Test Suite")
    print("=" * 60)
    
    tests = [
        test_polyglot_basic_frame,
        test_polyglot_tiny_frame,
        test_polyglot_mixed_stream,
        test_polyglot_minimal_frames,
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
