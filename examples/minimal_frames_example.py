#!/usr/bin/env python3
"""
Minimal Frame Parsing Example - Python

This example demonstrates how to use minimal frames (no length field, no CRC)
with the struct-frame parser using the AUTO-GENERATED get_msg_length function.

The generator automatically creates the get_msg_length function based on your
.proto file message definitions, so you don't need to write it yourself!

Minimal frames are ideal for:
- Fixed-size messages
- Bandwidth-constrained links (LoRa, radio, RF)
- Trusted communication (SPI, I2C, shared memory)
- Low-power applications
"""

import sys
import os

# Add generated code path
generated_path = os.path.join(os.path.dirname(__file__), '..', 'tests', 'generated', 'py')
sys.path.insert(0, generated_path)

from parser import Parser, HeaderType, PayloadType
# Import the AUTO-GENERATED get_msg_length function from your messages
from struct_frame.generated.serialization_test import get_msg_length, serialization_test_definitions

# The get_msg_length function is automatically generated and knows the size
# of each message based on your .proto definitions. No manual configuration needed!


def example_basic_minimal():
    """Example: BasicMinimal frame format"""
    print("=" * 70)
    print("Example 1: BasicMinimal Frame (0x90 0x70)")
    print("=" * 70)
    
    # Create parser with auto-generated callback for minimal frames
    parser = Parser(
        get_msg_length=get_msg_length,  # Auto-generated function!
        enabled_headers=[HeaderType.BASIC],
        enabled_payloads=[PayloadType.MINIMAL]
    )
    
    # Use a real message ID from the proto definitions
    msg_id = 204  # SerializationTestMessage
    msg_size = get_msg_length(msg_id)  # Automatically knows it's 95 bytes
    msg_data = bytes(range(min(msg_size, 256)))[:msg_size]
    
    print(f"Using message ID {msg_id} with auto-detected size {msg_size} bytes")
    
    frame = parser.encode(
        msg_id=msg_id,
        msg=msg_data,
        header_type=HeaderType.BASIC,
        payload_type=PayloadType.MINIMAL
    )
    
    print(f"Encoded BasicMinimal frame:")
    print(f"  Frame bytes: {' '.join(f'{b:02X}' for b in frame[:20])}... ({len(frame)} bytes total)")
    print(f"  Frame structure:")
    print(f"    [0x90] - Basic frame marker")
    print(f"    [0x70] - Minimal payload type (0x70 + 0)")
    print(f"    [0x{msg_id:02X}] - Message ID")
    print(f"    [data...] - Payload ({msg_size} bytes)")
    
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
        print(f"  Message ID: {result.msg_id}")
        print(f"  Message length: {result.msg_len} bytes")
        print(f"  ✓ Data matches: {result.msg_data == msg_data}")
    print()


def example_tiny_minimal():
    """Example: TinyMinimal frame format"""
    print("=" * 70)
    print("Example 2: TinyMinimal Frame (0x70)")
    print("=" * 70)
    
    # Create parser with auto-generated callback
    parser = Parser(
        get_msg_length=get_msg_length,  # Auto-generated!
        enabled_headers=[HeaderType.TINY],
        enabled_payloads=[PayloadType.MINIMAL]
    )
    
    # Use a different message ID
    msg_id = 203  # ComprehensiveArrayMessage
    msg_size = get_msg_length(msg_id)  # Automatically knows it's 139 bytes
    msg_data = bytes(range(min(msg_size, 256)))[:msg_size]
    
    print(f"Using message ID {msg_id} with auto-detected size {msg_size} bytes")
    
    frame = parser.encode(
        msg_id=msg_id,
        msg=msg_data,
        header_type=HeaderType.TINY,
        payload_type=PayloadType.MINIMAL
    )
    
    print(f"Encoded TinyMinimal frame:")
    print(f"  Frame bytes: {' '.join(f'{b:02X}' for b in frame[:20])}... ({len(frame)} bytes total)")
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


def example_auto_generated_function():
    """Example: Show available messages in the auto-generated function"""
    print("=" * 70)
    print("Example 3: Auto-Generated Message Definitions")
    print("=" * 70)
    
    print("The generator created these message definitions:")
    print()
    for msg_id, msg_class in serialization_test_definitions.items():
        size = get_msg_length(msg_id)
        print(f"  Message ID {msg_id}: {msg_class.__name__}")
        print(f"    Size: {size} bytes (auto-detected)")
    print()
    print("The get_msg_length() function automatically returns the correct")
    print("size for each message ID - no manual configuration needed!")
    print()


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("MINIMAL FRAME PARSING EXAMPLES - Using Auto-Generated Functions")
    print("=" * 70)
    print()
    print("Minimal frames use format: [MSG_ID] [PAYLOAD]")
    print("  • No length field")
    print("  • No CRC checksum")
    print("  • Uses AUTO-GENERATED get_msg_length callback")
    print("  • Overhead: 1-3 bytes depending on header type")
    print()
    
    example_basic_minimal()
    example_tiny_minimal()
    example_auto_generated_function()
    
    print("=" * 70)
    print("All examples completed!")
    print("=" * 70)
    print()
    print("Key takeaway: The get_msg_length() function is AUTO-GENERATED")
    print("from your .proto file. Just import and use it!")


if __name__ == '__main__':
    main()
