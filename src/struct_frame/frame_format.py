#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;

"""
Frame Format Parser and Generator

This module parses frame format definitions from .proto files and generates
frame parser code for multiple target languages.

Frame formats define how messages are framed for communication, including:
- Start bytes for synchronization
- Header structure (message ID, optional length)
- Footer structure (CRC/checksum)
"""

from proto_schema_parser.parser import Parser
from proto_schema_parser import ast


class FrameFormatField:
    """Represents a field in a frame format definition"""
    
    def __init__(self, name, field_type, hex_value=None):
        self.name = name
        self.field_type = field_type
        self.hex_value = hex_value  # For start bytes with [(hex) = 0xNN]
        self.is_start_byte = name.startswith('start_byte') or name in ['sync1', 'sync2', 'stx']
        self.is_crc = 'crc' in name.lower() or name.startswith('ck_')
        self.is_length = 'length' in name.lower() or 'len' in name.lower()
        self.is_msg_id = 'msg_id' in name.lower() or name == 'msg_id'
        self.is_payload = name == 'payload'
        # New header fields for extended frame formats
        self.is_sequence = name in ['sequence', 'seq']
        self.is_system_id = name == 'system_id'
        self.is_component_id = name == 'component_id'
        self.is_package_id = name == 'package_id'
        # Check if this is a header field (not start byte, payload, or CRC)
        self.is_header_field = (self.is_sequence or self.is_system_id or 
                                self.is_component_id or self.is_package_id)
        
    def __repr__(self):
        return f"FrameFormatField({self.name}, {self.field_type}, hex={self.hex_value})"


class FrameFormat:
    """
    Represents a parsed frame format definition.
    
    Frame formats describe how messages are framed for communication:
    - Start bytes: Synchronization markers
    - Header: Message ID, optional length field
    - Payload: The actual message data
    - Footer: CRC/checksum bytes
    """
    
    def __init__(self, name, comments=None):
        self.name = name
        self.comments = comments or []
        self.fields = []
        self.start_bytes = []      # List of (name, hex_value) tuples
        self.has_crc = False
        self.crc_bytes = 0         # Number of CRC bytes (usually 2)
        self.has_length = False
        self.length_bytes = 0      # 1 for uint8, 2 for uint16
        self.header_size = 0       # Total header size
        self.footer_size = 0       # Total footer size
        
    def parse(self, message):
        """Parse a proto message definition into a frame format"""
        self.name = message.name
        
        for element in message.elements:
            if isinstance(element, ast.Field):
                hex_value = None
                
                # Check for [(hex) = 0xNN] option
                if hasattr(element, 'options') and element.options:
                    for opt in element.options:
                        opt_name = getattr(opt, 'name', None)
                        opt_value = getattr(opt, 'value', None)
                        if opt_name and '(hex)' in str(opt_name):
                            # Parse hex value
                            try:
                                hex_value = int(str(opt_value), 16)
                            except (ValueError, TypeError):
                                hex_value = opt_value
                
                field = FrameFormatField(element.name, element.type, hex_value)
                self.fields.append(field)
                
                # Track start bytes
                if field.is_start_byte and hex_value is not None:
                    self.start_bytes.append((element.name, hex_value))
                    self.header_size += 1
                    
                # Track CRC bytes
                if field.is_crc:
                    self.has_crc = True
                    self.crc_bytes += 1
                    self.footer_size += 1
                    
                # Track length field
                if field.is_length:
                    self.has_length = True
                    if element.type == 'uint16':
                        self.length_bytes = 2
                    else:
                        self.length_bytes = 1
                    self.header_size += self.length_bytes
                    
                # Track payload/msg_id (1 byte for msg_id)
                if field.is_payload or field.is_msg_id:
                    self.header_size += 1
                
                # Track additional header fields (sequence, system_id, component_id, package_id)
                if field.is_header_field:
                    self.header_size += 1
                    
        return True
    
    def get_enum_value(self):
        """Get the enum value name for this frame format"""
        # Convert CamelCase to UPPER_SNAKE_CASE
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', self.name)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
        return name.upper()
    
    def __repr__(self):
        return (f"FrameFormat({self.name}, start_bytes={self.start_bytes}, "
                f"has_crc={self.has_crc}, has_length={self.has_length})")


class FrameFormatCollection:
    """Collection of frame formats parsed from a proto file"""
    
    def __init__(self):
        self.formats = {}
        self.format_enum = None  # The FrameFormatType enum if present
        
    def parse_file(self, filename):
        """Parse frame formats from a proto file"""
        with open(filename, 'r') as f:
            result = Parser().parse(f.read())
            
        for element in result.file_elements:
            if isinstance(element, ast.Enum):
                if element.name == 'FrameFormatType':
                    self.format_enum = element
                    
            elif isinstance(element, ast.Message):
                # Skip non-frame messages like BasicMessage, FrameFormatConfig
                if self._is_frame_format_message(element):
                    frame = FrameFormat(element.name)
                    if frame.parse(element):
                        self.formats[element.name] = frame
                        
    def _is_frame_format_message(self, message):
        """Check if a message defines a frame format"""
        # Frame format messages typically have start bytes or are named *Frame*
        has_start = False
        has_payload_or_id = False
        
        for element in message.elements:
            if isinstance(element, ast.Field):
                name = element.name.lower()
                if 'start' in name or 'sync' in name or 'stx' in name:
                    has_start = True
                if name == 'payload' or 'msg_id' in name:
                    has_payload_or_id = True
                    
        # Consider it a frame format if it has start bytes and payload/msg_id,
        # or if the name contains 'Frame' and has multiple fields
        name_indicates_frame = 'Frame' in message.name or message.name.endswith('Frame')
        
        return (has_start and has_payload_or_id) or (name_indicates_frame and len(message.elements) > 1)
    
    def get_format_by_start_byte(self, start_byte):
        """Find frame format(s) that match a given start byte"""
        matches = []
        for name, fmt in self.formats.items():
            if fmt.start_bytes:
                if fmt.start_bytes[0][1] == start_byte:
                    matches.append(fmt)
        return matches
    
    def __iter__(self):
        return iter(self.formats.values())
    
    def __len__(self):
        return len(self.formats)


def parse_frame_formats(filename):
    """Parse frame formats from a proto file"""
    collection = FrameFormatCollection()
    collection.parse_file(filename)
    return collection


if __name__ == '__main__':
    # Test with frame_formats.proto
    import sys
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = 'examples/frame_formats.proto'
        
    collection = parse_frame_formats(filename)
    
    print(f"Found {len(collection)} frame formats:")
    for fmt in collection:
        print(f"\n{fmt.name}:")
        print(f"  Start bytes: {fmt.start_bytes}")
        print(f"  Has CRC: {fmt.has_crc} ({fmt.crc_bytes} bytes)")
        print(f"  Has Length: {fmt.has_length} ({fmt.length_bytes} bytes)")
        print(f"  Header size: {fmt.header_size}")
        print(f"  Footer size: {fmt.footer_size}")
