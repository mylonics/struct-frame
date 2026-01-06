"""
Base classes and enumerations for frame formats.

This module defines the core data structures used across all frame format definitions.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


class HeaderType(Enum):
    """
    Header types define the start byte pattern used for frame synchronization.
    
    The header determines how many start bytes precede the payload and whether
    the payload type is encoded in the start bytes.
    """
    NONE = 0       # No start bytes (relies on external synchronization)
    TINY = 1       # 1 start byte [0x70+PayloadType]
    BASIC = 2      # 2 start bytes [0x90] [0x70+PayloadType]
    UBX = 3        # 2 start bytes [0xB5] [0x62] (u-blox GPS)
    MAVLINK_V1 = 4 # 1 start byte [0xFE] (Classic drone protocol)
    MAVLINK_V2 = 5 # 1 start byte [0xFD] (Modern drone protocol)


class PayloadType(Enum):
    """
    Payload types define the structure of header fields and footer (CRC) after start bytes.
    
    The payload type determines what metadata fields are included (length, sequence, 
    system ID, etc.) and whether CRC error detection is used.
    """
    MINIMAL = 0                      # [MSG_ID] [PACKET]
    DEFAULT = 1                      # [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
    EXTENDED_MSG_IDS = 2             # [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
    EXTENDED_LENGTH = 3              # [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2]
    EXTENDED = 4                     # [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
    SYS_COMP = 5                     # [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
    SEQ = 6                          # [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
    MULTI_SYSTEM_STREAM = 7          # [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
    EXTENDED_MULTI_SYSTEM_STREAM = 8 # [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
    # Third-party protocol payloads (value >= 100)
    UBX = 100                        # [CLASS] [ID] [LEN_LO] [LEN_HI] [MSG] [CK_A] [CK_B]
    MAVLINK_V1 = 101                 # [LEN] [SEQ] [SYS] [COMP] [MSG_ID] [PAYLOAD] [CRC_LO] [CRC_HI]
    MAVLINK_V2 = 102                 # [LEN] [INCOMPAT] [COMPAT] [SEQ] [SYS] [COMP] [MSG_ID x3] [PAYLOAD] [CRC]


@dataclass
class HeaderDefinition:
    """
    Defines a header type's structure and behavior.
    
    Attributes:
        header_type: The type of header
        name: Human-readable name
        start_bytes: Fixed start byte values (empty list for variable)
        num_start_bytes: Total number of start bytes
        encodes_payload_type: True if start byte encodes payload type (Basic, Tiny)
        payload_type_byte_index: Index of byte that encodes payload type (-1 if none)
        description: Human-readable description
    """
    header_type: HeaderType
    name: str
    start_bytes: List[int] = field(default_factory=list)
    num_start_bytes: int = 0
    encodes_payload_type: bool = False
    payload_type_byte_index: int = -1
    description: str = ""
    
    @property
    def size(self) -> int:
        """Size of header in bytes"""
        return self.num_start_bytes
    
    @property
    def is_fixed(self) -> bool:
        """True if all start bytes have fixed values"""
        return len(self.start_bytes) == self.num_start_bytes and not self.encodes_payload_type


@dataclass
class PayloadDefinition:
    """
    Defines a payload type's structure and metadata fields.
    
    Attributes:
        payload_type: The type of payload
        name: Human-readable name
        has_crc: True if payload includes CRC error detection
        crc_bytes: Number of CRC bytes (typically 0 or 2)
        has_length: True if payload includes a length field
        length_bytes: Size of length field (1 for uint8, 2 for uint16)
        has_sequence: True if payload includes a sequence number
        has_system_id: True if payload includes a system ID
        has_component_id: True if payload includes a component ID
        has_package_id: True if payload includes a package ID
        description: Human-readable description
    """
    payload_type: PayloadType
    name: str
    has_crc: bool = False
    crc_bytes: int = 0
    has_length: bool = False
    length_bytes: int = 0
    has_sequence: bool = False
    has_system_id: bool = False
    has_component_id: bool = False
    has_package_id: bool = False
    description: str = ""
    
    @property
    def header_size(self) -> int:
        """Size of payload header (fields before message data) in bytes"""
        size = 1  # msg_id is always 1 byte
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
        """Size of payload footer (CRC bytes after message data)"""
        return self.crc_bytes
    
    @property
    def overhead(self) -> int:
        """Total payload overhead (header + footer) in bytes"""
        return self.header_size + self.footer_size
    
    def get_field_order(self) -> List[str]:
        """
        Get the order of fields in the payload header.
        
        Returns:
            List of field names in the order they appear in the frame
        """
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


@dataclass
class FrameFormatDefinition:
    """
    Complete frame format definition combining header and payload.
    
    A frame format is the complete specification of how to encode/decode messages,
    including both the framing (start bytes) and payload structure.
    
    Attributes:
        name: Human-readable name (e.g., "BasicDefault")
        header: Header definition
        payload: Payload definition
        description: Human-readable description
    """
    name: str
    header: HeaderDefinition
    payload: PayloadDefinition
    description: str = ""
    
    @property
    def total_overhead(self) -> int:
        """Total overhead (header + payload header + payload footer) in bytes"""
        return self.header.size + self.payload.overhead
    
    @property
    def start_byte_value(self) -> Optional[int]:
        """
        Get the start byte value (for Tiny/Basic with encoded payload type).
        
        Returns:
            The computed start byte value, or None if not applicable
        """
        if self.header.encodes_payload_type:
            return 0x70 + self.payload.payload_type.value
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'name': self.name,
            'header_type': self.header.header_type.name,
            'payload_type': self.payload.payload_type.name,
            'total_overhead': self.total_overhead,
            'max_payload_size': 65535 if self.payload.length_bytes == 2 else 255 if self.payload.has_length else None,
            'has_crc': self.payload.has_crc,
            'has_sequence': self.payload.has_sequence,
            'has_routing': self.payload.has_system_id and self.payload.has_component_id,
            'description': self.description,
        }


# Constants
BASIC_START_BYTE = 0x90
PAYLOAD_TYPE_BASE = 0x70
UBX_SYNC1 = 0xB5
UBX_SYNC2 = 0x62
MAVLINK_V1_STX = 0xFE
MAVLINK_V2_STX = 0xFD
