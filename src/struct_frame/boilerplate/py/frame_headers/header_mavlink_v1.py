# Header Mavlink V1
# Format: [0xFE]

from .base import HeaderType, HeaderConfig, MAVLINK_V1_STX

HEADER_MAVLINK_V1_CONFIG = HeaderConfig(
    header_type=HeaderType.MAVLINK_V1,
    name="MavlinkV1",
    start_bytes=[MAVLINK_V1_STX],
    num_start_bytes=1,
    encodes_payload_type=False,
    payload_type_byte_index=-1,
    description="1 start byte [0xFE] - MAVLink v1 protocol"
)


def is_mavlink_v1_stx(byte: int) -> bool:
    """Check if byte is MAVLink v1 start byte"""
    return byte == MAVLINK_V1_STX
