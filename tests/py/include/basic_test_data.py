#!/usr/bin/env python3
"""
Test message data definitions (Python).
Hardcoded test messages for cross-platform compatibility testing.

This module follows the same pattern as C++ test data files, providing:
1. Typed message arrays (one per message type)
2. Message ID order array
3. Encoder class with write_message() method
4. Validator class with get_expected() method  
5. Config class for TestCodec templates
"""

import sys
import os
from typing import List, Tuple, Optional

# Add generated directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'generated', 'py'))

from serialization_test_sf import (
    SerializationTestSerializationTestMessage,
    SerializationTestBasicTypesMessage,
    SerializationTestUnionTestMessage,
    SerializationTestComprehensiveArrayMessage,
    SerializationTestSensor,
    SerializationTestStatus,
    get_msg_length as parser_get_message_length,
)


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
        fixed_statuses=[SerializationTestStatus.STATUS_ACTIVE.value, SerializationTestStatus.STATUS_ERROR.value],
        bounded_statuses=[SerializationTestStatus.STATUS_INACTIVE.value],
        fixed_sensors=[SerializationTestSensor(id=1, value=25.5, status=SerializationTestStatus.STATUS_ACTIVE.value, name=b'TempSensor')],
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


# ============================================================================
# Typed message arrays (one per message type, like C++)
# ============================================================================

def get_serialization_test_messages() -> List[SerializationTestSerializationTestMessage]:
    """Get SerializationTestMessage array (5 messages)."""
    return [
        create_serialization_test(0xDEADBEEF, "Cross-platform test!", 3.14159, True, [100, 200, 300]),
        create_serialization_test(0, "", 0.0, False, []),
        create_serialization_test(0xFFFFFFFF, "Maximum length test string for coverage!", 999999.9, True, [2147483647, -2147483648, 0, 1, -1]),
        create_serialization_test(0xAAAAAAAA, "Negative test", -273.15, False, [-100, -200, -300, -400]),
        create_serialization_test(1234567890, "Special: !@#$%^&*()", 2.71828, True, [0, 1, 1, 2, 3]),
    ]


def get_basic_types_messages() -> List[SerializationTestBasicTypesMessage]:
    """Get BasicTypesMessage array (4 messages)."""
    return [
        create_basic_types(42, 1000, 123456, 9876543210, 200, 50000, 4000000000, 9223372036854775807,
                          3.14159, 2.718281828459045, True, "DEVICE-001", "Basic test values"),
        create_basic_types(0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, False, "", ""),
        create_basic_types(-128, -32768, -2147483648, -9223372036854775807, 255, 65535, 4294967295, 9223372036854775807,
                          -273.15, -9999.999999, False, "NEG-TEST", "Negative and max values"),
        create_basic_types(-128, -32768, -2147483648, -9223372036854775807, 255, 65535, 4294967295, 9223372036854775807,
                          -273.15, -9999.999999, False, "NEG-TEST", "Negative and max values"),
    ]


def get_union_test_messages() -> List[SerializationTestUnionTestMessage]:
    """Get UnionTestMessage array (2 messages)."""
    return [
        create_union_with_array(),
        create_union_with_test(),
    ]


# ============================================================================
# Message ID order array - defines the encode/decode sequence
# ============================================================================

MESSAGE_COUNT = 11


def get_msg_id_order() -> List[int]:
    """Get the message ID order array (maps position to msg_id)."""
    return [
        SerializationTestSerializationTestMessage.MSG_ID,  # 0: SerializationTest[0]
        SerializationTestSerializationTestMessage.MSG_ID,  # 1: SerializationTest[1]
        SerializationTestSerializationTestMessage.MSG_ID,  # 2: SerializationTest[2]
        SerializationTestSerializationTestMessage.MSG_ID,  # 3: SerializationTest[3]
        SerializationTestSerializationTestMessage.MSG_ID,  # 4: SerializationTest[4]
        SerializationTestBasicTypesMessage.MSG_ID,         # 5: BasicTypes[0]
        SerializationTestBasicTypesMessage.MSG_ID,         # 6: BasicTypes[1]
        SerializationTestBasicTypesMessage.MSG_ID,         # 7: BasicTypes[2]
        SerializationTestUnionTestMessage.MSG_ID,          # 8: UnionTest[0]
        SerializationTestUnionTestMessage.MSG_ID,          # 9: UnionTest[1]
        SerializationTestBasicTypesMessage.MSG_ID,         # 10: BasicTypes[3]
    ]


# ============================================================================
# Encoder helper - writes messages in order using index tracking (like C++)
# ============================================================================

class Encoder:
    """Encoder that tracks indices into typed message arrays."""
    
    def __init__(self):
        self.serial_idx = 0
        self.basic_idx = 0
        self.union_idx = 0
        # Cache message arrays
        self._serial_msgs = get_serialization_test_messages()
        self._basic_msgs = get_basic_types_messages()
        self._union_msgs = get_union_test_messages()
    
    def write_message(self, writer, msg_id: int) -> int:
        """Write a message to the writer based on msg_id. Returns bytes written."""
        if msg_id == SerializationTestSerializationTestMessage.MSG_ID:
            msg = self._serial_msgs[self.serial_idx]
            self.serial_idx += 1
            return writer.write_msg(msg)
        elif msg_id == SerializationTestBasicTypesMessage.MSG_ID:
            msg = self._basic_msgs[self.basic_idx]
            self.basic_idx += 1
            return writer.write_msg(msg)
        elif msg_id == SerializationTestUnionTestMessage.MSG_ID:
            msg = self._union_msgs[self.union_idx]
            self.union_idx += 1
            return writer.write_msg(msg)
        return 0


# ============================================================================
# Validator helper - validates decoded messages against expected data (like C++)
# ============================================================================

class Validator:
    """Validator that tracks indices and validates using __eq__ operator."""
    
    def __init__(self):
        self.serial_idx = 0
        self.basic_idx = 0
        self.union_idx = 0
        # Cache message arrays
        self._serial_msgs = get_serialization_test_messages()
        self._basic_msgs = get_basic_types_messages()
        self._union_msgs = get_union_test_messages()
    
    def get_expected(self, msg_id: int) -> Tuple[Optional[bytes], Optional[int]]:
        """Get expected message data for validation. Returns (data, size)."""
        if msg_id == SerializationTestSerializationTestMessage.MSG_ID:
            msg = self._serial_msgs[self.serial_idx]
            self.serial_idx += 1
            data = msg.data()
            return data, len(data)
        elif msg_id == SerializationTestBasicTypesMessage.MSG_ID:
            msg = self._basic_msgs[self.basic_idx]
            self.basic_idx += 1
            data = msg.data()
            return data, len(data)
        elif msg_id == SerializationTestUnionTestMessage.MSG_ID:
            msg = self._union_msgs[self.union_idx]
            self.union_idx += 1
            data = msg.data()
            return data, len(data)
        return None, None

    def validate_with_equals(self, msg_id: int, decoded_data: bytes) -> bool:
        """Validate decoded message using __eq__ operator.
        
        Note: We unpack the expected message's packed data to ensure both messages
        have been through float32 conversion, making equality comparison valid.
        """
        if msg_id == SerializationTestSerializationTestMessage.MSG_ID:
            expected = self._serial_msgs[self.serial_idx]
            self.serial_idx += 1
            # Unpack both from packed bytes to ensure float32 precision matches
            expected_unpacked = SerializationTestSerializationTestMessage.create_unpack(expected.data())
            decoded = SerializationTestSerializationTestMessage.create_unpack(decoded_data)
            return decoded == expected_unpacked
        elif msg_id == SerializationTestBasicTypesMessage.MSG_ID:
            expected = self._basic_msgs[self.basic_idx]
            self.basic_idx += 1
            expected_unpacked = SerializationTestBasicTypesMessage.create_unpack(expected.data())
            decoded = SerializationTestBasicTypesMessage.create_unpack(decoded_data)
            return decoded == expected_unpacked
        elif msg_id == SerializationTestUnionTestMessage.MSG_ID:
            expected = self._union_msgs[self.union_idx]
            self.union_idx += 1
            expected_unpacked = SerializationTestUnionTestMessage.create_unpack(expected.data())
            decoded = SerializationTestUnionTestMessage.create_unpack(decoded_data)
            return decoded == expected_unpacked
        return False


# ============================================================================
# Test configuration - provides all data for TestCodec templates (like C++ Config)
# ============================================================================

class Config:
    """Test configuration for standard messages."""
    MESSAGE_COUNT = MESSAGE_COUNT
    BUFFER_SIZE = 4096
    FORMATS_HELP = "profile_standard, profile_sensor, profile_ipc, profile_bulk, profile_network"
    TEST_NAME = "Python"
    
    @staticmethod
    def get_msg_id_order() -> List[int]:
        return get_msg_id_order()
    
    @staticmethod
    def create_encoder() -> Encoder:
        return Encoder()
    
    @staticmethod
    def create_validator() -> Validator:
        return Validator()
    
    @staticmethod
    def get_message_length(msg_id: int) -> Optional[int]:
        return parser_get_message_length(msg_id)
    
    @staticmethod
    def supports_format(format_name: str) -> bool:
        return format_name in [
            'profile_standard', 'profile_sensor', 'profile_ipc',
            'profile_bulk', 'profile_network'
        ]


# Export config instance for convenience
basic_test_config = Config
