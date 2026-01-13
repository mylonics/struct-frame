# Frame Headers - Start byte patterns and header configurations (Python)
# Header types define start byte patterns and header-specific parsing

from enum import Enum
from dataclasses import dataclass
from typing import List


class HeaderType(Enum):
    """Header types defining start byte patterns"""
    NONE = 0       # No start bytes
    TINY = 1       # 1 start byte [0x70+PayloadType]
    BASIC = 2      # 2 start bytes [0x90] [0x70+PayloadType]
    UBX = 3        # 2 start bytes [0xB5] [0x62]
    MAVLINK_V1 = 4 # 1 start byte [0xFE]
    MAVLINK_V2 = 5 # 1 start byte [0xFD]


# Constants used across headers
BASIC_START_BYTE = 0x90
PAYLOAD_TYPE_BASE = 0x70  # Payload type encoded as 0x70 + PayloadType.value
UBX_SYNC1 = 0xB5
UBX_SYNC2 = 0x62
MAVLINK_V1_STX = 0xFE
MAVLINK_V2_STX = 0xFD
MAX_PAYLOAD_TYPE = 8


@dataclass
class HeaderConfig:
    """Configuration for a header type"""
    header_type: HeaderType
    name: str
    start_bytes: List[int]  # Fixed start bytes (empty for dynamic)
    num_start_bytes: int
    encodes_payload_type: bool  # True if start byte encodes payload type
    payload_type_byte_index: int  # Which byte encodes payload type (-1 if none)
    description: str

    @property
    def is_fixed(self) -> bool:
        """True if all start bytes are fixed values"""
        return len(self.start_bytes) == self.num_start_bytes and not self.encodes_payload_type


# =============================================================================
# Header Configurations
# =============================================================================

HEADER_NONE_CONFIG = HeaderConfig(
    header_type=HeaderType.NONE,
    name="None",
    start_bytes=[],
    num_start_bytes=0,
    encodes_payload_type=False,
    payload_type_byte_index=-1,
    description="No start bytes - relies on external synchronization"
)

HEADER_TINY_CONFIG = HeaderConfig(
    header_type=HeaderType.TINY,
    name="Tiny",
    start_bytes=[],  # Dynamic - depends on payload type
    num_start_bytes=1,
    encodes_payload_type=True,
    payload_type_byte_index=0,
    description="1 start byte [0x70+PayloadType] - compact framing"
)

HEADER_BASIC_CONFIG = HeaderConfig(
    header_type=HeaderType.BASIC,
    name="Basic",
    start_bytes=[BASIC_START_BYTE],  # First byte is fixed
    num_start_bytes=2,
    encodes_payload_type=True,
    payload_type_byte_index=1,  # Second byte encodes payload type
    description="2 start bytes [0x90] [0x70+PayloadType] - standard framing"
)

HEADER_UBX_CONFIG = HeaderConfig(
    header_type=HeaderType.UBX,
    name="UBX",
    start_bytes=[UBX_SYNC1, UBX_SYNC2],
    num_start_bytes=2,
    encodes_payload_type=False,
    payload_type_byte_index=-1,
    description="2 start bytes [0xB5] [0x62] - u-blox GPS/GNSS protocol"
)

HEADER_MAVLINK_V1_CONFIG = HeaderConfig(
    header_type=HeaderType.MAVLINK_V1,
    name="MavlinkV1",
    start_bytes=[MAVLINK_V1_STX],
    num_start_bytes=1,
    encodes_payload_type=False,
    payload_type_byte_index=-1,
    description="1 start byte [0xFE] - MAVLink v1 protocol"
)

HEADER_MAVLINK_V2_CONFIG = HeaderConfig(
    header_type=HeaderType.MAVLINK_V2,
    name="MavlinkV2",
    start_bytes=[MAVLINK_V2_STX],
    num_start_bytes=1,
    encodes_payload_type=False,
    payload_type_byte_index=-1,
    description="1 start byte [0xFD] - MAVLink v2 protocol"
)


# Registry of all header configurations
HEADER_CONFIGS = {
    HeaderType.NONE: HEADER_NONE_CONFIG,
    HeaderType.TINY: HEADER_TINY_CONFIG,
    HeaderType.BASIC: HEADER_BASIC_CONFIG,
    HeaderType.UBX: HEADER_UBX_CONFIG,
    HeaderType.MAVLINK_V1: HEADER_MAVLINK_V1_CONFIG,
    HeaderType.MAVLINK_V2: HEADER_MAVLINK_V2_CONFIG,
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_tiny_start_byte(payload_type_value: int) -> int:
    """Get the start byte for a Tiny frame with given payload type"""
    return PAYLOAD_TYPE_BASE + payload_type_value


def is_tiny_start_byte(byte: int) -> bool:
    """Check if byte is a valid Tiny frame start byte"""
    return PAYLOAD_TYPE_BASE <= byte <= PAYLOAD_TYPE_BASE + MAX_PAYLOAD_TYPE


def get_payload_type_from_tiny(byte: int) -> int:
    """Extract payload type value from Tiny start byte"""
    return byte - PAYLOAD_TYPE_BASE


def get_basic_start_bytes(payload_type_value: int) -> tuple:
    """Get start bytes for a Basic frame with given payload type"""
    return (BASIC_START_BYTE, PAYLOAD_TYPE_BASE + payload_type_value)


def is_basic_first_byte(byte: int) -> bool:
    """Check if byte is the Basic frame first start byte"""
    return byte == BASIC_START_BYTE


def is_basic_second_byte(byte: int) -> bool:
    """Check if byte is a valid Basic frame second start byte"""
    return PAYLOAD_TYPE_BASE <= byte <= PAYLOAD_TYPE_BASE + MAX_PAYLOAD_TYPE


def get_payload_type_from_basic(second_byte: int) -> int:
    """Extract payload type value from Basic second start byte"""
    return second_byte - PAYLOAD_TYPE_BASE


def is_ubx_sync1(byte: int) -> bool:
    """Check if byte is UBX first sync byte"""
    return byte == UBX_SYNC1


def is_ubx_sync2(byte: int) -> bool:
    """Check if byte is UBX second sync byte"""
    return byte == UBX_SYNC2


def is_mavlink_v1_stx(byte: int) -> bool:
    """Check if byte is MAVLink v1 start byte"""
    return byte == MAVLINK_V1_STX


def is_mavlink_v2_stx(byte: int) -> bool:
    """Check if byte is MAVLink v2 start byte"""
    return byte == MAVLINK_V2_STX
