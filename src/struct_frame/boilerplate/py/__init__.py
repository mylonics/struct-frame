# Frame parser boilerplate package
# Uses header + payload architecture for composable frame formats.

# Polyglot parser - handles multiple frame types in same stream
from .polyglot_parser import (
    # Enums
    HeaderType,
    PayloadType,
    ParserState,
    # Classes
    PayloadConfig,
    FrameMsgInfo,
    PolyglotParser,
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

# Re-export all
__all__ = [
    # Enums
    "HeaderType",
    "PayloadType",
    "ParserState",
    # Classes
    "PayloadConfig",
    "FrameMsgInfo",
    "PolyglotParser",
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
    # Utilities
    "fletcher_checksum",
]
