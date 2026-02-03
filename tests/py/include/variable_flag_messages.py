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
    get_message_info,
)

# Type alias for message union (like C++ MessageVariant)
MessageType = Union[
    SerializationTestTruncationTestNonVariable,
    SerializationTestTruncationTestVariable,
]

# Message count
MESSAGE_COUNT = 2


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


# ============================================================================
# get_message(index) - unified interface matching C++ MessageProvider pattern
# ============================================================================

def get_message(index: int) -> MessageType:
    """Get message by index."""
    if index == 0:
        return create_non_variable_1_3_filled()
    else:  # index == 1
        return create_variable_1_3_filled()
