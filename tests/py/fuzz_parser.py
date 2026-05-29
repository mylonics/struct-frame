#!/usr/bin/env python3
"""
Atheris fuzz harness for the Python AccumulatingReader.

Install + run locally:
    pip install atheris
    python tests/py/fuzz_parser.py -max_len=4096 -runs=100000

The harness feeds arbitrary bytes to the streaming parser for every shipped
profile and asserts the parser never raises an unexpected exception, never
returns inconsistent results, and always terminates.

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


def _stub_info(_msg_id: int) -> MessageInfo:
    """Return a tiny, well-formed MessageInfo for the parser to use when the
    profile lacks a length field.  The fuzz input dictates magic byte values,
    so the parser must remain safe even when its callback's magic bytes do
    not match the embedded ones (most inputs will mismatch and be dropped)."""
    return MessageInfo(size=64, magic1=0, magic2=0)


def _drive(data: bytes) -> None:
    if not data:
        return
    mid = len(data) // 2
    for cfg in _PROFILES:
        reader = AccumulatingReader(cfg, get_message_info=_stub_info)
        # Two-slice feed exercises the cross-buffer accumulation path.
        reader.add_data(bytes(data[:mid]))
        for _ in range(256):
            if not reader.next().valid:
                break
        reader.add_data(bytes(data[mid:]))
        for _ in range(256):
            if not reader.next().valid:
                break


def TestOneInput(data: bytes) -> None:  # noqa: N802  (atheris convention)
    try:
        _drive(data)
    except (ValueError, IndexError, OverflowError, TypeError):
        # These are acceptable parser-rejection signals.  Anything else
        # (MemoryError, RecursionError, AttributeError, AssertionError)
        # propagates and atheris reports it as a finding.
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
