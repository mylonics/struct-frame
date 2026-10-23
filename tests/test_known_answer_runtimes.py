#!/usr/bin/env python3
"""Known-answer tests for the C++, C# and Rust runtimes.

Companion to ``test_known_answer.py`` (which covers Python, C and JavaScript). The
vectors and the from-the-spec encoder live there; this file feeds the same vectors
through the other three runtimes and requires byte-identical frames. TypeScript is
not repeated: its runtime is the source the checked-in JavaScript is compiled from,
and the JavaScript runtime is already covered.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from test_known_answer import BOILERPLATE, EXPECTED, VECTORS, Vector

EXPECTED_HEX = [frame.hex() for frame in EXPECTED]


# --------------------------------------------------------------------------- C++

CPP_CONFIG = {"standard": "ProfileStandardConfig", "sensor": "ProfileSensorConfig",
              "ipc": "ProfileIPCConfig", "bulk": "ProfileBulkConfig",
              "network": "ProfileNetworkConfig"}


def _cpp_source(indexes) -> str:
    decls, calls = [], []
    for i in indexes:
        v = VECTORS[i]
        n = len(v.payload)
        payload = ", ".join(str(b) for b in v.payload)
        decls.append(
            f"#pragma pack(push, 1)\n"
            f"struct M{i} : MessageBase<M{i}, {v.wire_msg_id}, {n}, {v.magic1}, {v.magic2}, {n}> {{\n"
            f"  uint8_t d[{n}] = {{{payload}}};\n}};\n#pragma pack(pop)\n")
        cfg = CPP_CONFIG[v.profile]
        if v.profile == "network":
            # Only profiles with sequence/addressing fields take these arguments.
            write = f"w.write(m, {v.seq}, {v.sys_id}, {v.comp_id});"
        else:
            write = "w.write(m);"
        calls.append(f"  {{ M{i} m; uint8_t buf[1024]; BufferWriter<{cfg}> w(buf, sizeof(buf)); {write} dump(buf, w.size()); }}")
    return f"""
#include <cstdio>
#include "frame_profiles.hpp"
using namespace structframe;
{chr(10).join(decls)}
static void dump(const uint8_t* p, size_t n) {{ for (size_t i = 0; i < n; i++) std::printf("%02x", p[i]); std::printf("\\n"); }}
int main() {{
{chr(10).join(calls)}
  return 0;
}}
"""


def test_cpp_runtime_encodes_spec_frames(tmp_path):
    cxx = shutil.which(os.environ.get("CXX", "g++"))
    if cxx is None:
        pytest.skip("no C++ compiler")
    # A zero-length payload would need a zero-size array, which C++ does not allow.
    indexes = [i for i, v in enumerate(VECTORS) if v.payload]
    src = tmp_path / "kat.cpp"
    src.write_text(_cpp_source(indexes), encoding="utf-8")
    exe = tmp_path / ("kat_cpp.exe" if os.name == "nt" else "kat_cpp")
    build = subprocess.run([cxx, "-std=c++20", "-Wall", f"-I{BOILERPLATE / 'cpp'}", str(src), "-o", str(exe)],
                           capture_output=True, text=True, timeout=600)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    assert run.stdout.split() == [EXPECTED_HEX[i] for i in indexes], \
        "C++ runtime frames differ from the spec frames"


# --------------------------------------------------------------------------- Rust

RUST_CONFIG = {"standard": "PROFILE_STANDARD_CONFIG", "sensor": "PROFILE_SENSOR_CONFIG",
               "ipc": "PROFILE_IPC_CONFIG", "bulk": "PROFILE_BULK_CONFIG",
               "network": "PROFILE_NETWORK_CONFIG"}


def _rust_main() -> str:
    calls = []
    for v in VECTORS:
        payload = ", ".join(str(b) for b in v.payload)
        cfg = RUST_CONFIG[v.profile]
        if v.profile in ("sensor", "ipc"):
            call = f"encode_minimal(&{cfg}, &mut buf, {v.msg_id}, &payload)"
        else:
            call = (f"encode_with_crc_ext(&{cfg}, &mut buf, {v.seq}, {v.sys_id}, {v.comp_id}, "
                    f"{v.pkg_id}, {v.msg_id}, &payload, {v.magic1}, {v.magic2}, {len(v.payload)})")
        calls.append(f"""    {{
        let payload: Vec<u8> = vec![{payload}];
        let mut buf = [0u8; 1024];
        let n = {call};
        println!("{{}}", buf[..n].iter().map(|b| format!("{{:02x}}", b)).collect::<String>());
    }}""")
    body = "\n".join(calls)
    return f"use kat::frame_profiles::*;\n\nfn main() {{\n{body}\n}}\n"


def test_rust_runtime_encodes_spec_frames(tmp_path):
    cargo = shutil.which("cargo")
    if cargo is None:
        pytest.skip("cargo not installed")
    crate = tmp_path / "kat"
    (crate / "src").mkdir(parents=True)
    (crate / "Cargo.toml").write_text(
        '[package]\nname = "kat"\nversion = "0.0.0"\nedition = "2021"\n\n'
        '[lib]\nname = "kat"\npath = "src/lib.rs"\n', encoding="utf-8")
    for name in ("frame_base", "frame_headers", "payload_types", "frame_profiles"):
        shutil.copy(BOILERPLATE / "rust" / f"{name}.rs", crate / "src" / f"{name}.rs")
    (crate / "src" / "lib.rs").write_text(
        "#![allow(dead_code, unused_imports)]\npub mod frame_base;\npub mod frame_headers;\n"
        "pub mod payload_types;\npub mod frame_profiles;\n", encoding="utf-8")
    (crate / "src" / "main.rs").write_text(_rust_main(), encoding="utf-8")
    run = subprocess.run([cargo, "run", "--quiet", "--manifest-path", str(crate / "Cargo.toml")],
                         capture_output=True, text=True, timeout=1200,
                         env=dict(os.environ, CARGO_TARGET_DIR=str(tmp_path / "target")))
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.stdout.split() == EXPECTED_HEX, "Rust runtime frames differ from the spec frames"


# --------------------------------------------------------------------------- C#

CS_CONFIG = {"standard": "Standard", "sensor": "Sensor", "ipc": "IPC", "bulk": "Bulk",
             "network": "Network"}


def _csharp_program() -> str:
    rows = []
    for v in VECTORS:
        payload = ", ".join(str(b) for b in v.payload)
        rows.append(f'    ("{CS_CONFIG[v.profile]}", {v.msg_id}, {v.pkg_id}, {v.seq}, {v.sys_id}, {v.comp_id}, '
                    f'new byte[] {{ {payload} }}, {v.magic1}, {v.magic2}),')
    table = "\n".join(rows)
    return f"""using StructFrame;
using StructFrame.Framing;
using StructFrame.Profiles;

var vectors = new (string Profile, int MsgId, int Pkg, int Seq, int Sys, int Comp, byte[] Payload, int M1, int M2)[] {{
{table}
}};
foreach (var v in vectors)
{{
    var config = v.Profile switch {{
        "Standard" => Profiles.Standard, "Sensor" => Profiles.Sensor, "IPC" => Profiles.IPC,
        "Bulk" => Profiles.Bulk, _ => Profiles.Network }};
    var encoder = new FrameEncoder(config);
    var buffer = new byte[1024];
    int n = encoder.EncodeRaw(buffer, 0, (ushort)v.MsgId, v.Payload, (byte)v.Seq, (byte)v.Sys, (byte)v.Comp,
                              (byte)v.Pkg, new MessageInfo(v.Payload.Length, (byte)v.M1, (byte)v.M2, v.Payload.Length));
    Console.WriteLine(Convert.ToHexString(buffer, 0, n).ToLowerInvariant());
}}
"""


def test_csharp_runtime_encodes_spec_frames(tmp_path):
    dotnet = shutil.which("dotnet")
    if dotnet is None:
        pytest.skip("dotnet not installed")
    fw = (BOILERPLATE / "csharp" / "Framework").as_posix()
    proj = tmp_path / "kat"
    proj.mkdir()
    (proj / "kat.csproj").write_text(f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <LangVersion>latest</LangVersion>
    <AllowUnsafeBlocks>true</AllowUnsafeBlocks>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="{fw}/Types/**/*.cs;{fw}/Framing/**/*.cs;{fw}/Profiles/**/*.cs" />
  </ItemGroup>
</Project>
""", encoding="utf-8")
    (proj / "Program.cs").write_text(_csharp_program(), encoding="utf-8")
    run = subprocess.run([dotnet, "run", "--project", str(proj / "kat.csproj")],
                         capture_output=True, text=True, timeout=1500)
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.stdout.split() == EXPECTED_HEX, "C# runtime frames differ from the spec frames"
