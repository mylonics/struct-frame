"""
Payload definitions for frame formats.

Each payload defines the structure of header fields (before message data)
and footer fields (after message data, typically CRC).

Payload definitions are designed to be composable - more complex payloads
can build upon simpler ones by adding fields.
"""

from .base import PayloadType, PayloadDefinition


# Payload Minimal
# Format: [MSG_ID] [PACKET]
# No length field, no CRC. Requires known message sizes.
# This is the base - all other payloads add to this
PAYLOAD_MINIMAL = PayloadDefinition(
    payload_type=PayloadType.MINIMAL,
    name="Minimal",
    has_crc=False,
    crc_bytes=0,
    has_length=False,
    length_bytes=0,
    has_sequence=False,
    has_system_id=False,
    has_component_id=False,
    has_package_id=False,
    description="[MSG_ID] [PACKET] - Minimal overhead. No length, no CRC."
)


# Payload Default
# Format: [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
# Builds on Minimal by adding: 1-byte length field + 2-byte CRC
PAYLOAD_DEFAULT = PayloadDefinition(
    payload_type=PayloadType.DEFAULT,
    name="Default",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=1,
    has_sequence=False,
    has_system_id=False,
    has_component_id=False,
    has_package_id=False,
    description="[LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Standard format with length and CRC."
)


# Payload ExtendedMsgIds
# Format: [LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
# Builds on Default by adding: package ID for namespace separation
PAYLOAD_EXTENDED_MSG_IDS = PayloadDefinition(
    payload_type=PayloadType.EXTENDED_MSG_IDS,
    name="ExtendedMsgIds",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=1,
    has_sequence=False,
    has_system_id=False,
    has_component_id=False,
    has_package_id=True,
    description="[LEN] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] - Adds package namespace."
)


# Payload ExtendedLength
# Format: [LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2]
# Builds on Default by upgrading: 1-byte length -> 2-byte length (up to 64KB)
PAYLOAD_EXTENDED_LENGTH = PayloadDefinition(
    payload_type=PayloadType.EXTENDED_LENGTH,
    name="ExtendedLength",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=2,
    has_sequence=False,
    has_system_id=False,
    has_component_id=False,
    has_package_id=False,
    description="[LEN16] [MSG_ID] [PACKET] [CRC1] [CRC2] - Supports payloads up to 64KB."
)


# Payload Extended
# Format: [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
# Combines ExtendedLength + ExtendedMsgIds: 2-byte length + package ID
PAYLOAD_EXTENDED = PayloadDefinition(
    payload_type=PayloadType.EXTENDED,
    name="Extended",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=2,
    has_sequence=False,
    has_system_id=False,
    has_component_id=False,
    has_package_id=True,
    description="[LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] - Large payloads with package namespace."
)


# Payload SysComp
# Format: [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
# Builds on Default by adding: system ID + component ID for multi-node routing
PAYLOAD_SYS_COMP = PayloadDefinition(
    payload_type=PayloadType.SYS_COMP,
    name="SysComp",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=1,
    has_sequence=False,
    has_system_id=True,
    has_component_id=True,
    has_package_id=False,
    description="[SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Multi-node routing."
)


# Payload Seq
# Format: [SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
# Builds on Default by adding: sequence number for packet loss detection
PAYLOAD_SEQ = PayloadDefinition(
    payload_type=PayloadType.SEQ,
    name="Seq",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=1,
    has_sequence=True,
    has_system_id=False,
    has_component_id=False,
    has_package_id=False,
    description="[SEQ] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Adds sequence for packet loss detection."
)


# Payload MultiSystemStream
# Format: [SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2]
# Combines Seq + SysComp: sequence + routing for multi-system streaming
PAYLOAD_MULTI_SYSTEM_STREAM = PayloadDefinition(
    payload_type=PayloadType.MULTI_SYSTEM_STREAM,
    name="MultiSystemStream",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=1,
    has_sequence=True,
    has_system_id=True,
    has_component_id=True,
    has_package_id=False,
    description="[SEQ] [SYS_ID] [COMP_ID] [LEN] [MSG_ID] [PACKET] [CRC1] [CRC2] - Multi-system streaming."
)


# Payload ExtendedMultiSystemStream
# Format: [SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2]
# Full-featured: sequence + routing + 2-byte length + package ID
PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM = PayloadDefinition(
    payload_type=PayloadType.EXTENDED_MULTI_SYSTEM_STREAM,
    name="ExtendedMultiSystemStream",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=2,
    has_sequence=True,
    has_system_id=True,
    has_component_id=True,
    has_package_id=True,
    description="[SEQ] [SYS_ID] [COMP_ID] [LEN16] [PKG_ID] [MSG_ID] [PACKET] [CRC1] [CRC2] - Full featured."
)


# Third-party protocol payloads

# Payload UBX - u-blox GPS/GNSS protocol
# Format: [CLASS] [ID] [LEN_LO] [LEN_HI] [MSG] [CK_A] [CK_B]
PAYLOAD_UBX = PayloadDefinition(
    payload_type=PayloadType.UBX,
    name="UBX",
    has_crc=True,
    crc_bytes=2,  # UBX uses 2-byte checksum
    has_length=True,
    length_bytes=2,
    has_sequence=False,
    has_system_id=False,
    has_component_id=False,
    has_package_id=False,
    description="[CLASS] [ID] [LEN_LO] [LEN_HI] [MSG] [CK_A] [CK_B] - u-blox GPS protocol."
)


# Payload MAVLink V1
# Format: [LEN] [SEQ] [SYS] [COMP] [MSG_ID] [PAYLOAD] [CRC_LO] [CRC_HI]
PAYLOAD_MAVLINK_V1 = PayloadDefinition(
    payload_type=PayloadType.MAVLINK_V1,
    name="MavlinkV1",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=1,
    has_sequence=True,
    has_system_id=True,
    has_component_id=True,
    has_package_id=False,
    description="[LEN] [SEQ] [SYS] [COMP] [MSG_ID] [PAYLOAD] [CRC_LO] [CRC_HI] - MAVLink V1."
)


# Payload MAVLink V2
# Format: [LEN] [INCOMPAT] [COMPAT] [SEQ] [SYS] [COMP] [MSG_ID x3] [PAYLOAD] [CRC] [SIG?]
PAYLOAD_MAVLINK_V2 = PayloadDefinition(
    payload_type=PayloadType.MAVLINK_V2,
    name="MavlinkV2",
    has_crc=True,
    crc_bytes=2,  # Note: optional 13-byte signature not counted here
    has_length=True,
    length_bytes=1,
    has_sequence=True,
    has_system_id=True,
    has_component_id=True,
    has_package_id=False,
    description="[LEN] [INCOMPAT] [COMPAT] [SEQ] [SYS] [COMP] [MSG_ID x3] [PAYLOAD] [CRC] - MAVLink V2."
)


# Registry of all payload definitions
PAYLOAD_DEFINITIONS = {
    PayloadType.MINIMAL: PAYLOAD_MINIMAL,
    PayloadType.DEFAULT: PAYLOAD_DEFAULT,
    PayloadType.EXTENDED_MSG_IDS: PAYLOAD_EXTENDED_MSG_IDS,
    PayloadType.EXTENDED_LENGTH: PAYLOAD_EXTENDED_LENGTH,
    PayloadType.EXTENDED: PAYLOAD_EXTENDED,
    PayloadType.SYS_COMP: PAYLOAD_SYS_COMP,
    PayloadType.SEQ: PAYLOAD_SEQ,
    PayloadType.MULTI_SYSTEM_STREAM: PAYLOAD_MULTI_SYSTEM_STREAM,
    PayloadType.EXTENDED_MULTI_SYSTEM_STREAM: PAYLOAD_EXTENDED_MULTI_SYSTEM_STREAM,
    PayloadType.UBX: PAYLOAD_UBX,
    PayloadType.MAVLINK_V1: PAYLOAD_MAVLINK_V1,
    PayloadType.MAVLINK_V2: PAYLOAD_MAVLINK_V2,
}


def get_payload(payload_type: PayloadType) -> PayloadDefinition:
    """Get payload definition by type"""
    return PAYLOAD_DEFINITIONS[payload_type]
