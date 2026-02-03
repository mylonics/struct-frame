#!/usr/bin/env python3
"""
Extended test message data definitions (Python).
Hardcoded test messages for extended message ID and payload testing.

This module follows the C++ test pattern with a unified get_message(index) interface.
The get_message() function returns a message based on index, matching the C++ approach.
"""

import sys
import os
from typing import List, Union

# Add generated directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'generated', 'py'))

from struct_frame.generated.extended_test import (
    ExtendedTestExtendedIdMessage1,
    ExtendedTestExtendedIdMessage2,
    ExtendedTestExtendedIdMessage3,
    ExtendedTestExtendedIdMessage4,
    ExtendedTestExtendedIdMessage5,
    ExtendedTestExtendedIdMessage6,
    ExtendedTestExtendedIdMessage7,
    ExtendedTestExtendedIdMessage8,
    ExtendedTestExtendedIdMessage9,
    ExtendedTestExtendedIdMessage10,
    ExtendedTestLargePayloadMessage1,
    ExtendedTestLargePayloadMessage2,
    ExtendedTestExtendedVariableSingleArray,
    get_message_info,
)

# Type alias for message union (like C++ MessageVariant)
MessageType = Union[
    ExtendedTestExtendedIdMessage1,
    ExtendedTestExtendedIdMessage2,
    ExtendedTestExtendedIdMessage3,
    ExtendedTestExtendedIdMessage4,
    ExtendedTestExtendedIdMessage5,
    ExtendedTestExtendedIdMessage6,
    ExtendedTestExtendedIdMessage7,
    ExtendedTestExtendedIdMessage8,
    ExtendedTestExtendedIdMessage9,
    ExtendedTestExtendedIdMessage10,
    ExtendedTestLargePayloadMessage1,
    ExtendedTestLargePayloadMessage2,
    ExtendedTestExtendedVariableSingleArray,
]

# ============================================================================
# Message count and supported profiles
# ============================================================================

MESSAGE_COUNT = 17
PROFILES = "bulk, network"


# ============================================================================
# Helper functions to create messages (like C++ create_* functions)
# ============================================================================

def create_ext_id_1() -> ExtendedTestExtendedIdMessage1:
    return ExtendedTestExtendedIdMessage1(
        sequence_number=12345678,
        label=b"Test Label Extended 1",
        value=3.14159,
        enabled=True
    )


def create_ext_id_2() -> ExtendedTestExtendedIdMessage2:
    return ExtendedTestExtendedIdMessage2(
        sensor_id=-42,
        reading=2.718281828,
        status_code=50000,
        description=b"Extended ID test message 2"
    )


def create_ext_id_3() -> ExtendedTestExtendedIdMessage3:
    return ExtendedTestExtendedIdMessage3(
        timestamp=1704067200000000,
        temperature=-40,
        humidity=85,
        location=b"Sensor Room A"
    )


def create_ext_id_4() -> ExtendedTestExtendedIdMessage4:
    return ExtendedTestExtendedIdMessage4(
        event_id=999999,
        event_type=42,
        event_time=1704067200000,
        event_data=b"Event payload with extended message ID"
    )


def create_ext_id_5() -> ExtendedTestExtendedIdMessage5:
    return ExtendedTestExtendedIdMessage5(
        x_position=100.5,
        y_position=-200.25,
        z_position=50.125,
        frame_number=1000000
    )


def create_ext_id_6() -> ExtendedTestExtendedIdMessage6:
    return ExtendedTestExtendedIdMessage6(
        command_id=-12345,
        parameter1=1000,
        parameter2=2000,
        acknowledged=False,
        command_name=b"CALIBRATE_SENSOR"
    )


def create_ext_id_7() -> ExtendedTestExtendedIdMessage7:
    return ExtendedTestExtendedIdMessage7(
        counter=4294967295,
        average=123.456789,
        minimum=-999.99,
        maximum=999.99
    )


def create_ext_id_8() -> ExtendedTestExtendedIdMessage8:
    return ExtendedTestExtendedIdMessage8(
        level=255,
        offset=-32768,
        duration=86400000,
        tag=b"TEST123"
    )


def create_ext_id_9() -> ExtendedTestExtendedIdMessage9:
    return ExtendedTestExtendedIdMessage9(
        big_number=-9223372036854775807,
        big_unsigned=18446744073709551615,
        precision_value=1.7976931348623157e+308
    )


def create_ext_id_10() -> ExtendedTestExtendedIdMessage10:
    return ExtendedTestExtendedIdMessage10(
        small_value=256,
        short_text=b"Boundary Test",
        flag=True
    )


def create_large_1() -> ExtendedTestLargePayloadMessage1:
    sensor_readings = [float(i + 1) for i in range(64)]
    return ExtendedTestLargePayloadMessage1(
        sensor_readings=sensor_readings,
        reading_count=64,
        timestamp=1704067200000000,
        device_name=b"Large Sensor Array Device"
    )


def create_large_2() -> ExtendedTestLargePayloadMessage2:
    large_data = bytes([(i % 256) for i in range(280)])
    return ExtendedTestLargePayloadMessage2(
        large_data=large_data
    )


def create_ext_var_single_empty() -> ExtendedTestExtendedVariableSingleArray:
    """Create ExtendedVariableSingleArray with empty payload."""
    return ExtendedTestExtendedVariableSingleArray(
        timestamp=0x0000000000000001, telemetry_data=[], crc=0x00000001
    )


def create_ext_var_single_single() -> ExtendedTestExtendedVariableSingleArray:
    """Create ExtendedVariableSingleArray with single element."""
    return ExtendedTestExtendedVariableSingleArray(
        timestamp=0x0000000000000002, telemetry_data=[42], crc=0x00000002
    )


def create_ext_var_single_third() -> ExtendedTestExtendedVariableSingleArray:
    """Create ExtendedVariableSingleArray with 1/3 filled (83 elements for max_size=250)."""
    return ExtendedTestExtendedVariableSingleArray(
        timestamp=0x0000000000000003, telemetry_data=list(range(83)), crc=0x00000003
    )


def create_ext_var_single_almost() -> ExtendedTestExtendedVariableSingleArray:
    """Create ExtendedVariableSingleArray with 249 elements."""
    return ExtendedTestExtendedVariableSingleArray(
        timestamp=0x0000000000000004, telemetry_data=list(range(249)), crc=0x00000004
    )


def create_ext_var_single_full() -> ExtendedTestExtendedVariableSingleArray:
    """Create ExtendedVariableSingleArray with full 250 elements."""
    return ExtendedTestExtendedVariableSingleArray(
        timestamp=0x0000000000000005, telemetry_data=list(range(250)), crc=0x00000005
    )


# ============================================================================
# Unified get_message(index) function - matches C++ MessageProvider pattern
# ============================================================================

def get_message(index: int) -> MessageType:
    """
    Get message by index - unified interface matching C++ get_message().
    
    Message order: ExtendedId1-10, LargePayload1-2, ExtendedVariableSingleArray x5
    """
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
# Message class lookup - maps message type to class for deserialization
# ============================================================================

MESSAGE_CLASSES = {
    ExtendedTestExtendedIdMessage1.MSG_ID: ExtendedTestExtendedIdMessage1,
    ExtendedTestExtendedIdMessage2.MSG_ID: ExtendedTestExtendedIdMessage2,
    ExtendedTestExtendedIdMessage3.MSG_ID: ExtendedTestExtendedIdMessage3,
    ExtendedTestExtendedIdMessage4.MSG_ID: ExtendedTestExtendedIdMessage4,
    ExtendedTestExtendedIdMessage5.MSG_ID: ExtendedTestExtendedIdMessage5,
    ExtendedTestExtendedIdMessage6.MSG_ID: ExtendedTestExtendedIdMessage6,
    ExtendedTestExtendedIdMessage7.MSG_ID: ExtendedTestExtendedIdMessage7,
    ExtendedTestExtendedIdMessage8.MSG_ID: ExtendedTestExtendedIdMessage8,
    ExtendedTestExtendedIdMessage9.MSG_ID: ExtendedTestExtendedIdMessage9,
    ExtendedTestExtendedIdMessage10.MSG_ID: ExtendedTestExtendedIdMessage10,
    ExtendedTestLargePayloadMessage1.MSG_ID: ExtendedTestLargePayloadMessage1,
    ExtendedTestLargePayloadMessage2.MSG_ID: ExtendedTestLargePayloadMessage2,
    ExtendedTestExtendedVariableSingleArray.MSG_ID: ExtendedTestExtendedVariableSingleArray,
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
        
        # Unpack both from packed bytes to ensure precision matches
        expected_unpacked = msg_class.deserialize(expected.serialize())
        decoded = msg_class.deserialize(frame_info)
        return decoded == expected_unpacked


# ============================================================================
# Test configuration - matches C++ TestHarness pattern
# ============================================================================

class Config:
    """Test configuration for extended messages."""
    MESSAGE_COUNT = MESSAGE_COUNT
    BUFFER_SIZE = 8192  # Larger for extended payloads
    FORMATS_HELP = PROFILES
    TEST_NAME = "Python Extended"
    
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
        return get_message_info(msg_id)
    
    @staticmethod
    def supports_format(format_name: str) -> bool:
        return format_name in ['bulk', 'network']


# Export config instance for convenience
extended_test_config = Config
