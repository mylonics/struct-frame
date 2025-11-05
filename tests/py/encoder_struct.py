#!/usr/bin/env python3
"""
Encoder for cross-platform struct testing (no framing).
Encodes a SerializationTestMessage and writes raw struct bytes to stdout.
"""

import sys
import os

# Add generated code to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../generated/py'))

try:
    from serialization_test_sf import SerializationTestSerializationTestMessage
    
    # Create test message with known values
    msg = SerializationTestSerializationTestMessage(
        0xDEADBEEF,  # magic_number
        3.14159,     # test_float
        True         # test_bool
    )
    
    # Set string and array fields
    msg.test_string = "Hello from Python!"
    msg.test_array = [100, 200, 300]
    
    # Serialize to struct bytes (no framing) using pack()
    struct_bytes = msg.pack()
    
    # Write binary data to stdout
    sys.stdout.buffer.write(bytes(struct_bytes))
    sys.stdout.buffer.flush()
    
except ImportError as e:
    sys.stderr.write(f"ERROR: Generated modules not found: {e}\n")
    sys.exit(1)
except Exception as e:
    sys.stderr.write(f"ERROR: Failed to encode: {e}\n")
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
