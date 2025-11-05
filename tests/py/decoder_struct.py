#!/usr/bin/env python3
"""
Decoder for cross-platform struct testing (no framing).
Reads raw struct bytes from stdin and decodes SerializationTestMessage.
"""

import sys
import os

# Add generated code to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../generated/py'))

try:
    from serialization_test_sf import SerializationTestSerializationTestMessage
    
    # Read binary data from stdin
    binary_data = sys.stdin.buffer.read()
    
    if len(binary_data) == 0:
        sys.stderr.write("ERROR: No data received from stdin\n")
        sys.exit(1)
    
    # Deserialize from struct bytes (no framing) using create_unpack()
    msg = SerializationTestSerializationTestMessage.create_unpack(binary_data)
    
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
