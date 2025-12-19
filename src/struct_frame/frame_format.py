#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;

"""
Frame Format Parser

This module parses frame format definitions from .proto files that use the
separated header + payload architecture.

Headers define the start byte pattern (Basic, Tiny, None, UBX, Mavlink, etc.)
Payloads define the structure after start bytes (Minimal, Default, Extended, etc.)

Frame = Header + Payload
"""

from proto_schema_parser.parser import Parser
from proto_schema_parser import ast
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class HeaderType(Enum):
    """Header types defining start byte patterns"""
    NONE = 0      # No start bytes
    TINY = 1      # 1 start byte [0x70+PayloadType]
    BASIC = 2     # 2 start bytes [0x90] [0x70+PayloadType]
    UBX = 3       # 2 start bytes [0xB5] [0x62]
    MAVLINK_V1 = 4  # 1 start byte [0xFE]
    MAVLINK_V2 = 5  # 1 start byte [0xFD]


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
    # Third party
    UBX = 100                        # [CLASS] [ID] [LEN_LO] [LEN_HI] [MSG] [CK_A] [CK_B]
    MAVLINK_V1 = 101                 # [LEN] [SEQ] [SYS] [COMP] [MSG_ID] [PAYLOAD] [CRC_LO] [CRC_HI]
    MAVLINK_V2 = 102                 # [LEN] [INCOMPAT] [COMPAT] [SEQ] [SYS] [COMP] [MSG_ID x3] [PAYLOAD] [CRC]


@dataclass
class PayloadField:
    """Represents a field in a payload definition"""
    name: str
    field_type: str
    size: int = 1  # bytes
    
    @property
    def is_crc(self) -> bool:
        return 'crc' in self.name.lower() or self.name.startswith('ck_')
    
    @property
    def is_length(self) -> bool:
        return 'length' in self.name.lower() or 'len' in self.name.lower()
    
    @property
    def is_msg_id(self) -> bool:
        return 'msg_id' in self.name.lower()


@dataclass
class HeaderDefinition:
    """Defines a header type (start byte pattern)"""
    name: str
    header_type: HeaderType
    start_bytes: List[Tuple[str, int]] = field(default_factory=list)  # [(name, hex_value), ...]
    num_start_bytes: int = 0
    payload_type_encoded: bool = False  # True if start byte encodes payload type (Tiny, Basic)
    
    @property
    def size(self) -> int:
        return self.num_start_bytes


@dataclass
class PayloadDefinition:
    """Defines a payload type (header fields + footer)"""
    name: str
    payload_type: PayloadType
    fields: List[PayloadField] = field(default_factory=list)
    has_crc: bool = False
    crc_bytes: int = 0
    has_length: bool = False
    length_bytes: int = 1  # 1 for uint8, 2 for uint16
    has_sequence: bool = False
    has_system_id: bool = False
    has_component_id: bool = False
    has_package_id: bool = False
    
    @property
    def header_size(self) -> int:
        """Size of payload header (before message data)"""
        size = 1  # msg_id is always 1 byte
        size += self.length_bytes if self.has_length else 0
        size += 1 if self.has_sequence else 0
        size += 1 if self.has_system_id else 0
        size += 1 if self.has_component_id else 0
        size += 1 if self.has_package_id else 0
        return size
    
    @property
    def footer_size(self) -> int:
        """Size of payload footer (after message data)"""
        return self.crc_bytes
    
    @property
    def overhead(self) -> int:
        """Total overhead (header + footer)"""
        return self.header_size + self.footer_size


class FrameFormatCollection:
    """Collection of header and payload definitions parsed from a proto file"""
    
    def __init__(self):
        self.headers: Dict[HeaderType, HeaderDefinition] = {}
        self.payloads: Dict[PayloadType, PayloadDefinition] = {}
        self._header_type_enum = None
        self._payload_type_enum = None
    
    def parse_file(self, filename: str):
        """Parse frame formats from a proto file"""
        with open(filename, 'r') as f:
            result = Parser().parse(f.read())
        
        for element in result.file_elements:
            if isinstance(element, ast.Enum):
                if element.name == 'HeaderType':
                    self._header_type_enum = element
                elif element.name == 'PayloadType':
                    self._payload_type_enum = element
            elif isinstance(element, ast.Message):
                self._parse_message(element)
    
    def _parse_message(self, message: ast.Message):
        """Parse a message definition"""
        name = message.name
        
        # Parse Header definitions
        if name.startswith('Header'):
            header = self._parse_header(message)
            if header:
                self.headers[header.header_type] = header
        
        # Parse Payload definitions
        elif name.startswith('Payload'):
            payload = self._parse_payload(message)
            if payload:
                self.payloads[payload.payload_type] = payload
    
    def _parse_header(self, message: ast.Message) -> Optional[HeaderDefinition]:
        """Parse a header message definition"""
        name = message.name
        
        # Map message name to HeaderType
        header_type_map = {
            'HeaderNone': HeaderType.NONE,
            'HeaderTiny': HeaderType.TINY,
            'HeaderBasic': HeaderType.BASIC,
            'HeaderUbx': HeaderType.UBX,
            'HeaderMavlinkV1': HeaderType.MAVLINK_V1,
            'HeaderMavlinkV2': HeaderType.MAVLINK_V2,
        }
        
        header_type = header_type_map.get(name)
        if header_type is None:
            return None
        
        header = HeaderDefinition(
            name=name,
            header_type=header_type,
            payload_type_encoded=(header_type in [HeaderType.TINY, HeaderType.BASIC])
        )
        
        for element in message.elements:
            if isinstance(element, ast.Field):
                hex_value = self._get_hex_option(element)
                if hex_value is not None:
                    header.start_bytes.append((element.name, hex_value))
                    header.num_start_bytes += 1
                elif element.name in ['start_byte', 'start_byte1', 'start_byte2', 'sync1', 'sync2', 'stx']:
                    # Variable start byte (encodes payload type)
                    header.start_bytes.append((element.name, None))
                    header.num_start_bytes += 1
        
        return header
    
    def _parse_payload(self, message: ast.Message) -> Optional[PayloadDefinition]:
        """Parse a payload message definition"""
        name = message.name
        
        # Map message name to PayloadType
        payload_type_map = {
            'PayloadMinimal': PayloadType.MINIMAL,
            'PayloadDefault': PayloadType.DEFAULT,
            'PayloadExtendedMsgIds': PayloadType.EXTENDED_MSG_IDS,
            'PayloadExtendedLength': PayloadType.EXTENDED_LENGTH,
            'PayloadExtended': PayloadType.EXTENDED,
            'PayloadSysComp': PayloadType.SYS_COMP,
            'PayloadSeq': PayloadType.SEQ,
            'PayloadMultiSystemStream': PayloadType.MULTI_SYSTEM_STREAM,
            'PayloadExtendedMultiSystemStream': PayloadType.EXTENDED_MULTI_SYSTEM_STREAM,
            'PayloadUbx': PayloadType.UBX,
            'PayloadMavlinkV1': PayloadType.MAVLINK_V1,
            'PayloadMavlinkV2': PayloadType.MAVLINK_V2,
        }
        
        payload_type = payload_type_map.get(name)
        if payload_type is None:
            return None
        
        payload = PayloadDefinition(
            name=name,
            payload_type=payload_type
        )
        
        for element in message.elements:
            if isinstance(element, ast.Field):
                field_size = 2 if element.type == 'uint16' else 1
                pf = PayloadField(element.name, element.type, field_size)
                payload.fields.append(pf)
                
                # Track field types
                if pf.is_crc:
                    payload.has_crc = True
                    payload.crc_bytes += field_size
                
                if pf.is_length:
                    payload.has_length = True
                    payload.length_bytes = field_size
                
                if element.name == 'sequence':
                    payload.has_sequence = True
                if element.name == 'system_id':
                    payload.has_system_id = True
                if element.name == 'component_id':
                    payload.has_component_id = True
                if element.name == 'package_id':
                    payload.has_package_id = True
        
        return payload
    
    def _get_hex_option(self, field: ast.Field) -> Optional[int]:
        """Extract [(hex) = 0xNN] option value from a field"""
        if hasattr(field, 'options') and field.options:
            for opt in field.options:
                opt_name = getattr(opt, 'name', None)
                opt_value = getattr(opt, 'value', None)
                if opt_name and '(hex)' in str(opt_name):
                    try:
                        return int(str(opt_value), 16)
                    except (ValueError, TypeError):
                        pass
        return None
    
    def get_header(self, header_type: HeaderType) -> Optional[HeaderDefinition]:
        """Get header definition by type"""
        return self.headers.get(header_type)
    
    def get_payload(self, payload_type: PayloadType) -> Optional[PayloadDefinition]:
        """Get payload definition by type"""
        return self.payloads.get(payload_type)
    
    def get_standard_payloads(self) -> List[PayloadDefinition]:
        """Get standard payload types (not third-party protocols)"""
        return [p for p in self.payloads.values() if p.payload_type.value < 100]
    
    def get_third_party_payloads(self) -> List[PayloadDefinition]:
        """Get third-party protocol payload types"""
        return [p for p in self.payloads.values() if p.payload_type.value >= 100]
    
    def __iter__(self):
        """Iterate over payload definitions"""
        return iter(self.payloads.values())
    
    def __len__(self):
        return len(self.payloads)


def parse_frame_formats(filename: str) -> FrameFormatCollection:
    """Parse frame formats from a proto file"""
    collection = FrameFormatCollection()
    collection.parse_file(filename)
    return collection


if __name__ == '__main__':
    # Test with frame_formats.proto
    import sys
    import os
    
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        # Default to the frame_formats.proto in the same directory
        filename = os.path.join(os.path.dirname(__file__), 'frame_formats.proto')
    
    collection = parse_frame_formats(filename)
    
    print(f"Found {len(collection.headers)} header types:")
    for header in collection.headers.values():
        print(f"  {header.name}: {header.num_start_bytes} start bytes, "
              f"payload_type_encoded={header.payload_type_encoded}")
        for name, value in header.start_bytes:
            if value is not None:
                print(f"    {name}: 0x{value:02X}")
            else:
                print(f"    {name}: (variable)")
    
    print(f"\nFound {len(collection.payloads)} payload types:")
    for payload in collection.payloads.values():
        print(f"\n  {payload.name}:")
        print(f"    has_crc: {payload.has_crc} ({payload.crc_bytes} bytes)")
        print(f"    has_length: {payload.has_length} ({payload.length_bytes} bytes)")
        print(f"    has_sequence: {payload.has_sequence}")
        print(f"    has_system_id: {payload.has_system_id}")
        print(f"    has_component_id: {payload.has_component_id}")
        print(f"    has_package_id: {payload.has_package_id}")
        print(f"    overhead: {payload.overhead} bytes")
