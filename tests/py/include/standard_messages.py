#!/usr/bin/env python3
"""
Standard test message definitions (Python).
Provides get_message(index) function for test messages.

This file matches the C++ standard_messages.hpp structure.
"""

import sys
import os
from typing import List, Union

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

# Message count
MESSAGE_COUNT = 17


# ============================================================================
# Helper functions to create messages (like C++ create_* functions)
# ============================================================================

def create_serialization_test(magic: int, string: str, flt: float, bl: bool, arr: List[int]) -> SerializationTestSerializationTestMessage:
    return SerializationTestSerializationTestMessage(
        magic_number=magic,
        test_string=string.encode('utf-8'),
        test_float=flt,
        test_bool=bl,
        test_array=arr
    )


def create_basic_types(si: int, mi: int, ri: int, li: int, su: int, mu: int, ru: int, lu: int,
                       sp: float, dp: float, fl: bool, dev: str, desc: str) -> SerializationTestBasicTypesMessage:
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
    return SerializationTestVariableSingleArray(message_id=0x00000001, payload=[], checksum=0x0001)


def create_variable_single_array_single() -> SerializationTestVariableSingleArray:
    return SerializationTestVariableSingleArray(message_id=0x00000002, payload=[42], checksum=0x0002)


def create_variable_single_array_third() -> SerializationTestVariableSingleArray:
    return SerializationTestVariableSingleArray(message_id=0x00000003, payload=list(range(67)), checksum=0x0003)


def create_variable_single_array_almost() -> SerializationTestVariableSingleArray:
    return SerializationTestVariableSingleArray(message_id=0x00000004, payload=list(range(199)), checksum=0x0004)


def create_variable_single_array_full() -> SerializationTestVariableSingleArray:
    return SerializationTestVariableSingleArray(message_id=0x00000005, payload=list(range(200)), checksum=0x0005)


def create_message_test() -> SerializationTestMessage:
    return SerializationTestMessage(
        severity=SerializationTestMsgSeverity.SEV_MSG.value,
        module=b"test",
        msg=b"A really good"
    )


# ============================================================================
# get_message(index) - unified interface matching C++ MessageProvider pattern
# ============================================================================

def get_message(index: int) -> MessageType:
    """Get message by index."""
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
