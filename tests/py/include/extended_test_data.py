#!/usr/bin/env python3
"""
Extended test message data definitions (Python).
Hardcoded test messages for extended message ID and payload testing.

This module follows the same pattern as C++ extended_test_data.hpp, providing:
1. Message getter functions (one per message type)
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


def create_ext_var_single(timestamp: int, telemetry_data: List[int], crc: int) -> ExtendedTestExtendedVariableSingleArray:
    """Create an ExtendedVariableSingleArray message."""
    return ExtendedTestExtendedVariableSingleArray(
        timestamp=timestamp,
        telemetry_data=telemetry_data,
        crc=crc
    )


# ============================================================================
# Message getters - return cached instances (like C++ static functions)
# ============================================================================

_message_cache = {}


def get_message_ext_1() -> ExtendedTestExtendedIdMessage1:
    if 1 not in _message_cache:
        _message_cache[1] = create_ext_id_1()
    return _message_cache[1]


def get_message_ext_2() -> ExtendedTestExtendedIdMessage2:
    if 2 not in _message_cache:
        _message_cache[2] = create_ext_id_2()
    return _message_cache[2]


def get_message_ext_3() -> ExtendedTestExtendedIdMessage3:
    if 3 not in _message_cache:
        _message_cache[3] = create_ext_id_3()
    return _message_cache[3]


def get_message_ext_4() -> ExtendedTestExtendedIdMessage4:
    if 4 not in _message_cache:
        _message_cache[4] = create_ext_id_4()
    return _message_cache[4]


def get_message_ext_5() -> ExtendedTestExtendedIdMessage5:
    if 5 not in _message_cache:
        _message_cache[5] = create_ext_id_5()
    return _message_cache[5]


def get_message_ext_6() -> ExtendedTestExtendedIdMessage6:
    if 6 not in _message_cache:
        _message_cache[6] = create_ext_id_6()
    return _message_cache[6]


def get_message_ext_7() -> ExtendedTestExtendedIdMessage7:
    if 7 not in _message_cache:
        _message_cache[7] = create_ext_id_7()
    return _message_cache[7]


def get_message_ext_8() -> ExtendedTestExtendedIdMessage8:
    if 8 not in _message_cache:
        _message_cache[8] = create_ext_id_8()
    return _message_cache[8]


def get_message_ext_9() -> ExtendedTestExtendedIdMessage9:
    if 9 not in _message_cache:
        _message_cache[9] = create_ext_id_9()
    return _message_cache[9]


def get_message_ext_10() -> ExtendedTestExtendedIdMessage10:
    if 10 not in _message_cache:
        _message_cache[10] = create_ext_id_10()
    return _message_cache[10]


def get_message_large_1() -> ExtendedTestLargePayloadMessage1:
    if 11 not in _message_cache:
        _message_cache[11] = create_large_1()
    return _message_cache[11]


def get_message_large_2() -> ExtendedTestLargePayloadMessage2:
    if 12 not in _message_cache:
        _message_cache[12] = create_large_2()
    return _message_cache[12]


def get_ext_var_single_messages() -> List[ExtendedTestExtendedVariableSingleArray]:
    """Get ExtendedVariableSingleArray array (5 messages with different fill levels).
    
    Fill levels for max_size=250:
    - Empty (0 elements)
    - Single element (1 element)
    - One-third filled (83 elements)
    - One position empty (249 elements)
    - Full (250 elements)
    """
    if 'ext_var_single' not in _message_cache:
        _message_cache['ext_var_single'] = [
            # Empty payload (0 elements)
            create_ext_var_single(0x0000000000000001, [], 0x00000001),
            # Single element
            create_ext_var_single(0x0000000000000002, [42], 0x00000002),
            # One-third filled (83 elements for max_size=250)
            create_ext_var_single(0x0000000000000003, list(range(83)), 0x00000003),
            # One position empty (249 elements)
            create_ext_var_single(0x0000000000000004, list(range(249)), 0x00000004),
            # Full (250 elements)
            create_ext_var_single(0x0000000000000005, list(range(250)), 0x00000005),
        ]
    return _message_cache['ext_var_single']


# ============================================================================
# Message ID order array - defines the encode/decode sequence
# ============================================================================

MESSAGE_COUNT = 17


def get_msg_id_order() -> List[int]:
    """Get the message ID order array (maps position to msg_id)."""
    return [
        ExtendedTestExtendedIdMessage1.MSG_ID,    # 0
        ExtendedTestExtendedIdMessage2.MSG_ID,    # 1
        ExtendedTestExtendedIdMessage3.MSG_ID,    # 2
        ExtendedTestExtendedIdMessage4.MSG_ID,    # 3
        ExtendedTestExtendedIdMessage5.MSG_ID,    # 4
        ExtendedTestExtendedIdMessage6.MSG_ID,    # 5
        ExtendedTestExtendedIdMessage7.MSG_ID,    # 6
        ExtendedTestExtendedIdMessage8.MSG_ID,    # 7
        ExtendedTestExtendedIdMessage9.MSG_ID,    # 8
        ExtendedTestExtendedIdMessage10.MSG_ID,   # 9
        ExtendedTestLargePayloadMessage1.MSG_ID,  # 10
        ExtendedTestLargePayloadMessage2.MSG_ID,  # 11
        ExtendedTestExtendedVariableSingleArray.MSG_ID,  # 12: empty
        ExtendedTestExtendedVariableSingleArray.MSG_ID,  # 13: single
        ExtendedTestExtendedVariableSingleArray.MSG_ID,  # 14: 1/3 filled
        ExtendedTestExtendedVariableSingleArray.MSG_ID,  # 15: one empty
        ExtendedTestExtendedVariableSingleArray.MSG_ID,  # 16: full
    ]


# ============================================================================
# Encoder helper - writes messages by msg_id lookup (like C++)
# For variable messages, tracks indices since we have multiple instances
# ============================================================================

class Encoder:
    """Encoder that writes messages by msg_id lookup with index tracking for variable messages."""
    
    def __init__(self):
        self.ext_var_single_idx = 0
        self._ext_var_single_msgs = get_ext_var_single_messages()
    
    def write_message(self, writer, msg_id: int) -> int:
        """Write a message to the writer based on msg_id. Returns bytes written."""
        # Handle variable messages with index tracking
        if msg_id == ExtendedTestExtendedVariableSingleArray.MSG_ID:
            msg = self._ext_var_single_msgs[self.ext_var_single_idx]
            self.ext_var_single_idx += 1
            return writer.write(msg)
        
        # Handle fixed messages (single instance per type)
        msg_getters = {
            ExtendedTestExtendedIdMessage1.MSG_ID: get_message_ext_1,
            ExtendedTestExtendedIdMessage2.MSG_ID: get_message_ext_2,
            ExtendedTestExtendedIdMessage3.MSG_ID: get_message_ext_3,
            ExtendedTestExtendedIdMessage4.MSG_ID: get_message_ext_4,
            ExtendedTestExtendedIdMessage5.MSG_ID: get_message_ext_5,
            ExtendedTestExtendedIdMessage6.MSG_ID: get_message_ext_6,
            ExtendedTestExtendedIdMessage7.MSG_ID: get_message_ext_7,
            ExtendedTestExtendedIdMessage8.MSG_ID: get_message_ext_8,
            ExtendedTestExtendedIdMessage9.MSG_ID: get_message_ext_9,
            ExtendedTestExtendedIdMessage10.MSG_ID: get_message_ext_10,
            ExtendedTestLargePayloadMessage1.MSG_ID: get_message_large_1,
            ExtendedTestLargePayloadMessage2.MSG_ID: get_message_large_2,
        }
        
        getter = msg_getters.get(msg_id)
        if getter:
            return writer.write(getter())
        return 0


# ============================================================================
# Validator helper - validates decoded messages against expected data (like C++)
# For variable messages, tracks indices since we have multiple instances
# ============================================================================

class Validator:
    """Validator that returns expected message data and validates using __eq__."""
    
    def __init__(self):
        self.ext_var_single_idx = 0
        self._ext_var_single_msgs = get_ext_var_single_messages()
        self._msg_getters = {
            ExtendedTestExtendedIdMessage1.MSG_ID: get_message_ext_1,
            ExtendedTestExtendedIdMessage2.MSG_ID: get_message_ext_2,
            ExtendedTestExtendedIdMessage3.MSG_ID: get_message_ext_3,
            ExtendedTestExtendedIdMessage4.MSG_ID: get_message_ext_4,
            ExtendedTestExtendedIdMessage5.MSG_ID: get_message_ext_5,
            ExtendedTestExtendedIdMessage6.MSG_ID: get_message_ext_6,
            ExtendedTestExtendedIdMessage7.MSG_ID: get_message_ext_7,
            ExtendedTestExtendedIdMessage8.MSG_ID: get_message_ext_8,
            ExtendedTestExtendedIdMessage9.MSG_ID: get_message_ext_9,
            ExtendedTestExtendedIdMessage10.MSG_ID: get_message_ext_10,
            ExtendedTestLargePayloadMessage1.MSG_ID: get_message_large_1,
            ExtendedTestLargePayloadMessage2.MSG_ID: get_message_large_2,
        }
        self._msg_classes = {
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
    
    def get_expected(self, msg_id: int) -> Tuple[Optional[bytes], Optional[int]]:
        """Get expected message data for validation. Returns (data, size)."""
        # Handle variable messages with index tracking
        if msg_id == ExtendedTestExtendedVariableSingleArray.MSG_ID:
            msg = self._ext_var_single_msgs[self.ext_var_single_idx]
            self.ext_var_single_idx += 1
            data = msg.serialize()
            return data, len(data)
        
        getter = self._msg_getters.get(msg_id)
        if getter:
            msg = getter()
            data = msg.serialize()
            return data, len(data)
        return None, None

    def validate_with_equals(self, frame_info) -> bool:
        """Validate decoded message using __eq__ operator.
        
        Note: We unpack the expected message's packed data to ensure both messages
        have been through string padding conversion, making equality comparison valid.
        """
        msg_id = frame_info.msg_id
        decoded_data = frame_info
        msg_class = self._msg_classes.get(msg_id)
        if not msg_class:
            return False
        
        # Handle variable messages with index tracking
        if msg_id == ExtendedTestExtendedVariableSingleArray.MSG_ID:
            expected = self._ext_var_single_msgs[self.ext_var_single_idx]
            self.ext_var_single_idx += 1
            expected_unpacked = ExtendedTestExtendedVariableSingleArray.deserialize(expected.serialize())
            decoded = ExtendedTestExtendedVariableSingleArray.deserialize(decoded_data)
            return decoded == expected_unpacked
        
        getter = self._msg_getters.get(msg_id)
        if getter:
            expected = getter()
            expected_unpacked = msg_class.deserialize(expected.serialize())
            decoded = msg_class.deserialize(decoded_data)
            return decoded == expected_unpacked
        return False


# ============================================================================
# Test configuration - provides all data for TestCodec templates (like C++ Config)
# ============================================================================

class Config:
    """Test configuration for extended messages."""
    MESSAGE_COUNT = MESSAGE_COUNT
    BUFFER_SIZE = 8192  # Larger for extended payloads
    FORMATS_HELP = "profile_bulk, profile_network"
    TEST_NAME = "Python Extended"
    
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
    def get_message_info(msg_id: int):
        return get_message_info(msg_id)
    
    @staticmethod
    def supports_format(format_name: str) -> bool:
        return format_name in ['profile_bulk', 'profile_network']


# Export config instance for convenience
extended_test_config = Config
