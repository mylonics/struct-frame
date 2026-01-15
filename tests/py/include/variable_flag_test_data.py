#!/usr/bin/env python3
"""
Variable flag truncation test data definitions (Python).
Tests that messages with variable=true properly truncate unused array space.

Structure:
- Two identical messages (TruncationTestNonVariable and TruncationTestVariable)
- Only difference: TruncationTestVariable has option variable = true
- Both have data_array filled to 1/3 capacity (67 out of 200 bytes)
- Tests that variable message gets truncated and non-variable does not
"""

import sys
import os
from typing import List, Tuple, Optional

# Add generated directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'generated', 'py'))

from struct_frame.generated.serialization_test import (
    SerializationTestTruncationTestNonVariable,
    SerializationTestTruncationTestVariable,
    get_message_info,
)


# ============================================================================
# Helper functions to create messages
# ============================================================================

def create_non_variable_1_3_filled() -> SerializationTestTruncationTestNonVariable:
    """Create non-variable message with 1/3 filled array (67 out of 200 bytes)."""
    return SerializationTestTruncationTestNonVariable(
        sequence_id=0xDEADBEEF,
        data_array=list(range(67)),  # Fill 1/3 of the array
        footer=0xCAFE
    )


def create_variable_1_3_filled() -> SerializationTestTruncationTestVariable:
    """Create variable message with 1/3 filled array (67 out of 200 bytes).
    This should be identical in content but will serialize smaller due to variable flag."""
    return SerializationTestTruncationTestVariable(
        sequence_id=0xDEADBEEF,
        data_array=list(range(67)),  # Fill 1/3 of the array
        footer=0xCAFE
    )


# ============================================================================
# Typed message arrays
# ============================================================================

def get_non_variable_messages() -> List[SerializationTestTruncationTestNonVariable]:
    """Get non-variable message array (1 message)."""
    return [create_non_variable_1_3_filled()]


def get_variable_messages() -> List[SerializationTestTruncationTestVariable]:
    """Get variable message array (1 message)."""
    return [create_variable_1_3_filled()]


# Message count constant
MESSAGE_COUNT = 2

# The msg_id order array - maps position to which message type to use
MSG_ID_ORDER = [
    SerializationTestTruncationTestNonVariable.MSG_ID,  # 0: Non-variable message
    SerializationTestTruncationTestVariable.MSG_ID,     # 1: Variable message
]


# ============================================================================
# Encoder class - writes messages in order using index tracking
# ============================================================================

class Encoder:
    """Encoder class for variable flag tests."""
    
    def __init__(self):
        self.non_var_idx = 0
        self.var_idx = 0
        self._non_variable_messages = get_non_variable_messages()
        self._variable_messages = get_variable_messages()
    
    def write_message(self, writer, msg_id: int) -> int:
        """Write message to writer based on msg_id."""
        if msg_id == SerializationTestTruncationTestNonVariable.MSG_ID:
            msg = self._non_variable_messages[self.non_var_idx]
            self.non_var_idx += 1
            written = writer.write(msg)
            payload_size = len(msg.serialize())
            print(f"MSG1: {written} bytes (payload={payload_size}, no truncation)")
            return written
        elif msg_id == SerializationTestTruncationTestVariable.MSG_ID:
            msg = self._variable_messages[self.var_idx]
            self.var_idx += 1
            written = writer.write(msg)
            payload_size = len(msg.serialize())
            print(f"MSG2: {written} bytes (payload={payload_size}, TRUNCATED)")
            return written
        return 0


# ============================================================================
# Validator class - validates decoded messages against expected data
# ============================================================================

class Validator:
    """Validator class for variable flag tests."""
    
    def __init__(self):
        self.non_var_idx = 0
        self.var_idx = 0
        self._non_variable_messages = get_non_variable_messages()
        self._variable_messages = get_variable_messages()
    
    def get_expected(self, msg_id: int) -> Optional[Tuple[bytes, int]]:
        """Get expected serialized data for the given msg_id."""
        if msg_id == SerializationTestTruncationTestNonVariable.MSG_ID:
            msg = self._non_variable_messages[self.non_var_idx]
            self.non_var_idx += 1
            data = msg.serialize()
            return (data, len(data))
        elif msg_id == SerializationTestTruncationTestVariable.MSG_ID:
            msg = self._variable_messages[self.var_idx]
            self.var_idx += 1
            data = msg.serialize()
            return (data, len(data))
        return None
    
    def validate_with_equals(self, frame_info) -> bool:
        """Validate decoded message using equality testing."""
        msg_id = frame_info.msg_id
        decoded_data = frame_info
        if msg_id == SerializationTestTruncationTestNonVariable.MSG_ID:
            expected = self._non_variable_messages[self.non_var_idx]
            self.non_var_idx += 1
            expected_unpacked = SerializationTestTruncationTestNonVariable.deserialize(expected.serialize())
            decoded = SerializationTestTruncationTestNonVariable.deserialize(decoded_data)
            return decoded == expected_unpacked
        elif msg_id == SerializationTestTruncationTestVariable.MSG_ID:
            expected = self._variable_messages[self.var_idx]
            self.var_idx += 1
            expected_unpacked = SerializationTestTruncationTestVariable.deserialize(expected.serialize())
            decoded = SerializationTestTruncationTestVariable.deserialize(decoded_data)
            return decoded == expected_unpacked
        return False


# ============================================================================
# Test configuration - provides all data for TestCodec templates
# ============================================================================

class Config:
    """Configuration for variable flag tests."""
    
    MESSAGE_COUNT = MESSAGE_COUNT
    BUFFER_SIZE = 4096
    FORMATS_HELP = "profile_bulk"
    TEST_NAME = "Variable Flag Python"
    
    @staticmethod
    def get_msg_id_order() -> List[int]:
        return MSG_ID_ORDER
    
    @staticmethod
    def get_message_info(msg_id: int):
        return get_message_info(msg_id)
    
    @staticmethod
    def supports_format(format: str) -> bool:
        return format == "profile_bulk"
    
    @staticmethod
    def create_encoder():
        return Encoder()
    
    @staticmethod
    def create_validator():
        return Validator()
