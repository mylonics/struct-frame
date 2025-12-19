# Payload Extended Length
# Format: [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2]
# 2-byte length for payloads up to 65535 bytes.

from .base import PayloadType, PayloadConfig

PAYLOAD_EXTENDED_LENGTH_CONFIG = PayloadConfig(
    payload_type=PayloadType.EXTENDED_LENGTH,
    name="ExtendedLength",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=2,
    has_sequence=False,
    has_system_id=False,
    has_component_id=False,
    has_package_id=False,
    description="[LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2] - 2-byte length for large payloads."
)
