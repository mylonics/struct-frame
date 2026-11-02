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
    return "".join(f"{i} {n} {h}\n" for i, n, h in frames)


def parse_output(text: str):
    return [tuple(int(x) for x in line.split()) for line in text.splitlines() if line.strip()]


def reference_decode(profile: str, stream: bytes, chunk: int):
    """Decode with the Python runtime (the oracle other languages are compared with)."""
    import frame_profiles as fp
    reader = fp.AccumulatingReader(config_for(profile), get_message_info=get_message_info, buffer_size=1024)
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
            out.append((info.msg_id, len(data), fnv1a(data)))
    return out


def noisy_stream(profile: str, count: int = 80, seed: int = 3):
    """Valid frames with ~5% of the bytes overwritten at random (fuzz-style input)."""
    rng = random.Random(seed ^ 0xF00D)
    data = bytearray(b"".join(f for _, _, f in make_frames(profile, count, seed)))
    for _ in range(max(1, len(data) // 20)):
        data[rng.randrange(len(data))] = rng.randrange(256)
    return bytes(data)
