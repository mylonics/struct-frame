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


def fletcher_checksum_ext(data: Union[bytes, List[int]], start: int, base_end: int, end: int,
                          init1: int = 0, init2: int = 0) -> FrameChecksum:
    """
    Extension-aware Fletcher-16 checksum.

    Computes: Fletcher(data[start:base_end]) -> mix magic1/magic2 -> Fletcher(data[base_end:end]).
    When base_end == end the result is identical to fletcher_checksum.

    Args:
        data: Buffer to checksum
        start: Start index (inclusive)
        base_end: End of non-extension portion (exclusive); magic bytes are mixed here
        end: End index (exclusive)
        init1: Magic number 1
        init2: Magic number 2
    """
    byte1 = 0
    byte2 = 0
    for i in range(start, base_end):
        byte1 = (byte1 + data[i]) & 0xFF
        byte2 = (byte2 + byte1) & 0xFF
    byte1 = (byte1 + init1) & 0xFF
    byte2 = (byte2 + byte1) & 0xFF
    byte1 = (byte1 + init2) & 0xFF
    byte2 = (byte2 + byte1) & 0xFF
    for i in range(base_end, end):
        byte1 = (byte1 + data[i]) & 0xFF
        byte2 = (byte2 + byte1) & 0xFF
    return FrameChecksum(byte1, byte2)


# =============================================================================
# Parse Result
# =============================================================================

class FrameMsgStatus(Enum):
    """
    Reason code carried in FrameMsgInfo when valid is False.

    This lets callers distinguish between "parser is still accumulating bytes"
    (normal) and the various error conditions that cause the parser to discard
    data or fail validation.

    NONE              - Default / unset.  Used by one-shot buffer parsers when
                        no specific reason is available.
    WAITING_FOR_START - Parser is idle and searching for a start byte.  No
                        frame has been started yet (or the previous frame was
                        completed / reset).
    COLLECTING        - A frame is in progress; the parser is still accumulating
                        header or payload bytes.  More data is needed.
    CRC_FAILURE       - A complete frame was received but its CRC did not match.
                        Indicates noise or data corruption on the link.
    SYNC_RECOVERY     - The parser discarded one or more bytes to re-find a
                        valid frame start.  Triggered by bad bytes, unknown
                        message IDs, or internal buffer overflows.
    """
    NONE = 0
    WAITING_FOR_START = 1
    COLLECTING = 2
    CRC_FAILURE = 3
    SYNC_RECOVERY = 4


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

    # Parser state / reason code (meaningful when valid is False)
    status: FrameMsgStatus = FrameMsgStatus.NONE
    diagnostics: Optional['ParserDiagnostics'] = None
    
    def __bool__(self) -> bool:
        """Allow use in boolean context: while (result := reader.next()): ..."""
        return self.valid


# =============================================================================
# Parser Diagnostics
# =============================================================================

@dataclass
class ParserDiagnostics:
    """
    Error counters for parser diagnostics.

    Tracks error events detected by the AccumulatingReader in stream mode.
    These counters accumulate over the reader's lifetime and can be reset
    with reset_diagnostics().

    Attributes:
        cnt_crc_failures:   Complete frames where CRC validation failed.
                            Indicates noise or corruption on the line.
        cnt_sync_recoveries: Times the parser had to discard bytes and
                            re-search for a frame start.  Indicates lost
                            bytes or buffer overflows.
        cnt_failed_bytes:   Total bytes discarded when failures forced the
                    parser to restart searching for frame start.
        cnt_len_errors:     Frames where the explicit length in the header
                            does not match the expected message-struct size
                            returned by get_message_info().  Vital for
                            detecting sender/receiver definition mismatches.
        cnt_seq_gaps:       Sequence-number gaps in received messages.
                            Only incremented on profiles that carry a
                            sequence field (e.g. ProfileNetwork).
                            Indicates dropped packets.
    """
    cnt_crc_failures: int = 0
    cnt_sync_recoveries: int = 0
    cnt_failed_bytes: int = 0
    cnt_len_errors: int = 0
    cnt_seq_gaps: int = 0


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
