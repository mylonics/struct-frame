#!/usr/bin/env python3
"""
Decoder for cross-platform testing with framing.
Reads framed SerializationTestMessage from stdin and decodes it.
"""

import sys
import os

# Add generated code to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../generated/py'))

try:
    from serialization_test_sf import SerializationTestSerializationTestMessage
    from struct_frame_parser import BasicPacket, FrameParser
    
    # Read binary data from stdin
    binary_data = sys.stdin.buffer.read()
    
    if len(binary_data) == 0:
        sys.stderr.write("ERROR: No data received from stdin\n")
        sys.exit(1)
    
    # Create parser for deserialization
    packet_formats = {0x90: BasicPacket()}
    msg_definitions = {204: SerializationTestSerializationTestMessage}
    parser = FrameParser(packet_formats, msg_definitions)
    
    # Parse the binary data byte by byte
    msg = None
    for byte in binary_data:
        result = parser.parse_char(byte)
        if result:
            msg = result
            break
    
    if msg is None:
        sys.stderr.write("ERROR: Failed to decode message\n")
        sys.exit(1)
    
    # Print decoded values in a consistent format
    print(f"magic_number=0x{msg.magic_number:08X}")
    print(f"test_string={msg.test_string}")
    print(f"test_float={msg.test_float:.5f}")
    print(f"test_bool={msg.test_bool}")
    print(f"test_array={','.join(map(str, msg.test_array))}")
    
except ImportError as e:
    sys.stderr.write(f"ERROR: Generated modules not found: {e}\n")
    sys.exit(1)
except Exception as e:
    sys.stderr.write(f"ERROR: Failed to decode: {e}\n")
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
