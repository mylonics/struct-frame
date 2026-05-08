#!/usr/bin/env python3
"""
Extended test message definitions (Python).
Three representative extended IDs (boundary/mid/high) + two large-payload
messages + five variable-array fill levels = 10 total.
"""

import sys
import os
from typing import Union

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'generated', 'py'))

from struct_frame.generated.extended_test import (
    ExtendedIdMessage2,
    ExtendedIdMessage9,
    ExtendedIdMessage10,
    LargePayloadMessage1,
    LargePayloadMessage2,
    ExtendedVariableSingleArray,
    get_message_info,
)

MessageType = Union[
    ExtendedIdMessage10,
    ExtendedIdMessage2,
    ExtendedIdMessage9,
    LargePayloadMessage1,
    LargePayloadMessage2,
    ExtendedVariableSingleArray,
]

MESSAGE_COUNT = 10


# ============================================================================
# Helper functions to create messages
# ============================================================================

def create_ext_id_10() -> ExtendedIdMessage10:
    return ExtendedIdMessage10(
        small_value=256,
        short_text=b"Boundary Test",
        flag=True
    )


def create_ext_id_2() -> ExtendedIdMessage2:
    return ExtendedIdMessage2(
        sensor_id=-42,
        reading=2.718281828,
        status_code=50000,
        description=b"Extended ID test message 2"
    )


def create_ext_id_9() -> ExtendedIdMessage9:
    return ExtendedIdMessage9(
        big_number=-9223372036854775807,
        big_unsigned=18446744073709551615,
        precision_value=1.7976931348623157e+308
    )


def create_large_1() -> LargePayloadMessage1:
    return LargePayloadMessage1(
        sensor_readings=[float(i + 1) for i in range(64)],
        reading_count=64,
        timestamp=1704067200000000,
        device_name=b"Large Sensor Array Device"
    )


def create_large_2() -> LargePayloadMessage2:
    return LargePayloadMessage2(
        large_data=bytes([(i % 256) for i in range(280)])
    )


def _ext_var(ts: int, data: list, crc: int) -> ExtendedVariableSingleArray:
    return ExtendedVariableSingleArray(timestamp=ts, telemetry_data=data, crc=crc)


# ============================================================================
# get_message(index) - unified interface
# Order: ExtendedId10, ExtendedId2, ExtendedId9, Large1, Large2, Var×5
# ============================================================================

def get_message(index: int) -> MessageType:
    if index == 0:
        return create_ext_id_10()
    elif index == 1:
        return create_ext_id_2()
    elif index == 2:
        return create_ext_id_9()
    elif index == 3:
        return create_large_1()
    elif index == 4:
        return create_large_2()
    elif index == 5:
        return _ext_var(0x0000000000000001, [],           0x00000001)
    elif index == 6:
        return _ext_var(0x0000000000000002, [42],         0x00000002)
    elif index == 7:
        return _ext_var(0x0000000000000003, list(range(83)),  0x00000003)
    elif index == 8:
        return _ext_var(0x0000000000000004, list(range(249)), 0x00000004)
    else:
        return _ext_var(0x0000000000000005, list(range(250)), 0x00000005)


# ============================================================================
# check_message(index, info) - validates decoded message matches expected
# ============================================================================

def check_message(index: int, info) -> bool:
    expected = get_message(index)
    cls = type(expected)
    if info.msg_id != cls.MSG_ID:
        return False
    decoded = cls.deserialize(info)
    return decoded == expected
