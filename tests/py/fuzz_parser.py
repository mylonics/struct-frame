#!/usr/bin/env python3
"""
Atheris fuzz harness for the Python AccumulatingReader.

Install + run locally:
    pip install atheris
    python tests/py/fuzz_parser.py -max_len=4096 -runs=100000

The harness feeds arbitrary bytes to the streaming parser for every shipped
profile. It does not assert semantic properties itself; it relies on atheris
(and the Python runtime) to surface any uncaught exception or crash, and it
bounds the drain loop so a malformed input cannot livelock the fuzzer.

This module imports the runtime boilerplate directly from src/ so it works
without first running the code generator.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the in-repo boilerplate importable without a generation step.
_HERE = Path(__file__).resolve()
_BOILERPLATE = _HERE.parents[2] / "src" / "struct_frame" / "boilerplate" / "py"
sys.path.insert(0, str(_BOILERPLATE))

try:
    import atheris  # type: ignore
except ImportError:
    print("[fuzz_parser] atheris not installed; install with `pip install atheris` and rerun.",
          file=sys.stderr)
    sys.exit(2)

from frame_profiles import (  # type: ignore  # noqa: E402
    AccumulatingReader,
    MessageInfo,
    PROFILE_STANDARD_CONFIG,
    PROFILE_SENSOR_CONFIG,
    PROFILE_IPC_CONFIG,
    PROFILE_BULK_CONFIG,
    PROFILE_NETWORK_CONFIG,
)


_PROFILES = [
    PROFILE_STANDARD_CONFIG,
    PROFILE_SENSOR_CONFIG,
    PROFILE_IPC_CONFIG,
    PROFILE_BULK_CONFIG,
    PROFILE_NETWORK_CONFIG,
]


_TABLE = {1: (8, 11, 22), 2: (32, 33, 44), 3: (100, 55, 66), 4: (1, 77, 88), 5: (200, 99, 111)}


def _stub_info(msg_id: int):
    """Real message table, identical to tests/fuzz/corpus.py, so seed frames from
    tests/fuzz/make_seed_corpus.py pass the checksum and reach the deeper parser paths."""
    entry = _TABLE.get(msg_id)
    if entry is None:
        return None
    size, m1, m2 = entry
    return MessageInfo(size=size, magic1=m1, magic2=m2, base_size=size, min_size=size)


def _drive(data: bytes) -> None:
    if not data:
        return
    mid = len(data) // 2
    for cfg in _PROFILES:
        reader = AccumulatingReader(cfg, get_message_info=_stub_info)
        # Two-slice feed exercises the cross-buffer accumulation path.
        reader.add_data(bytes(data[:mid]))
        for _ in range(256):
            if reader.try_next() is None:
                break
        reader.add_data(bytes(data[mid:]))
        for _ in range(256):
            if reader.try_next() is None:
                break


def TestOneInput(data: bytes) -> None:  # noqa: N802  (atheris convention)
    _drive(data)


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
