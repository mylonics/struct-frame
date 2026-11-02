#!/usr/bin/env python3
"""Known-answer tests for the frame formats, independent of every runtime.

The golden files and the cross-language comparisons elsewhere in the suite are
produced by (and compared against) the struct-frame encoders themselves, so a bug
that is symmetric in encode and decode, or shared by all runtimes, would pass. These
tests fix the wire format from the specification instead:

* ``spec_frame`` below is a from-the-spec encoder that shares no code with any runtime.
* ``HAND_COMPUTED`` is a Standard frame whose checksum was worked out by hand
  (see the comment next to it), which pins the spec encoder itself.
* The Python, C and JavaScript runtimes must produce the same bytes for every
  vector, and the Python reader must decode them.

Format summary (all multi-byte values little-endian; the checksum is Fletcher-16 over
everything after the start bytes, then the two per-message magic bytes):

    Standard [90 71][LEN][MSG][payload][C1 C2]
    Sensor   [70][MSG][payload]
    IPC      [MSG][payload]
    Bulk     [90 74][LEN_LO LEN_HI][PKG][MSG][payload][C1 C2]
    Network  [90 78][SEQ][SYS][COMP][LEN_LO LEN_HI][PKG][MSG][payload][C1 C2]
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from test_utils import REPO_ROOT

BOILERPLATE = REPO_ROOT / "src" / "struct_frame" / "boilerplate"


@dataclass(frozen=True)
class Vector:
    profile: str          # standard | sensor | ipc | bulk | network
    msg_id: int           # local (low-byte) message id
    pkg_id: int = 0
    seq: int = 0
    sys_id: int = 0
    comp_id: int = 0
    payload: bytes = b""
    magic1: int = 0
    magic2: int = 0

    @property
    def wire_msg_id(self) -> int:
        """16-bit id as the runtimes see it: (pkg << 8) | msg for package profiles."""
        return (self.pkg_id << 8) | self.msg_id if self.profile in ("bulk", "network") else self.msg_id


def fletcher16(data: bytes, magic1: int, magic2: int) -> bytes:
    sum1 = sum2 = 0
    for byte in data + bytes([magic1, magic2]):
        sum1 = (sum1 + byte) % 256
        sum2 = (sum2 + sum1) % 256
    return bytes([sum1, sum2])


def spec_frame(v: Vector) -> bytes:
    """Encode ``v`` straight from the format description (no runtime code)."""
    n = len(v.payload)
    if v.profile == "standard":
        body = bytes([n, v.msg_id]) + v.payload
        return b"\x90\x71" + body + fletcher16(body, v.magic1, v.magic2)
    if v.profile == "sensor":
        return b"\x70" + bytes([v.msg_id]) + v.payload
    if v.profile == "ipc":
        return bytes([v.msg_id]) + v.payload
    if v.profile == "bulk":
        body = bytes([n & 0xFF, n >> 8, v.pkg_id, v.msg_id]) + v.payload
        return b"\x90\x74" + body + fletcher16(body, v.magic1, v.magic2)
    if v.profile == "network":
        body = bytes([v.seq, v.sys_id, v.comp_id, n & 0xFF, n >> 8, v.pkg_id, v.msg_id]) + v.payload
        return b"\x90\x78" + body + fletcher16(body, v.magic1, v.magic2)
    raise ValueError(v.profile)


# Hand-computed Standard frame: msg id 3, payload "abc", magic bytes 27 and 55.
#   checksummed bytes: 03 03 61 62 63 1B 37  (LEN, MSG, 'a' 'b' 'c', magic1, magic2)
#   sum1 running: 3, 6, 103, 201, 300%256=44, 71, 126        -> 0x7E
#   sum2 running: 3, 9, 112, 313%256=57, 101, 172, 298%256=42 -> 0x2A
HAND_COMPUTED = bytes.fromhex("90" "71" "03" "03" "616263" "7E" "2A")

VECTORS = [
    Vector("standard", 3, payload=b"abc", magic1=27, magic2=55),
    Vector("standard", 0, payload=b"", magic1=1, magic2=2),
    Vector("sensor", 5, payload=bytes([1, 2, 3, 4])),
    Vector("ipc", 9, payload=b"\xff"),
    Vector("bulk", 3, pkg_id=7, payload=bytes(range(16)), magic1=200, magic2=17),
    Vector("bulk", 255, pkg_id=255, payload=bytes(300 % 256 for _ in range(260)), magic1=1, magic2=1),
    Vector("network", 3, pkg_id=7, seq=9, sys_id=1, comp_id=42, payload=bytes(range(8)), magic1=1, magic2=2),
]
EXPECTED = [spec_frame(v) for v in VECTORS]


def test_spec_encoder_matches_hand_computed_frame():
    assert spec_frame(VECTORS[0]) == HAND_COMPUTED


def test_spec_vectors_are_what_we_think():
    assert EXPECTED[0] == HAND_COMPUTED
    assert EXPECTED[2] == bytes([0x70, 5, 1, 2, 3, 4])
    assert EXPECTED[3] == bytes([9, 0xFF])
    assert EXPECTED[4][:6] == bytes([0x90, 0x74, 16, 0, 7, 3])
    assert EXPECTED[5][2:4] == (260).to_bytes(2, "little")          # 16-bit length
    assert EXPECTED[6][:9] == bytes([0x90, 0x78, 9, 1, 42, 8, 0, 7, 3])


# --------------------------------------------------------------------------- Python

def _py_runtime(tmp_path: Path):
    """Import the Python boilerplate runtime (not generated code)."""
    import importlib.util

    def load(name):
        spec = importlib.util.spec_from_file_location(name, BOILERPLATE / "py" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    added = str(BOILERPLATE / "py")
    sys.path.insert(0, added)
    try:
        for name in ("frame_base", "frame_headers", "payload_types", "frame_profiles"):
            load(name)
        return sys.modules["frame_profiles"]
    finally:
        sys.path.remove(added)


PY_CONFIG = {"standard": "PROFILE_STANDARD_CONFIG", "sensor": "PROFILE_SENSOR_CONFIG",
             "ipc": "PROFILE_IPC_CONFIG", "bulk": "PROFILE_BULK_CONFIG",
             "network": "PROFILE_NETWORK_CONFIG"}


def _py_message(v: Vector):
    class Message:
        MSG_ID = v.wire_msg_id
        MAGIC1 = v.magic1
        MAGIC2 = v.magic2

        def serialize(self):
            return v.payload

    return Message()


@pytest.mark.parametrize("index", range(len(VECTORS)))
def test_python_runtime_encodes_spec_frames(index, tmp_path):
    fp = _py_runtime(tmp_path)
    v = VECTORS[index]
    config = getattr(fp, PY_CONFIG[v.profile])
    frame = fp.encode_message(config, _py_message(v), seq=v.seq, sys_id=v.sys_id, comp_id=v.comp_id)
    assert bytes(frame) == EXPECTED[index], f"{v.profile}: runtime frame differs from the spec frame"


@pytest.mark.parametrize("index", range(len(VECTORS)))
def test_python_runtime_decodes_spec_frames(index, tmp_path):
    fp = _py_runtime(tmp_path)
    v = VECTORS[index]
    if v.profile == "ipc":
        pytest.skip("headerless frames need an out-of-band length; covered by the encode test")
    config = getattr(fp, PY_CONFIG[v.profile])

    def info(msg_id):
        if msg_id != v.wire_msg_id:
            return None
        return fp.MessageInfo(size=len(v.payload), magic1=v.magic1, magic2=v.magic2,
                              base_size=len(v.payload), min_size=len(v.payload))

    reader = fp.AccumulatingReader(config, get_message_info=info)
    result = None
    for byte in EXPECTED[index]:
        result = reader.push_byte(byte)
    assert result is not None and result.valid, f"{v.profile}: reader rejected the spec frame"
    assert bytes(result.msg_data[:result.msg_len]) == v.payload
    assert result.msg_id == v.wire_msg_id


# --------------------------------------------------------------------------- C

C_CONFIG = {"standard": "PROFILE_STANDARD_CONFIG", "sensor": "PROFILE_SENSOR_CONFIG",
            "ipc": "PROFILE_IPC_CONFIG", "bulk": "PROFILE_BULK_CONFIG",
            "network": "PROFILE_NETWORK_CONFIG"}


def _c_source() -> str:
    rows = []
    for v in VECTORS:
        payload = ", ".join(str(b) for b in v.payload) or "0"
        rows.append(f"  {{&{C_CONFIG[v.profile]}, {v.msg_id}, {v.pkg_id}, {v.seq}, {v.sys_id}, "
                    f"{v.comp_id}, (const uint8_t[]){{{payload}}}, {len(v.payload)}, {v.magic1}, {v.magic2}}},")
    return f"""
#include <stdio.h>
#include "frame_profiles.h"

typedef struct {{
  const profile_config_t* cfg; uint16_t msg_id; uint8_t pkg, seq, sys, comp;
  const uint8_t* payload; size_t n; uint8_t m1, m2;
}} vec_t;

static const vec_t VECS[] = {{
{chr(10).join(rows)}
}};

int main(void) {{
  for (size_t i = 0; i < sizeof(VECS) / sizeof(VECS[0]); i++) {{
    const vec_t* v = &VECS[i];
    uint8_t buf[1024];
    buffer_writer_t w;
    buffer_writer_init(&w, v->cfg, buf, sizeof(buf));
    size_t n = buffer_writer_write(&w, v->msg_id, v->payload, v->n, v->seq, v->sys, v->comp, v->pkg, v->m1, v->m2);
    for (size_t k = 0; k < n; k++) printf("%02x", buf[k]);
    printf("\\n");
  }}
  return 0;
}}
"""


def test_c_runtime_encodes_spec_frames(tmp_path):
    cc = shutil.which(os.environ.get("CC", "gcc"))
    if cc is None:
        pytest.skip("no C compiler")
    src = tmp_path / "kat.c"
    src.write_text(_c_source(), encoding="utf-8")
    exe = tmp_path / ("kat.exe" if os.name == "nt" else "kat")
    build = subprocess.run([cc, "-std=c11", "-Wall", f"-I{BOILERPLATE / 'c'}", str(src), "-o", str(exe)],
                           capture_output=True, text=True, timeout=300)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    lines = run.stdout.split()
    assert lines == [frame.hex() for frame in EXPECTED], "C runtime frames differ from the spec frames"


# --------------------------------------------------------------------------- JavaScript

JS_CONFIG = {"standard": "ProfileStandardConfig", "sensor": "ProfileSensorConfig",
             "ipc": "ProfileIPCConfig", "bulk": "ProfileBulkConfig",
             "network": "ProfileNetworkConfig"}


def test_javascript_runtime_encodes_spec_frames(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    vectors = [{"config": JS_CONFIG[v.profile], "msgId": v.wire_msg_id, "pkg": v.pkg_id,
                "seq": v.seq, "sys": v.sys_id, "comp": v.comp_id, "payload": list(v.payload),
                "m1": v.magic1, "m2": v.magic2} for v in VECTORS]
    script = tmp_path / "kat.js"
    runtime = (BOILERPLATE / "js" / "frame-profiles.js").as_posix()
    script.write_text(f"""
const fp = require({json.dumps(runtime)});
const vectors = {json.dumps(vectors)};
for (const v of vectors) {{
  const payload = Uint8Array.from(v.payload);
  const msg = {{
    getMsgId: () => v.msgId, isVariable: () => false, _buffer: payload,
    serialize: () => payload, getMagic1: () => v.m1, getMagic2: () => v.m2,
  }};
  const frame = fp.encodeMessage(fp[v.config], msg, {{ seq: v.seq, sysId: v.sys, compId: v.comp, pkgId: v.pkg }});
  console.log(Buffer.from(frame).toString("hex"));
}}
""", encoding="utf-8")
    run = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.stdout.split() == [frame.hex() for frame in EXPECTED], \
        "JavaScript runtime frames differ from the spec frames"
