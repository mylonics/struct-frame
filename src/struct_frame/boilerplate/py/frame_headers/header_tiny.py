# Header Tiny - 1 start byte encoding payload type
# Format: [0x70+PayloadType]

from .base import HeaderType, HeaderConfig, PAYLOAD_TYPE_BASE

HEADER_TINY_CONFIG = HeaderConfig(
    header_type=HeaderType.TINY,
    name="Tiny",
    start_bytes=[],  # Dynamic - depends on payload type
    num_start_bytes=1,
    encodes_payload_type=True,
    payload_type_byte_index=0,
    description="1 start byte [0x70+PayloadType] - compact framing"
)


def get_tiny_start_byte(payload_type_value: int) -> int:
    """Get the start byte for a Tiny frame with given payload type"""
    return PAYLOAD_TYPE_BASE + payload_type_value


def is_tiny_start_byte(byte: int) -> bool:
    """Check if byte is a valid Tiny frame start byte"""
    from ..payload_types.base import MAX_PAYLOAD_TYPE
    return PAYLOAD_TYPE_BASE <= byte <= PAYLOAD_TYPE_BASE + MAX_PAYLOAD_TYPE


def get_payload_type_from_tiny(byte: int) -> int:
    """Extract payload type value from Tiny start byte"""
    return byte - PAYLOAD_TYPE_BASE
