# Header Mavlink V2
# Format: [0xFD]

from .base import HeaderType, HeaderConfig, MAVLINK_V2_STX

HEADER_MAVLINK_V2_CONFIG = HeaderConfig(
    header_type=HeaderType.MAVLINK_V2,
    name="MavlinkV2",
    start_bytes=[MAVLINK_V2_STX],
    num_start_bytes=1,
    encodes_payload_type=False,
    payload_type_byte_index=-1,
    description="1 start byte [0xFD] - MAVLink v2 protocol"
)


def is_mavlink_v2_stx(byte: int) -> bool:
    """Check if byte is MAVLink v2 start byte"""
    return byte == MAVLINK_V2_STX
