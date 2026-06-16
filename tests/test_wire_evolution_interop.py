#!/usr/bin/env python3
"""
Cross-version *extension interop* tests.

Unlike ``test_wire_evolution.py`` (which exercises a single schema and *simulates*
an older peer by trimming bytes), this suite generates two **separate** schema
versions of the same messages into two **separate** namespaces:

  * ``wire_evolution_v1`` -- base fields only, completely unaware of extensions.
  * ``wire_evolution_v2`` -- same msg_ids/base fields **plus** ``extensions_start``
    and the extension fields/variants.

Because each side is generated independently, neither knows about the other's
extra fields -- exactly mirroring two real code-bases that evolved apart.  The
two builds nevertheless agree on the magic bytes (computed from base fields
only) and the base field layout, which is what makes cross-version interop
work over a length-bearing profile.

Scenarios (mirrors the project's wire-evolution interop plan):

  1. Newer sender -> older receiver: v2 encodes extensions, v1 decodes base,
     trailing extension bytes skipped via the frame length field.
  2. Older sender -> newer receiver: v1 encodes base-only, v2 decodes base and
     zero-fills the extension fields.
  3. Same-version sanity: v2 -> v2 with extensions round-trips fully.
  4. Newer ext oneof variant -> older receiver degrades gracefully (unknown
     discriminator, no corruption).
  5. Older base oneof variant -> newer receiver decodes correctly.
  6. Multi-oneof: base oneof unaffected while the ext oneof exercises 4 and 5.
  7. Corrupted extension bytes invalidate the full CRC (magic seed still matches).
  8. Truncated payload (fewer bytes than the length field claims) is rejected.
  9. Length-less profile guard (IPC/Sensor): extension fields are fixed bytes,
     so a base-only older frame is *not* silently mis-parsed by a newer
     receiver -- documenting the "both sides must agree" constraint.
 10. Variable base array + trailing extension field, both interop directions.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from test_utils import _check, run_generator, load_generated_module, REPO_ROOT, SRC_DIR

PROTO_V1 = REPO_ROOT / "tests" / "proto" / "wire_evolution_v1.sf"
PROTO_V2 = REPO_ROOT / "tests" / "proto" / "wire_evolution_v2.sf"

# Length-bearing profiles (carry an explicit payload length field).
LENGTH_BEARING = ("standard", "bulk", "network")
# Length-less profiles (fixed size; both sides must agree on the full size).
LENGTH_LESS = ("sensor", "ipc")


def _generate(out_dir: Path) -> None:
    """Generate the v1 and v2 schemas into the *same* output dir."""
    for proto in (PROTO_V1, PROTO_V2):
        result = run_generator(
            proto,
            "--build_py", "--py_path", str(out_dir / "py"), "--force",
        )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            _check(False, f"code generation failed for {proto.name}")


def _load_gen(py_dir: Path, module_name: str):
    return load_generated_module(
        py_dir / "struct_frame" / "generated" / f"{module_name}.py",
        module_name,
    )


# ---------------------------------------------------------------------------
# Framing helpers (real length-bearing / length-less profile encode + parse)
# ---------------------------------------------------------------------------

class Framing:
    """Thin wrapper over the generated frame_profiles module."""

    def __init__(self, fp):
        self._configs = {
            "standard": fp.PROFILE_STANDARD_CONFIG,
            "sensor":   fp.PROFILE_SENSOR_CONFIG,
            "ipc":      fp.PROFILE_IPC_CONFIG,
            "bulk":     fp.PROFILE_BULK_CONFIG,
            "network":  fp.PROFILE_NETWORK_CONFIG,
        }
        self._fp = fp

    def encode(self, profile: str, msg) -> bytes:
        return self._fp.encode_message(self._configs[profile], msg)

    def parse(self, profile: str, buf: bytes, get_message_info):
        config = self._configs[profile]
        reader = self._fp.AccumulatingReader(config, get_message_info=get_message_info)
        reader.add_data(buf)
        return reader.next()

    def header_size(self, profile: str) -> int:
        return self._configs[profile].header_size


def _decode_zerofill(cls, info):
    """Decode a frame payload, zero-filling any extension bytes the sender omitted."""
    data = info.msg_data
    if len(data) < cls.MAX_SIZE:
        data = data + b"\x00" * (cls.MAX_SIZE - len(data))
    return cls.deserialize(data)


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

def scenario_1_newer_to_older(v1, v2, fr: Framing) -> None:
    """Newer sender -> older receiver over every length-bearing profile."""
    for profile in LENGTH_BEARING:
        orig = v2.BaseExtensionMessage(header=0xBEEF, seq=42, crc_seed=0xDEADC0DE)
        buf = fr.encode(profile, orig)
        info = fr.parse(profile, buf, v1.get_message_info)
        _check(info.valid, f"[S1/{profile}] v2->v1 frame validates CRC (magic from base only)")
        _check(info.msg_len == v2.BaseExtensionMessage.MAX_SIZE,
               f"[S1/{profile}] frame length carries full v2 payload size")
        decoded = v1.BaseExtensionMessage.deserialize(info.msg_data)
        _check(decoded.header == 0xBEEF and decoded.seq == 42,
               f"[S1/{profile}] v1 decodes base fields; trailing extension bytes ignored")


def scenario_2_older_to_newer(v1, v2, fr: Framing) -> None:
    """Older sender -> newer receiver: extensions zero-filled."""
    orig = v1.BaseExtensionMessage(header=0x1234, seq=7)
    buf = fr.encode("standard", orig)
    info = fr.parse("standard", buf, v2.get_message_info)
    _check(info.valid, "[S2] v1->v2 base-only frame validates CRC")
    _check(info.msg_len == v1.BaseExtensionMessage.MAX_SIZE,
           "[S2] frame length carries shorter base-only payload")
    decoded = _decode_zerofill(v2.BaseExtensionMessage, info)
    _check(decoded.header == 0x1234 and decoded.seq == 7,
           "[S2] v2 decodes base fields correctly")
    _check(decoded.crc_seed == 0, "[S2] v2 extension field zero-filled to default")


def scenario_3_same_version(v2, fr: Framing) -> None:
    """Same-version v2 -> v2 with extensions populated round-trips fully."""
    cmd = v2.ExtCommandC(value_c=3.14, mode_c=2)
    orig = v2.OneOfExtensionMessage(device_id=2, command={"cmd_c": cmd},
                                    command_which="cmd_c", command_discriminator=3)
    buf = fr.encode("standard", orig)
    info = fr.parse("standard", buf, v2.get_message_info)
    _check(info.valid, "[S3] v2->v2 (ext variant) frame validates CRC")
    decoded = v2.OneOfExtensionMessage.deserialize(info.msg_data)
    _check(decoded.command_which == "cmd_c", "[S3] v2 round-trips extension variant discriminator")
    _check(math.isclose(decoded.command["cmd_c"].value_c, 3.14, rel_tol=1e-5),
           "[S3] v2 round-trips extension variant payload")


def scenario_4_newer_ext_variant_to_older(v1, v2, fr: Framing) -> None:
    """Newer ext oneof variant -> older receiver degrades gracefully."""
    cmd = v2.ExtCommandD(value_d=2.718281828)
    orig = v2.OneOfExtensionMessage(device_id=9, command={"cmd_d": cmd},
                                    command_which="cmd_d", command_discriminator=4)
    buf = fr.encode("standard", orig)
    info = fr.parse("standard", buf, v1.get_message_info)
    _check(info.valid, "[S4] v2 ext-variant -> v1 frame validates CRC")
    decoded = v1.OneOfExtensionMessage.deserialize(info.msg_data)
    _check(decoded.device_id == 9, "[S4] v1 still decodes the base header field")
    _check(decoded.command_which is None,
           "[S4] v1 treats unknown ext discriminator as no active variant (graceful)")
    _check(decoded.command_discriminator == 4,
           "[S4] v1 preserves the raw discriminator value without corruption")


def scenario_5_older_base_variant_to_newer(v1, v2, fr: Framing) -> None:
    """Older base oneof variant -> newer receiver decodes correctly."""
    cmd = v1.BaseCommandB(value_b=-1234, active_b=True)
    orig = v1.OneOfExtensionMessage(device_id=5, command={"cmd_b": cmd},
                                    command_which="cmd_b", command_discriminator=2)
    buf = fr.encode("standard", orig)
    info = fr.parse("standard", buf, v2.get_message_info)
    _check(info.valid, "[S5] v1 base-variant -> v2 frame validates CRC")
    decoded = _decode_zerofill(v2.OneOfExtensionMessage, info)
    _check(decoded.command_which == "cmd_b" and decoded.command["cmd_b"].value_b == -1234,
           "[S5] v2 decodes the base oneof variant correctly")


def scenario_6_multi_oneof(v1, v2, fr: Framing) -> None:
    """Multi-oneof: base oneof unaffected; ext oneof exercises S4/S5."""
    # Newer sender selects an extension variant in the *second* oneof only.
    first = v2.BaseCommandA(value_a=100, flags_a=5)
    sec = v2.ExtCommandC(value_c=2.71, mode_c=1)
    orig = v2.MultiOneOfExtensionMessage(
        priority=3,
        base_union={"first_a": first}, base_union_which="first_a", base_union_discriminator=1,
        ext_union={"second_ext": sec}, ext_union_which="second_ext", ext_union_discriminator=2,
    )
    buf = fr.encode("standard", orig)
    info = fr.parse("standard", buf, v1.get_message_info)
    _check(info.valid, "[S6] v2 multi-oneof (ext in 2nd union) -> v1 validates CRC")
    decoded = v1.MultiOneOfExtensionMessage.deserialize(info.msg_data)
    _check(decoded.priority == 3, "[S6] v1 decodes base header field")
    _check(decoded.base_union_which == "first_a"
           and decoded.base_union["first_a"].value_a == 100,
           "[S6] v1 decodes the FIRST (base) oneof unaffected by ext in the second")
    _check(decoded.ext_union_which is None,
           "[S6] v1 treats the second oneof's unknown ext variant as inactive (graceful)")

    # Older sender selects the base variant in the second oneof -> newer receiver.
    sec_base = v1.BaseCommandA(value_a=77, flags_a=9)
    orig2 = v1.MultiOneOfExtensionMessage(
        priority=4,
        base_union={"first_b": v1.BaseCommandB(value_b=3, active_b=False)},
        base_union_which="first_b", base_union_discriminator=2,
        ext_union={"second_a": sec_base}, ext_union_which="second_a", ext_union_discriminator=1,
    )
    buf2 = fr.encode("standard", orig2)
    info2 = fr.parse("standard", buf2, v2.get_message_info)
    _check(info2.valid, "[S6] v1 multi-oneof (base in 2nd union) -> v2 validates CRC")
    decoded2 = _decode_zerofill(v2.MultiOneOfExtensionMessage, info2)
    _check(decoded2.ext_union_which == "second_a"
           and decoded2.ext_union["second_a"].value_a == 77,
           "[S6] v2 decodes the older base variant in the ext oneof correctly")


def scenario_7_corrupted_extension(v1, v2, fr: Framing) -> None:
    """Corrupted extension bytes invalidate the full CRC even though the
    magic (base seed) still matches."""
    orig = v2.BaseExtensionMessage(header=0xBEEF, seq=42, crc_seed=0xDEADC0DE)
    buf = bytearray(fr.encode("standard", orig))
    ext_offset = fr.header_size("standard") + v2.BaseExtensionMessage.BASE_SIZE
    buf[ext_offset] ^= 0xFF  # flip a byte inside the extension region
    info = fr.parse("standard", bytes(buf), v1.get_message_info)
    _check(not info.valid, "[S7] corrupted extension byte invalidates full CRC")


def scenario_8_truncated(v1, fr: Framing) -> None:
    """A payload shorter than its declared length field is rejected."""
    orig = v1.BaseExtensionMessage(header=1, seq=2)
    buf = fr.encode("standard", orig)
    info = fr.parse("standard", buf[:-1], v1.get_message_info)
    _check(not info.valid, "[S8] truncated payload (fewer bytes than length claims) is rejected")


def scenario_9_lengthless_guard(v1, v2, fr: Framing) -> None:
    """Length-less profiles: extensions are fixed bytes, both sides must agree."""
    # Positive control: same fixed size on both ends still works.
    same = v2.BaseExtensionMessage(header=0xAA, seq=5, crc_seed=0x99)
    info = fr.parse("ipc", fr.encode("ipc", same), v2.get_message_info)
    _check(info.valid, "[S9] IPC (length-less) same-version frame validates")

    # Cross-version base-only frame on a length-less profile: must be rejected.
    older = v1.BaseExtensionMessage(header=0xAA, seq=5)
    info = fr.parse("ipc", fr.encode("ipc", older), v2.get_message_info)
    _check(not info.valid,
           "[S9] IPC base-only older frame is rejected by newer receiver "
           "(both sides must agree on size)")


def scenario_10_variable(v1, v2, fr: Framing) -> None:
    """Variable base array + trailing extension field, both directions."""
    # Newer -> older: v1 reads the variable base, ignores the trailing ext bytes.
    orig = v2.VariableExtensionMessage(node_id=7, readings=[10, 20, 30],
                                       ext_timestamp=0x12345678)
    buf = fr.encode("standard", orig)
    info = fr.parse("standard", buf, v1.get_message_info)
    _check(info.valid, "[S10] v2 variable+ext -> v1 validates CRC")
    decoded = v1.VariableExtensionMessage.deserialize(info.msg_data)
    _check(decoded.node_id == 7 and list(decoded.readings) == [10, 20, 30],
           "[S10] v1 locates/decodes variable base; trailing ext bytes ignored")

    # Older -> newer: v2 zero-fills the extension after the variable base.
    orig2 = v1.VariableExtensionMessage(node_id=9, readings=[1, 2])
    buf2 = fr.encode("standard", orig2)
    info2 = fr.parse("standard", buf2, v2.get_message_info)
    _check(info2.valid, "[S10] v1 variable (base-only) -> v2 validates CRC")
    decoded2 = _decode_zerofill(v2.VariableExtensionMessage, info2)
    _check(decoded2.node_id == 9 and list(decoded2.readings) == [1, 2],
           "[S10] v2 locates variable base after cross-version decode")
    _check(decoded2.ext_timestamp == 0,
           "[S10] v2 zero-fills the trailing extension field")


# ---------------------------------------------------------------------------
# Single collected pytest entry point
# ---------------------------------------------------------------------------

def test_wire_evolution_interop(tmp_path: Path) -> None:
    """Cross-version wire-evolution interop: 10 scenarios verifying framing interop."""
    out = tmp_path
    _generate(out)
    py_dir = out / "py"

    fp = load_generated_module(py_dir / "frame_profiles.py", "frame_profiles")
    fr = Framing(fp)
    v1 = _load_gen(py_dir, "wire_evolution_v1")
    v2 = _load_gen(py_dir, "wire_evolution_v2")

    # Sanity: the two independent builds agree on magic + base size.
    for name in ("BaseExtensionMessage", "OneOfExtensionMessage",
                 "MultiOneOfExtensionMessage", "VariableExtensionMessage"):
        c1, c2 = getattr(v1, name), getattr(v2, name)
        _check((c1.MAGIC1, c1.MAGIC2) == (c2.MAGIC1, c2.MAGIC2),
               f"[setup] {name}: v1/v2 magic bytes agree (base-only seed)")
        _check(c1.BASE_SIZE == c2.BASE_SIZE,
               f"[setup] {name}: v1/v2 base_size agrees")

    scenario_1_newer_to_older(v1, v2, fr)
    scenario_2_older_to_newer(v1, v2, fr)
    scenario_3_same_version(v2, fr)
    scenario_4_newer_ext_variant_to_older(v1, v2, fr)
    scenario_5_older_base_variant_to_newer(v1, v2, fr)
    scenario_6_multi_oneof(v1, v2, fr)
    scenario_7_corrupted_extension(v1, v2, fr)
    scenario_8_truncated(v1, fr)
    scenario_9_lengthless_guard(v1, v2, fr)
    scenario_10_variable(v1, v2, fr)
