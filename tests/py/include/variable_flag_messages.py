#!/usr/bin/env python3
"""
Variable flag test message definitions (Python).
Provides get_message(index) function for variable flag truncation testing.

This file matches the C++ variable_flag_messages.hpp structure.
"""

import sys
import os
from typing import Union

# Add generated directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'generated', 'py'))

from struct_frame.generated.serialization_test import (
    SerializationTestTruncationTestNonVariable,
    SerializationTestTruncationTestVariable,
    SerializationTestNestedPayload,
    SerializationTestNestedVariableMessage,
    SerializationTestVariableMultipleArrays,
    SerializationTestVariableMixedFields,
    get_message_info,
)

# Type alias for message union (like C++ MessageVariant)
MessageType = Union[
    SerializationTestTruncationTestNonVariable,
    SerializationTestTruncationTestVariable,
    SerializationTestNestedVariableMessage,
    SerializationTestVariableMultipleArrays,
    SerializationTestVariableMixedFields,
]

# Message count
MESSAGE_COUNT = 5


# ============================================================================
# Helper functions to create messages (like C++ create_* functions)
# ============================================================================

def create_non_variable_1_3_filled() -> SerializationTestTruncationTestNonVariable:
    """Create non-variable message with 1/3 filled array (67 out of 200 bytes)."""
    return SerializationTestTruncationTestNonVariable(
        sequence_id=0xDEADBEEF,
        data_array=list(range(67)),
        footer=0xCAFE
    )


def create_variable_1_3_filled() -> SerializationTestTruncationTestVariable:
    """Create variable message with 1/3 filled array (67 out of 200 bytes)."""
    return SerializationTestTruncationTestVariable(
        sequence_id=0xDEADBEEF,
        data_array=list(range(67)),
        footer=0xCAFE
    )


def create_nested_variable() -> SerializationTestNestedVariableMessage:
    """Create nested variable message with partially-filled nested struct fields."""
    payload = SerializationTestNestedPayload(
        id=7,
        label=b'Hello',
        samples=[10, 20, 30]
    )
    return SerializationTestNestedVariableMessage(
        sequence=0x12345678,
        payload=payload,
        description=b'nested variable test'
    )


def create_multiple_arrays() -> SerializationTestVariableMultipleArrays:
    """Create multiple-arrays message with partially-filled arrays."""
    return SerializationTestVariableMultipleArrays(
        type=5,
        readings=[100, 200, 300],
        values=[1.5, 2.5],
        label=b'multi arrays test'
    )


def create_mixed_fields() -> SerializationTestVariableMixedFields:
    """Create mixed-fields message: fixed fields + partial variable array and string."""
    return SerializationTestVariableMixedFields(
        fixed_id=0xABCD1234,
        fixed_value=3.14,
        fixed_name=b'DeviceName',
        variable_data=[1000, 2000, 3000, 4000, 5000],
        variable_desc=b'mixed fields test'
    )


# ============================================================================
# get_message(index) - unified interface matching C++ MessageProvider pattern
# ============================================================================

def get_message(index: int) -> MessageType:
    """Get message by index."""
    if index == 0:
        return create_non_variable_1_3_filled()
    elif index == 1:
        return create_variable_1_3_filled()
    elif index == 2:
        return create_nested_variable()
    elif index == 3:
        return create_multiple_arrays()
    else:  # index == 4
        return create_mixed_fields()


# ============================================================================
# check_message(index, info) - validates decoded message matches expected
# This is the callback passed to ProfileRunner.parse()
# ============================================================================

def check_message(index: int, info) -> bool:
    """
    Check if decoded message matches expected.
    
    Args:
        index: Message index
        info: FrameMsgInfo from reader
        
    Returns:
        True if message matches expected, False otherwise
    """
    expected = get_message(index)
    
    # Check msg_id matches
    if info.msg_id != expected.MSG_ID:
        return False
    
    # Deserialize using the expected message's class
    msg_class = type(expected)
    decoded = msg_class.deserialize(info)
    
    # Normalize expected for comparison (round-trip through serialize/deserialize)
    expected_normalized = msg_class.deserialize(expected.serialize())
    
    return decoded == expected_normalized
