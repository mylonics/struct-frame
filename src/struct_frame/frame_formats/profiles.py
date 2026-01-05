"""
Profile definitions for frame formats.

Profiles are predefined combinations of headers and payloads for common use cases.
Users should use these 5 recommended profiles for most applications.

To create a custom profile, users can define it in their frame_format.proto file
by specifying a profile alias that combines a HeaderType and PayloadType.

For new header or payload types, please submit a PR to the struct-frame repository.
"""

from enum import Enum
from .base import HeaderType, PayloadType, FrameFormatDefinition
from .headers import get_header
from .payloads import get_payload


class Profile(Enum):
    """
    Standard frame format profiles for common use cases.
    
    These profiles provide intent-based frame format selection rather than
    requiring users to understand the technical details of headers and payloads.
    """
    # Standard profile: Basic header + Default payload
    # Use case: General purpose reliable communication (Serial/UART)
    STANDARD = 0
    
    # Sensor profile: Tiny header + Minimal payload
    # Use case: Low-overhead sensor data with known message sizes (Radio/LoRa)
    SENSOR = 1
    
    # IPC profile: None header + Minimal payload
    # Use case: Trusted inter-process communication (SPI/Shared Memory)
    IPC = 2
    
    # Bulk profile: Basic header + Extended payload
    # Use case: Large data transfers with package namespacing (Firmware/Files)
    BULK = 3
    
    # Network profile: Basic header + ExtendedMultiSystemStream payload
    # Use case: Multi-system networked communication (Mesh/Swarm)
    NETWORK = 4


def _create_profile_definition(
    profile: Profile,
    header_type: HeaderType,
    payload_type: PayloadType,
    description: str
) -> FrameFormatDefinition:
    """Create a frame format definition for a profile"""
    header = get_header(header_type)
    payload = get_payload(payload_type)
    
    # Generate name from header and payload (e.g., "BasicDefault")
    name = f"{header.name}{payload.name}"
    
    return FrameFormatDefinition(
        name=name,
        header=header,
        payload=payload,
        description=description
    )


# Define the 5 standard profiles
PROFILE_DEFINITIONS = {
    Profile.STANDARD: _create_profile_definition(
        Profile.STANDARD,
        HeaderType.BASIC,
        PayloadType.DEFAULT,
        "General purpose serial/UART communication. Basic header with default payload. "
        "Frame: [0x90] [0x71] [LEN] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]. "
        "Overhead: 6 bytes. Max payload: 255 bytes."
    ),
    
    Profile.SENSOR: _create_profile_definition(
        Profile.SENSOR,
        HeaderType.TINY,
        PayloadType.MINIMAL,
        "Low-bandwidth sensor data with known message sizes. Tiny header with minimal payload. "
        "Frame: [0x70] [MSG_ID] [PAYLOAD]. "
        "Overhead: 2 bytes. No length field or CRC. Requires fixed message sizes."
    ),
    
    Profile.IPC: _create_profile_definition(
        Profile.IPC,
        HeaderType.NONE,
        PayloadType.MINIMAL,
        "Trusted inter-process communication. No header, minimal payload. "
        "Frame: [MSG_ID] [PAYLOAD]. "
        "Overhead: 1 byte. Relies on external synchronization (e.g., message framing from transport layer)."
    ),
    
    Profile.BULK: _create_profile_definition(
        Profile.BULK,
        HeaderType.BASIC,
        PayloadType.EXTENDED,
        "Large data transfers with package namespacing. Basic header with extended payload. "
        "Frame: [0x90] [0x74] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]. "
        "Overhead: 8 bytes. Max payload: 64KB. Supports package namespaces."
    ),
    
    Profile.NETWORK: _create_profile_definition(
        Profile.NETWORK,
        HeaderType.BASIC,
        PayloadType.EXTENDED_MULTI_SYSTEM_STREAM,
        "Multi-node networked communication. Basic header with full-featured payload. "
        "Frame: [0x90] [0x78] [SEQ] [SYS_ID] [COMP_ID] [LEN_LO] [LEN_HI] [PKG_ID] [MSG_ID] [PAYLOAD] [CRC1] [CRC2]. "
        "Overhead: 11 bytes. Max payload: 64KB. Supports routing, sequencing, and package namespaces."
    ),
}


def get_profile(profile: Profile) -> FrameFormatDefinition:
    """
    Get frame format definition for a standard profile.
    
    Args:
        profile: The profile to get
        
    Returns:
        FrameFormatDefinition for the profile
    """
    return PROFILE_DEFINITIONS[profile]


def get_profile_by_name(name: str) -> FrameFormatDefinition:
    """
    Get frame format definition by profile name.
    
    Args:
        name: Profile name (e.g., "STANDARD", "SENSOR", etc.)
        
    Returns:
        FrameFormatDefinition for the profile
        
    Raises:
        ValueError: If profile name is not recognized
    """
    try:
        profile = Profile[name.upper()]
        return get_profile(profile)
    except KeyError:
        raise ValueError(f"Unknown profile: {name}. Valid profiles: {[p.name for p in Profile]}")


def create_custom_profile(
    name: str,
    header_type: HeaderType,
    payload_type: PayloadType,
    description: str = ""
) -> FrameFormatDefinition:
    """
    Create a custom frame format profile.
    
    This allows users to create custom combinations of headers and payloads
    without modifying the struct-frame codebase.
    
    Args:
        name: Name for the custom profile
        header_type: Header type to use
        payload_type: Payload type to use
        description: Optional description
        
    Returns:
        FrameFormatDefinition for the custom profile
    """
    header = get_header(header_type)
    payload = get_payload(payload_type)
    
    return FrameFormatDefinition(
        name=name,
        header=header,
        payload=payload,
        description=description or f"Custom profile: {header.name} + {payload.name}"
    )


def list_profiles():
    """
    List all standard profiles with their details.
    
    Returns:
        List of tuples: (profile_name, frame_format_name, description)
    """
    profiles = []
    for profile in Profile:
        definition = get_profile(profile)
        profiles.append((
            profile.name,
            definition.name,
            definition.total_overhead,
            definition.description
        ))
    return profiles
