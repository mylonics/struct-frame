# Payload Extended
# Format: [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
# Extended message IDs + 2-byte length.

from .base import PayloadType, PayloadConfig

PAYLOAD_EXTENDED_CONFIG = PayloadConfig(
    payload_type=PayloadType.EXTENDED,
    name="Extended",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=2,
    has_sequence=False,
    has_system_id=False,
    has_component_id=False,
    has_package_id=True,
    description="[LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] - Extended IDs + 2-byte length."
)
