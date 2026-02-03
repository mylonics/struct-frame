#!/usr/bin/env python3
"""
Test message data definitions (Python).
Hardcoded test messages for cross-platform compatibility testing.

This module follows the C++ test pattern with a unified get_message(index) interface.
The get_message() function returns a message based on index, matching the C++ approach.
"""

import sys
import os
from typing import List, Optional, Union

# Add generated directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'generated', 'py'))

from struct_frame.generated.serialization_test import (
    SerializationTestSerializationTestMessage,
    SerializationTestBasicTypesMessage,
    SerializationTestUnionTestMessage,
    SerializationTestComprehensiveArrayMessage,
    SerializationTestSensor,
    SerializationTestStatus,
    SerializationTestVariableSingleArray,
    SerializationTestMessage,
    SerializationTestMsgSeverity,
    get_message_info,
)

# Type alias for message union (like C++ MessageVariant)
MessageType = Union[
    SerializationTestSerializationTestMessage,
    SerializationTestBasicTypesMessage,
    SerializationTestUnionTestMessage,
    SerializationTestVariableSingleArray,
    SerializationTestMessage,
]

# ============================================================================
# Message count and supported profiles
# ============================================================================

MESSAGE_COUNT = 17
PROFILES = "standard, sensor, ipc, bulk, network"


# ============================================================================
# Helper functions to create messages (like C++ create_* functions)
# ============================================================================

def create_serialization_test(magic: int, string: str, flt: float, bl: bool, arr: List[int]) -> SerializationTestSerializationTestMessage:
    """Create a SerializationTestMessage from test values."""
    return SerializationTestSerializationTestMessage(
        magic_number=magic,
        test_string=string.encode('utf-8'),
        test_float=flt,
        test_bool=bl,
        test_array=arr
    )


def create_basic_types(si: int, mi: int, ri: int, li: int, su: int, mu: int, ru: int, lu: int,
                       sp: float, dp: float, fl: bool, dev: str, desc: str) -> SerializationTestBasicTypesMessage:
    """Create a BasicTypesMessage from test values."""
    return SerializationTestBasicTypesMessage(
        small_int=si,
        medium_int=mi,
        regular_int=ri,
        large_int=li,
        small_uint=su,
        medium_uint=mu,
        regular_uint=ru,
        large_uint=lu,
        single_precision=sp,
        double_precision=dp,
        flag=fl,
        device_id=dev.encode('utf-8'),
        description=desc.encode('utf-8')
    )


def create_union_with_array() -> SerializationTestUnionTestMessage:
    """Create UnionTestMessage with array_payload."""
    arr = SerializationTestComprehensiveArrayMessage(
        fixed_ints=[10, 20, 30],
        fixed_floats=[1.5, 2.5],
        fixed_bools=[True, False, True, False],
        bounded_uints=[100, 200],
        bounded_doubles=[3.14159],
        fixed_strings=[b'Hello', b'World'],
        bounded_strings=[b'Test'],
        fixed_statuses=[SerializationTestStatus.ACTIVE.value, SerializationTestStatus.ERROR.value],
        bounded_statuses=[SerializationTestStatus.INACTIVE.value],
        fixed_sensors=[SerializationTestSensor(id=1, value=25.5, status=SerializationTestStatus.ACTIVE.value, name=b'TempSensor')],
        bounded_sensors=[]
    )
    return SerializationTestUnionTestMessage(
        payload={'array_payload': arr},
        payload_which='array_payload',
        payload_discriminator=SerializationTestComprehensiveArrayMessage.MSG_ID
    )


def create_union_with_test() -> SerializationTestUnionTestMessage:
    """Create UnionTestMessage with test_payload."""
    test = SerializationTestSerializationTestMessage(
        magic_number=0x12345678,
        test_string=b'Union test message',
        test_float=99.99,
        test_bool=True,
        test_array=[1, 2, 3, 4, 5]
    )
    return SerializationTestUnionTestMessage(
        payload={'test_payload': test},
        payload_which='test_payload',
        payload_discriminator=SerializationTestSerializationTestMessage.MSG_ID
    )


def create_variable_single_array_empty() -> SerializationTestVariableSingleArray:
    """Create VariableSingleArray with empty payload."""
    return SerializationTestVariableSingleArray(message_id=0x00000001, payload=[], checksum=0x0001)


def create_variable_single_array_single() -> SerializationTestVariableSingleArray:
    """Create VariableSingleArray with single element."""
    return SerializationTestVariableSingleArray(message_id=0x00000002, payload=[42], checksum=0x0002)


def create_variable_single_array_third() -> SerializationTestVariableSingleArray:
    """Create VariableSingleArray with 1/3 filled (67 elements)."""
    return SerializationTestVariableSingleArray(message_id=0x00000003, payload=list(range(67)), checksum=0x0003)


def create_variable_single_array_almost() -> SerializationTestVariableSingleArray:
    """Create VariableSingleArray with 199 elements."""
    return SerializationTestVariableSingleArray(message_id=0x00000004, payload=list(range(199)), checksum=0x0004)


def create_variable_single_array_full() -> SerializationTestVariableSingleArray:
    """Create VariableSingleArray with full 200 elements."""
    return SerializationTestVariableSingleArray(message_id=0x00000005, payload=list(range(200)), checksum=0x0005)


def create_message_test() -> SerializationTestMessage:
    """Create a Message."""
    return SerializationTestMessage(
        severity=SerializationTestMsgSeverity.SEV_MSG.value,
        module=b"test",
        msg=b"A really good"
    )


# ============================================================================
# Unified get_message(index) function - matches C++ MessageProvider pattern
# ============================================================================

def get_message(index: int) -> MessageType:
    """
    Get message by index - unified interface matching C++ get_message().
    
    Message order matches standard_test_data get_msg_id_order():
    - SerializationTest messages (0-4)
    - BasicTypes messages (5-7)
    - UnionTest messages (8-9)
    - BasicTypes message (10)
    - VariableSingleArray messages (11-15)
    - Message (16)
    """
    if index == 0:
        return create_serialization_test(0xDEADBEEF, "Cross-platform test!", 3.14159, True, [100, 200, 300])
    elif index == 1:
        return create_serialization_test(0, "", 0.0, False, [])
    elif index == 2:
        return create_serialization_test(0xFFFFFFFF, "Maximum length test string for coverage!", 999999.9, True,
                                         [2147483647, -2147483648, 0, 1, -1])
    elif index == 3:
        return create_serialization_test(0xAAAAAAAA, "Negative test", -273.15, False, [-100, -200, -300, -400])
    elif index == 4:
        return create_serialization_test(1234567890, "Special: !@#$%^&*()", 2.71828, True, [0, 1, 1, 2, 3])
    elif index == 5:
        return create_basic_types(42, 1000, 123456, 9876543210, 200, 50000, 4000000000, 9223372036854775807,
                                  3.14159, 2.718281828459045, True, "DEVICE-001", "Basic test values")
    elif index == 6:
        return create_basic_types(0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, False, "", "")
    elif index == 7:
        return create_basic_types(-128, -32768, -2147483648, -9223372036854775807, 255, 65535, 4294967295, 9223372036854775807,
                                  -273.15, -9999.999999, False, "NEG-TEST", "Negative and max values")
    elif index == 8:
        return create_union_with_array()
    elif index == 9:
        return create_union_with_test()
    elif index == 10:
        return create_basic_types(-128, -32768, -2147483648, -9223372036854775807, 255, 65535, 4294967295, 9223372036854775807,
                                  -273.15, -9999.999999, False, "NEG-TEST", "Negative and max values")
    elif index == 11:
        return create_variable_single_array_empty()
    elif index == 12:
        return create_variable_single_array_single()
    elif index == 13:
        return create_variable_single_array_third()
    elif index == 14:
        return create_variable_single_array_almost()
    elif index == 15:
        return create_variable_single_array_full()
    else:  # index == 16
        return create_message_test()


# ============================================================================
# Message class lookup - maps message type to class for deserialization
# ============================================================================

MESSAGE_CLASSES = {
    SerializationTestSerializationTestMessage.MSG_ID: SerializationTestSerializationTestMessage,
    SerializationTestBasicTypesMessage.MSG_ID: SerializationTestBasicTypesMessage,
    SerializationTestUnionTestMessage.MSG_ID: SerializationTestUnionTestMessage,
    SerializationTestVariableSingleArray.MSG_ID: SerializationTestVariableSingleArray,
    SerializationTestMessage.MSG_ID: SerializationTestMessage,
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
        self._index += 1
        return writer.write(msg)


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
        
        # Unpack both from packed bytes to ensure float32 precision matches
        expected_unpacked = msg_class.deserialize(expected.serialize())
        decoded = msg_class.deserialize(frame_info)
        return decoded == expected_unpacked


# ============================================================================
# Test configuration - matches C++ TestHarness pattern
# ============================================================================

class Config:
    """Test configuration for standard messages."""
    MESSAGE_COUNT = MESSAGE_COUNT
    BUFFER_SIZE = 4096
    FORMATS_HELP = PROFILES
    TEST_NAME = "Python"
    
    @staticmethod
    def get_msg_id_order() -> List[int]:
        """Get message ID order array."""
        return [get_message(i).MSG_ID for i in range(MESSAGE_COUNT)]
    
    @staticmethod
    def create_encoder() -> Encoder:
        return Encoder()
    
    @staticmethod
    def create_validator() -> Validator:
        return Validator()
    
    @staticmethod
    def get_message_info(msg_id: int):
        """Get unified message info (size, magic1, magic2)."""
        return get_message_info(msg_id)
    
    @staticmethod
    def supports_format(format_name: str) -> bool:
        return format_name in ['standard', 'sensor', 'ipc', 'bulk', 'network']
