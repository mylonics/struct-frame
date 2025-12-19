# Base classes and enums for payload types

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
MAX_PAYLOAD_TYPE = 8


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
