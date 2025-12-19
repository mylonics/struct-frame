# Header None - No start bytes
# Relies on external synchronization

from .base import HeaderType, HeaderConfig

HEADER_NONE_CONFIG = HeaderConfig(
    header_type=HeaderType.NONE,
    name="None",
    start_bytes=[],
    num_start_bytes=0,
    encodes_payload_type=False,
    payload_type_byte_index=-1,
    description="No start bytes - relies on external synchronization"
)
