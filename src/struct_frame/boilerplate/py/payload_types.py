# Payload Types - Message structure configurations (Python)
# Payload types define message structure (length fields, CRC, extra fields)

from enum import Enum
from dataclasses import dataclass


class PayloadType(Enum):
    """Payload types defining header/footer structure"""
    MINIMAL = 0                      # [MSG_ID] [PACKET]
    DEFAULT = 1                      # [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
    EXTENDED_MSG_IDS = 2             # [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
    EXTENDED_LENGTH = 3              # [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2]
    EXTENDED = 4                     # [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
    SYS_COMP = 5                     # [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
    SEQ = 6                          # [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
    MULTI_SYSTEM_STREAM = 7          # [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
    EXTENDED_MULTI_SYSTEM_STREAM = 8 # [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]


# Maximum payload type value (for range checking)
MAX_PAYLOAD_TYPE_VALUE = 8


@dataclass
class PayloadConfig:
    """Configuration for a payload type"""
    payload_type: PayloadType
    name: str
    has_crc: bool
    crc_bytes: int
    has_length: bool
    length_bytes: int  # 1 or 2
    has_sequence: bool
    has_system_id: bool
    has_component_id: bool
    has_package_id: bool
    description: str

    @property
    def header_size(self) -> int:
        """Size of payload header (before message data)"""
        size = 1  # msg_id
        if self.has_length:
            size += self.length_bytes
        if self.has_sequence:
            size += 1
        if self.has_system_id:
            size += 1
        if self.has_component_id:
            size += 1
        if self.has_package_id:
            size += 1
        return size

    @property
    def footer_size(self) -> int:
        """Size of payload footer (CRC)"""
        return self.crc_bytes

    @property
    def overhead(self) -> int:
        """Total overhead (header + footer)"""
        return self.header_size + self.footer_size

    def get_field_order(self) -> list:
        """Get the order of fields in the payload header"""
        fields = []
        if self.has_sequence:
            fields.append('sequence')
        if self.has_system_id:
            fields.append('system_id')
        if self.has_component_id:
            fields.append('component_id')
        if self.has_length:
            if self.length_bytes == 2:
                fields.append('length_lo')
                fields.append('length_hi')
            else:
                fields.append('length')
        if self.has_package_id:
            fields.append('package_id')
        fields.append('msg_id')
        return fields


# =============================================================================
# Payload Configurations
# =============================================================================

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


# Registry of all payload configurations
PAYLOAD_CONFIGS = {
    PayloadType.MINIMAL: PAYLOAD_MINIMAL_CONFIG,
    PayloadType.DEFAULT: PAYLOAD_DEFAULT_CONFIG,
    PayloadType.EXTENDED_MSG_IDS: PAYLOAD_EXTENDED_MSG_IDS_CONFIG,
    PayloadType.EXTENDED_LENGTH: PAYLOAD_EXTENDED_LENGTH_CONFIG,
    PayloadType.EXTENDED: PAYLOAD_EXTENDED_CONFIG,
    PayloadType.SYS_COMP: PAYLOAD_SYS_COMP_CONFIG,
    PayloadType.SEQ: PAYLOAD_SEQ_CONFIG,
    PayloadType.MULTI_SYSTEM_STREAM: PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG,
    PayloadType.EXTENDED_MULTI_SYSTEM_STREAM: PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG,
}
