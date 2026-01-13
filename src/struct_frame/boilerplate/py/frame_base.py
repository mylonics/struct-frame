# Frame Base - Core utilities for frame parsing (Python)
# Mirrors frame_base.hpp from C++ boilerplate

from typing import Union, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# Checksum
# =============================================================================

@dataclass
class FrameChecksum:
    """Checksum result - two bytes"""
    byte1: int = 0
    byte2: int = 0
    
    def __iter__(self):
        """Allow unpacking: b1, b2 = checksum"""
        return iter((self.byte1, self.byte2))
    
    def as_tuple(self) -> Tuple[int, int]:
        """Return as tuple"""
        return (self.byte1, self.byte2)


def fletcher_checksum(data: Union[bytes, List[int]], start: int = 0, end: Optional[int] = None, 
                      init1: int = 0, init2: int = 0) -> FrameChecksum:
    """
    Calculate Fletcher-16 checksum over the given data.
    
    Args:
        data: Buffer to checksum
        start: Start index (inclusive)
        end: End index (exclusive), defaults to len(data)
        init1: Magic number 1 (added at the end)
        init2: Magic number 2 (added at the end)
    
    Returns:
        FrameChecksum with byte1 and byte2
    """
    if end is None:
        end = len(data)
    
    byte1 = 0
    byte2 = 0
    for i in range(start, end):
        byte1 = (byte1 + data[i]) & 0xFF
        byte2 = (byte2 + byte1) & 0xFF
    
    # Add magic numbers at the end
    byte1 = (byte1 + init1) & 0xFF
    byte2 = (byte2 + byte1) & 0xFF
    byte1 = (byte1 + init2) & 0xFF
    byte2 = (byte2 + byte1) & 0xFF
    
    return FrameChecksum(byte1, byte2)


# =============================================================================
# Parse Result
# =============================================================================

@dataclass
class FrameMsgInfo:
    """
    Result from frame parsing.
    
    Mirrors C++ FrameMsgInfo structure for compatibility.
    """
    valid: bool = False
    msg_id: int = 0           # Message ID (16-bit for extended profiles)
    msg_len: int = 0          # Payload length (message data only)
    frame_size: int = 0       # Total frame size (header + payload + footer)
    msg_data: bytes = b''     # Pointer to message data
    
    # Optional extended fields (for profiles that support them)
    package_id: int = 0
    sequence: int = 0
    system_id: int = 0
    component_id: int = 0
    
    def __bool__(self) -> bool:
        """Allow use in boolean context: while (result := reader.next()): ..."""
        return self.valid


# =============================================================================
# Parser State (for streaming parsers)
# =============================================================================

class ParserState(Enum):
    """Parser state machine states"""
    LOOKING_FOR_START = 0
    GOT_BASIC_START = 1     # Got 0x90, waiting for payload type byte
    GOT_UBX_SYNC1 = 2       # Got 0xB5, waiting for 0x62
    PARSING_HEADER = 3      # Parsing payload header fields
    PARSING_PAYLOAD = 4     # Parsing message data
    PARSING_FOOTER = 5      # Parsing CRC
