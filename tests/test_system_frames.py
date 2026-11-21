#!/usr/bin/env python3
"""System frames (payload type 9): the wire format and the Python runtime.

A system frame carries one of struct-frame's own messages (``sf_system.sf``) after a Basic
(``90 79``) or Tiny (``79``) header::

    [start bytes][SEQ][SYS][COMP][LEN lo][LEN hi][SYS_MSG_ID] fixed fields [tail] [CRC1][CRC2]

The CRC is Fletcher-16 over everything after the start bytes, with the message's magic bytes
mixed in at the end. Readers hide system frames by default (counting them in
``cnt_system_frames``) and validate the header before collecting a payload, so a stray 0x79
cannot swallow application frames.

The known-answer frames here are built from that description alone; the other six runtimes
are checked against the same frames in ``test_system_frames_runtimes.py``.
"""
from __future__ import annotations

import importlib.util
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from test_known_answer import BOILERPLATE, fletcher16

# --------------------------------------------------------------------------- the spec

# Wire layout of the system messages the vectors use: (system message id, struct format of the
# fixed fields in wire order, (magic1, magic2), field names). This is the sf_system.sf contract;
# test_layout_matches_the_builtin_schema keeps it honest.
LAYOUT = {
    "Heartbeat": (0x01, "<IIIHBBBB", (58, 250),
                  ("uptime_ms", "counter", "wire_hash", "interval_ms", "protocol_version",
                   "node_type", "state", "flags")),
    "Ping": (0x10, "<QIBB", (28, 82), ("t_send_us", "seq", "target_sys", "target_comp")),
    "Pong": (0x11, "<QIH", (25, 56), ("t_send_us", "seq", "max_tail")),
    "RpcRequest": (0x30, "<HHBBBB", (31, 99),
                   ("call_id", "payload_id", "payload_magic1", "payload_magic2", "target_sys",
                    "target_comp")),
    "LinkTestStop": (0x23, "<B", (2, 2), ("test_id",)),
}

TAIL_MESSAGES = ("Ping", "Pong", "LinkTestData", "RpcRequest", "RpcResponse")
MAX_TAIL = 1024


@dataclass(frozen=True)
class SysVector:
    profile: str          # standard | sensor | network
    message: str          # a LAYOUT key
    fields: tuple         # fixed-field values in wire order
    tail: bytes = b""
    seq: int = 0
    sys_id: int = 0
    comp_id: int = 0


def spec_frame(v: SysVector) -> bytes:
    """Encode ``v`` straight from the format description (no runtime code)."""
    msg_id, fmt, (magic1, magic2), _names = LAYOUT[v.message]
    payload = struct.pack(fmt, *v.fields) + v.tail
    start = b"\x79" if v.profile == "sensor" else b"\x90\x79"
    body = bytes([v.seq, v.sys_id, v.comp_id, len(payload) & 0xFF, len(payload) >> 8, msg_id]) + payload
    return start + body + fletcher16(body, magic1, magic2)


# Hand-computed: LinkTestStop{test_id=3} after a Basic header. Fletcher over
# 00 00 00 01 00 23 03 then the magic 02 02 gives 2B A1.
HAND_COMPUTED = bytes.fromhex("9079" "000000" "0100" "23" "03" "2BA1")

VECTORS = [
    SysVector("standard", "Heartbeat", (1234, 5, 0xDEADBEEF, 1000, 1, 0, 0, 0), seq=7, sys_id=4, comp_id=5),
    SysVector("sensor", "Heartbeat", (0xFFFFFFFF, 1, 0, 250, 1, 2, 1, 6), seq=0, sys_id=1, comp_id=2),
    SysVector("standard", "Ping", (0x0102030405060708, 9, 3, 4), tail=bytes([0xAA, 0xBB, 0xCC]),
              seq=255, sys_id=6, comp_id=7),
    SysVector("sensor", "RpcRequest", (0x1234, 0x0102, 0x11, 0x22, 1, 2), tail=bytes(range(10)),
              seq=1, sys_id=2, comp_id=3),
    SysVector("network", "LinkTestStop", (3,)),
]
EXPECTED = [spec_frame(v) for v in VECTORS]


def test_spec_encoder_matches_hand_computed_frame():
    assert spec_frame(SysVector("standard", "LinkTestStop", (3,))) == HAND_COMPUTED


def test_tiny_and_basic_frames_differ_only_in_the_start_bytes():
    basic = spec_frame(SysVector("standard", "Ping", (1, 2, 3, 4), tail=b"xy", seq=5))
    tiny = spec_frame(SysVector("sensor", "Ping", (1, 2, 3, 4), tail=b"xy", seq=5))
    assert basic[:2] == b"\x90\x79" and tiny[:1] == b"\x79" and basic[2:] == tiny[1:]


# --------------------------------------------------------------------------- the Python runtime

_RUNTIME = ("frame_base", "frame_headers", "payload_types", "frame_profiles", "sf_system", "system_frames")


@pytest.fixture(scope="module")
def rt():
    """The Python boilerplate runtime (not generated code), loaded as flat modules."""
    saved = {name: sys.modules.get(name) for name in _RUNTIME}
    added = str(BOILERPLATE / "py")
    sys.path.insert(0, added)
    try:
        for name in _RUNTIME:
            sys.modules.pop(name, None)
        for name in _RUNTIME:
            if name in sys.modules:
                continue  # imported by an earlier module (frame_profiles imports system_frames)
            spec = importlib.util.spec_from_file_location(name, BOILERPLATE / "py" / f"{name}.py")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
        mods = {name: sys.modules[name] for name in _RUNTIME}
    finally:
        sys.path.remove(added)
    yield type("Runtime", (), mods)
    for name, module in saved.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module


PROFILES = {"standard": "PROFILE_STANDARD_CONFIG", "sensor": "PROFILE_SENSOR_CONFIG",
            "bulk": "PROFILE_BULK_CONFIG", "network": "PROFILE_NETWORK_CONFIG",
            "ipc": "PROFILE_IPC_CONFIG"}


def _config(rt, profile):
    return getattr(rt.frame_profiles, PROFILES[profile])


def _message(rt, v: SysVector):
    cls = getattr(rt.sf_system, v.message)
    names = LAYOUT[v.message][3]
    return cls(**dict(zip(names, v.fields)))


def test_layout_matches_the_builtin_schema(rt):
    for name, (msg_id, fmt, (magic1, magic2), names) in LAYOUT.items():
        cls = getattr(rt.sf_system, name)
        assert (cls.MSG_ID, cls.MAGIC1, cls.MAGIC2) == (msg_id, magic1, magic2), name
        assert cls.MAX_SIZE == struct.calcsize(fmt), name


def test_tail_messages_match_the_builtin_list(rt):
    from struct_frame import builtin
    assert tuple(builtin.TAIL_MESSAGES) == TAIL_MESSAGES
    want = {getattr(rt.sf_system, name).MSG_ID for name in TAIL_MESSAGES}
    assert set(rt.system_frames.TAIL_MESSAGES) == want
    assert rt.system_frames.MAX_TAIL == MAX_TAIL


@pytest.mark.parametrize("index", range(len(VECTORS)))
def test_python_runtime_encodes_spec_frames(rt, index):
    v = VECTORS[index]
    frame = rt.system_frames.encode(_config(rt, v.profile), _message(rt, v), tail=v.tail, seq=v.seq,
                                    sys_id=v.sys_id, comp_id=v.comp_id)
    assert frame == EXPECTED[index]


@pytest.mark.parametrize("index", range(len(VECTORS)))
@pytest.mark.parametrize("mode", ["buffer", "stream"])
def test_python_runtime_decodes_spec_frames(rt, index, mode):
    v = VECTORS[index]
    fp = rt.frame_profiles
    reader = fp.AccumulatingReader(_config(rt, v.profile), deliver_system_frames=True)
    if mode == "buffer":
        reader.add_data(EXPECTED[index])
        result = reader.next()
    else:
        for byte in EXPECTED[index]:
            result = reader.push_byte(byte)
    assert result.valid and result.is_system
    assert (result.msg_id, result.sequence, result.system_id, result.component_id) == \
        (LAYOUT[v.message][0], v.seq, v.sys_id, v.comp_id)
    message, tail = rt.system_frames.decode(result)
    assert type(message).__name__ == v.message
    assert tuple(getattr(message, n) for n in LAYOUT[v.message][3]) == v.fields
    assert tail == v.tail


# --------------------------------------------------------------------------- mixed streams

USER_SIZES = {1: 3, 2: 5}


def _user_info(rt):
    def info(msg_id):
        size = USER_SIZES.get(msg_id & 0xFF)
        if size is None:
            return None
        return rt.frame_profiles.MessageInfo(size=size, magic1=7, magic2=9, base_size=size, min_size=size)
    return info


@dataclass
class Item:
    user: bool
    msg_id: int
    data: bytes
    tail: bytes = b""
    seq: int = 0
    offset: int = 0       # where the frame starts in the stream


def _user_frame(rt, config, msg_id, data, seq):
    pkg = 0x0100 if config.payload.has_package_id else 0

    class Message:
        MSG_ID = pkg | msg_id
        MAGIC1 = 7
        MAGIC2 = 9

        def serialize(self):
            return data

    return rt.frame_profiles.encode_message(config, Message(), seq=seq, sys_id=1, comp_id=2)


def _mixed_stream(rt, config, garbage=b"\x00\x13"):
    """garbage, user, Heartbeat, user, Ping+tail, user -- and the expected items."""
    sf = rt.sf_system
    hb = sf.Heartbeat(uptime_ms=1234, counter=5, wire_hash=0xDEADBEEF, interval_ms=1000, protocol_version=1)
    ping = sf.Ping(t_send_us=99, seq=3)
    items = [
        Item(True, 1, bytes([1, 2, 3])),
        Item(False, sf.Heartbeat.MSG_ID, hb.serialize(), seq=0),
        Item(True, 2, bytes([9, 8, 7, 6, 5])),
        Item(False, sf.Ping.MSG_ID, ping.serialize(), tail=bytes(range(1, 8)), seq=1),
        Item(True, 1, bytes([4, 5, 6])),
    ]
    out = bytearray(garbage)
    user_seq = 0
    for item, msg in zip(items, [None, hb, None, ping, None]):
        item.offset = len(out)
        if item.user:
            out += _user_frame(rt, config, item.msg_id, item.data, user_seq)
            user_seq += 1
        else:
            out += rt.system_frames.encode(config, msg, tail=item.tail, seq=item.seq, sys_id=4, comp_id=5)
    return bytes(out), items


def _drain(rt, config, data, mode, deliver, buffer_size=1100):
    fp = rt.frame_profiles
    info = _user_info(rt)
    frames = []
    if mode == "buffer_reader":
        reader = fp.BufferReader(config, data, get_message_info=info, deliver_system_frames=deliver)
        while (f := reader.try_next()) is not None:
            if f.valid:
                frames.append((f, bytes(f.msg_data[:f.msg_len])))
        return frames, None
    reader = fp.AccumulatingReader(config, get_message_info=info, buffer_size=buffer_size,
                                   deliver_system_frames=deliver)
    if mode == "stream":
        for byte in data:
            f = reader.push_byte(byte)
            if f.valid:
                frames.append((f, bytes(f.msg_data[:f.msg_len])))
    else:
        chunk = len(data) if mode == "whole" else int(mode.split("_")[1])
        for i in range(0, len(data), chunk):
            reader.add_data(data[i:i + chunk])
            while (f := reader.try_next()) is not None:
                if f.valid:
                    frames.append((f, bytes(f.msg_data[:f.msg_len])))
    return frames, reader.diagnostics


def _check_frames(rt, frames, items, deliver):
    want = [i for i in items if i.user or deliver]
    assert len(frames) == len(want)
    for (f, data), item in zip(frames, want):
        if item.user:
            assert not f.is_system and (f.msg_id & 0xFF) == item.msg_id and data == item.data
        else:
            assert f.is_system and f.msg_id == item.msg_id and data == item.data + item.tail
            assert (f.sequence, f.system_id, f.component_id) == (item.seq, 4, 5)
            _message, tail = rt.system_frames.decode(f)
            assert tail == item.tail


MODES = ["buffer_reader", "chunk_1", "chunk_3", "chunk_7", "whole", "stream"]


@pytest.mark.parametrize("profile", ["standard", "sensor", "bulk", "network"])
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("deliver", [False, True], ids=["hidden", "delivered"])
def test_system_frames_between_application_frames(rt, profile, mode, deliver):
    config = _config(rt, profile)
    data, items = _mixed_stream(rt, config)
    frames, diag = _drain(rt, config, data, mode, deliver)
    _check_frames(rt, frames, items, deliver)
    if diag is not None:
        assert diag.cnt_system_frames == 2
        assert diag.cnt_crc_failures == 0 and diag.cnt_seq_gaps == 0 and diag.cnt_system_rejected == 0


@pytest.mark.parametrize("profile", ["standard", "sensor", "bulk", "network"])
@pytest.mark.parametrize("mode", ["chunk_1", "whole", "stream"])
def test_false_system_start_loses_only_frames_inside_its_header_window(rt, profile, mode):
    """A stray 0x79 (or 90 79) starts a system-header candidate that is rejected once its
    header is complete (7 bytes after a Tiny start, 8 after a Basic one). Buffer mode rescans
    the rejected bytes and loses nothing; stream mode, which never rescans, can lose only the
    frames that start inside that window."""
    config = _config(rt, profile)
    stray = bytes([0x90, 0x79]) if config.num_start_bytes == 2 else bytes([0x79])
    data, items = _mixed_stream(rt, config, garbage=stray)
    window = rt.system_frames.system_config(config).header_size
    frames, diag = _drain(rt, config, data, mode, deliver=True)
    got = [(f.is_system, f.msg_id & 0xFF) for f, _ in frames]
    after = [(not i.user, i.msg_id) for i in items if i.offset >= window]
    if mode == "stream":
        assert got[len(got) - len(after):] == after
    else:
        assert got == [(not i.user, i.msg_id) for i in items]
    assert diag.cnt_system_rejected == 1


def _rejected_header(case):
    """A system header that the reader must reject without collecting a payload."""
    if case == "unknown_id":
        return bytes([0x90, 0x79, 0, 0, 0, 1, 0, 0x7F])
    if case == "too_long":         # Heartbeat takes no tail: 19 > 18
        return bytes([0x90, 0x79, 0, 0, 0, 19, 0, 0x01])
    if case == "too_short":        # below Heartbeat's fixed size
        return bytes([0x90, 0x79, 0, 0, 0, 17, 0, 0x01])
    if case == "oversized":        # far beyond any system message
        return bytes([0x90, 0x79, 0, 0, 0, 0xFF, 0xFF, 0x01])
    raise AssertionError(case)


@pytest.mark.parametrize("case", ["unknown_id", "too_long", "too_short", "oversized"])
@pytest.mark.parametrize("mode", ["chunk_1", "whole", "stream"])
def test_bad_system_header_is_rejected_before_its_payload(rt, case, mode):
    config = _config(rt, "standard")
    good = _user_frame(rt, config, 1, bytes([1, 2, 3]), 0)
    data = _rejected_header(case) + good + good
    frames, diag = _drain(rt, config, data, mode, deliver=True, buffer_size=256)
    assert len(frames) == 2 and not any(f.is_system for f, _ in frames)
    assert diag.cnt_system_rejected == 1 and diag.cnt_system_frames == 0


@pytest.mark.parametrize("mode", ["chunk_1", "chunk_3", "whole", "stream"])
def test_corrupt_system_frame_is_a_crc_failure(rt, mode):
    config = _config(rt, "standard")
    good = _user_frame(rt, config, 1, bytes([1, 2, 3]), 0)
    bad = bytearray(rt.system_frames.encode(config, rt.sf_system.LinkTestStop(test_id=3)))
    bad[-3] ^= 0xFF
    frames, diag = _drain(rt, config, good + bytes(bad) + good, mode, deliver=True, buffer_size=256)
    assert len(frames) == 2
    assert diag.cnt_crc_failures == 1 and diag.cnt_system_frames == 0


@pytest.mark.parametrize("mode", ["chunk_1", "whole", "stream"])
def test_system_and_application_sequence_numbers_are_separate(rt, mode):
    """Network frames carry their own sequence; system frames count gaps in their own space."""
    config = _config(rt, "network")
    sf = rt.sf_system
    stop = sf.LinkTestStop(test_id=1)
    data = (_user_frame(rt, config, 1, b"abc", 0)
            + rt.system_frames.encode(config, stop, seq=40)
            + _user_frame(rt, config, 1, b"abc", 1)
            + rt.system_frames.encode(config, stop, seq=41)
            + _user_frame(rt, config, 1, b"abc", 2))
    _frames, diag = _drain(rt, config, data, mode, deliver=False)
    assert diag.cnt_seq_gaps == 0 and diag.cnt_system_frames == 2
    gap = data + rt.system_frames.encode(config, stop, seq=43)   # 41 -> 43 skips one
    _frames, diag = _drain(rt, config, gap, mode, deliver=False)
    assert diag.cnt_seq_gaps == 1 and diag.cnt_system_frames == 3


def test_headerless_profile_treats_0x79_as_an_application_id(rt):
    fp = rt.frame_profiles
    config = _config(rt, "ipc")
    assert not rt.system_frames.supports_system_frames(config)

    def info(msg_id):
        return fp.MessageInfo(size=2, magic1=0, magic2=0, base_size=2, min_size=2) if msg_id == 0x79 else None

    data = bytes([0x79, 0xAB, 0xCD]) * 2
    for deliver in (False, True):
        reader = fp.AccumulatingReader(config, get_message_info=info, deliver_system_frames=deliver)
        reader.add_data(data)
        frames = [f for f in iter(reader.try_next, None) if f.valid]
        assert [(f.msg_id, f.is_system) for f in frames] == [(0x79, False)] * 2
        assert reader.diagnostics.cnt_system_frames == 0


def test_largest_tail_round_trips(rt):
    config = _config(rt, "standard")
    tail = bytes(i & 0xFF for i in range(MAX_TAIL))
    frame = rt.system_frames.encode(config, rt.sf_system.Ping(seq=1), tail=tail)
    reader = rt.frame_profiles.AccumulatingReader(config, buffer_size=len(frame), deliver_system_frames=True)
    reader.add_data(frame)
    result = reader.next()
    assert result.valid and rt.system_frames.decode(result)[1] == tail


def test_encode_refuses_what_the_wire_cannot_carry(rt):
    sf, sysf = rt.sf_system, rt.system_frames
    with pytest.raises(ValueError):
        sysf.encode(_config(rt, "ipc"), sf.Heartbeat())                     # no start byte
    with pytest.raises(ValueError):
        sysf.encode(_config(rt, "standard"), sf.Heartbeat(), tail=b"x")     # takes no tail
    with pytest.raises(ValueError):
        sysf.encode(_config(rt, "standard"), sf.Ping(), tail=bytes(MAX_TAIL + 1))


def test_conformance_page_lists_these_vectors():
    """The frames in the conformance page (section 9.3) are the frames built here."""
    from test_utils import REPO_ROOT
    page = (REPO_ROOT / "docs" / "src" / "content" / "docs" / "reference" / "conformance.md").read_text(encoding="utf-8")
    section = page.split("### 9.3 Test vectors", 1)[1]
    rows = [line for line in section.splitlines() if line.startswith("| Standard") or line.startswith("| Sensor")]
    listed = [bytes.fromhex(row.rstrip(" |").rsplit("`", 2)[1]) for row in rows]
    want = [HAND_COMPUTED] + [f for v, f in zip(VECTORS, EXPECTED) if v.profile != "network"]
    assert listed == want
