# Payload Seq
# Format: [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
# Adds sequence number for packet loss detection.

from .base import PayloadType, PayloadConfig

PAYLOAD_SEQ_CONFIG = PayloadConfig(
    payload_type=PayloadType.SEQ,
    name="Seq",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=1,
    has_sequence=True,
    has_system_id=False,
    has_component_id=False,
    has_package_id=False,
    description="[SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Packet loss detection."
)
