#!/usr/bin/env python3
"""
Wire evolution for variants inside a trimmed ``oneof`` (variable envelope,
non-variable discriminated oneof with ``option min_size``).

The three fixtures ``tests/proto/trimmed_union_v{2,3,4}.sf`` declare the same
``TaskEnvelope`` with a ``ScanTaskCommand`` variant that grows between
versions (v2: 52B, v3: 62B, v4: 70B; ``min_size = 60``). Frames encoded by one
version must decode in another:

  * older sender -> newer receiver: missing extension fields take their schema
    default (zero when none is declared)
  * newer sender -> older receiver: unknown trailing bytes are ignored
  * frames shorter than the smallest valid payload are rejected cleanly
  * ``MIN_SIZE`` is the smallest valid frame, not the largest variant

Python is exercised in-process (via generated modules); C and C++ decoders are
compiled with a tiny harness and fed frames encoded by the Python encoder.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from test_utils import run_generator, load_generated_module, REPO_ROOT

PROTO_DIR = REPO_ROOT / "tests" / "proto"
VERSIONS = (2, 3, 4)

BASE = dict(channel_mask=1, step_count=7, start_level=1.5, end_level=2.5,
            rate_hz=3.5, reserved=[0] * 32, request_id=9)

CPP_HARNESS = r"""
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include PKG_HDR
using namespace structframe::PKG;
int main(int, char** argv) {
    if (std::strcmp(argv[1], "serialize") == 0) {
        TaskEnvelope e{};
        e.execute_now = true;
        e.task_discriminator = static_cast<decltype(e.task_discriminator)>(1);
        e.task.scan_task = {};
        std::vector<uint8_t> out(e.serialized_size());
        size_t n = e.serialize(out);
        std::printf("n=%zu\nbytes=", n);
        for (uint8_t b : out) std::printf("%02x", b);
        std::printf("\n");
        return 0;
    }
#ifdef HAS_TINY
    if (std::strcmp(argv[1], "tiny") == 0) {
        const uint8_t frame[] = {2, 0x44, 0x33, 0x22, 0x11};
        TinyEnvelope e;
        size_t n = e.deserialize(frame, sizeof(frame));
        std::printf("n=%zu extra=%u\n", n, (unsigned)e.command.zero_default.extra);
        return 0;
    }
#endif
    std::vector<uint8_t> buf;
    for (const char* p = argv[1]; p[0] && p[1]; p += 2) {
        char h[3] = {p[0], p[1], 0};
        buf.push_back((uint8_t)strtol(h, nullptr, 16));
    }
    TaskEnvelope e;
    size_t n = e.deserialize(buf.data(), buf.size());
    std::printf("n=%zu\n", n);
    if (!n) return 0;
    auto& s = e.task.scan_task;
    std::printf("wb=%u we=%u\n", (unsigned)s.window_begin_pct, (unsigned)s.window_end_pct);
#ifdef HAS_WARMUP
    std::printf("stage=%u mode=%d\n", (unsigned)s.warmup.stage_id, (int)s.warmup.mode);
#endif
#ifdef HAS_SCALE
    std::printf("scale=%g\n", s.scale_factor);
#endif
    std::printf("min=%zu\n", (size_t)TaskEnvelope::MIN_SIZE);
    return 0;
}
"""

C_HARNESS = r"""
#include <stdio.h>
#include <stdlib.h>
#include PKG_HDR
int main(int argc, char** argv) {
    (void)argc;
    uint8_t buf[1024]; size_t len = 0;
    for (const char* p = argv[1]; p[0] && p[1]; p += 2) {
        char h[3] = {p[0], p[1], 0};
        buf[len++] = (uint8_t)strtol(h, NULL, 16);
    }
    PFX(TaskEnvelope) e;
    size_t n = PFX(TaskEnvelope_deserialize)(buf, len, &e);
    printf("n=%zu\n", n);
    if (!n) return 0;
    printf("wb=%u we=%u\n", (unsigned)e.task.scan_task.window_begin_pct, (unsigned)e.task.scan_task.window_end_pct);
#ifdef HAS_WARMUP
    printf("stage=%u mode=%d\n", (unsigned)e.task.scan_task.warmup.stage_id, (int)e.task.scan_task.warmup.mode);
#endif
#ifdef HAS_SCALE
    printf("scale=%g\n", e.task.scan_task.scale_factor);
#endif
    printf("min=%d\n", (int)MIN_CONST);
    return 0;
}
"""

JS_HARNESS = r"""
const assert = require('assert');
const args = process.argv.slice(process.argv[1].endsWith('.ts') ? 2 : 1);
const v2 = require(args[0]);
const v3 = require(args[1]);
const v4 = require(args[2]);
const olderBytes = Buffer.from(args[3], 'hex');
const currentBytes = Buffer.from(args[4], 'hex');
const newerBytes = Buffer.from(args[5], 'hex');
const malformedBytes = Buffer.from(args[6], 'hex');

function scan(env, mod) {
  return new mod.ScanTaskCommand(
    Buffer.from(env.taskData).subarray(0, mod.ScanTaskCommand._size));
}
function rejects(fn) {
  let rejected = false;
  try { fn(); } catch (_) { rejected = true; }
  assert(rejected, 'malformed frame must be rejected');
}

const fromOlder = scan(v3.TaskEnvelope.deserializeWire(olderBytes), v3);
assert.strictEqual(fromOlder.windowBeginPct, 85);
assert.strictEqual(fromOlder.warmup[0].stageId, 0);
const fromNewer = scan(v3.TaskEnvelope.deserializeWire(newerBytes), v3);
assert.strictEqual(fromNewer.warmup[0].stageId, 1);
const withDefault = scan(v4.TaskEnvelope.deserializeWire(currentBytes), v4);
assert.strictEqual(withDefault.scaleFactor, 1.5);
rejects(() => v3.TaskEnvelope.deserializeWire(malformedBytes));

const tiny = Buffer.from([2, 0x44, 0x33, 0x22, 0x11]);
const tinyEnvelope = v3.TinyEnvelope.deserializeWire(tiny);
const zero = new v3.TinyZeroCommand(
  Buffer.from(tinyEnvelope.commandData).subarray(0, v3.TinyZeroCommand._size));
assert.strictEqual(zero.extra, 0);
assert.doesNotThrow(() => v3.TinyUnknownEnvelope.deserializeWire(Buffer.alloc(5)));
"""

RUST_HARNESS = r"""
use struct_frame_sdk::trimmed_union_v3 as v3;
use struct_frame_sdk::trimmed_union_v4 as v4;

fn from_hex(value: &str) -> Vec<u8> {
    value.as_bytes().chunks_exact(2).map(|pair| {
        u8::from_str_radix(std::str::from_utf8(pair).unwrap(), 16).unwrap()
    }).collect()
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let older = from_hex(&args[1]);
    let current = from_hex(&args[2]);
    let newer = from_hex(&args[3]);
    let malformed = from_hex(&args[4]);

    let from_older = v3::TaskEnvelope::unpack(&older).unwrap();
    assert_eq!(from_older.task_bytes[50], 85);
    assert_eq!(&from_older.task_bytes[52..62], &[0; 10]);
    let from_newer = v3::TaskEnvelope::unpack(&newer).unwrap();
    assert_eq!(from_newer.task_bytes[52 + 9], 1);

    let with_default = v4::TaskEnvelope::unpack(&current).unwrap();
    assert_eq!(f64::from_le_bytes(with_default.task_bytes[62..70].try_into().unwrap()), 1.5);
    assert!(v3::TaskEnvelope::unpack(&malformed).is_none());
    assert!(v3::TinyUnknownEnvelope::unpack(&[0; 5]).is_some());

    let tiny = v3::TinyEnvelope::unpack(&[2, 0x44, 0x33, 0x22, 0x11]).unwrap();
    assert_eq!(u32::from_le_bytes(tiny.command_bytes[4..8].try_into().unwrap()), 0);
}
"""

CSHARP_HARNESS = r"""
using System;
using V3 = StructFrame.TrimmedUnionV3;
using V4 = StructFrame.TrimmedUnionV4;

static byte[] FromHex(string value) => Convert.FromHexString(value);
static void Check(bool condition, string message)
{
    if (!condition) throw new Exception(message);
}
static void Rejects(Action action)
{
    try { action(); }
    catch (Exception) { return; }
    throw new Exception("malformed frame was accepted");
}

var olderBytes = FromHex(args[0]);
var currentBytes = FromHex(args[1]);
var newerBytes = FromHex(args[2]);
var malformedBytes = FromHex(args[3]);

var fromOlder = V3.TaskEnvelope.DeserializeVariable(olderBytes);
Check(fromOlder.ScanTask.WindowBeginPct == 85, "older sender fields");
Check(fromOlder.ScanTask.Warmup.StageId == 0, "missing nested fields default");
var fromNewer = V3.TaskEnvelope.DeserializeVariable(newerBytes);
Check(fromNewer.ScanTask.Warmup.StageId == 1, "newer sender fields");
var withDefault = V4.TaskEnvelope.DeserializeVariable(currentBytes);
Check(withDefault.ScanTask.ScaleFactor == 1.5, "schema default");
Rejects(() => V3.TaskEnvelope.DeserializeVariable(malformedBytes));

var tiny = V3.TinyEnvelope.DeserializeVariable(new byte[] { 2, 0x44, 0x33, 0x22, 0x11 });
Check(tiny.ZeroDefault.Extra == 0, "zero-default extension");
_ = V3.TinyUnknownEnvelope.DeserializeVariable(new byte[5]);
"""


@pytest.fixture(scope="module")
def gen(tmp_path_factory):
    out = tmp_path_factory.mktemp("trimmed_union")
    for v in VERSIONS:
        result = run_generator(
            PROTO_DIR / f"trimmed_union_v{v}.sf",
            "--build_py", "--py_path", str(out / "py"),
            "--build_c", "--c_path", str(out / "c"),
            "--build_cpp", "--cpp_path", str(out / "cpp"),
            "--build_ts", "--ts_path", str(out / "ts"),
            "--build_js", "--js_path", str(out / "js"),
            "--build_rust", "--rust_path", str(out / "rust"),
            "--build_csharp", "--csharp_path", str(out / "csharp"),
            "--force")
        assert result.returncode == 0, result.stdout + result.stderr
    mods = {
        v: load_generated_module(
            out / "py" / "struct_frame" / "generated" / f"trimmed_union_v{v}.py",
            f"trimmed_union_v{v}")
        for v in VERSIONS
    }
    return out, mods


def _frame(mod, **ext):
    scan = mod.ScanTaskCommand(**BASE, **ext)
    return mod.TaskEnvelope(execute_now=True, task_which="scan_task",
                            task={"scan_task": scan}).serialize()


def _v3_frame(mods, begin=75, end=95):
    m = mods[3]
    return _frame(m, window_begin_pct=begin, window_end_pct=end,
                  warmup=m.WarmupConfig(mode=2, duration_sec=5.0, stage_id=2))


def _v2_frame(mods):
    return _frame(mods[2], window_begin_pct=85, window_end_pct=95)


def _v4_frame(mods):
    m = mods[4]
    return _frame(m, window_begin_pct=80, window_end_pct=100,
                  warmup=m.WarmupConfig(mode=2, duration_sec=3.0, stage_id=1),
                  scale_factor=1.5)


def _bulk_frame(mods):
    m = mods[3]
    return m.TaskEnvelope(execute_now=True, task_which="bulk_config",
                          task={"bulk_config": m.BulkConfigCommand(table_bytes=[0] * 353)}).serialize()


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------

def test_wire_sizes_and_min_size(gen):
    _, mods = gen
    assert len(_v2_frame(mods)) == 62
    assert len(_v3_frame(mods)) == 64
    assert len(_v4_frame(mods)) == 72
    for v in VERSIONS:
        assert mods[v].TaskEnvelope.MIN_SIZE == 62
        assert mods[v].TaskEnvelope.MAX_SIZE == 355


def test_py_round_trip(gen):
    _, mods = gen
    scan = mods[3].TaskEnvelope.deserialize(_v3_frame(mods)).task["scan_task"]
    assert (scan.window_begin_pct, scan.window_end_pct) == (75, 95)
    assert (scan.warmup.mode, scan.warmup.duration_sec, scan.warmup.stage_id) == (2, 5.0, 2)
    assert scan.step_count == 7


def test_py_older_sender_newer_receiver(gen):
    _, mods = gen
    scan = mods[3].TaskEnvelope.deserialize(_v2_frame(mods)).task["scan_task"]
    assert (scan.window_begin_pct, scan.window_end_pct) == (85, 95)
    assert (scan.warmup.mode, scan.warmup.duration_sec, scan.warmup.stage_id) == (0, 0.0, 0)


def test_py_newer_sender_older_receiver(gen):
    _, mods = gen
    scan = mods[3].TaskEnvelope.deserialize(_v4_frame(mods)).task["scan_task"]
    assert (scan.window_begin_pct, scan.window_end_pct) == (80, 100)
    assert (scan.warmup.mode, scan.warmup.duration_sec, scan.warmup.stage_id) == (2, 3.0, 1)


def test_py_extension_schema_default(gen):
    _, mods = gen
    scan = mods[4].TaskEnvelope.deserialize(_v3_frame(mods)).task["scan_task"]
    assert scan.scale_factor == 1.5
    assert scan.window_begin_pct == 75


def test_py_max_size_bulk_variant(gen):
    _, mods = gen
    bulk = _bulk_frame(mods)
    assert len(bulk) == 355
    assert mods[3].TaskEnvelope.deserialize(bulk) is not None


@pytest.mark.parametrize("size", [0, 1, 61])
def test_py_truncated_frames_rejected(gen, size):
    _, mods = gen
    assert mods[3].TaskEnvelope.deserialize(_v2_frame(mods)[:size]) is None


def test_py_variant_shorter_than_base_rejected(gen):
    _, mods = gen
    assert mods[3].TaskEnvelope.deserialize(_bulk_frame(mods)[:62]) is None


# ---------------------------------------------------------------------------
# C / C++ (compiled harness)
# ---------------------------------------------------------------------------

def _run_args(exe: Path, *args: str) -> dict:
    out = subprocess.run([str(exe), *args], capture_output=True, text=True, check=True).stdout
    result = {}
    for line in out.split():
        for item in line.split():
            k, _, v = item.partition("=")
            result[k] = v
    return result


def _run(exe: Path, frame: bytes) -> dict:
    return _run_args(exe, frame.hex())


def _build(tmp: Path, lang: str, ver: int, gen_dir: Path) -> Path:
    flags = []
    if ver >= 3:
        flags.append("-DHAS_WARMUP")
    if ver == 3:
        flags.append("-DHAS_TINY")
    if ver >= 4:
        flags.append("-DHAS_SCALE")
    exe = tmp / f"{lang}_v{ver}"
    if lang == "cpp":
        if not shutil.which("g++"):
            pytest.skip("g++ not available")
        src = tmp / "harness.cpp"
        src.write_text(CPP_HARNESS)
        cmd = ["g++", "-std=c++20", "-Wall", "-Werror", f"-I{gen_dir / 'cpp'}",
               f"-DPKG=trimmed_union_v{ver}",
               f'-DPKG_HDR="trimmed_union_v{ver}.structframe.hpp"', *flags, str(src), "-o", str(exe)]
    else:
        if not shutil.which("gcc"):
            pytest.skip("gcc not available")
        src = tmp / "harness.c"
        src.write_text(C_HARNESS)
        cmd = ["gcc", "-Wall", "-Werror", f"-I{gen_dir / 'c'}",
               f'-DPKG_HDR="trimmed_union_v{ver}.structframe.h"',
               f"-DPFX(x)=TrimmedUnionV{ver}##x",
               f"-DMIN_CONST=TRIMMED_UNION_V{ver}_TASK_ENVELOPE_MIN_SIZE", *flags, str(src), "-o", str(exe)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return exe


@pytest.mark.parametrize("lang", ["c", "cpp"])
def test_native_decoders(gen, tmp_path, lang):
    gen_dir, mods = gen
    v3 = _build(tmp_path, lang, 3, gen_dir)
    v4 = _build(tmp_path, lang, 4, gen_dir)

    r = _run(v3, _v3_frame(mods))
    assert (r["n"], r["wb"], r["we"], r["stage"], r["mode"]) == ("64", "75", "95", "2", "2")

    r = _run(v3, _v2_frame(mods))
    assert (r["n"], r["wb"], r["we"], r["stage"], r["mode"]) == ("62", "85", "95", "0", "0")

    r = _run(v3, _v4_frame(mods))
    assert (r["n"], r["wb"], r["we"], r["stage"], r["mode"]) == ("72", "80", "100", "1", "2")

    r = _run(v4, _v3_frame(mods))
    assert (r["n"], r["wb"], r["scale"]) == ("64", "75", "1.5")

    r = _run(v4, _v2_frame(mods))
    assert (r["n"], r["wb"], r["stage"], r["scale"]) == ("62", "85", "0", "1.5")

    assert _run(v3, _v2_frame(mods))["min"] == "62"

    for size in (0, 1, 61):
        assert _run(v3, _v2_frame(mods)[:size])["n"] == "0"
    assert _run(v3, _bulk_frame(mods)[:62])["n"] == "0"


def test_cpp_serialization_zeroes_min_size_padding(gen, tmp_path):
    gen_dir, _ = gen
    v2 = _build(tmp_path, "cpp", 2, gen_dir)
    serialized = _run_args(v2, "serialize")
    wire = bytes.fromhex(serialized["bytes"])
    assert int(serialized["n"]) == len(wire) == 62
    assert wire[-8:] == b"\x00" * 8


def test_cpp_short_zero_default_variant_is_initialized(gen, tmp_path):
    gen_dir, _ = gen
    v3 = _build(tmp_path, "cpp", 3, gen_dir)
    result = _run_args(v3, "tiny")
    assert result == {"n": "5", "extra": "0"}


def test_py_unknown_discriminator_uses_structural_minimum(gen):
    _, mods = gen
    unknown = b"\x00" + b"\x00" * 4
    decoded = mods[3].TinyUnknownEnvelope.deserialize(unknown)
    assert decoded is not None
    assert mods[3].TinyUnknownEnvelope.MIN_SIZE == 9


def _interop_args(gen):
    gen_dir, mods = gen
    older = _v2_frame(mods)
    current = _v3_frame(mods)
    newer = _v4_frame(mods)
    return gen_dir, [older.hex(), current.hex(), newer.hex(), older[:61].hex()]


def _run_harness(command, *, cwd=None):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_js_trimmed_union_evolution(gen):
    if not shutil.which("node"):
        pytest.skip("node not available")
    gen_dir, frames = _interop_args(gen)
    modules = [
        gen_dir / "js" / f"trimmed-union-v{v}.structframe.js"
        for v in VERSIONS
    ]
    _run_harness(["node", "-e", JS_HARNESS, *(str(path) for path in modules), *frames])


def test_ts_trimmed_union_evolution(gen, tmp_path):
    ts_node = REPO_ROOT / "tests" / "ts" / "node_modules" / ".bin" / (
        "ts-node.cmd" if os.name == "nt" else "ts-node")
    if not ts_node.exists():
        pytest.skip("ts-node not installed; run npm ci in tests/ts")
    gen_dir, frames = _interop_args(gen)
    modules = [
        gen_dir / "ts" / f"trimmed-union-v{v}.structframe"
        for v in VERSIONS
    ]
    script = tmp_path / "trimmed_union_harness.ts"
    script.write_text(JS_HARNESS)
    _run_harness([
        str(ts_node), "--transpile-only", "--compiler-options", '{"module":"CommonJS"}',
        str(script), *(str(path) for path in modules), *frames,
    ], cwd=REPO_ROOT / "tests" / "ts")


def test_rust_trimmed_union_evolution(gen):
    if not shutil.which("cargo"):
        pytest.skip("cargo not available")
    gen_dir, frames = _interop_args(gen)
    rust_dir = gen_dir / "rust"
    source = rust_dir / "src" / "bin" / "trimmed_union_regression.rs"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(RUST_HARNESS)
    _run_harness([
        "cargo", "run", "--quiet", "--manifest-path", str(rust_dir / "Cargo.toml"),
        "--bin", "trimmed_union_regression", "--", *frames,
    ])


def test_csharp_trimmed_union_evolution(gen, tmp_path):
    if not shutil.which("dotnet"):
        pytest.skip("dotnet not available")
    sdk_version = subprocess.run(
        ["dotnet", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    sdk_major = int(sdk_version.split(".", 1)[0])
    if sdk_major < 8:
        pytest.skip("a .NET 8 or newer SDK is required")
    target_framework = f"net{min(sdk_major, 10)}.0"
    gen_dir, frames = _interop_args(gen)
    project = tmp_path / "TrimmedUnionRegression.csproj"
    project.write_text(
        '<Project Sdk="Microsoft.NET.Sdk">\n'
        f'  <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>{target_framework}</TargetFramework>'
        '<ImplicitUsings>enable</ImplicitUsings></PropertyGroup>\n'
        f'  <ItemGroup><ProjectReference Include="{gen_dir / "csharp" / "StructFrame.csproj"}" />'
        '</ItemGroup>\n</Project>\n'
    )
    (tmp_path / "Program.cs").write_text(CSHARP_HARNESS)
    _run_harness([
        "dotnet", "run", "--project", str(project), "--framework", target_framework, "--", *frames,
    ])
