# Utilities for frame parsing
# Contains checksum functions and common data structures

from typing import Union, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

try:
    from .frame_headers.base import HeaderType
    from .payload_types.base import PayloadType
except ImportError:
    from frame_headers.base import HeaderType
    from payload_types.base import PayloadType


def fletcher_checksum(buffer: Union[bytes, List[int]], start: int = 0, end: int = None) -> Tuple[int, int]:
    """Calculate Fletcher-16 checksum over the given data"""
    if end is None:
        end = len(buffer)
    byte1 = 0
    byte2 = 0
    for x in range(start, end):
        byte1 = (byte1 + buffer[x]) % 256
        byte2 = (byte2 + byte1) % 256
    return (byte1, byte2)


@dataclass
class FrameMsgInfo:
    """Result from frame parsing"""
    valid: bool = False
    header_type: Optional[HeaderType] = None
    payload_type: Optional[PayloadType] = None
    msg_id: int = 0
    msg_len: int = 0
    msg_data: bytes = b''
    # Optional extended fields
    package_id: int = 0
    sequence: int = 0
    system_id: int = 0
    component_id: int = 0


class ParserState(Enum):
    """Parser state machine states"""
    LOOKING_FOR_START = 0
    GOT_BASIC_START = 1  # Got 0x90, waiting for payload type byte
    GOT_UBX_SYNC1 = 2    # Got 0xB5, waiting for 0x62
    PARSING_HEADER = 3   # Parsing payload header fields
    PARSING_PAYLOAD = 4  # Parsing message data
    PARSING_FOOTER = 5   # Parsing CRC


# Profile definitions - map common use cases to (HeaderType, PayloadType) pairs
class Profile(Enum):
    """Pre-defined frame format profiles"""
    STANDARD = (HeaderType.BASIC, PayloadType.DEFAULT)
    SENSOR = (HeaderType.TINY, PayloadType.MINIMAL)
    BULK = (HeaderType.BASIC, PayloadType.EXTENDED)
    NETWORK = (HeaderType.BASIC, PayloadType.EXTENDED_MULTI_SYSTEM_STREAM)
    SEQUENCED = (HeaderType.BASIC, PayloadType.SEQ)
