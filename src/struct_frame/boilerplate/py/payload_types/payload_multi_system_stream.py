# Payload Multi System Stream
# Format: [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
# Combines Seq + SysComp for multi-system streaming.

from .base import PayloadType, PayloadConfig

PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG = PayloadConfig(
    payload_type=PayloadType.MULTI_SYSTEM_STREAM,
    name="MultiSystemStream",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=1,
    has_sequence=True,
    has_system_id=True,
    has_component_id=True,
    has_package_id=False,
    description="[SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Multi-system streaming."
)
