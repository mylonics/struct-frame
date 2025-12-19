# Payload Extended Message IDs
# Format: [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
# Adds package ID for message namespace separation.

from .base import PayloadType, PayloadConfig

PAYLOAD_EXTENDED_MSG_IDS_CONFIG = PayloadConfig(
    payload_type=PayloadType.EXTENDED_MSG_IDS,
    name="ExtendedMsgIds",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=1,
    has_sequence=False,
    has_system_id=False,
    has_component_id=False,
    has_package_id=True,
    description="[LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] - Adds package ID for namespacing."
)
