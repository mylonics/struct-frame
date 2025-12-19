# Payload Default
# Format: [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
# 1-byte length, 2-byte CRC. Standard format.

from .base import PayloadType, PayloadConfig

PAYLOAD_DEFAULT_CONFIG = PayloadConfig(
    payload_type=PayloadType.DEFAULT,
    name="Default",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=1,
    has_sequence=False,
    has_system_id=False,
    has_component_id=False,
    has_package_id=False,
    description="[LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Standard format with 1-byte length and CRC."
)
