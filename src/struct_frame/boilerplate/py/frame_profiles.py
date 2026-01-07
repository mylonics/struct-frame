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
