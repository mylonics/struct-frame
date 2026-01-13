#!/usr/bin/env python3
"""
Test for variable length message encoding/decoding.
"""

import sys
import os

# Add the generated code to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'generated', 'struct_frame', 'generated'))

from variable_messages import (
    VariableMessagesVariableDataMessage,
    VariableMessagesFixedDataMessage, 
    VariableMessagesMultiArrayVariable
)


def test_variable_message_constants():
    """Test that variable messages have the correct constants."""
    print("Testing variable message constants...")
    
    # VariableDataMessage should have MIN_SIZE and IS_VARIABLE
    assert hasattr(VariableMessagesVariableDataMessage, 'MIN_SIZE'), "Variable message should have MIN_SIZE"
    assert hasattr(VariableMessagesVariableDataMessage, 'IS_VARIABLE'), "Variable message should have IS_VARIABLE"
    assert VariableMessagesVariableDataMessage.IS_VARIABLE == True
    assert VariableMessagesVariableDataMessage.MIN_SIZE == 7  # 4 (message_id) + 1 (data count) + 2 (checksum)
    
    # FixedDataMessage should NOT have MIN_SIZE or IS_VARIABLE
    assert not hasattr(VariableMessagesFixedDataMessage, 'MIN_SIZE'), "Fixed message should not have MIN_SIZE"
    assert not hasattr(VariableMessagesFixedDataMessage, 'IS_VARIABLE'), "Fixed message should not have IS_VARIABLE"
    
    # MultiArrayVariable should have MIN_SIZE = 4 (type + count_readings + count_values + length_label)
    assert VariableMessagesMultiArrayVariable.MIN_SIZE == 4
    assert VariableMessagesMultiArrayVariable.IS_VARIABLE == True
    
    print("  OK: Variable message constants are correct")


def test_variable_pack_size():
    """Test that pack_size returns the correct value based on actual data."""
    print("Testing variable pack_size method...")
    
    # Empty data array
    msg1 = VariableMessagesVariableDataMessage()
    msg1.message_id = 42
    msg1.data = []
    msg1.checksum = 1234
    assert msg1.pack_size() == 7, f"Expected 7, got {msg1.pack_size()}"
    
    # With 10 data bytes
    msg2 = VariableMessagesVariableDataMessage()
    msg2.message_id = 42
    msg2.data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    msg2.checksum = 1234
    assert msg2.pack_size() == 17, f"Expected 17, got {msg2.pack_size()}"  # 4 + 1 + 10 + 2
    
    print("  OK: pack_size returns correct values")


def test_variable_pack_unpack():
    """Test that pack_variable and unpack_variable work correctly."""
    print("Testing variable pack/unpack methods...")
    
    # Create a message with some data
    original = VariableMessagesVariableDataMessage()
    original.message_id = 12345
    original.data = [0xAA, 0xBB, 0xCC, 0xDD]
    original.checksum = 0x5678
    
    # Pack variable
    packed = original.pack_variable()
    expected_size = 4 + 1 + 4 + 2  # message_id + count + 4 data bytes + checksum
    assert len(packed) == expected_size, f"Expected {expected_size} bytes, got {len(packed)}"
    
    # Compare to fixed pack
    fixed_packed = original.pack()
    assert len(fixed_packed) == VariableMessagesVariableDataMessage.MAX_SIZE, \
        f"Fixed pack should be {VariableMessagesVariableDataMessage.MAX_SIZE} bytes"
    
    # Verify variable pack is smaller
    assert len(packed) < len(fixed_packed), "Variable pack should be smaller than fixed pack"
    
    # Unpack variable
    unpacked = VariableMessagesVariableDataMessage.unpack_variable(packed)
    assert unpacked.message_id == original.message_id
    assert list(unpacked.data) == list(original.data)
    assert unpacked.checksum == original.checksum
    
    print("  OK: pack_variable/unpack_variable work correctly")


def test_multi_array_variable():
    """Test variable message with multiple arrays."""
    print("Testing multi-array variable message...")
    
    msg = VariableMessagesMultiArrayVariable()
    msg.type = 5
    msg.readings = [100, 200, 300]  # 3 int32 values = 12 bytes
    msg.values = [1.5, 2.5]  # 2 float values = 8 bytes  
    msg.label = b"test"  # 4 bytes
    
    # Calculate expected size: type(1) + count(1) + 12 + count(1) + 8 + length(1) + 4 = 28
    expected = 1 + 1 + 12 + 1 + 8 + 1 + 4
    actual = msg.pack_size()
    assert actual == expected, f"Expected {expected}, got {actual}"
    
    # Pack and unpack
    packed = msg.pack_variable()
    assert len(packed) == expected
    
    unpacked = VariableMessagesMultiArrayVariable.unpack_variable(packed)
    assert unpacked.type == msg.type
    assert list(unpacked.readings) == list(msg.readings)
    assert list(unpacked.values) == list(msg.values)
    assert unpacked.label == msg.label
    
    print("  OK: Multi-array variable message works correctly")


def main():
    """Run all tests."""
    print("\n=== Variable Message Tests ===\n")
    
    try:
        test_variable_message_constants()
        test_variable_pack_size()
        test_variable_pack_unpack()
        test_multi_array_variable()
        
        print("\n=== All tests passed! ===\n")
        return 0
    except AssertionError as e:
        print(f"\n!!! Test FAILED: {e}\n")
        return 1
    except Exception as e:
        print(f"\n!!! Error: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
