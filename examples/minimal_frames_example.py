#!/usr/bin/env python3
"""
Minimal Frame Parsing Example - Python

This example demonstrates how to use minimal frames (no length field, no CRC)
with the struct-frame parser. 

**Important**: Struct-frame automatically generates a `get_msg_length` function
based on your message definitions. You can import and use it directly!

Example:
    from my_messages_sf import get_msg_length
    parser = Parser(get_msg_length=get_msg_length, ...)

For this example, we define message sizes manually for demonstration purposes.

Minimal frames are ideal for:
- Fixed-size messages
- Bandwidth-constrained links (LoRa, radio, RF)
- Trusted communication (SPI, I2C, shared memory)
- Low-power applications
"""

import sys
import os

# Add generated code path (adjust as needed for your setup)
# Expected structure: examples/generated/parser.py and related modules
# In production, generate the parser in your project and adjust this path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'generated'))

from parser import Parser, HeaderType, PayloadType

# Define message sizes for your protocol
# NOTE: In production, import the auto-generated get_msg_length function instead:
#   from my_messages_sf import get_msg_length
# The generator creates this function automatically based on your .proto file.
MESSAGE_SIZES = {
    1: 10,  # Status message - 10 bytes
    2: 20,  # Command message - 20 bytes
    3: 5,   # Sensor reading - 5 bytes
    4: 100, # Data payload - 100 bytes
}

def get_msg_length(msg_id: int) -> int:
    """
    Callback function that returns the expected message length for each msg_id.
    
    This is REQUIRED for minimal frames since they don't include a length field.
    Without this callback, the parser cannot determine message boundaries.
    
    NOTE: Struct-frame generates this function automatically! In production,
    import it from your generated messages file instead of defining it manually.
    
    Args:
        msg_id: Message ID from the frame
        
    Returns:
        Expected message length in bytes, or 0 if unknown
    """
    return MESSAGE_SIZES.get(msg_id, 0)


def example_basic_minimal():
    """Example: BasicMinimal frame format"""
    print("=" * 70)
    print("Example 1: BasicMinimal Frame (0x90 0x70)")
    print("=" * 70)
    
    # Create parser with callback for minimal frames
    parser = Parser(
        get_msg_length=get_msg_length,
        enabled_headers=[HeaderType.BASIC],
        enabled_payloads=[PayloadType.MINIMAL]
    )
    
    # Encode a message
    msg_id = 1
    msg_data = bytes([i for i in range(10)])  # 10 bytes as expected for msg_id=1
    frame = parser.encode(
        msg_id=msg_id,
        msg=msg_data,
        header_type=HeaderType.BASIC,
        payload_type=PayloadType.MINIMAL
    )
    
    print(f"Encoded BasicMinimal frame:")
    print(f"  Frame bytes: {' '.join(f'{b:02X}' for b in frame)}")
    print(f"  Frame structure:")
    print(f"    [0x90] - Basic frame marker")
    print(f"    [0x70] - Minimal payload type (0x70 + 0)")
    print(f"    [0x{msg_id:02X}] - Message ID")
    print(f"    [{' '.join(f'{b:02X}' for b in msg_data)}] - Payload (10 bytes)")
    
    # Parse it back
    print(f"\nParsing the frame byte-by-byte:")
    parser.reset()
    result = None
    for i, byte in enumerate(frame):
        result = parser.parse_byte(byte)
        if result.valid:
            print(f"  ✓ Complete frame parsed after {i+1} bytes")
            break
    
    if result and result.valid:
        print(f"\nParsed result:")
        print(f"  Header type: {result.header_type}")
        print(f"  Payload type: {result.payload_type}")
        print(f"  Message ID: {result.msg_id}")
        print(f"  Message length: {result.msg_len} bytes")
        print(f"  Message data: {' '.join(f'{b:02X}' for b in result.msg_data)}")
        print(f"  ✓ Data matches: {result.msg_data == msg_data}")
    print()


def example_tiny_minimal():
    """Example: TinyMinimal frame format"""
    print("=" * 70)
    print("Example 2: TinyMinimal Frame (0x70)")
    print("=" * 70)
    
    # Create parser with callback
    parser = Parser(
        get_msg_length=get_msg_length,
        enabled_headers=[HeaderType.TINY],
        enabled_payloads=[PayloadType.MINIMAL]
    )
    
    # Encode a sensor reading (msg_id=3, 5 bytes)
    msg_id = 3
    msg_data = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE])
    frame = parser.encode(
        msg_id=msg_id,
        msg=msg_data,
        header_type=HeaderType.TINY,
        payload_type=PayloadType.MINIMAL
    )
    
    print(f"Encoded TinyMinimal frame:")
    print(f"  Frame bytes: {' '.join(f'{b:02X}' for b in frame)}")
    print(f"  Frame structure:")
    print(f"    [0x70] - Tiny+Minimal marker (0x70 = 0x70+0)")
    print(f"    [0x{msg_id:02X}] - Message ID")
    print(f"    [{' '.join(f'{b:02X}' for b in msg_data)}] - Payload (5 bytes)")
    print(f"  Total overhead: 2 bytes (just start byte + msg_id)")
    
    # Parse it back
    parser.reset()
    result = None
    for byte in frame:
        result = parser.parse_byte(byte)
        if result.valid:
            break
    
    if result and result.valid:
        print(f"\nParsed result:")
        print(f"  ✓ Message ID: {result.msg_id}")
        print(f"  ✓ Message length: {result.msg_len} bytes")
        print(f"  ✓ Data matches: {result.msg_data == msg_data}")
    print()


def example_none_minimal():
    """Example: NoneMinimal frame format"""
    print("=" * 70)
    print("Example 3: NoneMinimal Frame (no start bytes)")
    print("=" * 70)
    
    # Create parser with callback, enable NONE header
    parser = Parser(
        get_msg_length=get_msg_length,
        enabled_headers=[HeaderType.NONE],
        enabled_payloads=[PayloadType.MINIMAL],
        default_payload_type=PayloadType.MINIMAL
    )
    
    # Encode a sensor reading (msg_id=3, 5 bytes)
    msg_id = 3
    msg_data = bytes([0x11, 0x22, 0x33, 0x44, 0x55])
    frame = parser.encode(
        msg_id=msg_id,
        msg=msg_data,
        header_type=HeaderType.NONE,
        payload_type=PayloadType.MINIMAL
    )
    
    print(f"Encoded NoneMinimal frame:")
    print(f"  Frame bytes: {' '.join(f'{b:02X}' for b in frame)}")
    print(f"  Frame structure:")
    print(f"    [0x{msg_id:02X}] - Message ID")
    print(f"    [{' '.join(f'{b:02X}' for b in msg_data)}] - Payload (5 bytes)")
    print(f"  Total overhead: 1 byte (just msg_id)")
    print(f"  WARNING: No synchronization - requires external framing!")
    
    # Parse it back
    parser.reset()
    result = None
    for byte in frame:
        result = parser.parse_byte(byte)
        if result.valid:
            break
    
    if result and result.valid:
        print(f"\nParsed result:")
        print(f"  ✓ Message ID: {result.msg_id}")
        print(f"  ✓ Message length: {result.msg_len} bytes")
        print(f"  ✓ Data matches: {result.msg_data == msg_data}")
    print()


def example_mixed_stream():
    """Example: Parsing a stream with multiple minimal frames"""
    print("=" * 70)
    print("Example 4: Mixed Stream of Minimal Frames")
    print("=" * 70)
    
    # Create parser that can handle multiple frame types
    parser = Parser(
        get_msg_length=get_msg_length,
        enabled_headers=[HeaderType.BASIC, HeaderType.TINY],
        enabled_payloads=[PayloadType.MINIMAL]
    )
    
    # Create multiple frames of different types
    frames = []
    
    # Basic+Minimal with msg_id=1 (10 bytes)
    frames.append(parser.encode(1, bytes(range(10)), HeaderType.BASIC, PayloadType.MINIMAL))
    
    # Tiny+Minimal with msg_id=3 (5 bytes)
    frames.append(parser.encode(3, bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE]), HeaderType.TINY, PayloadType.MINIMAL))
    
    # Basic+Minimal with msg_id=2 (20 bytes)
    frames.append(parser.encode(2, bytes(range(20)), HeaderType.BASIC, PayloadType.MINIMAL))
    
    # Concatenate into a stream
    stream = b''.join(frames)
    
    print(f"Created stream with {len(frames)} frames:")
    print(f"  Total stream length: {len(stream)} bytes")
    print(f"  Stream (hex): {stream.hex()}")
    
    # Parse the stream byte-by-byte
    print(f"\nParsing stream:")
    parser.reset()
    messages = []
    for byte in stream:
        result = parser.parse_byte(byte)
        if result.valid:
            messages.append(result)
            print(f"  ✓ Parsed message {len(messages)}: "
                  f"header={result.header_type}, msg_id={result.msg_id}, len={result.msg_len}")
    
    print(f"\nSuccessfully parsed {len(messages)} messages from stream")
    print(f"  Expected: {len(frames)} frames")
    print(f"  ✓ All frames parsed correctly: {len(messages) == len(frames)}")
    print()


def example_error_handling():
    """Example: What happens without the callback"""
    print("=" * 70)
    print("Example 5: Error Handling - Missing Callback")
    print("=" * 70)
    
    # Create parser WITHOUT callback (wrong!)
    parser = Parser(
        # get_msg_length=None,  # Missing!
        enabled_headers=[HeaderType.TINY],
        enabled_payloads=[PayloadType.MINIMAL]
    )
    
    # Try to parse a minimal frame
    msg_id = 3
    msg_data = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE])
    
    # We'll manually create the frame since encode might also fail
    frame = bytes([0x70, msg_id]) + msg_data
    
    print(f"Attempting to parse without callback:")
    print(f"  Frame bytes: {' '.join(f'{b:02X}' for b in frame)}")
    
    result = None
    for i, byte in enumerate(frame):
        result = parser.parse_byte(byte)
        if result.valid:
            print(f"  Parsed at byte {i}")
            break
    
    if result and result.valid:
        print(f"  ✗ Unexpected: Frame parsed without callback!")
    else:
        print(f"  ✓ Correct: Parser cannot determine message length")
        print(f"  ✓ Parser resets because no callback was provided")
    
    print(f"\n  SOLUTION: Always provide get_msg_length callback for minimal frames!")
    print()


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("MINIMAL FRAME PARSING EXAMPLES - PYTHON")
    print("=" * 70)
    print()
    print("Minimal frames use format: [MSG_ID] [PAYLOAD]")
    print("  • No length field")
    print("  • No CRC checksum")
    print("  • Requires get_msg_length callback")
    print("  • Overhead: 1-3 bytes depending on header type")
    print()
    
    example_basic_minimal()
    example_tiny_minimal()
    example_none_minimal()
    example_mixed_stream()
    example_error_handling()
    
    print("=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == '__main__':
    main()
