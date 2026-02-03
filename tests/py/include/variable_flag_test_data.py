#!/usr/bin/env python3
"""
Variable flag truncation test data definitions (Python).
Tests that messages with variable=true properly truncate unused array space.

This module follows the C++ test pattern with a unified get_message(index) interface.
"""

import sys
import os
from typing import List, Union

# Add generated directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'generated', 'py'))

from struct_frame.generated.serialization_test import (
    SerializationTestTruncationTestNonVariable,
    SerializationTestTruncationTestVariable,
    get_message_info,
)

# Type alias for message union (like C++ MessageVariant)
MessageType = Union[
    SerializationTestTruncationTestNonVariable,
    SerializationTestTruncationTestVariable,
]

# ============================================================================
# Message count and supported profiles
# ============================================================================

MESSAGE_COUNT = 2
PROFILES = "bulk"


# ============================================================================
# Helper functions to create messages (like C++ create_* functions)
# ============================================================================

def create_non_variable_1_3_filled() -> SerializationTestTruncationTestNonVariable:
    """Create non-variable message with 1/3 filled array (67 out of 200 bytes)."""
    return SerializationTestTruncationTestNonVariable(
        sequence_id=0xDEADBEEF,
        data_array=list(range(67)),  # Fill 1/3 of the array
        footer=0xCAFE
    )


def create_variable_1_3_filled() -> SerializationTestTruncationTestVariable:
    """Create variable message with 1/3 filled array (67 out of 200 bytes)."""
    return SerializationTestTruncationTestVariable(
        sequence_id=0xDEADBEEF,
        data_array=list(range(67)),  # Fill 1/3 of the array
        footer=0xCAFE
    )


# ============================================================================
# Unified get_message(index) function - matches C++ MessageProvider pattern
# ============================================================================

def get_message(index: int) -> MessageType:
    """
    Get message by index - unified interface matching C++ get_message().
    
    Message order: TruncationTestNonVariable, TruncationTestVariable
    """
    if index == 0:
        return create_non_variable_1_3_filled()
    else:  # index == 1
        return create_variable_1_3_filled()


# ============================================================================
# Message class lookup - maps message type to class for deserialization
# ============================================================================

MESSAGE_CLASSES = {
    SerializationTestTruncationTestNonVariable.MSG_ID: SerializationTestTruncationTestNonVariable,
    SerializationTestTruncationTestVariable.MSG_ID: SerializationTestTruncationTestVariable,
}


# ============================================================================
# Encoder - simplified to use get_message(index) directly
# ============================================================================

class Encoder:
    """Encoder that uses get_message(index) for encoding."""
    
    def __init__(self):
        self._index = 0
    
    def write_message(self, writer, _msg_id: int) -> int:
        """Write message at current index to writer. Returns bytes written."""
        msg = get_message(self._index)
        payload_size = len(msg.serialize())
        
        self._index += 1
        written = writer.write(msg)
        
        # Print size info for variable flag tests
        if self._index == 1:
            print(f"MSG1: {written} bytes (payload={payload_size}, no truncation)")
        else:
            print(f"MSG2: {written} bytes (payload={payload_size}, TRUNCATED)")
        
        return written


# ============================================================================
# Validator - simplified to use get_message(index) directly
# ============================================================================

class Validator:
    """Validator that uses get_message(index) for validation."""
    
    def __init__(self):
        self._index = 0
    
    def validate_with_equals(self, frame_info) -> bool:
        """Validate decoded message using __eq__ operator."""
        msg_id = frame_info.msg_id
        msg_class = MESSAGE_CLASSES.get(msg_id)
        if not msg_class:
            return False
        
        expected = get_message(self._index)
        self._index += 1
        
        # Unpack both from packed bytes to ensure precision matches
        expected_unpacked = msg_class.deserialize(expected.serialize())
        decoded = msg_class.deserialize(frame_info)
        return decoded == expected_unpacked


# ============================================================================
# Test configuration - matches C++ TestHarness pattern
# ============================================================================

class Config:
    """Configuration for variable tests."""
    
    MESSAGE_COUNT = MESSAGE_COUNT
    BUFFER_SIZE = 4096
    FORMATS_HELP = PROFILES
    TEST_NAME = "Variable Python"
    
    @staticmethod
    def get_msg_id_order() -> List[int]:
        """Get message ID order array."""
        return [get_message(i).MSG_ID for i in range(MESSAGE_COUNT)]
    
    @staticmethod
    def get_message_info(msg_id: int):
        return get_message_info(msg_id)
    
    @staticmethod
    def supports_format(format: str) -> bool:
        return format == "bulk"
    
    @staticmethod
    def create_encoder():
        return Encoder()
    
    @staticmethod
    def create_validator():
        return Validator()
