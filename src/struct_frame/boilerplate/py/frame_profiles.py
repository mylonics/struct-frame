"""
Frame Profiles - Pre-defined Header + Payload combinations

This module provides ready-to-use encode/parse functions for the 5 standard profiles:
- Profile.STANDARD: Basic + Default (General serial/UART)
- Profile.SENSOR: Tiny + Minimal (Low-bandwidth sensors)
- Profile.IPC: None + Minimal (Trusted inter-process communication)
- Profile.BULK: Basic + Extended (Large data transfers with package namespacing)
- Profile.NETWORK: Basic + ExtendedMultiSystemStream (Multi-system networked communication)

This module builds on the existing frame_headers and payload_types boilerplate code,
providing maximum code reuse through a generic FrameFormatConfig class.
"""

from dataclasses import dataclass
from typing import Optional, Callable, Tuple, List
from enum import Enum

try:
    from .frame_headers.base import (
        HeaderType, BASIC_START_BYTE, PAYLOAD_TYPE_BASE
    )
    from .payload_types.base import PayloadType
    from .utils import fletcher_checksum, FrameMsgInfo
except ImportError:
    from frame_headers.base import (
        HeaderType, BASIC_START_BYTE, PAYLOAD_TYPE_BASE
    )
    from payload_types.base import PayloadType
    from utils import fletcher_checksum, FrameMsgInfo


@dataclass
class FrameFormatConfig:
    """
    Generic frame format configuration - combines header type with payload type.
    
    This class allows creating any header+payload combination by specifying
    the configuration parameters. The standard profiles are pre-defined instances
    of this configuration.
    """
    name: str
    header_type: HeaderType
    payload_type: PayloadType
    num_start_bytes: int
    start_byte1: int
    start_byte2: int
    header_size: int        # Total header size (start bytes + payload header fields)
    footer_size: int        # Footer size (CRC bytes)
    has_length: bool
    length_bytes: int       # 1 or 2
    has_crc: bool
    has_pkg_id: bool
    has_seq: bool
    has_sys_id: bool
    has_comp_id: bool

    @property
    def overhead(self) -> int:
        """Total overhead (header + footer)"""
        return self.header_size + self.footer_size

    @property
    def max_payload(self) -> Optional[int]:
        """Maximum payload size, or None if no length field"""
        if not self.has_length:
            return None
        return 65535 if self.length_bytes == 2 else 255


def _frame_format_encode_with_crc(
    config: FrameFormatConfig,
    msg_id: int,
    payload: bytes,
    seq: int = 0,
    sys_id: int = 0,
    comp_id: int = 0
) -> bytes:
    """
    Generic encode function for frames with CRC.
    
    Args:
        config: Frame format configuration
        msg_id: Message ID. When config.has_pkg_id is True, this should be a 16-bit value
                with package ID in upper 8 bits and message ID in lower 8 bits: (pkg_id << 8) | msg_id
        payload: Message payload bytes
        seq: Sequence number (for profiles with sequence)
        sys_id: System ID (for profiles with routing)
        comp_id: Component ID (for profiles with routing)
    
    Returns:
        Encoded frame as bytes
    """
    payload_size = len(payload)
    
    if config.max_payload is not None and payload_size > config.max_payload:
        raise ValueError(f"Payload size {payload_size} exceeds maximum {config.max_payload}")
    
    output = []
    
    # Write start bytes
    if config.num_start_bytes >= 1:
        output.append(config.start_byte1)
    if config.num_start_bytes >= 2:
        output.append(config.start_byte2)
    
    crc_start = len(output)  # CRC calculation starts after start bytes
    
    # Write optional fields before length
    if config.has_seq:
        output.append(seq & 0xFF)
    if config.has_sys_id:
        output.append(sys_id & 0xFF)
    if config.has_comp_id:
        output.append(comp_id & 0xFF)
    
    # Write length field
    if config.has_length:
        if config.length_bytes == 1:
            output.append(payload_size & 0xFF)
        else:
            output.append(payload_size & 0xFF)
            output.append((payload_size >> 8) & 0xFF)
    
    # Write package ID and message ID
    if config.has_pkg_id:
        # Extract package ID from upper 8 bits and message ID from lower 8 bits
        pkg_id = (msg_id >> 8) & 0xFF
        local_msg_id = msg_id & 0xFF
        output.append(pkg_id)
        output.append(local_msg_id)
    else:
        # Write message ID only
        output.append(msg_id & 0xFF)
    
    # Write payload
    output.extend(payload)
    
    # Calculate and write CRC
    if config.has_crc:
        crc = fletcher_checksum(output, crc_start)
        output.append(crc[0])
        output.append(crc[1])
    
    return bytes(output)


def _frame_format_encode_minimal(
    config: FrameFormatConfig,
    msg_id: int,
    payload: bytes
) -> bytes:
    """
    Generic encode function for minimal frames (no length, no CRC).
    
    Args:
        config: Frame format configuration
        msg_id: Message ID (0-255)
        payload: Message payload bytes
    
    Returns:
        Encoded frame as bytes
    """
    output = []
    
    # Write start bytes
    if config.num_start_bytes >= 1:
        output.append(config.start_byte1)
    if config.num_start_bytes >= 2:
        output.append(config.start_byte2)
    
    # Write message ID
    output.append(msg_id & 0xFF)
    
    # Write payload
    output.extend(payload)
    
    return bytes(output)


def _frame_format_parse_with_crc(
    config: FrameFormatConfig,
    buffer: bytes
) -> FrameMsgInfo:
    """
    Generic parse function for frames with CRC.
    
    Args:
        config: Frame format configuration
        buffer: Buffer containing the complete frame
    
    Returns:
        FrameMsgInfo with valid=True if frame is valid
    """
    result = FrameMsgInfo()
    length = len(buffer)
    
    if length < config.overhead:
        return result
    
    idx = 0
    
    # Verify start bytes
    if config.num_start_bytes >= 1:
        if buffer[idx] != config.start_byte1:
            return result
        idx += 1
    if config.num_start_bytes >= 2:
        if buffer[idx] != config.start_byte2:
            return result
        idx += 1
    
    crc_start = idx
    
    # Read optional fields before length
    seq = 0
    sys_id = 0
    comp_id = 0
    if config.has_seq:
        seq = buffer[idx]
        idx += 1
    if config.has_sys_id:
        sys_id = buffer[idx]
        idx += 1
    if config.has_comp_id:
        comp_id = buffer[idx]
        idx += 1
    
    # Read length field
    msg_len = 0
    if config.has_length:
        if config.length_bytes == 1:
            msg_len = buffer[idx]
            idx += 1
        else:
            msg_len = buffer[idx] | (buffer[idx + 1] << 8)
            idx += 2
    
    # Read package ID
    pkg_id = 0
    if config.has_pkg_id:
        pkg_id = buffer[idx]
        idx += 1
    
    # Read message ID
    msg_id = buffer[idx]
    idx += 1
    
    # Verify total size
    total_size = config.overhead + msg_len
    if length < total_size:
        return result
    
    # Verify CRC
    if config.has_crc:
        crc_len = total_size - crc_start - config.footer_size
        calc_crc = fletcher_checksum(buffer, crc_start, crc_start + crc_len)
        recv_crc = (buffer[total_size - 2], buffer[total_size - 1])
        if calc_crc != recv_crc:
            return result
    
    # Extract message data
    msg_data = bytes(buffer[config.header_size:config.header_size + msg_len])
    
    result.valid = True
    result.header_type = config.header_type
    result.payload_type = config.payload_type
    result.msg_id = msg_id
    result.msg_len = msg_len
    result.msg_data = msg_data
    result.package_id = pkg_id
    result.sequence = seq
    result.system_id = sys_id
    result.component_id = comp_id
    
    return result


def _frame_format_parse_minimal(
    config: FrameFormatConfig,
    buffer: bytes,
    get_msg_length: Callable[[int], int]
) -> FrameMsgInfo:
    """
    Generic parse function for minimal frames (requires get_msg_length callback).
    
    Args:
        config: Frame format configuration
        buffer: Buffer containing the complete frame
        get_msg_length: Callback to get expected message length from msg_id
    
    Returns:
        FrameMsgInfo with valid=True if frame is valid
    """
    result = FrameMsgInfo()
    
    if len(buffer) < config.header_size:
        return result
    
    idx = 0
    
    # Verify start bytes
    if config.num_start_bytes >= 1:
        if buffer[idx] != config.start_byte1:
            return result
        idx += 1
    if config.num_start_bytes >= 2:
        if buffer[idx] != config.start_byte2:
            return result
        idx += 1
    
    # Read message ID
    msg_id = buffer[idx]
    
    # Get message length from callback
    msg_len = get_msg_length(msg_id)
    if msg_len is None:
        return result
    
    total_size = config.header_size + msg_len
    if len(buffer) < total_size:
        return result
    
    # Extract message data
    msg_data = bytes(buffer[config.header_size:config.header_size + msg_len])
    
    result.valid = True
    result.header_type = config.header_type
    result.payload_type = config.payload_type
    result.msg_id = msg_id
    result.msg_len = msg_len
    result.msg_data = msg_data
    
    return result


# =============================================================================
# Profile Configurations
# =============================================================================

# Profile Standard: Basic + Default
# Frame: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
PROFILE_STANDARD_CONFIG = FrameFormatConfig(
    name="ProfileStandard",
    header_type=HeaderType.BASIC,
    payload_type=PayloadType.DEFAULT,
    num_start_bytes=2,
    start_byte1=BASIC_START_BYTE,
    start_byte2=PAYLOAD_TYPE_BASE + PayloadType.DEFAULT.value,
    header_size=4,   # start1 + start2 + len + msg_id
    footer_size=2,   # CRC
    has_length=True,
    length_bytes=1,
    has_crc=True,
    has_pkg_id=False,
    has_seq=False,
    has_sys_id=False,
    has_comp_id=False
)

# Profile Sensor: Tiny + Minimal
# Frame: [0x70] [MSG_ID] [PAYLOAD]
PROFILE_SENSOR_CONFIG = FrameFormatConfig(
    name="ProfileSensor",
    header_type=HeaderType.TINY,
    payload_type=PayloadType.MINIMAL,
    num_start_bytes=1,
    start_byte1=PAYLOAD_TYPE_BASE + PayloadType.MINIMAL.value,
    start_byte2=0,
    header_size=2,   # start + msg_id
    footer_size=0,
    has_length=False,
    length_bytes=0,
    has_crc=False,
    has_pkg_id=False,
    has_seq=False,
    has_sys_id=False,
    has_comp_id=False
)

# Profile IPC: None + Minimal
# Frame: [MSG_ID] [PAYLOAD]
PROFILE_IPC_CONFIG = FrameFormatConfig(
    name="ProfileIPC",
    header_type=HeaderType.NONE,
    payload_type=PayloadType.MINIMAL,
    num_start_bytes=0,
    start_byte1=0,
    start_byte2=0,
    header_size=1,   # msg_id only
    footer_size=0,
    has_length=False,
    length_bytes=0,
    has_crc=False,
    has_pkg_id=False,
    has_seq=False,
    has_sys_id=False,
    has_comp_id=False
)

# Profile Bulk: Basic + Extended
# Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
PROFILE_BULK_CONFIG = FrameFormatConfig(
    name="ProfileBulk",
    header_type=HeaderType.BASIC,
    payload_type=PayloadType.EXTENDED,
    num_start_bytes=2,
    start_byte1=BASIC_START_BYTE,
    start_byte2=PAYLOAD_TYPE_BASE + PayloadType.EXTENDED.value,
    header_size=6,   # start1 + start2 + len16 + pkg_id + msg_id
    footer_size=2,   # CRC
    has_length=True,
    length_bytes=2,
    has_crc=True,
    has_pkg_id=True,
    has_seq=False,
    has_sys_id=False,
    has_comp_id=False
)

# Profile Network: Basic + ExtendedMultiSystemStream
# Frame: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
PROFILE_NETWORK_CONFIG = FrameFormatConfig(
    name="ProfileNetwork",
    header_type=HeaderType.BASIC,
    payload_type=PayloadType.EXTENDED_MULTI_SYSTEM_STREAM,
    num_start_bytes=2,
    start_byte1=BASIC_START_BYTE,
    start_byte2=PAYLOAD_TYPE_BASE + PayloadType.EXTENDED_MULTI_SYSTEM_STREAM.value,
    header_size=9,   # start1 + start2 + seq + sys + comp + len16 + pkg_id + msg_id
    footer_size=2,   # CRC
    has_length=True,
    length_bytes=2,
    has_crc=True,
    has_pkg_id=True,
    has_seq=True,
    has_sys_id=True,
    has_comp_id=True
)


# =============================================================================
# Profile-Specific Convenience Functions
# =============================================================================

def encode_profile_standard(msg_id: int, payload: bytes) -> bytes:
    """Encode using Profile Standard (Basic + Default)"""
    return _frame_format_encode_with_crc(PROFILE_STANDARD_CONFIG, msg_id, payload)


def parse_profile_standard_buffer(buffer: bytes) -> FrameMsgInfo:
    """Parse Profile Standard frame from buffer"""
    return _frame_format_parse_with_crc(PROFILE_STANDARD_CONFIG, buffer)


def encode_profile_sensor(msg_id: int, payload: bytes) -> bytes:
    """Encode using Profile Sensor (Tiny + Minimal)"""
    return _frame_format_encode_minimal(PROFILE_SENSOR_CONFIG, msg_id, payload)


def parse_profile_sensor_buffer(buffer: bytes, get_msg_length: Callable[[int], int]) -> FrameMsgInfo:
    """Parse Profile Sensor frame from buffer (requires get_msg_length callback)"""
    return _frame_format_parse_minimal(PROFILE_SENSOR_CONFIG, buffer, get_msg_length)


def encode_profile_ipc(msg_id: int, payload: bytes) -> bytes:
    """Encode using Profile IPC (None + Minimal)"""
    return _frame_format_encode_minimal(PROFILE_IPC_CONFIG, msg_id, payload)


def parse_profile_ipc_buffer(buffer: bytes, get_msg_length: Callable[[int], int]) -> FrameMsgInfo:
    """Parse Profile IPC frame from buffer (requires get_msg_length callback)"""
    return _frame_format_parse_minimal(PROFILE_IPC_CONFIG, buffer, get_msg_length)


def encode_profile_bulk(msg_id: int, payload: bytes) -> bytes:
    """Encode using Profile Bulk (Basic + Extended)
    
    Args:
        msg_id: 16-bit message ID with package ID in upper 8 bits: (pkg_id << 8) | msg_id
        payload: Message payload bytes
    
    Returns:
        Encoded frame as bytes
    """
    return _frame_format_encode_with_crc(PROFILE_BULK_CONFIG, msg_id, payload)


def parse_profile_bulk_buffer(buffer: bytes) -> FrameMsgInfo:
    """Parse Profile Bulk frame from buffer"""
    return _frame_format_parse_with_crc(PROFILE_BULK_CONFIG, buffer)


def encode_profile_network(
    msg_id: int,
    payload: bytes,
    seq: int = 0,
    sys_id: int = 0,
    comp_id: int = 0
) -> bytes:
    """Encode using Profile Network (Basic + ExtendedMultiSystemStream)
    
    Args:
        msg_id: 16-bit message ID with package ID in upper 8 bits: (pkg_id << 8) | msg_id
        payload: Message payload bytes
        seq: Sequence number
        sys_id: System ID
        comp_id: Component ID
    
    Returns:
        Encoded frame as bytes
    """
    return _frame_format_encode_with_crc(
        PROFILE_NETWORK_CONFIG, msg_id, payload,
        seq=seq, sys_id=sys_id, comp_id=comp_id
    )


def parse_profile_network_buffer(buffer: bytes) -> FrameMsgInfo:
    """Parse Profile Network frame from buffer"""
    return _frame_format_parse_with_crc(PROFILE_NETWORK_CONFIG, buffer)


# =============================================================================
# Generic Encoder/Parser Functions
# =============================================================================

def encode_frame(
    config: FrameFormatConfig,
    msg_id: int,
    payload: bytes,
    seq: int = 0,
    sys_id: int = 0,
    comp_id: int = 0,
    pkg_id: int = 0
) -> bytes:
    """
    Generic encode function that works with any FrameFormatConfig.
    
    Args:
        config: Frame format configuration
        msg_id: Message ID (0-255)
        payload: Message payload bytes
        seq: Sequence number (for profiles with sequence)
        sys_id: System ID (for profiles with routing)
        comp_id: Component ID (for profiles with routing)
        pkg_id: Package ID (for profiles with package namespacing)
    
    Returns:
        Encoded frame as bytes
    """
    if config.has_crc:
        return _frame_format_encode_with_crc(
            config, msg_id, payload,
            seq=seq, sys_id=sys_id, comp_id=comp_id, pkg_id=pkg_id
        )
    else:
        return _frame_format_encode_minimal(config, msg_id, payload)


def parse_frame_buffer(
    config: FrameFormatConfig,
    buffer: bytes,
    get_msg_length: Callable[[int], int] = None
) -> FrameMsgInfo:
    """
    Generic parse function that works with any FrameFormatConfig.
    
    Args:
        config: Frame format configuration
        buffer: Buffer containing the complete frame
        get_msg_length: Callback to get expected message length (required for minimal frames)
    
    Returns:
        FrameMsgInfo with valid=True if frame is valid
    """
    if config.has_crc:
        return _frame_format_parse_with_crc(config, buffer)
    else:
        if get_msg_length is None:
            raise ValueError("get_msg_length callback required for minimal frames")
        return _frame_format_parse_minimal(config, buffer, get_msg_length)


def create_custom_config(
    name: str,
    header_type: HeaderType,
    payload_type: PayloadType,
    has_length: bool = True,
    length_bytes: int = 1,
    has_crc: bool = True,
    has_pkg_id: bool = False,
    has_seq: bool = False,
    has_sys_id: bool = False,
    has_comp_id: bool = False
) -> FrameFormatConfig:
    """
    Create a custom frame format configuration.
    
    This allows creating any header+payload combination for specialized use cases.
    
    Args:
        name: Name for the custom configuration
        header_type: Header type (NONE, TINY, or BASIC)
        payload_type: Payload type (used for start byte calculation)
        has_length: Whether the frame includes a length field
        length_bytes: Number of bytes for length field (1 or 2)
        has_crc: Whether the frame includes CRC
        has_pkg_id: Whether the frame includes package ID
        has_seq: Whether the frame includes sequence number
        has_sys_id: Whether the frame includes system ID
        has_comp_id: Whether the frame includes component ID
    
    Returns:
        FrameFormatConfig instance
    """
    # Calculate start bytes based on header type
    if header_type == HeaderType.NONE:
        num_start_bytes = 0
        start_byte1 = 0
        start_byte2 = 0
    elif header_type == HeaderType.TINY:
        num_start_bytes = 1
        start_byte1 = PAYLOAD_TYPE_BASE + payload_type.value
        start_byte2 = 0
    else:  # BASIC
        num_start_bytes = 2
        start_byte1 = BASIC_START_BYTE
        start_byte2 = PAYLOAD_TYPE_BASE + payload_type.value
    
    # Calculate header size
    header_size = num_start_bytes + 1  # start bytes + msg_id
    if has_seq:
        header_size += 1
    if has_sys_id:
        header_size += 1
    if has_comp_id:
        header_size += 1
    if has_length:
        header_size += length_bytes
    if has_pkg_id:
        header_size += 1
    
    # Calculate footer size
    footer_size = 2 if has_crc else 0
    
    return FrameFormatConfig(
        name=name,
        header_type=header_type,
        payload_type=payload_type,
        num_start_bytes=num_start_bytes,
        start_byte1=start_byte1,
        start_byte2=start_byte2,
        header_size=header_size,
        footer_size=footer_size,
        has_length=has_length,
        length_bytes=length_bytes,
        has_crc=has_crc,
        has_pkg_id=has_pkg_id,
        has_seq=has_seq,
        has_sys_id=has_sys_id,
        has_comp_id=has_comp_id
    )


# =============================================================================
# BufferReader - Iterate through multiple frames in a buffer
# =============================================================================

class BufferReader:
    """
    BufferReader - Iterate through a buffer parsing multiple frames.
    
    Usage:
        reader = BufferReader(PROFILE_STANDARD_CONFIG, buffer)
        while True:
            result = reader.next()
            if not result.valid:
                break
            # Process result.msg_id, result.msg_data, result.msg_len
    
    For minimal profiles that need get_msg_length:
        reader = BufferReader(PROFILE_SENSOR_CONFIG, buffer, get_msg_length)
    """
    
    def __init__(self, config: FrameFormatConfig, buffer: bytes, 
                 get_msg_length: Callable[[int], Optional[int]] = None):
        """
        Initialize buffer reader.
        
        Args:
            config: Frame format configuration
            buffer: Buffer containing one or more frames
            get_msg_length: Callback to get message length (required for minimal frames)
        """
        self._config = config
        self._buffer = buffer
        self._size = len(buffer)
        self._offset = 0
        self._get_msg_length = get_msg_length
    
    def next(self) -> FrameMsgInfo:
        """
        Parse the next frame in the buffer.
        
        Returns:
            FrameMsgInfo with valid=True if successful, valid=False if no more frames.
        """
        if self._offset >= self._size:
            return FrameMsgInfo()
        
        remaining = self._buffer[self._offset:]
        
        if self._config.has_crc or self._config.has_length:
            result = _frame_format_parse_with_crc(self._config, remaining)
        else:
            if self._get_msg_length is None:
                # No more valid data to parse without length callback
                self._offset = self._size
                return FrameMsgInfo()
            result = _frame_format_parse_minimal(self._config, remaining, self._get_msg_length)
        
        if result.valid:
            frame_size = self._config.overhead + result.msg_len
            self._offset += frame_size
        else:
            # No more valid frames - stop parsing
            self._offset = self._size
        
        return result
    
    def reset(self):
        """Reset the reader to the beginning of the buffer."""
        self._offset = 0
    
    @property
    def offset(self) -> int:
        """Get the current offset in the buffer."""
        return self._offset
    
    @property
    def remaining(self) -> int:
        """Get the remaining bytes in the buffer."""
        return max(0, self._size - self._offset)
    
    def has_more(self) -> bool:
        """Check if there are more bytes to parse."""
        return self._offset < self._size


# =============================================================================
# BufferWriter - Encode multiple frames with automatic offset tracking
# =============================================================================

class BufferWriter:
    """
    BufferWriter - Encode multiple frames into a buffer with automatic offset tracking.
    
    Usage:
        writer = BufferWriter(PROFILE_STANDARD_CONFIG, 1024)
        writer.write(0x01, msg1_payload)
        writer.write(0x02, msg2_payload)
        encoded_data = writer.data()
        total_bytes = writer.size()
    
    For profiles with extra header fields:
        writer = BufferWriter(PROFILE_NETWORK_CONFIG, 1024)
        writer.write(0x01, payload, seq=1, sys_id=1, comp_id=1)
    """
    
    def __init__(self, config: FrameFormatConfig, capacity: int):
        """
        Initialize buffer writer.
        
        Args:
            config: Frame format configuration
            capacity: Maximum buffer capacity in bytes
        """
        self._config = config
        self._capacity = capacity
        self._buffer = bytearray(capacity)
        self._offset = 0
    
    def write(self, msg_id: int, payload: bytes, seq: int = 0, 
              sys_id: int = 0, comp_id: int = 0) -> int:
        """
        Write a message to the buffer.
        
        Args:
            msg_id: Message ID (or 16-bit with pkg_id for extended profiles)
            payload: Message payload bytes
            seq: Sequence number (for profiles with sequence)
            sys_id: System ID (for profiles with routing)
            comp_id: Component ID (for profiles with routing)
        
        Returns:
            Number of bytes written, or 0 on failure.
        """
        if self._config.has_crc or self._config.has_length:
            encoded = _frame_format_encode_with_crc(
                self._config, msg_id, payload, seq=seq, sys_id=sys_id, comp_id=comp_id
            )
        else:
            encoded = _frame_format_encode_minimal(self._config, msg_id, payload)
        
        written = len(encoded)
        if self._offset + written > self._capacity:
            return 0
        
        self._buffer[self._offset:self._offset + written] = encoded
        self._offset += written
        return written
    
    def reset(self):
        """Reset the writer to the beginning of the buffer."""
        self._offset = 0
    
    def size(self) -> int:
        """Get the total number of bytes written."""
        return self._offset
    
    @property
    def remaining(self) -> int:
        """Get the remaining capacity in the buffer."""
        return max(0, self._capacity - self._offset)
    
    def data(self) -> bytes:
        """Get the written data as bytes."""
        return bytes(self._buffer[:self._offset])


# =============================================================================
# AccumulatingReader - Unified parser for buffer and byte-by-byte streaming
# =============================================================================

class AccumulatingReaderState(Enum):
    """Parser state for streaming mode"""
    IDLE = 0
    LOOKING_FOR_START1 = 1
    LOOKING_FOR_START2 = 2
    COLLECTING_HEADER = 3
    COLLECTING_PAYLOAD = 4
    BUFFER_MODE = 5


class AccumulatingReader:
    """
    AccumulatingReader - Unified parser for buffer and byte-by-byte streaming input.
    
    Handles partial messages across buffer boundaries and supports both:
    - Buffer mode: add_data() for processing chunks of data
    - Stream mode: push_byte() for byte-by-byte processing (e.g., UART)
    
    Buffer mode usage:
        reader = AccumulatingReader(PROFILE_STANDARD_CONFIG)
        reader.add_data(chunk1)
        while True:
            result = reader.next()
            if not result.valid:
                break
            # Process complete messages
    
    Stream mode usage:
        reader = AccumulatingReader(PROFILE_STANDARD_CONFIG)
        while receiving:
            byte = read_byte()
            result = reader.push_byte(byte)
            if result.valid:
                # Process complete message
    
    For minimal profiles:
        reader = AccumulatingReader(PROFILE_SENSOR_CONFIG, get_msg_length=get_message_length)
    """
    
    def __init__(self, config: FrameFormatConfig, 
                 get_msg_length: Callable[[int], Optional[int]] = None,
                 buffer_size: int = 1024):
        """
        Initialize accumulating reader.
        
        Args:
            config: Frame format configuration
            get_msg_length: Callback to get message length (required for minimal profiles)
            buffer_size: Size of internal buffer for partial messages (default: 1024)
        """
        self._config = config
        self._get_msg_length = get_msg_length
        self._buffer_size = buffer_size
        
        # Internal buffer for partial messages
        self._internal_buffer = bytearray(buffer_size)
        self._internal_data_len = 0
        self._expected_frame_size = 0
        self._state = AccumulatingReaderState.IDLE
        
        # Buffer mode state
        self._current_buffer: Optional[bytes] = None
        self._current_size = 0
        self._current_offset = 0
    
    # =========================================================================
    # Buffer Mode API
    # =========================================================================
    
    def add_data(self, buffer: bytes):
        """
        Add a new buffer of data to process.
        
        If there was a partial message from the previous buffer, data is appended
        to the internal buffer to complete it.
        
        Note: Do not mix add_data() with push_byte() on the same reader instance.
        
        Args:
            buffer: New data to process
        """
        self._current_buffer = buffer
        self._current_size = len(buffer)
        self._current_offset = 0
        self._state = AccumulatingReaderState.BUFFER_MODE
        
        # If we have partial data in internal buffer, try to complete it
        if self._internal_data_len > 0:
            space_available = self._buffer_size - self._internal_data_len
            bytes_to_copy = min(len(buffer), space_available)
            self._internal_buffer[self._internal_data_len:self._internal_data_len + bytes_to_copy] = buffer[:bytes_to_copy]
            self._internal_data_len += bytes_to_copy
    
    def next(self) -> FrameMsgInfo:
        """
        Parse the next frame (buffer mode).
        
        Returns:
            FrameMsgInfo with valid=True if successful, valid=False if no more complete frames.
        """
        if self._state != AccumulatingReaderState.BUFFER_MODE:
            return FrameMsgInfo()
        
        # First, try to complete a partial message from the internal buffer
        if self._internal_data_len > 0 and self._current_offset == 0:
            internal_bytes = bytes(self._internal_buffer[:self._internal_data_len])
            result = self._parse_buffer(internal_bytes)
            
            if result.valid:
                frame_size = self._config.overhead + result.msg_len
                # Calculate how many bytes from current buffer were consumed
                partial_len = self._internal_data_len - self._current_size if self._internal_data_len > self._current_size else 0
                bytes_from_current = frame_size - partial_len if frame_size > partial_len else 0
                self._current_offset = bytes_from_current
                
                # Clear internal buffer state
                self._internal_data_len = 0
                self._expected_frame_size = 0
                
                return result
            else:
                # Still not enough data for a complete message
                return FrameMsgInfo()
        
        # Parse from current buffer
        if self._current_buffer is None or self._current_offset >= self._current_size:
            return FrameMsgInfo()
        
        remaining = self._current_buffer[self._current_offset:]
        result = self._parse_buffer(remaining)
        
        if result.valid:
            frame_size = self._config.overhead + result.msg_len
            self._current_offset += frame_size
            return result
        
        # Parse failed - might be partial message at end of buffer
        remaining_len = self._current_size - self._current_offset
        if remaining_len > 0 and remaining_len < self._buffer_size:
            self._internal_buffer[:remaining_len] = remaining
            self._internal_data_len = remaining_len
            self._current_offset = self._current_size
        
        return FrameMsgInfo()
    
    # =========================================================================
    # Stream Mode API
    # =========================================================================
    
    def push_byte(self, byte: int) -> FrameMsgInfo:
        """
        Push a single byte for parsing (stream mode).
        
        Returns:
            FrameMsgInfo with valid=True when a complete valid message is received.
        
        Note: Do not mix push_byte() with add_data() on the same reader instance.
        """
        # Initialize state on first byte if idle
        if self._state == AccumulatingReaderState.IDLE or self._state == AccumulatingReaderState.BUFFER_MODE:
            self._state = AccumulatingReaderState.LOOKING_FOR_START1
            self._internal_data_len = 0
            self._expected_frame_size = 0
        
        if self._state == AccumulatingReaderState.LOOKING_FOR_START1:
            return self._handle_looking_for_start1(byte)
        elif self._state == AccumulatingReaderState.LOOKING_FOR_START2:
            return self._handle_looking_for_start2(byte)
        elif self._state == AccumulatingReaderState.COLLECTING_HEADER:
            return self._handle_collecting_header(byte)
        elif self._state == AccumulatingReaderState.COLLECTING_PAYLOAD:
            return self._handle_collecting_payload(byte)
        else:
            self._state = AccumulatingReaderState.LOOKING_FOR_START1
            return FrameMsgInfo()
    
    def _handle_looking_for_start1(self, byte: int) -> FrameMsgInfo:
        """Handle LOOKING_FOR_START1 state"""
        if self._config.num_start_bytes == 0:
            # No start bytes - this byte is the beginning of the frame
            self._internal_buffer[0] = byte
            self._internal_data_len = 1
            
            if not self._config.has_length and not self._config.has_crc:
                return self._handle_minimal_msg_id(byte)
            else:
                self._state = AccumulatingReaderState.COLLECTING_HEADER
        else:
            if byte == self._config.start_byte1:
                self._internal_buffer[0] = byte
                self._internal_data_len = 1
                
                if self._config.num_start_bytes == 1:
                    self._state = AccumulatingReaderState.COLLECTING_HEADER
                else:
                    self._state = AccumulatingReaderState.LOOKING_FOR_START2
        
        return FrameMsgInfo()
    
    def _handle_looking_for_start2(self, byte: int) -> FrameMsgInfo:
        """Handle LOOKING_FOR_START2 state"""
        if byte == self._config.start_byte2:
            self._internal_buffer[self._internal_data_len] = byte
            self._internal_data_len += 1
            self._state = AccumulatingReaderState.COLLECTING_HEADER
        elif byte == self._config.start_byte1:
            # Might be start of new frame - restart
            self._internal_buffer[0] = byte
            self._internal_data_len = 1
        else:
            # Invalid - go back to looking for start
            self._state = AccumulatingReaderState.LOOKING_FOR_START1
            self._internal_data_len = 0
        
        return FrameMsgInfo()
    
    def _handle_collecting_header(self, byte: int) -> FrameMsgInfo:
        """Handle COLLECTING_HEADER state"""
        if self._internal_data_len >= self._buffer_size:
            # Buffer overflow - reset
            self._state = AccumulatingReaderState.LOOKING_FOR_START1
            self._internal_data_len = 0
            return FrameMsgInfo()
        
        self._internal_buffer[self._internal_data_len] = byte
        self._internal_data_len += 1
        
        # Check if we have enough header bytes to determine frame size
        if self._internal_data_len >= self._config.header_size:
            if not self._config.has_length and not self._config.has_crc:
                # For minimal profiles, we need the callback to determine length
                msg_id = self._internal_buffer[self._config.header_size - 1]
                if self._get_msg_length:
                    msg_len = self._get_msg_length(msg_id)
                    if msg_len is not None:
                        self._expected_frame_size = self._config.header_size + msg_len
                        
                        if self._expected_frame_size > self._buffer_size:
                            self._state = AccumulatingReaderState.LOOKING_FOR_START1
                            self._internal_data_len = 0
                            return FrameMsgInfo()
                        
                        if msg_len == 0:
                            # Zero-length message - complete!
                            result = FrameMsgInfo(
                                valid=True,
                                msg_id=msg_id,
                                msg_len=0,
                                msg_data=b''
                            )
                            self._state = AccumulatingReaderState.LOOKING_FOR_START1
                            self._internal_data_len = 0
                            self._expected_frame_size = 0
                            return result
                        
                        self._state = AccumulatingReaderState.COLLECTING_PAYLOAD
                    else:
                        self._state = AccumulatingReaderState.LOOKING_FOR_START1
                        self._internal_data_len = 0
                else:
                    self._state = AccumulatingReaderState.LOOKING_FOR_START1
                    self._internal_data_len = 0
            else:
                # Calculate payload length from header
                len_offset = self._config.num_start_bytes
                
                # Skip seq, sys_id, comp_id if present
                if self._config.has_seq:
                    len_offset += 1
                if self._config.has_sys_id:
                    len_offset += 1
                if self._config.has_comp_id:
                    len_offset += 1
                
                payload_len = 0
                if self._config.has_length:
                    if self._config.length_bytes == 1:
                        payload_len = self._internal_buffer[len_offset]
                    else:
                        payload_len = self._internal_buffer[len_offset] | (self._internal_buffer[len_offset + 1] << 8)
                
                self._expected_frame_size = self._config.overhead + payload_len
                
                if self._expected_frame_size > self._buffer_size:
                    self._state = AccumulatingReaderState.LOOKING_FOR_START1
                    self._internal_data_len = 0
                    return FrameMsgInfo()
                
                # Check if we already have the complete frame
                if self._internal_data_len >= self._expected_frame_size:
                    return self._validate_and_return()
                
                self._state = AccumulatingReaderState.COLLECTING_PAYLOAD
        
        return FrameMsgInfo()
    
    def _handle_collecting_payload(self, byte: int) -> FrameMsgInfo:
        """Handle COLLECTING_PAYLOAD state"""
        if self._internal_data_len >= self._buffer_size:
            # Buffer overflow - reset
            self._state = AccumulatingReaderState.LOOKING_FOR_START1
            self._internal_data_len = 0
            return FrameMsgInfo()
        
        self._internal_buffer[self._internal_data_len] = byte
        self._internal_data_len += 1
        
        if self._internal_data_len >= self._expected_frame_size:
            return self._validate_and_return()
        
        return FrameMsgInfo()
    
    def _handle_minimal_msg_id(self, msg_id: int) -> FrameMsgInfo:
        """Handle minimal profile msg_id"""
        if self._get_msg_length:
            msg_len = self._get_msg_length(msg_id)
            if msg_len is not None:
                self._expected_frame_size = self._config.header_size + msg_len
                
                if self._expected_frame_size > self._buffer_size:
                    self._state = AccumulatingReaderState.LOOKING_FOR_START1
                    self._internal_data_len = 0
                    return FrameMsgInfo()
                
                if msg_len == 0:
                    # Zero-length message - complete!
                    result = FrameMsgInfo(
                        valid=True,
                        msg_id=msg_id,
                        msg_len=0,
                        msg_data=b''
                    )
                    self._state = AccumulatingReaderState.LOOKING_FOR_START1
                    self._internal_data_len = 0
                    self._expected_frame_size = 0
                    return result
                
                self._state = AccumulatingReaderState.COLLECTING_PAYLOAD
            else:
                self._state = AccumulatingReaderState.LOOKING_FOR_START1
                self._internal_data_len = 0
        else:
            self._state = AccumulatingReaderState.LOOKING_FOR_START1
            self._internal_data_len = 0
        
        return FrameMsgInfo()
    
    def _validate_and_return(self) -> FrameMsgInfo:
        """Validate and return completed message"""
        internal_bytes = bytes(self._internal_buffer[:self._internal_data_len])
        result = self._parse_buffer(internal_bytes)
        
        # Reset state for next message
        self._state = AccumulatingReaderState.LOOKING_FOR_START1
        self._internal_data_len = 0
        self._expected_frame_size = 0
        
        return result
    
    def _parse_buffer(self, buffer: bytes) -> FrameMsgInfo:
        """Parse a buffer using the appropriate parser"""
        if self._config.has_crc or self._config.has_length:
            return _frame_format_parse_with_crc(self._config, buffer)
        else:
            if self._get_msg_length is None:
                return FrameMsgInfo()
            return _frame_format_parse_minimal(self._config, buffer, self._get_msg_length)
    
    # =========================================================================
    # Common API
    # =========================================================================
    
    def has_more(self) -> bool:
        """Check if there might be more data to parse (buffer mode only)."""
        if self._state != AccumulatingReaderState.BUFFER_MODE:
            return False
        return (self._internal_data_len > 0) or (self._current_buffer is not None and self._current_offset < self._current_size)
    
    def has_partial(self) -> bool:
        """Check if there's a partial message waiting for more data."""
        return self._internal_data_len > 0
    
    def partial_size(self) -> int:
        """Get the size of the partial message data (0 if none)."""
        return self._internal_data_len
    
    @property
    def state(self) -> AccumulatingReaderState:
        """Get current parser state (for debugging)."""
        return self._state
    
    def reset(self):
        """Reset the reader, clearing any partial message data."""
        self._internal_data_len = 0
        self._expected_frame_size = 0
        self._state = AccumulatingReaderState.IDLE
        self._current_buffer = None
        self._current_size = 0
        self._current_offset = 0


# =============================================================================
# Convenience Type Aliases for standard profiles
# =============================================================================

def create_profile_standard_reader(buffer: bytes) -> BufferReader:
    """Create a BufferReader for Profile Standard"""
    return BufferReader(PROFILE_STANDARD_CONFIG, buffer)

def create_profile_standard_writer(capacity: int = 1024) -> BufferWriter:
    """Create a BufferWriter for Profile Standard"""
    return BufferWriter(PROFILE_STANDARD_CONFIG, capacity)

def create_profile_standard_accumulating_reader(buffer_size: int = 1024) -> AccumulatingReader:
    """Create an AccumulatingReader for Profile Standard"""
    return AccumulatingReader(PROFILE_STANDARD_CONFIG, buffer_size=buffer_size)

def create_profile_sensor_reader(buffer: bytes, get_msg_length: Callable[[int], Optional[int]]) -> BufferReader:
    """Create a BufferReader for Profile Sensor"""
    return BufferReader(PROFILE_SENSOR_CONFIG, buffer, get_msg_length)

def create_profile_sensor_writer(capacity: int = 1024) -> BufferWriter:
    """Create a BufferWriter for Profile Sensor"""
    return BufferWriter(PROFILE_SENSOR_CONFIG, capacity)

def create_profile_sensor_accumulating_reader(get_msg_length: Callable[[int], Optional[int]], buffer_size: int = 1024) -> AccumulatingReader:
    """Create an AccumulatingReader for Profile Sensor"""
    return AccumulatingReader(PROFILE_SENSOR_CONFIG, get_msg_length=get_msg_length, buffer_size=buffer_size)

def create_profile_ipc_reader(buffer: bytes, get_msg_length: Callable[[int], Optional[int]]) -> BufferReader:
    """Create a BufferReader for Profile IPC"""
    return BufferReader(PROFILE_IPC_CONFIG, buffer, get_msg_length)

def create_profile_ipc_writer(capacity: int = 1024) -> BufferWriter:
    """Create a BufferWriter for Profile IPC"""
    return BufferWriter(PROFILE_IPC_CONFIG, capacity)

def create_profile_ipc_accumulating_reader(get_msg_length: Callable[[int], Optional[int]], buffer_size: int = 1024) -> AccumulatingReader:
    """Create an AccumulatingReader for Profile IPC"""
    return AccumulatingReader(PROFILE_IPC_CONFIG, get_msg_length=get_msg_length, buffer_size=buffer_size)

def create_profile_bulk_reader(buffer: bytes) -> BufferReader:
    """Create a BufferReader for Profile Bulk"""
    return BufferReader(PROFILE_BULK_CONFIG, buffer)

def create_profile_bulk_writer(capacity: int = 1024) -> BufferWriter:
    """Create a BufferWriter for Profile Bulk"""
    return BufferWriter(PROFILE_BULK_CONFIG, capacity)

def create_profile_bulk_accumulating_reader(buffer_size: int = 1024) -> AccumulatingReader:
    """Create an AccumulatingReader for Profile Bulk"""
    return AccumulatingReader(PROFILE_BULK_CONFIG, buffer_size=buffer_size)

def create_profile_network_reader(buffer: bytes) -> BufferReader:
    """Create a BufferReader for Profile Network"""
    return BufferReader(PROFILE_NETWORK_CONFIG, buffer)

def create_profile_network_writer(capacity: int = 1024) -> BufferWriter:
    """Create a BufferWriter for Profile Network"""
    return BufferWriter(PROFILE_NETWORK_CONFIG, capacity)

def create_profile_network_accumulating_reader(buffer_size: int = 1024) -> AccumulatingReader:
    """Create an AccumulatingReader for Profile Network"""
    return AccumulatingReader(PROFILE_NETWORK_CONFIG, buffer_size=buffer_size)
