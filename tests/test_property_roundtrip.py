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

The test is intentionally skippable in local/dev environments when Hypothesis
or generated artifacts are missing. In CI, missing dependencies/artifacts are
treated as hard failures.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

CI_MODE = bool(os.environ.get("CI"))

try:
    import pytest
except ModuleNotFoundError:
    if CI_MODE:
        raise
    if __name__ == "__main__":
        print("SKIP: pytest not installed")
        raise SystemExit(0)
    raise

REPO_ROOT = Path(__file__).resolve().parents[1]
GEN_PY = REPO_ROOT / "tests" / "generated" / "py"

if CI_MODE:
    from hypothesis import HealthCheck, given, settings, strategies as st  # noqa: E402
else:
    pytest.importorskip("hypothesis", reason="hypothesis not installed")
    from hypothesis import HealthCheck, given, settings, strategies as st  # noqa: E402

if not GEN_PY.exists():
    msg = "tests/generated/py does not exist — run `python test_all.py --only-generate` first."
    if CI_MODE:
        raise RuntimeError(msg)
    pytest.skip(msg, allow_module_level=True)

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
except (ImportError, ModuleNotFoundError, SyntaxError) as exc:  # pragma: no cover
    msg = f"generated Python SDK not importable: {exc}"
    if CI_MODE:
        raise RuntimeError(msg) from exc
    pytest.skip(msg, allow_module_level=True)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

@st.composite
def basic_types_messages(draw):  # noqa: D401
    """Random BasicTypesMessage with field values inside their declared ranges.

    Floats deliberately *include* NaN/±Inf (and, via Hypothesis, ±0.0 and
    subnormals): the round-trip compares the serialized byte representation, so
    the special-value bit patterns must survive encode→decode. These were
    previously excluded (allow_nan=False/allow_infinity=False), leaving a real
    gap — IEEE-754 special values are a classic source of serialization bugs.
    """
    return BasicTypesMessage(
        small_int=draw(st.integers(min_value=-(2**7), max_value=2**7 - 1)),
        medium_int=draw(st.integers(min_value=-(2**15), max_value=2**15 - 1)),
        regular_int=draw(st.integers(min_value=-(2**31), max_value=2**31 - 1)),
        large_int=draw(st.integers(min_value=-(2**63), max_value=2**63 - 1)),
        small_uint=draw(st.integers(min_value=0, max_value=2**8 - 1)),
        medium_uint=draw(st.integers(min_value=0, max_value=2**16 - 1)),
        regular_uint=draw(st.integers(min_value=0, max_value=2**32 - 1)),
        large_uint=draw(st.integers(min_value=0, max_value=2**64 - 1)),
        single_precision=draw(st.floats(allow_nan=True, allow_infinity=True, width=32)),
        double_precision=draw(st.floats(allow_nan=True, allow_infinity=True, width=64)),
        flag=draw(st.booleans()),
    )


# Explicit IEEE-754 edge values that must round-trip bit-for-bit, in addition to
# the randomized coverage above (guarantees these are always exercised).
_EDGE_FLOATS = [
    0.0, -0.0, 1.0, -1.0,
    float("inf"), float("-inf"), float("nan"),
    1.175494e-38,   # ~smallest normal float32
    3.402823e38,    # ~largest finite float32
]


# ---------------------------------------------------------------------------
# Round-trip property
# ---------------------------------------------------------------------------

def _roundtrip(profile, msg):
    encoded = encode_message(profile, msg)
    reader = AccumulatingReader(profile, get_message_info=get_message_info)
    reader.add_data(encoded)
    result = reader.next()
    assert result.valid, f"parser rejected its own output for {type(msg).__name__}"
    decoded = type(msg).deserialize(result.msg_data)
    assert decoded is not None, f"deserialize returned None for {type(msg).__name__}"
    assert decoded.serialize() == msg.serialize(), (
        f"decoded payload differs from original for {type(msg).__name__}"
    )
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


@pytest.mark.parametrize("value", _EDGE_FLOATS, ids=lambda v: repr(v))
def test_ieee754_edge_floats_roundtrip(value):
    """IEEE-754 edge values (±0.0, ±Inf, NaN, subnormal/max) must survive
    encode→decode bit-for-bit via the serialized representation.

    The round-trip compares ``serialize()`` bytes, so e.g. -0.0 (sign bit set)
    must not collapse to +0.0 and a NaN bit pattern must be preserved.
    """
    msg = BasicTypesMessage(single_precision=value, double_precision=value)
    result = _roundtrip(PROFILE_STANDARD_CONFIG, msg)
    assert result.valid
