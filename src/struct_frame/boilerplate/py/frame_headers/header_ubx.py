# Header UBX - u-blox GPS/GNSS protocol
# Format: [0xB5] [0x62]

from .base import HeaderType, HeaderConfig, UBX_SYNC1, UBX_SYNC2

HEADER_UBX_CONFIG = HeaderConfig(
    header_type=HeaderType.UBX,
    name="UBX",
    start_bytes=[UBX_SYNC1, UBX_SYNC2],
    num_start_bytes=2,
    encodes_payload_type=False,
    payload_type_byte_index=-1,
    description="2 start bytes [0xB5] [0x62] - u-blox GPS/GNSS protocol"
)


def is_ubx_sync1(byte: int) -> bool:
    """Check if byte is UBX first sync byte"""
    return byte == UBX_SYNC1


def is_ubx_sync2(byte: int) -> bool:
    """Check if byte is UBX second sync byte"""
    return byte == UBX_SYNC2
