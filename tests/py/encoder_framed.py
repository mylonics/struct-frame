#!/usr/bin/env python3
"""
Encoder for cross-platform testing with framing.
Encodes a SerializationTestMessage with framing and writes to stdout.
"""

import sys
import os

# Add generated code to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../generated/py'))

try:
    from serialization_test_sf import SerializationTestSerializationTestMessage
    from struct_frame_parser import BasicPacket
    
    # Create test message with known values
    msg = SerializationTestSerializationTestMessage(
        0xDEADBEEF,  # magic_number
        3.14159,     # test_float
        True         # test_bool
    )
    
    # Set string and array fields
    msg.test_string = "Hello from Python!"
    msg.test_array = [100, 200, 300]
    
    # Serialize with framing using BasicPacket
    packet = BasicPacket()
    encoded_data = packet.encode_msg(msg)
    
    # Write binary data to stdout
    sys.stdout.buffer.write(bytes(encoded_data))
    sys.stdout.buffer.flush()
    
except ImportError as e:
    sys.stderr.write(f"ERROR: Generated modules not found: {e}\n")
    sys.exit(1)
except Exception as e:
    sys.stderr.write(f"ERROR: Failed to encode: {e}\n")
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
