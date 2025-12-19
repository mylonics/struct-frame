# Header Basic - 2 start bytes
# Format: [0x90] [0x70+PayloadType]

from .base import HeaderType, HeaderConfig, BASIC_START_BYTE, PAYLOAD_TYPE_BASE

HEADER_BASIC_CONFIG = HeaderConfig(
    header_type=HeaderType.BASIC,
    name="Basic",
    start_bytes=[BASIC_START_BYTE],  # First byte is fixed
    num_start_bytes=2,
    encodes_payload_type=True,
    payload_type_byte_index=1,  # Second byte encodes payload type
    description="2 start bytes [0x90] [0x70+PayloadType] - standard framing"
)


def get_basic_start_bytes(payload_type_value: int) -> tuple:
    """Get start bytes for a Basic frame with given payload type"""
    return (BASIC_START_BYTE, PAYLOAD_TYPE_BASE + payload_type_value)


def is_basic_first_byte(byte: int) -> bool:
    """Check if byte is the Basic frame first start byte"""
    return byte == BASIC_START_BYTE


def is_basic_second_byte(byte: int) -> bool:
    """Check if byte is a valid Basic frame second start byte"""
    from ..payload_types.base import MAX_PAYLOAD_TYPE
    return PAYLOAD_TYPE_BASE <= byte <= PAYLOAD_TYPE_BASE + MAX_PAYLOAD_TYPE


def get_payload_type_from_basic(second_byte: int) -> int:
    """Extract payload type value from Basic second start byte"""
    return second_byte - PAYLOAD_TYPE_BASE
