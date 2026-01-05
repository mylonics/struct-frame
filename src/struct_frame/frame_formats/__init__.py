"""
Frame Format Definitions - Language-Agnostic Architecture

This module provides language-agnostic definitions for frame formats used in struct-frame.
The definitions are organized into:

1. Headers: Define start byte patterns for frame synchronization
2. Payloads: Define the structure of header fields and CRC
3. Profiles: Predefined combinations of headers + payloads for common use cases

Users should use the 5 recommended profiles for most applications:
- STANDARD: General purpose serial/UART (BasicDefault)
- SENSOR: Low-bandwidth sensors (TinyMinimal)
- IPC: Trusted inter-process communication (NoneMinimal)
- BULK: Large file transfers (BasicExtended)
- NETWORK: Multi-node mesh networks (BasicExtendedMultiSystemStream)

For custom requirements, users can create new profile aliases by combining existing
headers and payloads. New header or payload types should be contributed via PR.
"""

from .base import (
    HeaderType,
    PayloadType,
    FrameFormatDefinition,
    HeaderDefinition,
    PayloadDefinition,
)
from .profiles import (
    Profile,
    PROFILE_DEFINITIONS,
    get_profile,
    get_profile_by_name,
    create_custom_profile,
    list_profiles,
)
from .headers import HEADER_DEFINITIONS, get_header
from .payloads import PAYLOAD_DEFINITIONS, get_payload
from .crc import calculate_crc16, crc_to_bytes, bytes_to_crc, verify_crc

__all__ = [
    # Base types
    'HeaderType',
    'PayloadType',
    'FrameFormatDefinition',
    'HeaderDefinition',
    'PayloadDefinition',
    # Profiles
    'Profile',
    'PROFILE_DEFINITIONS',
    'get_profile',
    'get_profile_by_name',
    'create_custom_profile',
    'list_profiles',
    # Headers and Payloads
    'HEADER_DEFINITIONS',
    'PAYLOAD_DEFINITIONS',
    'get_header',
    'get_payload',
    # CRC utilities
    'calculate_crc16',
    'crc_to_bytes',
    'bytes_to_crc',
    'verify_crc',
]
