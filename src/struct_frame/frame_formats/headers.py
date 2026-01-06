"""
Header definitions for frame formats.

Each header defines the start byte pattern used for frame synchronization.
"""

from .base import HeaderType, HeaderDefinition, BASIC_START_BYTE, PAYLOAD_TYPE_BASE
from .base import UBX_SYNC1, UBX_SYNC2, MAVLINK_V1_STX, MAVLINK_V2_STX


# Header None - No start bytes
# Relies on external synchronization (e.g., message length from lower layer)
HEADER_NONE = HeaderDefinition(
    header_type=HeaderType.NONE,
    name="None",
    start_bytes=[],
    num_start_bytes=0,
    encodes_payload_type=False,
    payload_type_byte_index=-1,
    description="No start bytes. Relies on external synchronization."
)


# Header Tiny - 1 start byte encoding payload type
# Start byte = 0x70 + PayloadType value
HEADER_TINY = HeaderDefinition(
    header_type=HeaderType.TINY,
    name="Tiny",
    start_bytes=[],  # Variable based on payload type
    num_start_bytes=1,
    encodes_payload_type=True,
    payload_type_byte_index=0,
    description="1 start byte [0x70+PayloadType]. Minimal overhead."
)


# Header Basic - 2 start bytes
# Start byte 1 = 0x90 (fixed)
# Start byte 2 = 0x70 + PayloadType value
HEADER_BASIC = HeaderDefinition(
    header_type=HeaderType.BASIC,
    name="Basic",
    start_bytes=[BASIC_START_BYTE],  # First byte is fixed, second varies
    num_start_bytes=2,
    encodes_payload_type=True,
    payload_type_byte_index=1,
    description="2 start bytes [0x90] [0x70+PayloadType]. Standard framing."
)


# Header UBX - u-blox GPS/GNSS protocol
# 2 fixed start bytes: 0xB5, 0x62
HEADER_UBX = HeaderDefinition(
    header_type=HeaderType.UBX,
    name="UBX",
    start_bytes=[UBX_SYNC1, UBX_SYNC2],
    num_start_bytes=2,
    encodes_payload_type=False,
    payload_type_byte_index=-1,
    description="u-blox GPS/GNSS protocol. 2 start bytes [0xB5] [0x62]."
)


# Header MAVLink V1 - Classic drone protocol
# 1 fixed start byte: 0xFE
HEADER_MAVLINK_V1 = HeaderDefinition(
    header_type=HeaderType.MAVLINK_V1,
    name="MavlinkV1",
    start_bytes=[MAVLINK_V1_STX],
    num_start_bytes=1,
    encodes_payload_type=False,
    payload_type_byte_index=-1,
    description="MAVLink V1 protocol. 1 start byte [0xFE]."
)


# Header MAVLink V2 - Modern drone protocol
# 1 fixed start byte: 0xFD
HEADER_MAVLINK_V2 = HeaderDefinition(
    header_type=HeaderType.MAVLINK_V2,
    name="MavlinkV2",
    start_bytes=[MAVLINK_V2_STX],
    num_start_bytes=1,
    encodes_payload_type=False,
    payload_type_byte_index=-1,
    description="MAVLink V2 protocol. 1 start byte [0xFD]."
)


# Registry of all header definitions
HEADER_DEFINITIONS = {
    HeaderType.NONE: HEADER_NONE,
    HeaderType.TINY: HEADER_TINY,
    HeaderType.BASIC: HEADER_BASIC,
    HeaderType.UBX: HEADER_UBX,
    HeaderType.MAVLINK_V1: HEADER_MAVLINK_V1,
    HeaderType.MAVLINK_V2: HEADER_MAVLINK_V2,
}


def get_header(header_type: HeaderType) -> HeaderDefinition:
    """Get header definition by type"""
    return HEADER_DEFINITIONS[header_type]
