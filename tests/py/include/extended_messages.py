#!/usr/bin/env python3
"""
Extended test message definitions (Python).
Provides get_message(index) function for extended message ID and payload testing.

This file matches the C++ extended_messages.hpp structure.
"""

import sys
import os
from typing import Union

# Add generated directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'generated', 'py'))

from struct_frame.generated.extended_test import (
    ExtendedIdMessage1,
    ExtendedIdMessage2,
    ExtendedIdMessage3,
    ExtendedIdMessage4,
    ExtendedIdMessage5,
    ExtendedIdMessage6,
    ExtendedIdMessage7,
    ExtendedIdMessage8,
    ExtendedIdMessage9,
    ExtendedIdMessage10,
    LargePayloadMessage1,
    LargePayloadMessage2,
    ExtendedVariableSingleArray,
    get_message_info,
)

# Type alias for message union (like C++ MessageVariant)
MessageType = Union[
    ExtendedIdMessage1,
    ExtendedIdMessage2,
    ExtendedIdMessage3,
    ExtendedIdMessage4,
    ExtendedIdMessage5,
    ExtendedIdMessage6,
    ExtendedIdMessage7,
    ExtendedIdMessage8,
    ExtendedIdMessage9,
    ExtendedIdMessage10,
    LargePayloadMessage1,
    LargePayloadMessage2,
    ExtendedVariableSingleArray,
]

# Message count
MESSAGE_COUNT = 17


# ============================================================================
# Helper functions to create messages (like C++ create_* functions)
# ============================================================================

def create_ext_id_1() -> ExtendedIdMessage1:
    return ExtendedIdMessage1(
        sequence_number=12345678,
        label=b"Test Label Extended 1",
        value=3.14159,
        enabled=True
    )


def create_ext_id_2() -> ExtendedIdMessage2:
    return ExtendedIdMessage2(
        sensor_id=-42,
        reading=2.718281828,
        status_code=50000,
        description=b"Extended ID test message 2"
    )


def create_ext_id_3() -> ExtendedIdMessage3:
    return ExtendedIdMessage3(
        timestamp=1704067200000000,
        temperature=-40,
        humidity=85,
        location=b"Sensor Room A"
    )


def create_ext_id_4() -> ExtendedIdMessage4:
    return ExtendedIdMessage4(
        event_id=999999,
        event_type=42,
        event_time=1704067200000,
        event_data=b"Event payload with extended message ID"
    )


def create_ext_id_5() -> ExtendedIdMessage5:
    return ExtendedIdMessage5(
        x_position=100.5,
        y_position=-200.25,
        z_position=50.125,
        frame_number=1000000
    )


def create_ext_id_6() -> ExtendedIdMessage6:
    return ExtendedIdMessage6(
        command_id=-12345,
        parameter1=1000,
        parameter2=2000,
        acknowledged=False,
        command_name=b"CALIBRATE_SENSOR"
    )


def create_ext_id_7() -> ExtendedIdMessage7:
    return ExtendedIdMessage7(
        counter=4294967295,
        average=123.456789,
        minimum=-999.99,
        maximum=999.99
    )


def create_ext_id_8() -> ExtendedIdMessage8:
    return ExtendedIdMessage8(
        level=255,
        offset=-32768,
        duration=86400000,
        tag=b"TEST123"
    )


def create_ext_id_9() -> ExtendedIdMessage9:
    return ExtendedIdMessage9(
        big_number=-9223372036854775807,
        big_unsigned=18446744073709551615,
        precision_value=1.7976931348623157e+308
    )


def create_ext_id_10() -> ExtendedIdMessage10:
    return ExtendedIdMessage10(
        small_value=256,
        short_text=b"Boundary Test",
        flag=True
    )


def create_large_1() -> LargePayloadMessage1:
    sensor_readings = [float(i + 1) for i in range(64)]
    return LargePayloadMessage1(
        sensor_readings=sensor_readings,
        reading_count=64,
        timestamp=1704067200000000,
        device_name=b"Large Sensor Array Device"
    )


def create_large_2() -> LargePayloadMessage2:
    large_data = bytes([(i % 256) for i in range(280)])
    return LargePayloadMessage2(
        large_data=large_data
    )


def create_ext_var_single_empty() -> ExtendedVariableSingleArray:
    return ExtendedVariableSingleArray(
        timestamp=0x0000000000000001, telemetry_data=[], crc=0x00000001
    )


def create_ext_var_single_single() -> ExtendedVariableSingleArray:
    return ExtendedVariableSingleArray(
        timestamp=0x0000000000000002, telemetry_data=[42], crc=0x00000002
    )


def create_ext_var_single_third() -> ExtendedVariableSingleArray:
    return ExtendedVariableSingleArray(
        timestamp=0x0000000000000003, telemetry_data=list(range(83)), crc=0x00000003
    )


def create_ext_var_single_almost() -> ExtendedVariableSingleArray:
    return ExtendedVariableSingleArray(
        timestamp=0x0000000000000004, telemetry_data=list(range(249)), crc=0x00000004
    )


def create_ext_var_single_full() -> ExtendedVariableSingleArray:
    return ExtendedVariableSingleArray(
        timestamp=0x0000000000000005, telemetry_data=list(range(250)), crc=0x00000005
    )


# ============================================================================
# get_message(index) - unified interface matching C++ MessageProvider pattern
# ============================================================================

def get_message(index: int) -> MessageType:
    """Get message by index."""
    if index == 0:
        return create_ext_id_1()
    elif index == 1:
        return create_ext_id_2()
    elif index == 2:
        return create_ext_id_3()
    elif index == 3:
        return create_ext_id_4()
    elif index == 4:
        return create_ext_id_5()
    elif index == 5:
        return create_ext_id_6()
    elif index == 6:
        return create_ext_id_7()
    elif index == 7:
        return create_ext_id_8()
    elif index == 8:
        return create_ext_id_9()
    elif index == 9:
        return create_ext_id_10()
    elif index == 10:
        return create_large_1()
    elif index == 11:
        return create_large_2()
    elif index == 12:
        return create_ext_var_single_empty()
    elif index == 13:
        return create_ext_var_single_single()
    elif index == 14:
        return create_ext_var_single_third()
    elif index == 15:
        return create_ext_var_single_almost()
    else:  # index == 16
        return create_ext_var_single_full()


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
