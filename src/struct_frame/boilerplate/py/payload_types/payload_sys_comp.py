# Payload SysComp
# Format: [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
# Adds system and component IDs for multi-system networks.

from .base import PayloadType, PayloadConfig

PAYLOAD_SYS_COMP_CONFIG = PayloadConfig(
    payload_type=PayloadType.SYS_COMP,
    name="SysComp",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=1,
    has_sequence=False,
    has_system_id=True,
    has_component_id=True,
    has_package_id=False,
    description="[SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Multi-system support."
)
