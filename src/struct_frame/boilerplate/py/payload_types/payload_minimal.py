# Payload Minimal
# Format: [MSG_ID] [PACKET]
# No length field, no CRC. Requires known message sizes.

from .base import PayloadType, PayloadConfig

PAYLOAD_MINIMAL_CONFIG = PayloadConfig(
    payload_type=PayloadType.MINIMAL,
    name="Minimal",
    has_crc=False,
    crc_bytes=0,
    has_length=False,
    length_bytes=0,
    has_sequence=False,
    has_system_id=False,
    has_component_id=False,
    has_package_id=False,
    description="[MSG_ID] [PACKET] - No length, no CRC. Requires known message sizes."
)
