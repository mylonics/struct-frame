#!/usr/bin/env python3
"""System-frame known answers for the C, C++, JavaScript, C# and Rust runtimes.

Companion to ``test_system_frames.py``, which holds the spec encoder, the vectors and the
Python runtime tests. Each runtime here

* encodes every vector through its own system-frame API (typed messages, tails, sequence
  and addressing) and must produce the spec frame byte for byte, and
* decodes every spec frame byte by byte (stream mode) with system frames delivered and
  reports the message id, header fields and payload.

TypeScript is covered through the checked-in JavaScript, which is compiled from it. Mixed
streams (hidden vs delivered, counters, chunking) are compared across runtimes in
``test_stream_cross_lang.py``.
"""
from __future__ import annotations

import os
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

from test_known_answer import BOILERPLATE
from test_system_frames import EXPECTED, LAYOUT, VECTORS

EXPECTED_HEX = [frame.hex() for frame in EXPECTED]


def _expected_lines():
    lines = [f"E {h}" for h in EXPECTED_HEX]
    for v in VECTORS:
        msg_id, fmt, _magic, _names = LAYOUT[v.message]
        payload = struct.pack(fmt, *v.fields) + v.tail
        lines.append(f"D {msg_id} {v.seq} {v.sys_id} {v.comp_id} {payload.hex()}")
    return lines


EXPECTED_LINES = _expected_lines()


def _check(output: str, lang: str):
    got = [line.strip() for line in output.splitlines() if line.strip()]
    assert got == EXPECTED_LINES, f"{lang}: system frames differ from the spec\n" + "\n".join(
        f"  {'ok ' if g == w else 'BAD'} got {g}\n      want {w}" for g, w in zip(got, EXPECTED_LINES))


def _camel(name):
    head, *rest = name.split("_")
    return head + "".join(p.capitalize() for p in rest)


def _pascal(name):
    return "".join(p.capitalize() for p in name.split("_"))


def _bytes_list(data: bytes) -> str:
    return ", ".join(str(b) for b in data)


def _spec_frames_c_array() -> str:
    return ",\n".join("    {" + _bytes_list(f) + "}" for f in EXPECTED)


# --------------------------------------------------------------------------- C

C_CONFIG = {"standard": "PROFILE_STANDARD_CONFIG", "sensor": "PROFILE_SENSOR_CONFIG",
            "network": "PROFILE_NETWORK_CONFIG"}


def _c_source() -> str:
    enc = []
    for i, v in enumerate(VECTORS):
        msg_id, _fmt, _m, names = LAYOUT[v.message]
        sets = " ".join(f"m.{n} = {val}u;" for n, val in zip(names, v.fields))
        tail = f"static const uint8_t tail{i}[] = {{{_bytes_list(v.tail) or '0'}}};"
        enc.append(f"""  {{
    SfSystem{v.message} m; memset(&m, 0, sizeof m); {sets}
    {tail}
    uint8_t fixed[64]; size_t fl = SfSystem{v.message}_serialize(&m, fixed);
    uint8_t buf[2048];
    size_t n = profile_encode_system_frame(&{C_CONFIG[v.profile]}, buf, sizeof buf, {v.seq}, {v.sys_id}, {v.comp_id},
                                           {msg_id}, fixed, fl, tail{i}, {len(v.tail)});
    dump("E ", buf, n);
  }}""")
    dec = []
    for i, v in enumerate(VECTORS):
        dec.append(f"""  {{
    static const uint8_t frame[] = {{{_bytes_list(EXPECTED[i])}}};
    uint8_t internal[2048];
    accumulating_reader_t r;
    accumulating_reader_init(&r, &{C_CONFIG[v.profile]}, internal, sizeof internal, NULL);
    accumulating_reader_set_deliver_system_frames(&r, true);
    for (size_t k = 0; k < sizeof frame; k++) {{
      frame_msg_info_t f = accumulating_reader_push_byte(&r, frame[k]);
      if (f.valid && f.is_system) {{
        printf("D %u %u %u %u ", f.msg_id, f.sequence, f.system_id, f.component_id);
        dump("", f.msg_data, f.msg_len);
      }}
    }}
  }}""")
    return f"""#include <stdio.h>
#include <string.h>
#include "sf_system.structframe.h"
#include "frame_profiles.h"
static void dump(const char* prefix, const uint8_t* p, size_t n) {{
  printf("%s", prefix);
  for (size_t i = 0; i < n; i++) printf("%02x", p[i]);
  printf("\\n");
}}
int main(void) {{
{chr(10).join(enc)}
{chr(10).join(dec)}
  return 0;
}}
"""


def test_c_runtime_system_frames(tmp_path):
    cc = shutil.which(os.environ.get("CC", "gcc"))
    if cc is None:
        pytest.skip("no C compiler")
    src = tmp_path / "sys.c"
    src.write_text(_c_source(), encoding="utf-8")
    exe = tmp_path / ("sys_c.exe" if os.name == "nt" else "sys_c")
    build = subprocess.run([cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
                            f"-I{BOILERPLATE / 'c'}", str(src), "-o", str(exe)],
                           capture_output=True, text=True, timeout=600)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    _check(run.stdout, "C")


def test_c_runtime_compiles_without_system_frames(tmp_path):
    """SF_DISABLE_SYSTEM_FRAMES compiles the reader support out; 0x79 is then ordinary data."""
    cc = shutil.which(os.environ.get("CC", "gcc"))
    if cc is None:
        pytest.skip("no C compiler")
    src = tmp_path / "off.c"
    src.write_text(f"""#include <stdio.h>
#include "frame_parsers.h"
int main(void) {{
  static const uint8_t frame[] = {{{_bytes_list(EXPECTED[0])}}};
  uint8_t internal[256];
  accumulating_reader_t r;
  accumulating_reader_init(&r, &PROFILE_STANDARD_CONFIG, internal, sizeof internal, NULL);
  accumulating_reader_set_deliver_system_frames(&r, true);
  accumulating_reader_add_data(&r, frame, sizeof frame);
  frame_msg_info_t f; int valid = 0;
  while (accumulating_reader_try_next(&r, &f)) valid += f.valid;
  printf("%d %u %d\\n", valid, r.diagnostics.cnt_system_frames, profile_supports_system_frames(&PROFILE_STANDARD_CONFIG));
  return 0;
}}
""", encoding="utf-8")
    exe = tmp_path / ("off.exe" if os.name == "nt" else "off")
    build = subprocess.run([cc, "-std=c99", "-Wall", "-DSF_DISABLE_SYSTEM_FRAMES", f"-I{BOILERPLATE / 'c'}",
                            str(src), "-o", str(exe)], capture_output=True, text=True, timeout=600)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.stdout.split() == ["0", "0", "0"]


# --------------------------------------------------------------------------- C++

CPP_CONFIG = {"standard": "ProfileStandardConfig", "sensor": "ProfileSensorConfig",
              "network": "ProfileNetworkConfig"}


def _cpp_source() -> str:
    enc, dec = [], []
    for i, v in enumerate(VECTORS):
        _msg_id, _fmt, _m, names = LAYOUT[v.message]
        sets = " ".join(f"m.{n} = {val}u;" for n, val in zip(names, v.fields))
        enc.append(f"""  {{
    sf_system::{v.message} m{{}}; {sets}
    const uint8_t tail[] = {{{_bytes_list(v.tail) or '0'}}};
    uint8_t buf[2048];
    size_t n = system_frames::encode<{CPP_CONFIG[v.profile]}>(buf, sizeof buf, m, tail, {len(v.tail)}, {v.seq},
                                                             {v.sys_id}, {v.comp_id});
    dump("E ", buf, n);
  }}""")
        dec.append(f"""  {{
    const uint8_t frame[] = {{{_bytes_list(EXPECTED[i])}}};
    AccumulatingReader<{CPP_CONFIG[v.profile]}, 2048, MessageInfoFn> r(no_info);
    r.set_deliver_system_frames(true);
    for (uint8_t b : frame) {{
      FrameMsgInfo f = r.push_byte(b);
      if (f.valid && f.is_system) {{
        std::printf("D %u %u %u %u ", f.msg_id, f.sequence, f.system_id, f.component_id);
        dump("", f.msg_data, f.msg_len);
      }}
    }}
  }}""")
    return f"""#include <cstdio>
#include "frame_profiles.hpp"
#include "sf_system.structframe.hpp"
using namespace structframe;
static MessageInfo no_info(uint16_t) {{ return MessageInfo(); }}
static void dump(const char* prefix, const uint8_t* p, size_t n) {{
  std::printf("%s", prefix);
  for (size_t i = 0; i < n; i++) std::printf("%02x", p[i]);
  std::printf("\\n");
}}
int main() {{
{chr(10).join(enc)}
{chr(10).join(dec)}
  return 0;
}}
"""


def test_cpp_runtime_system_frames(tmp_path):
    cxx = shutil.which(os.environ.get("CXX", "g++"))
    if cxx is None:
        pytest.skip("no C++ compiler")
    src = tmp_path / "sys.cpp"
    src.write_text(_cpp_source(), encoding="utf-8")
    exe = tmp_path / ("sys_cpp.exe" if os.name == "nt" else "sys_cpp")
    build = subprocess.run([cxx, "-std=c++20", "-Wall", "-Wextra", "-Wno-class-memaccess", f"-I{BOILERPLATE / 'cpp'}",
                            str(src), "-o", str(exe)], capture_output=True, text=True, timeout=600)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    _check(run.stdout, "C++")



def test_cpp_runtime_compiles_without_system_frames(tmp_path):
    """SF_DISABLE_SYSTEM_FRAMES turns supports_system_frames off at compile time."""
    cxx = shutil.which(os.environ.get("CXX", "g++"))
    if cxx is None:
        pytest.skip("no C++ compiler")
    src = tmp_path / "off.cpp"
    src.write_text(f"""#include <cstdio>
#include "frame_profiles.hpp"
using namespace structframe;
static MessageInfo no_info(uint16_t) {{ return MessageInfo(); }}
static_assert(!ProfileStandardConfig::supports_system_frames, "compiled out");
int main() {{
  const uint8_t frame[] = {{{_bytes_list(EXPECTED[0])}}};
  AccumulatingReader<ProfileStandardConfig, 256, MessageInfoFn> r(no_info);
  r.set_deliver_system_frames(true);
  r.add_data(frame, sizeof frame);
  FrameMsgInfo f; int valid = 0;
  while (r.try_next(f)) valid += f.valid;
  std::printf("%d %u\\n", valid, r.diagnostics().cnt_system_frames);
  return 0;
}}
""", encoding="utf-8")
    exe = tmp_path / ("off_cpp.exe" if os.name == "nt" else "off_cpp")
    build = subprocess.run([cxx, "-std=c++20", "-Wall", "-DSF_DISABLE_SYSTEM_FRAMES", f"-I{BOILERPLATE / 'cpp'}",
                            str(src), "-o", str(exe)], capture_output=True, text=True, timeout=600)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.stdout.split() == ["0", "0"]

# --------------------------------------------------------------------------- JavaScript

JS_CONFIG = {"standard": "ProfileStandardConfig", "sensor": "ProfileSensorConfig",
             "network": "ProfileNetworkConfig"}


def _js_value(fmt_char, value):
    return f"{value}n" if fmt_char == "Q" else str(value)


def test_javascript_runtime_system_frames(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    runtime = (BOILERPLATE / "js" / "index.js").as_posix()
    enc, dec = [], []
    for i, v in enumerate(VECTORS):
        _msg_id, fmt, _m, names = LAYOUT[v.message]
        init = ", ".join(f"{_camel(n)}: {_js_value(c, val)}" for n, c, val in zip(names, fmt[1:], v.fields))
        enc.append(f"""out.push('E ' + hex(rt.encodeSystemMessage(rt.{JS_CONFIG[v.profile]}, new rt.sfSystem.{v.message}({{{init}}}),
    {{ tail: Uint8Array.from([{_bytes_list(v.tail)}]), seq: {v.seq}, sysId: {v.sys_id}, compId: {v.comp_id} }})));""")
        dec.append(f"""{{
  const r = new rt.AccumulatingReader(rt.{JS_CONFIG[v.profile]}, undefined, 2048, true);
  for (const b of [{_bytes_list(EXPECTED[i])}]) {{
    const f = r.pushByte(b);
    if (f.valid && f.isSystem) out.push(`D ${{f.msgId}} ${{f.sequence}} ${{f.systemId}} ${{f.componentId}} ${{hex(f.msgData.subarray(0, f.msgLen))}}`);
  }}
}}""")
    script = tmp_path / "sys.js"
    script.write_text(f"""const rt = require({runtime!r});
const hex = (b) => Buffer.from(b).toString('hex');
const out = [];
{chr(10).join(enc)}
{chr(10).join(dec)}
console.log(out.join('\\n'));
""", encoding="utf-8")
    run = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stdout + run.stderr
    _check(run.stdout, "JavaScript")


# --------------------------------------------------------------------------- C#

CS_CONFIG = {"standard": "Standard", "sensor": "Sensor", "network": "Network"}
CS_TYPES = {"I": "uint", "H": "ushort", "B": "byte", "Q": "ulong"}


def test_csharp_runtime_system_frames(tmp_path):
    dotnet = shutil.which("dotnet")
    if dotnet is None:
        pytest.skip("dotnet not installed")
    enc, dec = [], []
    for i, v in enumerate(VECTORS):
        _msg_id, fmt, _m, names = LAYOUT[v.message]
        init = ", ".join(f"{_pascal(n)} = ({CS_TYPES[c]}){val}" for n, c, val in zip(names, fmt[1:], v.fields))
        enc.append(f"""Console.WriteLine("E " + Hex(SystemFrames.Encode(Profiles.{CS_CONFIG[v.profile]}, new Sf.{v.message} {{ {init} }},
    new byte[] {{ {_bytes_list(v.tail)} }}, {v.seq}, {v.sys_id}, {v.comp_id})));""")
        dec.append(f"""{{
    var r = new AccumulatingReader(Profiles.{CS_CONFIG[v.profile]}, 2048) {{ DeliverSystemFrames = true }};
    foreach (byte b in new byte[] {{ {_bytes_list(EXPECTED[i])} }})
    {{
        var f = r.PushByte(b);
        if (f.Valid && f.IsSystem)
            Console.WriteLine($"D {{f.MsgId}} {{f.Seq}} {{f.SysId}} {{f.CompId}} {{Hex(f.GetPayloadSpan().ToArray())}}");
    }}
}}""")
    fw = (BOILERPLATE / "csharp" / "Framework").as_posix()
    proj = tmp_path / "sys"
    proj.mkdir()
    (proj / "sys.csproj").write_text(f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>disable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <AllowUnsafeBlocks>true</AllowUnsafeBlocks>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="{fw}/Types/**/*.cs;{fw}/Framing/**/*.cs;{fw}/Profiles/**/*.cs;{fw}/SfSystem/**/*.cs" />
  </ItemGroup>
</Project>
""", encoding="utf-8")
    (proj / "Program.cs").write_text(f"""using System;
using StructFrame;
using StructFrame.Framing;
using StructFrame.Profiles;
using Sf = StructFrame.SfSystem;

static string Hex(byte[] b) => Convert.ToHexString(b).ToLowerInvariant();
{chr(10).join(enc)}
{chr(10).join(dec)}
""", encoding="utf-8")
    run = subprocess.run([dotnet, "run", "--project", str(proj / "sys.csproj")],
                         capture_output=True, text=True, timeout=1500)
    subprocess.run([dotnet, "build-server", "shutdown"], capture_output=True, timeout=120)
    assert run.returncode == 0, run.stdout + run.stderr
    _check(run.stdout, "C#")


# --------------------------------------------------------------------------- Rust

RUST_CONFIG = {"standard": "PROFILE_STANDARD_CONFIG", "sensor": "PROFILE_SENSOR_CONFIG",
               "network": "PROFILE_NETWORK_CONFIG"}


def test_rust_runtime_system_frames(tmp_path):
    cargo = shutil.which("cargo")
    if cargo is None:
        pytest.skip("cargo not installed")
    enc, dec = [], []
    for i, v in enumerate(VECTORS):
        _msg_id, _fmt, _m, names = LAYOUT[v.message]
        init = ", ".join(f"{n}: {val}" for n, val in zip(names, v.fields))
        enc.append(f"""    {{
        let m = sf::{v.message} {{ {init}, ..Default::default() }};
        let mut buf = vec![0u8; 2048];
        let n = system_frames::encode(&{RUST_CONFIG[v.profile]}, &mut buf, &m, &[{_bytes_list(v.tail)}], {v.seq}, {v.sys_id}, {v.comp_id});
        println!("E {{}}", hex(&buf[..n]));
    }}""")
        dec.append(f"""    {{
        let mut r = AccumulatingReader::new({RUST_CONFIG[v.profile]}, 2048);
        r.set_deliver_system_frames(true);
        for &b in [{_bytes_list(EXPECTED[i])}u8].iter() {{
            if let Some(f) = r.push_byte(b, &|_| None) {{
                if f.valid && f.is_system {{
                    println!("D {{}} {{}} {{}} {{}} {{}}", f.msg_id, f.sequence, f.system_id, f.component_id, hex(&f.msg_data));
                }}
            }}
        }}
    }}""")
    crate = tmp_path / "sysrs"
    (crate / "src").mkdir(parents=True)
    (crate / "Cargo.toml").write_text(
        '[package]\nname = "sysrs"\nversion = "0.0.0"\nedition = "2021"\n\n'
        f'[lib]\nname = "struct_frame_sdk"\npath = "{(BOILERPLATE / "rust" / "lib.rs").as_posix()}"\n\n'
        '[[bin]]\nname = "sysrs"\npath = "src/main.rs"\n\n[workspace]\n', encoding="utf-8")
    (crate / "src" / "main.rs").write_text(f"""#![allow(clippy::all)]
use struct_frame_sdk::frame_profiles::*;
use struct_frame_sdk::sf_system as sf;
use struct_frame_sdk::system_frames;

fn hex(b: &[u8]) -> String {{ b.iter().map(|x| format!("{{:02x}}", x)).collect() }}

fn main() {{
{chr(10).join(enc)}
{chr(10).join(dec)}
}}
""", encoding="utf-8")
    run = subprocess.run([cargo, "run", "--quiet", "--manifest-path", str(crate / "Cargo.toml")],
                         capture_output=True, text=True, timeout=1500,
                         env=dict(os.environ, CARGO_TARGET_DIR=str(tmp_path / "target")))
    assert run.returncode == 0, run.stdout + run.stderr
    _check(run.stdout, "Rust")
