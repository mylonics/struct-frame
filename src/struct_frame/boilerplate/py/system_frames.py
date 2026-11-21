"""System frames: struct-frame's own messages (heartbeat, ping, link tests, RPC).

A system frame uses the header of the profile it travels with (Basic or Tiny; profiles
without start bytes cannot carry system frames) followed by a fixed payload layout:

    [start bytes][SEQ][SYS][COMP][LEN lo][LEN hi][SYS_MSG_ID] payload [CRC1][CRC2]

The second start byte (Basic) or the start byte (Tiny) is 0x79: payload type 9. System
message ids are a separate id space (see ``sf_system.py``), so they never collide with
application messages. The CRC is the usual Fletcher-16 over everything after the start
bytes, with the system message's magic bytes mixed in after the data (as for application
frames).

Some system messages carry a raw *tail* after their fixed fields (ping padding, link-test
data, RPC payloads); its length is the frame length minus the message's fixed size.
"""

from typing import Optional

try:
    from .frame_base import fletcher_checksum
    from .frame_headers import HeaderType
    from .frame_profiles import MessageInfo, ProfileConfig
    from .payload_types import PayloadConfig, PayloadType
    from . import sf_system
except ImportError:  # pragma: no cover - flat layout (tests import the runtime directly)
    from frame_base import fletcher_checksum
    from frame_headers import HeaderType
    from frame_profiles import MessageInfo, ProfileConfig
    from payload_types import PayloadConfig, PayloadType
    import sf_system

# Payload type of system frames (the start byte is PAYLOAD_TYPE_BASE + 9 = 0x79).
SYSTEM_PAYLOAD_TYPE_VALUE = 9
SYSTEM_START_BYTE = 0x70 + SYSTEM_PAYLOAD_TYPE_VALUE

# Largest tail accepted after a system message's fixed fields.
MAX_TAIL = sf_system.MAX_TAIL

PAYLOAD_SYSTEM_CONFIG = PayloadConfig(
    payload_type=PayloadType.SYSTEM,
    name="System",
    has_crc=True,
    crc_bytes=2,
    has_length=True,
    length_bytes=2,
    has_sequence=True,
    has_system_id=True,
    has_component_id=True,
    has_package_id=False,
    description="[SEQ] [SYS] [COMP] [LEN16] [SYS_MSG_ID] [PACKET] [CRC1] [CRC2] - struct-frame system messages.",
)

# System messages that may carry a tail, by system message id.
TAIL_MESSAGES = frozenset({
    sf_system.Ping.MSG_ID,
    sf_system.Pong.MSG_ID,
    sf_system.LinkTestData.MSG_ID,
    sf_system.RpcRequest.MSG_ID,
    sf_system.RpcResponse.MSG_ID,
})

_MESSAGES = {cls.MSG_ID: cls for cls in (
    sf_system.Heartbeat, sf_system.LinkStats, sf_system.Ping, sf_system.Pong,
    sf_system.LinkTestStart, sf_system.LinkTestAck, sf_system.LinkTestData,
    sf_system.LinkTestStop, sf_system.LinkTestReport, sf_system.RpcRequest,
    sf_system.RpcResponse,
)}


def supports_system_frames(config: ProfileConfig) -> bool:
    """True when frames of *config* can be told apart from system frames: the header
    carries the payload type in a start byte (Basic and Tiny headers)."""
    # A structural check (not an enum comparison): the runtime may be imported both as a
    # package and as flat modules, which gives two copies of HeaderType.
    return bool(config.header.encodes_payload_type) and config.num_start_bytes >= 1


def system_config(config: ProfileConfig) -> ProfileConfig:
    """The system-frame profile for the header of *config*."""
    if not supports_system_frames(config):
        raise ValueError(f"profile {config.name} has no start byte that identifies the payload "
                         f"type, so it cannot carry system frames")
    cached = _SYSTEM_CONFIGS.get(id(config.header))
    if cached is None:
        cached = ProfileConfig(header=config.header, payload=PAYLOAD_SYSTEM_CONFIG,
                               name=f"{config.header.name}System")
        _SYSTEM_CONFIGS[id(config.header)] = cached
    return cached


_SYSTEM_CONFIGS = {}


def message_info(msg_id: int) -> Optional[MessageInfo]:
    """Size limits and magic bytes of a system message, for the frame readers.

    ``min_size`` is the fixed size; ``size`` also allows a tail for the messages that
    take one. ``base_size`` equals ``size`` so the CRC is never extension-split.
    """
    cls = _MESSAGES.get(msg_id)
    if cls is None:
        return None
    fixed = cls.MAX_SIZE
    largest = fixed + (MAX_TAIL if msg_id in TAIL_MESSAGES else 0)
    return MessageInfo(size=largest, magic1=cls.MAGIC1, magic2=cls.MAGIC2, base_size=largest,
                       min_size=fixed)


def message_class(msg_id: int):
    """The generated class of a system message id, or None."""
    return _MESSAGES.get(msg_id)


def encode(config: ProfileConfig, message, tail: bytes = b"", seq: int = 0, sys_id: int = 0,
           comp_id: int = 0) -> bytes:
    """Encode a system message (and its tail) as a system frame for the header of *config*."""
    cfg = system_config(config)
    msg_id = type(message).MSG_ID
    if tail and msg_id not in TAIL_MESSAGES:
        raise ValueError(f"{type(message).__name__} does not take a tail")
    if len(tail) > MAX_TAIL:
        raise ValueError(f"tail of {len(tail)} bytes exceeds MAX_TAIL ({MAX_TAIL})")
    payload = message.serialize() + bytes(tail)
    out = bytearray()
    if cfg.num_start_bytes >= 1:
        out.append(cfg.computed_start_byte1())
    if cfg.num_start_bytes >= 2:
        out.append(cfg.computed_start_byte2())
    crc_start = len(out)
    out += bytes((seq & 0xFF, sys_id & 0xFF, comp_id & 0xFF,
                  len(payload) & 0xFF, (len(payload) >> 8) & 0xFF, msg_id & 0xFF))
    out += payload
    crc = fletcher_checksum(out, crc_start, len(out), init1=type(message).MAGIC1,
                            init2=type(message).MAGIC2)
    out += bytes((crc.byte1, crc.byte2))
    return bytes(out)


def decode(frame) -> tuple:
    """(message, tail) of a valid system frame returned by a reader (``frame.is_system``)."""
    cls = _MESSAGES.get(frame.msg_id)
    if cls is None:
        raise ValueError(f"unknown system message id 0x{frame.msg_id:02X}")
    data = bytes(frame.msg_data)
    return cls.deserialize(data[:cls.MAX_SIZE]), data[cls.MAX_SIZE:]
