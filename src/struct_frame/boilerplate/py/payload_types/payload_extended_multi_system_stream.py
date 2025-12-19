# Payload Extended Multi System Stream
# Format: [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
# Full featured format with all extensions.

from .base import PayloadType, PayloadConfig

PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG = PayloadConfig(
    payload_type=PayloadType.EXTENDED_MULTI_SYSTEM_STREAM,
    name="ExtendedMultiSystemStream",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=2,
    has_sequence=True,
    has_system_id=True,
    has_component_id=True,
    has_package_id=True,
    description="[SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] - Full-featured."
)
