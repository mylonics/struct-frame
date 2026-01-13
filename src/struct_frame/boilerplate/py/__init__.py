# Frame parser boilerplate package
# Uses header + payload architecture for composable frame formats.
# Mirrors the C++ boilerplate structure.

# Frame base - Core utilities (like frame_base.hpp)
from .frame_base import (
    FrameChecksum,
    FrameMsgInfo,
    ParserState,
    fletcher_checksum,
)

# Frame headers - Start byte patterns (like frame_headers.hpp)
from .frame_headers import (
    HeaderType,
    HeaderConfig,
    BASIC_START_BYTE,
    PAYLOAD_TYPE_BASE,
    UBX_SYNC1,
    UBX_SYNC2,
    MAVLINK_V1_STX,
    MAVLINK_V2_STX,
    MAX_PAYLOAD_TYPE,
    HEADER_NONE_CONFIG,
    HEADER_TINY_CONFIG,
    HEADER_BASIC_CONFIG,
    HEADER_UBX_CONFIG,
    HEADER_MAVLINK_V1_CONFIG,
    HEADER_MAVLINK_V2_CONFIG,
    HEADER_CONFIGS,
)

# Payload types - Message structure configurations (like payload_types.hpp)
from .payload_types import (
    PayloadType,
    PayloadConfig,
    MAX_PAYLOAD_TYPE_VALUE,
    PAYLOAD_MINIMAL_CONFIG,
    PAYLOAD_DEFAULT_CONFIG,
    PAYLOAD_EXTENDED_MSG_IDS_CONFIG,
    PAYLOAD_EXTENDED_LENGTH_CONFIG,
    PAYLOAD_EXTENDED_CONFIG,
    PAYLOAD_SYS_COMP_CONFIG,
    PAYLOAD_SEQ_CONFIG,
    PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG,
    PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG,
    PAYLOAD_CONFIGS,
)

# Frame profiles - Pre-defined Header + Payload combinations (like frame_profiles.hpp)
from .frame_profiles import (
    # Profile configuration class
    ProfileConfig,
    FrameFormatConfig,  # Backwards compatibility alias
    # Profile configurations
    PROFILE_STANDARD_CONFIG,
    PROFILE_SENSOR_CONFIG,
    PROFILE_IPC_CONFIG,
    PROFILE_BULK_CONFIG,
    PROFILE_NETWORK_CONFIG,
    # Profile convenience functions
    encode_profile_standard,
    parse_profile_standard_buffer,
    encode_profile_sensor,
    parse_profile_sensor_buffer,
    encode_profile_ipc,
    parse_profile_ipc_buffer,
    encode_profile_bulk,
    parse_profile_bulk_buffer,
    encode_profile_network,
    parse_profile_network_buffer,
    # Generic functions
    encode_frame,
    parse_frame_buffer,
    create_custom_config,
    # BufferReader/BufferWriter/AccumulatingReader base classes
    BufferReader,
    BufferWriter,
    AccumulatingReader,
    AccumulatingReaderState,
    # Profile-specific classes
    ProfileStandardReader,
    ProfileStandardWriter,
    ProfileStandardAccumulatingReader,
    ProfileSensorReader,
    ProfileSensorWriter,
    ProfileSensorAccumulatingReader,
    ProfileIPCReader,
    ProfileIPCWriter,
    ProfileIPCAccumulatingReader,
    ProfileBulkReader,
    ProfileBulkWriter,
    ProfileBulkAccumulatingReader,
    ProfileNetworkReader,
    ProfileNetworkWriter,
    ProfileNetworkAccumulatingReader,
)

# Re-export all
__all__ = [
    # Frame base
    "FrameChecksum",
    "FrameMsgInfo",
    "ParserState",
    "fletcher_checksum",
    # Frame headers
    "HeaderType",
    "HeaderConfig",
    "BASIC_START_BYTE",
    "PAYLOAD_TYPE_BASE",
    "UBX_SYNC1",
    "UBX_SYNC2",
    "MAVLINK_V1_STX",
    "MAVLINK_V2_STX",
    "MAX_PAYLOAD_TYPE",
    "HEADER_NONE_CONFIG",
    "HEADER_TINY_CONFIG",
    "HEADER_BASIC_CONFIG",
    "HEADER_UBX_CONFIG",
    "HEADER_MAVLINK_V1_CONFIG",
    "HEADER_MAVLINK_V2_CONFIG",
    "HEADER_CONFIGS",
    # Payload types
    "PayloadType",
    "PayloadConfig",
    "MAX_PAYLOAD_TYPE_VALUE",
    "PAYLOAD_MINIMAL_CONFIG",
    "PAYLOAD_DEFAULT_CONFIG",
    "PAYLOAD_EXTENDED_MSG_IDS_CONFIG",
    "PAYLOAD_EXTENDED_LENGTH_CONFIG",
    "PAYLOAD_EXTENDED_CONFIG",
    "PAYLOAD_SYS_COMP_CONFIG",
    "PAYLOAD_SEQ_CONFIG",
    "PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG",
    "PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG",
    "PAYLOAD_CONFIGS",
    # Frame profiles
    "ProfileConfig",
    "FrameFormatConfig",
    "PROFILE_STANDARD_CONFIG",
    "PROFILE_SENSOR_CONFIG",
    "PROFILE_IPC_CONFIG",
    "PROFILE_BULK_CONFIG",
    "PROFILE_NETWORK_CONFIG",
    "encode_profile_standard",
    "parse_profile_standard_buffer",
    "encode_profile_sensor",
    "parse_profile_sensor_buffer",
    "encode_profile_ipc",
    "parse_profile_ipc_buffer",
    "encode_profile_bulk",
    "parse_profile_bulk_buffer",
    "encode_profile_network",
    "parse_profile_network_buffer",
    "encode_frame",
    "parse_frame_buffer",
    "create_custom_config",
    "BufferReader",
    "BufferWriter",
    "AccumulatingReader",
    "AccumulatingReaderState",
    # Profile-specific classes
    "ProfileStandardReader",
    "ProfileStandardWriter",
    "ProfileStandardAccumulatingReader",
    "ProfileSensorReader",
    "ProfileSensorWriter",
    "ProfileSensorAccumulatingReader",
    "ProfileIPCReader",
    "ProfileIPCWriter",
    "ProfileIPCAccumulatingReader",
    "ProfileBulkReader",
    "ProfileBulkWriter",
    "ProfileBulkAccumulatingReader",
    "ProfileNetworkReader",
    "ProfileNetworkWriter",
    "ProfileNetworkAccumulatingReader",
]
