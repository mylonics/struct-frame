# Base classes and enums for frame headers

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional


class HeaderType(Enum):
    """Header types defining start byte patterns"""
    NONE = 0       # No start bytes
    TINY = 1       # 1 start byte [0x70+PayloadType]
    BASIC = 2      # 2 start bytes [0x90] [0x70+PayloadType]
    UBX = 3        # 2 start bytes [0xB5] [0x62]
    MAVLINK_V1 = 4 # 1 start byte [0xFE]
    MAVLINK_V2 = 5 # 1 start byte [0xFD]


@dataclass
class HeaderConfig:
    """Configuration for a header type"""
    header_type: HeaderType
    name: str
    start_bytes: List[int]  # Fixed start bytes (empty for dynamic)
    num_start_bytes: int
    encodes_payload_type: bool  # True if start byte encodes payload type
    payload_type_byte_index: int  # Which byte encodes payload type (-1 if none)
    description: str

    @property
    def is_fixed(self) -> bool:
        """True if all start bytes are fixed values"""
        return len(self.start_bytes) == self.num_start_bytes and not self.encodes_payload_type


# Constants used across headers
BASIC_START_BYTE = 0x90
PAYLOAD_TYPE_BASE = 0x70  # Payload type encoded as 0x70 + PayloadType.value
UBX_SYNC1 = 0xB5
UBX_SYNC2 = 0x62
MAVLINK_V1_STX = 0xFE
MAVLINK_V2_STX = 0xFD
MAX_PAYLOAD_TYPE = 8
