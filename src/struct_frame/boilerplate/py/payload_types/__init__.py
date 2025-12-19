# Payload Types
# Each payload type defines the header/footer structure of the payload

from .base import PayloadType, PayloadConfig, MAX_PAYLOAD_TYPE
from .payload_minimal import PAYLOAD_MINIMAL_CONFIG
from .payload_default import PAYLOAD_DEFAULT_CONFIG
from .payload_extended_msg_ids import PAYLOAD_EXTENDED_MSG_IDS_CONFIG
from .payload_extended_length import PAYLOAD_EXTENDED_LENGTH_CONFIG
from .payload_extended import PAYLOAD_EXTENDED_CONFIG
from .payload_sys_comp import PAYLOAD_SYS_COMP_CONFIG
from .payload_seq import PAYLOAD_SEQ_CONFIG
from .payload_multi_system_stream import PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG
from .payload_extended_multi_system_stream import PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG

# Registry of all payload configurations
PAYLOAD_CONFIGS = {
    PayloadType.MINIMAL: PAYLOAD_MINIMAL_CONFIG,
    PayloadType.DEFAULT: PAYLOAD_DEFAULT_CONFIG,
    PayloadType.EXTENDED_MSG_IDS: PAYLOAD_EXTENDED_MSG_IDS_CONFIG,
    PayloadType.EXTENDED_LENGTH: PAYLOAD_EXTENDED_LENGTH_CONFIG,
    PayloadType.EXTENDED: PAYLOAD_EXTENDED_CONFIG,
    PayloadType.SYS_COMP: PAYLOAD_SYS_COMP_CONFIG,
    PayloadType.SEQ: PAYLOAD_SEQ_CONFIG,
    PayloadType.MULTI_SYSTEM_STREAM: PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG,
    PayloadType.EXTENDED_MULTI_SYSTEM_STREAM: PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG,
}

__all__ = [
    'PayloadType',
    'PayloadConfig',
    'MAX_PAYLOAD_TYPE',
    'PAYLOAD_CONFIGS',
    'PAYLOAD_MINIMAL_CONFIG',
    'PAYLOAD_DEFAULT_CONFIG',
    'PAYLOAD_EXTENDED_MSG_IDS_CONFIG',
    'PAYLOAD_EXTENDED_LENGTH_CONFIG',
    'PAYLOAD_EXTENDED_CONFIG',
    'PAYLOAD_SYS_COMP_CONFIG',
    'PAYLOAD_SEQ_CONFIG',
    'PAYLOAD_MULTI_SYSTEM_STREAM_CONFIG',
    'PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM_CONFIG',
]
