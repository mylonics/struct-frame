"""
Frame Profiles - Pre-defined Header + Payload combinations

This module provides ready-to-use encode/parse functions for frame format profiles:
- ProfileStandard: Basic + Default (General serial/UART)
- ProfileSensor: Tiny + Minimal (Low-bandwidth sensors)
- ProfileIPC: None + Minimal (Trusted inter-process communication)
- ProfileBulk: Basic + Extended (Large data transfers with package namespacing)
- ProfileNetwork: Basic + ExtendedMultiSystemStream (Multi-system networked communication)

Each profile provides:
- Encoder: encode messages into a buffer
- BufferParser: parse/validate a complete frame in a buffer
- BufferReader: iterate through multiple frames in a buffer
- BufferWriter: encode multiple frames with automatic offset tracking
- AccumulatingReader: unified parser supporting both buffer chunks and byte-by-byte streaming

This module composes HeaderConfig + PayloadConfig for maximum code reuse,
matching the C++ frame_profiles.hpp pattern.
"""

from dataclasses import dataclass
from typing import Optional, Callable, List, NamedTuple
from enum import Enum

try:
    from .frame_headers import (
        HeaderType, HeaderConfig,
        BASIC_START_BYTE, PAYLOAD_TYPE_BASE,
        HEADER_NONE_CONFIG, HEADER_TINY_CONFIG, HEADER_BASIC_CONFIG
    )
    from .payload_types import (
        PayloadType, PayloadConfig,
        PAYLOAD_MINIMAL_CONFIG, PAYLOAD_DEFAULT_CONFIG, PAYLOAD_EXTENDED_CONFIG,
        PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG
    )
    from .frame_base import fletcher_checksum, FrameMsgInfo, FrameChecksum, ParserState
except ImportError:
    from frame_headers import (
        HeaderType, HeaderConfig,
        BASIC_START_BYTE, PAYLOAD_TYPE_BASE,
        HEADER_NONE_CONFIG, HEADER_TINY_CONFIG, HEADER_BASIC_CONFIG
    )
    from payload_types import (
        PayloadType, PayloadConfig,
        PAYLOAD_MINIMAL_CONFIG, PAYLOAD_DEFAULT_CONFIG, PAYLOAD_EXTENDED_CONFIG,
        PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG
    )
    from frame_base import fletcher_checksum, FrameMsgInfo, FrameChecksum, ParserState


# =============================================================================
# MessageInfo - Unified message information type
# =============================================================================

class MessageInfo(NamedTuple):
    """
    Unified message information for parsing.
    
    This type combines message size and magic numbers into a single lookup result,
    simplifying the parser API by requiring only one callback instead of two.
    
    Attributes:
        size: Message payload size in bytes
        magic1: First magic number for CRC calculation
        magic2: Second magic number for CRC calculation
    """
    size: int
    magic1: int = 0
    magic2: int = 0


# =============================================================================
# Profile Configuration - Composed from Header + Payload configs
# =============================================================================

@dataclass
class ProfileConfig:
    """
    Profile configuration - combines a HeaderConfig with a PayloadConfig.
    
    This mirrors the C++ ProfileConfig template, providing composed configurations
    for maximum code reuse.
    
    Usage:
        config = ProfileConfig(HEADER_BASIC_CONFIG, PAYLOAD_DEFAULT_CONFIG)
    """
    header: HeaderConfig
    payload: PayloadConfig
    name: str = ""
    
    def __post_init__(self):
        """Generate name if not provided"""
        if not self.name:
            self.name = f"{self.header.name}{self.payload.name}"
    
    # Header properties
    @property
    def num_start_bytes(self) -> int:
        return self.header.num_start_bytes
    
    @property
    def header_type(self) -> HeaderType:
        return self.header.header_type
    
    # Payload properties
    @property
    def payload_type(self) -> PayloadType:
        return self.payload.payload_type
    
    @property
    def has_length(self) -> bool:
        return self.payload.has_length
    
    @property
    def length_bytes(self) -> int:
        return self.payload.length_bytes
    
    @property
    def has_crc(self) -> bool:
        return self.payload.has_crc
    
    @property
    def has_pkg_id(self) -> bool:
        return self.payload.has_package_id
    
    @property
    def has_seq(self) -> bool:
        return self.payload.has_sequence
    
    @property
    def has_sys_id(self) -> bool:
        return self.payload.has_system_id
    
    @property
    def has_comp_id(self) -> bool:
        return self.payload.has_component_id
    
    # Combined sizes
    @property
    def header_size(self) -> int:
        """Total header size (start bytes + payload header fields)"""
        return self.header.num_start_bytes + self.payload.header_size
    
    @property
    def footer_size(self) -> int:
        """Footer size (CRC bytes)"""
        return self.payload.footer_size
    
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
    
    def computed_start_byte1(self) -> int:
        """
        Compute start byte1 dynamically for headers that encode payload type.
        For Tiny header: 0x70 + payload_type
        """
        if self.header.encodes_payload_type and self.header.num_start_bytes == 1:
            return PAYLOAD_TYPE_BASE + self.payload.payload_type.value
        return self.header.start_bytes[0] if self.header.start_bytes else 0
    
    def computed_start_byte2(self) -> int:
        """
        Compute start byte2 dynamically for headers that encode payload type.
        For Basic header: start_byte1 is fixed (0x90), start_byte2 = 0x70 + payload_type
        """
        if self.header.encodes_payload_type and self.header.num_start_bytes == 2:
            return PAYLOAD_TYPE_BASE + self.payload.payload_type.value
        return self.header.start_bytes[1] if len(self.header.start_bytes) > 1 else 0
    
    # Convenience properties for backwards compatibility
    @property
    def start_byte1(self) -> int:
        return self.computed_start_byte1()
    
    @property
    def start_byte2(self) -> int:
        return self.computed_start_byte2()


# =============================================================================
# Standard Profile Configurations
# =============================================================================

# Profile Standard: Basic + Default
# Frame: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
PROFILE_STANDARD_CONFIG = ProfileConfig(
    header=HEADER_BASIC_CONFIG,
    payload=PAYLOAD_DEFAULT_CONFIG,
    name="ProfileStandard"
)

# Profile Sensor: Tiny + Minimal
# Frame: [0x70] [MSG_ID] [PAYLOAD]
PROFILE_SENSOR_CONFIG = ProfileConfig(
    header=HEADER_TINY_CONFIG,
    payload=PAYLOAD_MINIMAL_CONFIG,
    name="ProfileSensor"
)

# Profile IPC: None + Minimal
# Frame: [MSG_ID] [PAYLOAD]
PROFILE_IPC_CONFIG = ProfileConfig(
    header=HEADER_NONE_CONFIG,
    payload=PAYLOAD_MINIMAL_CONFIG,
    name="ProfileIPC"
)

# Profile Bulk: Basic + Extended
# Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
PROFILE_BULK_CONFIG = ProfileConfig(
    header=HEADER_BASIC_CONFIG,
    payload=PAYLOAD_EXTENDED_CONFIG,
    name="ProfileBulk"
)

# Profile Network: Basic + ExtendedMultiSystemStream
# Frame: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]
PROFILE_NETWORK_CONFIG = ProfileConfig(
    header=HEADER_BASIC_CONFIG,
    payload=PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG,
    name="ProfileNetwork"
)


# =============================================================================
# Generic Frame Encoder/Parser Functions
# =============================================================================

def encode_message(
    config: ProfileConfig,
    msg,
    seq: int = 0,
    sys_id: int = 0,
    comp_id: int = 0
) -> bytes:
    """
    Encode a message object.
    
    Automatically extracts msg_id, payload, and magic numbers from the message object.
    
    Args:
        config: Profile configuration
        msg: Message object with MSG_ID/msg_id, data()/pack() methods, and MAGIC1/MAGIC2 attributes
        seq: Sequence number (for profiles with sequence)
        sys_id: System ID (for profiles with routing)
        comp_id: Component ID (for profiles with routing)
    
    Returns:
        Encoded frame as bytes
    """
    if config.has_crc or config.has_length:
        return _frame_format_encode_with_crc(config, msg, seq, sys_id, comp_id)
    else:
        return _frame_format_encode_minimal(config, msg)


def _frame_format_encode_with_crc(
    config: ProfileConfig,
    msg,
    seq: int = 0,
    sys_id: int = 0,
    comp_id: int = 0
) -> bytes:
    """
    Generic encode function for frames with CRC.
    
    Args:
        config: Profile configuration
        msg: Message object with MSG_ID/msg_id, data()/pack() methods, and MAGIC1/MAGIC2 attributes
        seq: Sequence number (for profiles with sequence)
        sys_id: System ID (for profiles with routing)
        comp_id: Component ID (for profiles with routing)
    
    Returns:
        Encoded frame as bytes
    """
    # Get message ID
    msg_id = getattr(msg, 'MSG_ID', None) or getattr(msg, 'msg_id', None)
    if msg_id is None:
        raise ValueError("Message object must have MSG_ID or msg_id attribute")
    
    # Get payload
    # For minimal profiles (no length field), variable messages must use pack_max_size()
    # Non-variable messages and variable messages on profiles with length fields use pack()
    is_variable = getattr(msg, 'IS_VARIABLE', False)
    if is_variable and not config.payload.has_length:
        # Variable message on minimal profile (ProfileSensor/ProfileIPC) - need MAX_SIZE
        if hasattr(msg, 'serialize_max_size') and callable(msg.serialize_max_size):
            payload = msg.serialize_max_size()
        else:
            # Fallback to serialize() if serialize_max_size doesn't exist (shouldn't happen)
            payload = msg.serialize()
    elif hasattr(msg, 'serialize') and callable(msg.serialize):
        # Standard path: serialize() returns variable encoding for variable messages,
        # MAX_SIZE for non-variable messages
        payload = msg.serialize()
    else:
        raise ValueError("Message object must have serialize() method")
    
    # Get magic numbers
    msg_class = type(msg)
    magic1 = getattr(msg_class, 'MAGIC1', 0)
    magic2 = getattr(msg_class, 'MAGIC2', 0)
    
    payload_size = len(payload)
    
    if config.max_payload is not None and payload_size > config.max_payload:
        raise ValueError(f"Payload size {payload_size} exceeds maximum {config.max_payload}")
    
    output = []
    
    # Write start bytes (use computed values for dynamic payload type encoding)
    if config.num_start_bytes >= 1:
        output.append(config.computed_start_byte1())
    if config.num_start_bytes >= 2:
        output.append(config.computed_start_byte2())
    
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
        crc = fletcher_checksum(output, crc_start, init1=magic1, init2=magic2)
        output.append(crc.byte1)
        output.append(crc.byte2)
    
    return bytes(output)


def _frame_format_encode_minimal(
    config: ProfileConfig,
    msg
) -> bytes:
    """
    Generic encode function for minimal frames (no length, no CRC).
    
    NOTE: Minimal profiles do NOT support variable-length encoding!
    Variable messages are always encoded at MAX_SIZE for minimal profiles
    because the parser has no length field and cannot determine message boundaries.
    
    Args:
        config: Profile configuration
        msg: Message object with MSG_ID/msg_id and data()/pack() methods
    
    Returns:
        Encoded frame as bytes
    """
    # Get message ID
    msg_id = getattr(msg, 'MSG_ID', None) or getattr(msg, 'msg_id', None)
    if msg_id is None:
        raise ValueError("Message object must have MSG_ID or msg_id attribute")
    
    # Get payload - ALWAYS use MAX_SIZE for minimal profiles
    # For variable messages, use pack_max_size() if available
    # For non-variable messages, pack() already returns MAX_SIZE
    is_variable = getattr(msg, 'IS_VARIABLE', False)
    if is_variable and hasattr(msg, 'serialize_max_size') and callable(msg.serialize_max_size):
        payload = msg.serialize_max_size()
    elif hasattr(msg, 'serialize') and callable(msg.serialize):
        payload = msg.serialize()
    else:
        raise ValueError("Message object must have serialize() or serialize_max_size() method")
    
    output = []
    
    # Write start bytes (use computed values for dynamic payload type encoding)
    if config.num_start_bytes >= 1:
        output.append(config.computed_start_byte1())
    if config.num_start_bytes >= 2:
        output.append(config.computed_start_byte2())
    
    # Write message ID
    output.append(msg_id & 0xFF)
    
    # Write payload
    output.extend(payload)
    
    return bytes(output)


def _frame_format_parse_with_crc(
    config: ProfileConfig,
    buffer: bytes,
    get_message_info: Callable[[int], Optional[MessageInfo]] = None
) -> FrameMsgInfo:
    """
    Generic parse function for frames with CRC.
    
    Args:
        config: Profile configuration
        buffer: Buffer containing the complete frame
        get_message_info: Optional function to get message info (size, magic1, magic2) for a message ID
    
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
        if buffer[idx] != config.computed_start_byte1():
            return result
        idx += 1
    if config.num_start_bytes >= 2:
        if buffer[idx] != config.computed_start_byte2():
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
    
    # Read package ID and message ID
    pkg_id = 0
    if config.has_pkg_id:
        # Read package ID and message ID as separate bytes
        pkg_id = buffer[idx]
        idx += 1
        local_msg_id = buffer[idx]
        idx += 1
        # Combine into 16-bit msg_id (pkg_id << 8 | msg_id)
        msg_id = (pkg_id << 8) | local_msg_id
    else:
        # Read message ID only
        msg_id = buffer[idx]
        idx += 1
    
    # Verify total size
    total_size = config.overhead + msg_len
    if length < total_size:
        return result
    
    # Verify CRC
    if config.has_crc:
        crc_len = total_size - crc_start - config.footer_size
        
        # Get magic numbers for this message type
        magic1, magic2 = 0, 0
        if get_message_info:
            msg_info = get_message_info(msg_id)
            if msg_info:
                magic1, magic2 = msg_info.magic1, msg_info.magic2
        
        calc_crc = fletcher_checksum(buffer, crc_start, crc_start + crc_len, init1=magic1, init2=magic2)
        recv_crc = FrameChecksum(buffer[total_size - 2], buffer[total_size - 1])
        if calc_crc.byte1 != recv_crc.byte1 or calc_crc.byte2 != recv_crc.byte2:
            return result
    
    # Extract message data
    msg_data = bytes(buffer[config.header_size:config.header_size + msg_len])
    
    result.valid = True
    result.msg_id = msg_id
    result.msg_len = msg_len
    result.frame_size = total_size
    result.msg_data = msg_data
    result.package_id = pkg_id
    result.sequence = seq
    result.system_id = sys_id
    result.component_id = comp_id
    
    return result


def _frame_format_parse_minimal(
    config: ProfileConfig,
    buffer: bytes,
    get_message_info: Callable[[int], Optional[MessageInfo]]
) -> FrameMsgInfo:
    """
    Generic parse function for minimal frames (requires get_message_info callback for size).
    
    Args:
        config: Profile configuration
        buffer: Buffer containing the complete frame
        get_message_info: Callback to get message info (size field used) for a msg_id
    
    Returns:
        FrameMsgInfo with valid=True if frame is valid
    """
    result = FrameMsgInfo()
    
    if len(buffer) < config.header_size:
        return result
    
    idx = 0
    
    # Verify start bytes
    if config.num_start_bytes >= 1:
        if buffer[idx] != config.computed_start_byte1():
            return result
        idx += 1
    if config.num_start_bytes >= 2:
        if buffer[idx] != config.computed_start_byte2():
            return result
        idx += 1
    
    # Read message ID
    msg_id = buffer[idx]
    
    # Get message info from callback
    msg_info = get_message_info(msg_id)
    if msg_info is None:
        return result
    msg_len = msg_info.size
    
    total_size = config.header_size + msg_len
    if len(buffer) < total_size:
        return result
    
    # Extract message data
    msg_data = bytes(buffer[config.header_size:config.header_size + msg_len])
    
    result.valid = True
    result.msg_id = msg_id
    result.msg_len = msg_len
    result.frame_size = total_size
    result.msg_data = msg_data
    
    return result


# =============================================================================
# Profile-Specific Convenience Functions
# =============================================================================

def encode_profile_standard(msg) -> bytes:
    """Encode using Profile Standard (Basic + Default)"""
    return _frame_format_encode_with_crc(PROFILE_STANDARD_CONFIG, msg)


def parse_profile_standard_buffer(buffer: bytes) -> FrameMsgInfo:
    """Parse Profile Standard frame from buffer"""
    return _frame_format_parse_with_crc(PROFILE_STANDARD_CONFIG, buffer)


def encode_profile_sensor(msg) -> bytes:
    """Encode using Profile Sensor (Tiny + Minimal)"""
    return _frame_format_encode_minimal(PROFILE_SENSOR_CONFIG, msg)


def parse_profile_sensor_buffer(buffer: bytes, get_message_info: Callable[[int], Optional[MessageInfo]]) -> FrameMsgInfo:
    """Parse Profile Sensor frame from buffer (requires get_message_info callback)"""
    return _frame_format_parse_minimal(PROFILE_SENSOR_CONFIG, buffer, get_message_info)


def encode_profile_ipc(msg) -> bytes:
    """Encode using Profile IPC (None + Minimal)"""
    return _frame_format_encode_minimal(PROFILE_IPC_CONFIG, msg)


def parse_profile_ipc_buffer(buffer: bytes, get_message_info: Callable[[int], Optional[MessageInfo]]) -> FrameMsgInfo:
    """Parse Profile IPC frame from buffer (requires get_message_info callback)"""
    return _frame_format_parse_minimal(PROFILE_IPC_CONFIG, buffer, get_message_info)


def encode_profile_bulk(msg) -> bytes:
    """Encode using Profile Bulk (Basic + Extended)
    
    Args:
        msg: Message object (msg_id should be 16-bit with package ID in upper 8 bits: (pkg_id << 8) | msg_id)
    
    Returns:
        Encoded frame as bytes
    """
    return _frame_format_encode_with_crc(PROFILE_BULK_CONFIG, msg)


def parse_profile_bulk_buffer(buffer: bytes) -> FrameMsgInfo:
    """Parse Profile Bulk frame from buffer"""
    return _frame_format_parse_with_crc(PROFILE_BULK_CONFIG, buffer)


def encode_profile_network(
    msg,
    seq: int = 0,
    sys_id: int = 0,
    comp_id: int = 0
) -> bytes:
    """Encode using Profile Network (Basic + ExtendedMultiSystemStream)
    
    Args:
        msg: Message object (msg_id should be 16-bit with package ID in upper 8 bits: (pkg_id << 8) | msg_id)
        seq: Sequence number
        sys_id: System ID
        comp_id: Component ID
    
    Returns:
        Encoded frame as bytes
    """
    return _frame_format_encode_with_crc(
        PROFILE_NETWORK_CONFIG, msg,
        seq=seq, sys_id=sys_id, comp_id=comp_id
    )


def parse_profile_network_buffer(buffer: bytes) -> FrameMsgInfo:
    """Parse Profile Network frame from buffer"""
    return _frame_format_parse_with_crc(PROFILE_NETWORK_CONFIG, buffer)


# =============================================================================
# Generic Encoder/Parser Functions
# =============================================================================

def encode_frame(
    config: ProfileConfig,
    msg,
    seq: int = 0,
    sys_id: int = 0,
    comp_id: int = 0
) -> bytes:
    """
    Generic encode function that works with any ProfileConfig.
    
    Args:
        config: Profile configuration
        msg: Message object with MSG_ID/msg_id, data()/pack() methods, and MAGIC1/MAGIC2 attributes
        seq: Sequence number (for profiles with sequence)
        sys_id: System ID (for profiles with routing)
        comp_id: Component ID (for profiles with routing)
    
    Returns:
        Encoded frame as bytes
    """
    if config.has_crc or config.has_length:
        return _frame_format_encode_with_crc(
            config, msg,
            seq=seq, sys_id=sys_id, comp_id=comp_id
        )
    else:
        return _frame_format_encode_minimal(config, msg)


def parse_frame_buffer(
    config: ProfileConfig,
    buffer: bytes,
    get_message_info: Callable[[int], Optional[MessageInfo]] = None
) -> FrameMsgInfo:
    """
    Generic parse function that works with any ProfileConfig.
    
    Args:
        config: Profile configuration
        buffer: Buffer containing the complete frame
        get_message_info: Callback to get message info (required for minimal frames, optional for CRC frames)
    
    Returns:
        FrameMsgInfo with valid=True if frame is valid
    """
    if config.has_crc or config.has_length:
        return _frame_format_parse_with_crc(config, buffer, get_message_info)
    else:
        if get_message_info is None:
            raise ValueError("get_message_info callback required for minimal frames")
        return _frame_format_parse_minimal(config, buffer, get_message_info)


def create_custom_config(
    header: HeaderConfig,
    payload: PayloadConfig,
    name: str = ""
) -> ProfileConfig:
    """
    Create a custom profile configuration from header and payload configs.
    
    This allows creating any header+payload combination for specialized use cases.
    
    Args:
        header: Header configuration
        payload: Payload configuration
        name: Optional name for the configuration
    
    Returns:
        ProfileConfig instance
    """
    return ProfileConfig(header=header, payload=payload, name=name)


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
    
    For minimal profiles that need get_message_info:
        reader = BufferReader(PROFILE_SENSOR_CONFIG, buffer, get_message_info)
    
    For profiles with CRC that need magic numbers:
        reader = BufferReader(PROFILE_STANDARD_CONFIG, buffer, get_message_info=get_message_info)
    """
    
    def __init__(self, config: ProfileConfig, buffer: bytes, 
                 get_message_info: Callable[[int], Optional[MessageInfo]] = None):
        """
        Initialize buffer reader.
        
        Args:
            config: Profile configuration
            buffer: Buffer containing one or more frames
            get_message_info: Callback to get message info (size, magic1, magic2) for a message ID
        """
        self._config = config
        self._buffer = buffer
        self._size = len(buffer)
        self._offset = 0
        self._get_message_info = get_message_info
    
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
            result = _frame_format_parse_with_crc(self._config, remaining, self._get_message_info)
        else:
            if self._get_message_info is None:
                self._offset = self._size
                return FrameMsgInfo()
            result = _frame_format_parse_minimal(self._config, remaining, self._get_message_info)
        
        if result.valid and result.frame_size > 0:
            self._offset += result.frame_size
        else:
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
    
    def __init__(self, config: ProfileConfig, capacity: int):
        """
        Initialize buffer writer.
        
        Args:
            config: Profile configuration
            capacity: Maximum buffer capacity in bytes
        """
        self._config = config
        self._capacity = capacity
        self._buffer = bytearray(capacity)
        self._offset = 0
    
    def write(self, msg, seq: int = 0, sys_id: int = 0, comp_id: int = 0) -> int:
        """
        Write a message object to the buffer.
        
        The message object must have MSG_ID (or msg_id) and data() (or pack()) methods.
        Magic numbers for checksum are automatically extracted from the message class
        if MAGIC1/MAGIC2 class attributes are present.
        
        Args:
            msg: Message object with MSG_ID/msg_id and data()/pack() attributes
            seq: Sequence number (for profiles with sequence)
            sys_id: System ID (for profiles with routing)
            comp_id: Component ID (for profiles with routing)
        
        Returns:
            Number of bytes written, or 0 on failure.
        """
        encoded = encode_message(self._config, msg, seq=seq, sys_id=sys_id, comp_id=comp_id)
        
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
        reader = AccumulatingReader(PROFILE_SENSOR_CONFIG, get_message_info=get_message_info)
    
    For profiles with CRC that need magic numbers:
        reader = AccumulatingReader(PROFILE_STANDARD_CONFIG, get_message_info=get_message_info)
    """
    
    def __init__(self, config: ProfileConfig, 
                 get_message_info: Callable[[int], Optional[MessageInfo]] = None,
                 buffer_size: int = 1024):
        """
        Initialize accumulating reader.
        
        Args:
            config: Profile configuration
            get_message_info: Callback to get message info (size, magic1, magic2) for a message ID
            buffer_size: Size of internal buffer for partial messages (default: 1024)
        """
        self._config = config
        self._get_message_info = get_message_info
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
                frame_size = result.frame_size
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
            self._current_offset += result.frame_size
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
            if byte == self._config.computed_start_byte1():
                self._internal_buffer[0] = byte
                self._internal_data_len = 1
                
                if self._config.num_start_bytes == 1:
                    self._state = AccumulatingReaderState.COLLECTING_HEADER
                else:
                    self._state = AccumulatingReaderState.LOOKING_FOR_START2
        
        return FrameMsgInfo()
    
    def _handle_looking_for_start2(self, byte: int) -> FrameMsgInfo:
        """Handle LOOKING_FOR_START2 state"""
        if byte == self._config.computed_start_byte2():
            self._internal_buffer[self._internal_data_len] = byte
            self._internal_data_len += 1
            self._state = AccumulatingReaderState.COLLECTING_HEADER
        elif byte == self._config.computed_start_byte1():
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
                if self._get_message_info:
                    msg_info = self._get_message_info(msg_id)
                    if msg_info is not None:
                        msg_len = msg_info.size
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
                                frame_size=self._config.header_size,
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
        if self._get_message_info:
            msg_info = self._get_message_info(msg_id)
            if msg_info is not None:
                msg_len = msg_info.size
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
                        frame_size=self._config.header_size,
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
            return _frame_format_parse_with_crc(self._config, buffer, self._get_message_info)
        else:
            if self._get_message_info is None:
                return FrameMsgInfo()
            return _frame_format_parse_minimal(self._config, buffer, self._get_message_info)
    
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
# Profile-Specific Classes (Direct Instantiation)
# =============================================================================

# Profile Standard: Basic + Default
class ProfileStandardReader(BufferReader):
    """BufferReader for Profile Standard"""
    def __init__(self, buffer: bytes, get_message_info: Callable[[int], Optional[MessageInfo]] = None):
        super().__init__(PROFILE_STANDARD_CONFIG, buffer, get_message_info)

class ProfileStandardWriter(BufferWriter):
    """BufferWriter for Profile Standard"""
    def __init__(self, capacity: int = 1024):
        super().__init__(PROFILE_STANDARD_CONFIG, capacity)

class ProfileStandardAccumulatingReader(AccumulatingReader):
    """AccumulatingReader for Profile Standard"""
    def __init__(self, get_message_info: Callable[[int], Optional[MessageInfo]] = None, buffer_size: int = 1024):
        super().__init__(PROFILE_STANDARD_CONFIG, get_message_info=get_message_info, buffer_size=buffer_size)

# Profile Sensor: Tiny + Minimal
class ProfileSensorReader(BufferReader):
    """BufferReader for Profile Sensor"""
    def __init__(self, buffer: bytes, get_message_info: Callable[[int], Optional[MessageInfo]]):
        super().__init__(PROFILE_SENSOR_CONFIG, buffer, get_message_info)

class ProfileSensorWriter(BufferWriter):
    """BufferWriter for Profile Sensor"""
    def __init__(self, capacity: int = 1024):
        super().__init__(PROFILE_SENSOR_CONFIG, capacity)

class ProfileSensorAccumulatingReader(AccumulatingReader):
    """AccumulatingReader for Profile Sensor"""
    def __init__(self, get_message_info: Callable[[int], Optional[MessageInfo]], buffer_size: int = 1024):
        super().__init__(PROFILE_SENSOR_CONFIG, get_message_info=get_message_info, buffer_size=buffer_size)

# Profile IPC: None + Minimal
class ProfileIPCReader(BufferReader):
    """BufferReader for Profile IPC"""
    def __init__(self, buffer: bytes, get_message_info: Callable[[int], Optional[MessageInfo]]):
        super().__init__(PROFILE_IPC_CONFIG, buffer, get_message_info)

class ProfileIPCWriter(BufferWriter):
    """BufferWriter for Profile IPC"""
    def __init__(self, capacity: int = 1024):
        super().__init__(PROFILE_IPC_CONFIG, capacity)

class ProfileIPCAccumulatingReader(AccumulatingReader):
    """AccumulatingReader for Profile IPC"""
    def __init__(self, get_message_info: Callable[[int], Optional[MessageInfo]], buffer_size: int = 1024):
        super().__init__(PROFILE_IPC_CONFIG, get_message_info=get_message_info, buffer_size=buffer_size)

# Profile Bulk: Basic + Extended
class ProfileBulkReader(BufferReader):
    """BufferReader for Profile Bulk"""
    def __init__(self, buffer: bytes, get_message_info: Callable[[int], Optional[MessageInfo]] = None):
        super().__init__(PROFILE_BULK_CONFIG, buffer, get_message_info)

class ProfileBulkWriter(BufferWriter):
    """BufferWriter for Profile Bulk"""
    def __init__(self, capacity: int = 1024):
        super().__init__(PROFILE_BULK_CONFIG, capacity)

class ProfileBulkAccumulatingReader(AccumulatingReader):
    """AccumulatingReader for Profile Bulk"""
    def __init__(self, get_message_info: Callable[[int], Optional[MessageInfo]] = None, buffer_size: int = 1024):
        super().__init__(PROFILE_BULK_CONFIG, get_message_info=get_message_info, buffer_size=buffer_size)

# Profile Network: Basic + ExtendedMultiSystemStream
class ProfileNetworkReader(BufferReader):
    """BufferReader for Profile Network"""
    def __init__(self, buffer: bytes, get_message_info: Callable[[int], Optional[MessageInfo]] = None):
        super().__init__(PROFILE_NETWORK_CONFIG, buffer, get_message_info)

class ProfileNetworkWriter(BufferWriter):
    """BufferWriter for Profile Network"""
    def __init__(self, capacity: int = 1024):
        super().__init__(PROFILE_NETWORK_CONFIG, capacity)

class ProfileNetworkAccumulatingReader(AccumulatingReader):
    """AccumulatingReader for Profile Network"""
    def __init__(self, get_message_info: Callable[[int], Optional[MessageInfo]] = None, buffer_size: int = 1024):
        super().__init__(PROFILE_NETWORK_CONFIG, get_message_info=get_message_info, buffer_size=buffer_size)


# =============================================================================
# Backwards Compatibility - FrameFormatConfig alias
# =============================================================================

# Alias for backwards compatibility
FrameFormatConfig = ProfileConfig
