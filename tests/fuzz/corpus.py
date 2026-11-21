"""Shared corpus for the cross-language stream-parser tests.

Both the tests and the fuzz seed corpus use the same fixed message table, so every
language's driver can supply real message info (size + magic numbers) instead of the
stub the old fuzz harnesses used. That lets a mutated input get past the checksum and
reach the deeper parser paths.

Message table: id -> (payload size, magic1, magic2). Keep it in sync with the
``TABLE`` constant in each driver under ``tests/fuzz/drivers``.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "struct_frame" / "boilerplate" / "py"))

TABLE = {
    1: (8, 11, 22),
    2: (32, 33, 44),
    3: (100, 55, 66),
    4: (1, 77, 88),
    5: (200, 99, 111),
}
PROFILES = ["standard", "sensor", "ipc", "bulk", "network"]


def fnv1a(data: bytes) -> int:
    h = 0x811C9DC5
    for b in data:
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


class _Msg:
    """Minimal object the Python encoder accepts."""

    def __init__(self, msg_id: int, payload: bytes):
        self.MSG_ID = msg_id
        self._payload = payload

    def serialize(self) -> bytes:
        return self._payload


def _msg_cls(msg_id: int):
    _, m1, m2 = TABLE[msg_id]
    return type(f"M{msg_id}", (_Msg,), {"MAGIC1": m1, "MAGIC2": m2})


def config_for(profile: str):
    import frame_profiles as fp
    return getattr(fp, f"PROFILE_{profile.upper()}_CONFIG")


def get_message_info(msg_id: int):
    import frame_profiles as fp
    entry = TABLE.get(msg_id)
    if entry is None:
        return None
    size, m1, m2 = entry
    return fp.MessageInfo(size=size, magic1=m1, magic2=m2, base_size=size, min_size=size)


def make_frames(profile: str, count: int, seed: int) -> List[Tuple[int, bytes, bytes]]:
    """Return [(msg_id, payload, frame_bytes)] for ``count`` valid frames."""
    import frame_profiles as fp
    rng = random.Random(seed)
    cfg = config_for(profile)
    out = []
    for i in range(count):
        msg_id = rng.choice(list(TABLE))
        size = TABLE[msg_id][0]
        payload = bytes(rng.randrange(256) for _ in range(size))
        frame = fp.encode_message(cfg, _msg_cls(msg_id)(msg_id, payload), seq=i & 0xFF, sys_id=1, comp_id=2)
        out.append((msg_id, payload, frame))
    return out


def clean_stream(profile: str, count: int = 40, seed: int = 1, junk: bool = True):
    """Valid frames separated by random garbage. Returns (stream, expected_frames)."""
    rng = random.Random(seed ^ 0x5EED)
    frames = make_frames(profile, count, seed)
    stream = bytearray()
    for _, _, frame in frames:
        # Garbage between frames. Avoid the profile's start bytes so garbage cannot
        # swallow a following frame header; that is the corrupted_stream case below.
        gap = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 6))) if junk else b""
        stream += gap + frame
    return bytes(stream), [(i, len(p), fnv1a(p)) for i, p, _ in frames]


def corrupted_stream(profile: str, count: int = 60, seed: int = 2):
    """Valid frames with random bit flips, truncations and garbage. Returns (stream, originals)."""
    rng = random.Random(seed ^ 0xBAD)
    frames = make_frames(profile, count, seed)
    stream = bytearray()
    for _, _, frame in frames:
        data = bytearray(frame)
        roll = rng.random()
        if roll < 0.2:
            data[rng.randrange(len(data))] ^= 1 << rng.randrange(8)
        elif roll < 0.3:
            data = data[: rng.randrange(1, len(data))]
        elif roll < 0.4:
            data = bytearray(rng.randrange(256) for _ in range(rng.randrange(1, 40)))
        stream += data
    originals = {(i, len(p), fnv1a(p)) for i, p, _ in frames}
    return bytes(stream), originals


def render(frames) -> str:
    return "".join(" ".join(str(x) for x in row) + "\n" for row in frames)


def parse_output(text: str):
    return [tuple(int(x) for x in line.split()) for line in text.splitlines() if line.strip()]


SYSTEM_ID_OFFSET = 65536   # drivers print system frames as msg_id + 65536


def reference_decode(profile: str, stream: bytes, chunk: int, system: bool = False):
    """Decode with the Python runtime (the oracle other languages are compared with).

    With ``system`` the reader delivers system frames (reported as msg_id + 65536) and the
    output ends with ``(-1, cnt_system_frames, cnt_system_rejected, cnt_crc_failures,
    cnt_seq_gaps)``, as the drivers print.
    """
    import frame_profiles as fp
    reader = fp.AccumulatingReader(config_for(profile), get_message_info=get_message_info, buffer_size=1024,
                                   deliver_system_frames=system)
    out = []
    pos = 0
    while pos < len(stream):
        reader.add_data(bytes(stream[pos:pos + chunk]))
        pos += chunk
        for _ in range(100000):
            info = reader.try_next()
            if info is None:
                break
            if not info.valid:
                continue
            data = bytes(info.msg_data)
            out.append((info.msg_id + (SYSTEM_ID_OFFSET if info.is_system else 0), len(data), fnv1a(data)))
    if system:
        d = reader.diagnostics
        out.append((-1, d.cnt_system_frames, d.cnt_system_rejected, d.cnt_crc_failures, d.cnt_seq_gaps))
    return out


# Profiles whose header can carry system frames (payload type 9, start byte 0x79).
SYSTEM_PROFILES = ["standard", "sensor", "bulk", "network"]


def _system_message(rng):
    """A random system message and tail (tails stay small: frames must fit every reader)."""
    import sf_system as sf
    import system_frames
    choice = rng.randrange(6)
    if choice == 0:
        msg = sf.Heartbeat(uptime_ms=rng.randrange(1 << 32), counter=rng.randrange(1 << 32),
                           wire_hash=rng.randrange(1 << 32), interval_ms=rng.randrange(1 << 16),
                           protocol_version=1, state=rng.randrange(5))
    elif choice == 1:
        msg = sf.Ping(t_send_us=rng.randrange(1 << 64), seq=rng.randrange(1 << 32))
    elif choice == 2:
        msg = sf.Pong(t_send_us=rng.randrange(1 << 64), seq=rng.randrange(1 << 32), max_tail=1024)
    elif choice == 3:
        msg = sf.LinkTestData(seq=rng.randrange(1 << 32), test_id=rng.randrange(256))
    elif choice == 4:
        msg = sf.RpcRequest(call_id=rng.randrange(1 << 16), payload_id=rng.randrange(256),
                            payload_magic1=rng.randrange(256), payload_magic2=rng.randrange(256))
    else:
        msg = sf.LinkStats(rx_bytes=rng.randrange(1 << 64), crc_failures=rng.randrange(1 << 32))
    takes_tail = type(msg).MSG_ID in system_frames.TAIL_MESSAGES
    tail = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 65))) if takes_tail else b""
    return msg, tail


def _stray_system_header(profile: str, rng) -> bytes:
    """A system start followed by a header no reader may accept (unknown system message id),
    so it is rejected and rescanned rather than swallowing the frames after it."""
    start = b"\x79" if profile == "sensor" else b"\x90\x79"
    plain = [b for b in range(256) if b not in (0x79, 0x90)]
    return start + bytes([rng.choice(plain), rng.choice(plain), rng.choice(plain), 5, 0, 0x7F])


def system_stream(profile: str, count: int = 40, seed: int = 4):
    """Application frames interleaved with system frames, corrupted system frames and
    skipped system sequence numbers, plus (CRC profiles) garbage and stray system headers.
    Returns (stream, expected_hidden, expected_delivered).

    Garbage never contains 0x79 or 0x90, so every frame stays recoverable; the expected
    lists are what a reader reports with system frames hidden and delivered (the latter
    ending with the (-1, system frames, rejected headers, CRC failures, sequence gaps)
    diagnostics row). Application frames never fail: the only CRC failures and sequence
    gaps are the system frames'."""
    import frame_profiles as fp
    import system_frames
    rng = random.Random(seed ^ 0x5157)
    cfg = config_for(profile)
    crc = cfg.has_crc
    frames = make_frames(profile, count, seed)
    stream = bytearray()
    hidden, delivered = [], []
    sys_seq = 0
    rejected = 0
    systems = 0
    crc_failures = 0
    gaps = 0
    for msg_id, payload, frame in frames:
        if crc and rng.random() < 0.3:
            stream += bytes(rng.choice([b for b in range(256) if b not in (0x79, 0x90)])
                            for _ in range(rng.randrange(1, 6)))
        if crc and rng.random() < 0.2:
            stream += _stray_system_header(profile, rng)
            rejected += 1
        if rng.random() < 0.1:
            # A corrupted system frame: a CRC failure. Its sequence number is not used up,
            # so the next system frame carries it and no gap is counted.
            msg, tail = _system_message(rng)
            bad = bytearray(system_frames.encode(cfg, msg, tail=tail, seq=sys_seq & 0xFF, sys_id=3, comp_id=4))
            bad[-3] ^= 0x5A           # the last payload byte
            stream += bad
            crc_failures += 1
        if rng.random() < 0.5:
            if systems and rng.random() < 0.15:
                sys_seq += 1          # a lost system frame: one sequence gap
                gaps += 1
            msg, tail = _system_message(rng)
            body = msg.serialize() + tail
            stream += system_frames.encode(cfg, msg, tail=tail, seq=sys_seq & 0xFF, sys_id=3, comp_id=4)
            sys_seq += 1
            systems += 1
            delivered.append((type(msg).MSG_ID + SYSTEM_ID_OFFSET, len(body), fnv1a(body)))
        stream += frame
        hidden.append((msg_id, len(payload), fnv1a(payload)))
        delivered.append((msg_id, len(payload), fnv1a(payload)))
    delivered.append((-1, systems, rejected, crc_failures, gaps))
    del fp
    return bytes(stream), hidden, delivered


def noisy_stream(profile: str, count: int = 80, seed: int = 3):
    """Valid frames with ~5% of the bytes overwritten at random (fuzz-style input)."""
    rng = random.Random(seed ^ 0xF00D)
    data = bytearray(b"".join(f for _, _, f in make_frames(profile, count, seed)))
    for _ in range(max(1, len(data) // 20)):
        data[rng.randrange(len(data))] = rng.randrange(256)
    return bytes(data)
