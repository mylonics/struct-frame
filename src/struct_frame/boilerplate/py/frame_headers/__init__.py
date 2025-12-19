# Frame Header Types
# Each header type defines start byte patterns for frame synchronization

from .base import (
    HeaderType, HeaderConfig,
    BASIC_START_BYTE, PAYLOAD_TYPE_BASE,
    UBX_SYNC1, UBX_SYNC2,
    MAVLINK_V1_STX, MAVLINK_V2_STX
)
from .header_none import HEADER_NONE_CONFIG
from .header_tiny import HEADER_TINY_CONFIG, is_tiny_start_byte, get_payload_type_from_tiny
from .header_basic import HEADER_BASIC_CONFIG
from .header_ubx import HEADER_UBX_CONFIG
from .header_mavlink_v1 import HEADER_MAVLINK_V1_CONFIG
from .header_mavlink_v2 import HEADER_MAVLINK_V2_CONFIG

# Registry of all header configurations
HEADER_CONFIGS = {
    HeaderType.NONE: HEADER_NONE_CONFIG,
    HeaderType.TINY: HEADER_TINY_CONFIG,
    HeaderType.BASIC: HEADER_BASIC_CONFIG,
    HeaderType.UBX: HEADER_UBX_CONFIG,
    HeaderType.MAVLINK_V1: HEADER_MAVLINK_V1_CONFIG,
    HeaderType.MAVLINK_V2: HEADER_MAVLINK_V2_CONFIG,
}

__all__ = [
    'HeaderType',
    'HeaderConfig',
    'BASIC_START_BYTE',
    'PAYLOAD_TYPE_BASE',
    'UBX_SYNC1',
    'UBX_SYNC2',
    'MAVLINK_V1_STX',
    'MAVLINK_V2_STX',
    'HEADER_CONFIGS',
    'HEADER_NONE_CONFIG',
    'HEADER_TINY_CONFIG',
    'HEADER_BASIC_CONFIG',
    'HEADER_UBX_CONFIG',
    'HEADER_MAVLINK_V1_CONFIG',
    'HEADER_MAVLINK_V2_CONFIG',
    'is_tiny_start_byte',
    'get_payload_type_from_tiny',
]
