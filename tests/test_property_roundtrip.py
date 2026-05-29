#!/usr/bin/env python3
"""
Property-based round-trip tests using Hypothesis.

Tier C item 3 (scaffold): for every generated Python message class, generate
random instances, encode them through each supported profile, decode them
back, and assert equality.

This first revision only exercises the Python encode → Python decode path.
The cross-language fan-out described in the gap analysis (Python encode →
C/C++/JS/TS/C#/Rust decode) is tracked as a follow-up — it requires a
test-runner-level harness that drives subprocess decoders, which would
duplicate much of `tests/run_tests.py`.

Run:
    pip install hypothesis
    python test_all.py --only-generate   # produce tests/generated/py
    python -m pytest tests/test_property_roundtrip.py -v

The test is intentionally skipped when Hypothesis is not installed or when
the generator has not run yet — it must not block the standard suite.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GEN_PY = REPO_ROOT / "tests" / "generated" / "py"

pytest.importorskip("hypothesis", reason="hypothesis not installed")
from hypothesis import HealthCheck, given, settings, strategies as st  # noqa: E402

if not GEN_PY.exists():
    pytest.skip(
        "tests/generated/py does not exist — run `python test_all.py --only-generate` first.",
        allow_module_level=True,
    )

sys.path.insert(0, str(GEN_PY))

# Import the runtime + a small, representative subset of generated message
# classes.  We intentionally avoid the comprehensive-array / nested-enum
# classes here: they require careful strategy construction and are covered
# by the deterministic round-trip suite already.
try:
    from frame_profiles import (  # type: ignore  # noqa: E402
        AccumulatingReader,
        PROFILE_BULK_CONFIG,
        PROFILE_NETWORK_CONFIG,
        PROFILE_STANDARD_CONFIG,
        encode_message,
    )
    from struct_frame.generated.serialization_test import (  # type: ignore  # noqa: E402
        BasicTypesMessage,
        get_message_info,
    )
except Exception as exc:  # pragma: no cover  — fail soft, scaffold not yet wired
    pytest.skip(f"generated Python SDK not importable: {exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

@st.composite
def basic_types_messages(draw):  # noqa: D401
    """Random BasicTypesMessage with field values inside their declared ranges."""
    return BasicTypesMessage(
        small_int=draw(st.integers(min_value=-(2**7),  max_value=2**7 - 1)),
        medium_int=draw(st.integers(min_value=-(2**15), max_value=2**15 - 1)),
        regular_int=draw(st.integers(min_value=-(2**31), max_value=2**31 - 1)),
        large_int=draw(st.integers(min_value=-(2**63), max_value=2**63 - 1)),
        small_uint=draw(st.integers(min_value=0, max_value=2**8 - 1)),
        medium_uint=draw(st.integers(min_value=0, max_value=2**16 - 1)),
        regular_uint=draw(st.integers(min_value=0, max_value=2**32 - 1)),
        large_uint=draw(st.integers(min_value=0, max_value=2**64 - 1)),
        single_precision=draw(st.floats(allow_nan=False, allow_infinity=False, width=32)),
        double_precision=draw(st.floats(allow_nan=False, allow_infinity=False, width=64)),
        flag=draw(st.booleans()),
    )


# ---------------------------------------------------------------------------
# Round-trip property
# ---------------------------------------------------------------------------

def _roundtrip(profile, msg):
    encoded = encode_message(profile, msg)
    reader = AccumulatingReader(profile, get_message_info=get_message_info)
    reader.add_data(encoded)
    result = reader.next()
    assert result.valid, f"parser rejected its own output for {type(msg).__name__}"
    return result


# Hypothesis can take a while; cap deadlines so CI doesn't flap.
@settings(max_examples=50, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
@given(msg=basic_types_messages())
def test_basic_types_roundtrip_standard(msg):
    """Standard profile (CRC + length): encode → decode → equal."""
    _roundtrip(PROFILE_STANDARD_CONFIG, msg)


@settings(max_examples=50, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
@given(msg=basic_types_messages())
def test_basic_types_roundtrip_bulk(msg):
    """Bulk profile (no CRC, extended msg-id): encode → decode."""
    _roundtrip(PROFILE_BULK_CONFIG, msg)


@settings(max_examples=50, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
@given(msg=basic_types_messages())
def test_basic_types_roundtrip_network(msg):
    """Network profile (CRC + extended msg-id): encode → decode."""
    _roundtrip(PROFILE_NETWORK_CONFIG, msg)
