# Frame parser boilerplate package
# Uses header + payload architecture for composable frame formats.

# Parser - handles multiple frame types in same stream
from .parser import (
    # Enums
    HeaderType,
    PayloadType,
    ParserState,
    # Classes
    PayloadConfig,
    FrameMsgInfo,
    Parser,
    # Constants
    BASIC_START_BYTE,
    PAYLOAD_TYPE_BASE,
    MAX_PAYLOAD_TYPE,
    UBX_SYNC1,
    UBX_SYNC2,
    MAVLINK_V1_STX,
    MAVLINK_V2_STX,
    # Payload configurations
    PAYLOAD_CONFIGS,
    # Utilities
    fletcher_checksum,
)

# Frame Profiles - pre-defined header+payload combinations
from .frame_profiles import (
    # Config class
    FrameFormatConfig,
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
)

# Re-export all
__all__ = [
    # Enums
    "HeaderType",
    "PayloadType",
    "ParserState",
    # Classes
    "PayloadConfig",
    "FrameMsgInfo",
    "Parser",
    "FrameFormatConfig",
    # Constants
    "BASIC_START_BYTE",
    "PAYLOAD_TYPE_BASE",
    "MAX_PAYLOAD_TYPE",
    "UBX_SYNC1",
    "UBX_SYNC2",
    "MAVLINK_V1_STX",
    "MAVLINK_V2_STX",
    # Payload configurations
    "PAYLOAD_CONFIGS",
    # Profile configurations
    "PROFILE_STANDARD_CONFIG",
    "PROFILE_SENSOR_CONFIG",
    "PROFILE_IPC_CONFIG",
    "PROFILE_BULK_CONFIG",
    "PROFILE_NETWORK_CONFIG",
    # Profile convenience functions
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
    # Generic functions
    "encode_frame",
    "parse_frame_buffer",
    "create_custom_config",
    # Utilities
    "fletcher_checksum",
]
