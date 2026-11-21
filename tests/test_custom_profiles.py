#!/usr/bin/env python3
"""Custom profiles: any header combined with any payload type, in every runtime.

The five named profiles are fixed header/payload pairs; a custom profile picks its own.
The payload type is then folded into the start byte (Tiny) or the second start byte
(Basic) however the pair was built. The C runtime once read the Tiny start byte from the
header table (where it is 0, "computed") instead of computing it, so Tiny + a CRC payload
never round-tripped there; these vectors pin that for all seven runtimes.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass

import pytest

from test_known_answer import BOILERPLATE, fletcher16


@dataclass(frozen=True)
class Custom:
    header: str          # tiny | basic
    payload: str         # payload type name (Default, Seq, ExtendedMultiSystemStream)
    payload_type: int
    msg_id: int
    pkg_id: int = 0
    seq: int = 0
    sys_id: int = 0
    comp_id: int = 0
    data: bytes = b"\x01\x02\x03"
    magic1: int = 7
    magic2: int = 9

    @property
    def wire_msg_id(self):
        return (self.pkg_id << 8) | self.msg_id if self.payload == "ExtendedMultiSystemStream" else self.msg_id


VECTORS = [
    Custom("tiny", "Default", 1, msg_id=5),
    Custom("basic", "Seq", 6, msg_id=9, seq=77),
    Custom("tiny", "ExtendedMultiSystemStream", 8, msg_id=0x21, pkg_id=4, seq=3, sys_id=1, comp_id=2,
           data=bytes(range(10))),
]


def spec_frame(v: Custom) -> bytes:
    start = bytes([0x70 + v.payload_type]) if v.header == "tiny" else bytes([0x90, 0x70 + v.payload_type])
    n = len(v.data)
    if v.payload == "Default":
        body = bytes([n, v.msg_id])
    elif v.payload == "Seq":
        body = bytes([v.seq, n, v.msg_id])
    else:
        body = bytes([v.seq, v.sys_id, v.comp_id, n & 0xFF, n >> 8, v.pkg_id, v.msg_id])
    body += v.data
    return start + body + fletcher16(body, v.magic1, v.magic2)


EXPECTED = [spec_frame(v) for v in VECTORS]
EXPECTED_LINES = [f"E {f.hex()}" for f in EXPECTED] + [f"D {v.wire_msg_id} {v.data.hex()}" for v in VECTORS]


def _check(output, lang):
    got = [line.strip() for line in output.splitlines() if line.strip()]
    assert got == EXPECTED_LINES, f"{lang}: custom-profile frames differ from the spec\n" + "\n".join(
        f"  {'ok ' if g == w else 'BAD'} {g}  (want {w})" for g, w in zip(got, EXPECTED_LINES))


def _list(data: bytes) -> str:
    return ", ".join(str(b) for b in data)


def test_spec_frames():
    assert EXPECTED[0][:3] == bytes([0x71, 3, 5])
    assert EXPECTED[1][:5] == bytes([0x90, 0x76, 77, 3, 9])
    assert EXPECTED[2][:1] == bytes([0x78])


# --------------------------------------------------------------------------- Python

def test_python_runtime(tmp_path):
    from test_known_answer import _py_runtime
    fp = _py_runtime(tmp_path)
    import frame_headers
    import payload_types
    lines = []
    for v in VECTORS:
        cfg = fp.ProfileConfig(getattr(frame_headers, f"HEADER_{v.header.upper()}_CONFIG"),
                               getattr(payload_types, f"PAYLOAD_{_snake(v.payload).upper()}_CONFIG"))

        class Message:
            MSG_ID = v.wire_msg_id
            MAGIC1 = v.magic1
            MAGIC2 = v.magic2

            def serialize(self, _d=v.data):
                return _d

        lines.append("E " + bytes(fp.encode_message(cfg, Message(), seq=v.seq, sys_id=v.sys_id,
                                                    comp_id=v.comp_id)).hex())
    for v, frame in zip(VECTORS, EXPECTED):
        cfg = fp.ProfileConfig(getattr(frame_headers, f"HEADER_{v.header.upper()}_CONFIG"),
                               getattr(payload_types, f"PAYLOAD_{_snake(v.payload).upper()}_CONFIG"))
        n = len(v.data)
        info = lambda mid, v=v, n=n: (fp.MessageInfo(size=n, magic1=v.magic1, magic2=v.magic2, base_size=n,
                                                     min_size=n) if mid == v.wire_msg_id else None)
        reader = fp.AccumulatingReader(cfg, get_message_info=info)
        for byte in frame:
            f = reader.push_byte(byte)
            if f.valid:
                lines.append(f"D {f.msg_id} {bytes(f.msg_data[:f.msg_len]).hex()}")
    _check("\n".join(lines), "Python")


def _snake(name):
    out = ""
    for i, c in enumerate(name):
        if c.isupper() and i:
            out += "_"
        out += c.lower()
    return out


# --------------------------------------------------------------------------- C

def test_c_runtime(tmp_path):
    cc = shutil.which(os.environ.get("CC", "gcc"))
    if cc is None:
        pytest.skip("no C compiler")
    body = []
    for i, (v, frame) in enumerate(zip(VECTORS, EXPECTED)):
        cfg = f"HEADER_{v.header.upper()}_CONFIG, PAYLOAD_{_snake(v.payload).upper()}_CONFIG"
        body.append(f"""  {{
    static const profile_config_t cfg = {{{cfg}}};
    static const uint8_t data[] = {{{_list(v.data)}}};
    uint8_t buf[64];
    size_t n = profile_encode_message(&cfg, buf, sizeof buf, {v.seq}, {v.sys_id}, {v.comp_id}, {v.pkg_id},
                                      {v.msg_id}, data, sizeof data, sizeof data, {v.magic1}, {v.magic2});
    dump("E ", buf, n);
  }}""")
    for i, (v, frame) in enumerate(zip(VECTORS, EXPECTED)):
        cfg = f"HEADER_{v.header.upper()}_CONFIG, PAYLOAD_{_snake(v.payload).upper()}_CONFIG"
        body.append(f"""  {{
    static const profile_config_t cfg = {{{cfg}}};
    static const uint8_t frame[] = {{{_list(frame)}}};
    uint8_t internal[256];
    accumulating_reader_t r;
    accumulating_reader_init(&r, &cfg, internal, sizeof internal, info{i});
    for (size_t k = 0; k < sizeof frame; k++) {{
      frame_msg_info_t f = accumulating_reader_push_byte(&r, frame[k]);
      if (f.valid) {{ printf("D %u ", f.msg_id); dump("", f.msg_data, f.msg_len); }}
    }}
  }}""")
    infos = "\n".join(
        f"static bool info{i}(uint16_t id, message_info_t* m) {{ if (id != {v.wire_msg_id}) return false; "
        f"m->size = m->base_size = m->min_size = {len(v.data)}; m->magic1 = {v.magic1}; m->magic2 = {v.magic2}; "
        f"return true; }}" for i, v in enumerate(VECTORS))
    src = tmp_path / "custom.c"
    src.write_text(f"""#include <stdio.h>
#include "frame_parsers.h"
static void dump(const char* p, const uint8_t* d, size_t n) {{
  printf("%s", p); for (size_t i = 0; i < n; i++) printf("%02x", d[i]); printf("\\n");
}}
{infos}
int main(void) {{
{chr(10).join(body)}
  return 0;
}}
""", encoding="utf-8")
    exe = tmp_path / ("custom_c.exe" if os.name == "nt" else "custom_c")
    build = subprocess.run([cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic", f"-I{BOILERPLATE / 'c'}",
                            str(src), "-o", str(exe)], capture_output=True, text=True, timeout=600)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    _check(run.stdout, "C")


# --------------------------------------------------------------------------- C++

def test_cpp_runtime(tmp_path):
    cxx = shutil.which(os.environ.get("CXX", "g++"))
    if cxx is None:
        pytest.skip("no C++ compiler")
    decls, body = [], []
    for i, (v, frame) in enumerate(zip(VECTORS, EXPECTED)):
        n = len(v.data)
        cfg = (f"ProfileConfig<headers::HEADER_{v.header.upper()}_CONFIG, "
               f"payloads::PAYLOAD_{_snake(v.payload).upper()}_CONFIG>")
        decls.append(f"#pragma pack(push, 1)\nstruct M{i} : MessageBase<M{i}, {v.wire_msg_id}, {n}, {v.magic1}, "
                     f"{v.magic2}, {n}> {{ uint8_t d[{n}] = {{{_list(v.data)}}}; }};\n#pragma pack(pop)\n"
                     f"using C{i} = {cfg};\n"
                     f"static MessageInfo info{i}(uint16_t id) {{ return id == {v.wire_msg_id} ? "
                     f"MessageInfo({n}, {v.magic1}, {v.magic2}, {n}, {n}) : MessageInfo(); }}")
        body.append(f"  {{ M{i} m; uint8_t buf[64]; size_t n = FrameEncoderWithCrc<C{i}>::encode(buf, sizeof buf, m, "
                    f"{v.seq}, {v.sys_id}, {v.comp_id}); dump(\"E \", buf, n); }}")
    for i, (v, frame) in enumerate(zip(VECTORS, EXPECTED)):
        body.append(f"""  {{
    const uint8_t frame[] = {{{_list(frame)}}};
    AccumulatingReader<C{i}, 256, MessageInfoFn> r(info{i});
    for (uint8_t b : frame) {{
      FrameMsgInfo f = r.push_byte(b);
      if (f.valid) {{ std::printf("D %u ", f.msg_id); dump("", f.msg_data, f.msg_len); }}
    }}
  }}""")
    src = tmp_path / "custom.cpp"
    src.write_text(f"""#include <cstdio>
#include "frame_profiles.hpp"
using namespace structframe;
static void dump(const char* p, const uint8_t* d, size_t n) {{
  std::printf("%s", p); for (size_t i = 0; i < n; i++) std::printf("%02x", d[i]); std::printf("\\n");
}}
{chr(10).join(decls)}
int main() {{
{chr(10).join(body)}
  return 0;
}}
""", encoding="utf-8")
    exe = tmp_path / ("custom_cpp.exe" if os.name == "nt" else "custom_cpp")
    build = subprocess.run([cxx, "-std=c++20", "-Wall", "-Wextra", f"-I{BOILERPLATE / 'cpp'}", str(src), "-o", str(exe)],
                           capture_output=True, text=True, timeout=600)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    _check(run.stdout, "C++")


# --------------------------------------------------------------------------- JavaScript

def test_javascript_runtime(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    runtime = (BOILERPLATE / "js" / "index.js").as_posix()
    body = []
    for v in VECTORS:
        cfg = (f"rt.createProfileConfig('Custom', rt.HEADER_{v.header.upper()}_CONFIG, "
               f"rt.PAYLOAD_{_snake(v.payload).upper()}_CONFIG)")
        body.append(f"""{{
  const cfg = {cfg};
  const data = Uint8Array.from([{_list(v.data)}]);
  const msg = {{ getMsgId: () => {v.wire_msg_id}, isVariable: () => false, _buffer: data, serialize: () => data,
                getMagic1: () => {v.magic1}, getMagic2: () => {v.magic2} }};
  out.push('E ' + hex(rt.encodeMessage(cfg, msg, {{ seq: {v.seq}, sysId: {v.sys_id}, compId: {v.comp_id} }})));
}}""")
    for v, frame in zip(VECTORS, EXPECTED):
        cfg = (f"rt.createProfileConfig('Custom', rt.HEADER_{v.header.upper()}_CONFIG, "
               f"rt.PAYLOAD_{_snake(v.payload).upper()}_CONFIG)")
        n = len(v.data)
        body.append(f"""{{
  const r = new rt.AccumulatingReader({cfg}, (id) => id === {v.wire_msg_id}
      ? {{ size: {n}, minSize: {n}, magic1: {v.magic1}, magic2: {v.magic2}, baseSize: {n} }} : undefined);
  for (const b of [{_list(frame)}]) {{
    const f = r.pushByte(b);
    if (f.valid) out.push(`D ${{f.msgId}} ${{hex(f.msgData.subarray(0, f.msgLen))}}`);
  }}
}}""")
    script = tmp_path / "custom.js"
    script.write_text(f"""const rt = require({runtime!r});
const hex = (b) => Buffer.from(b).toString('hex');
const out = [];
{chr(10).join(body)}
console.log(out.join('\\n'));
""", encoding="utf-8")
    run = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stdout + run.stderr
    _check(run.stdout, "JavaScript")


# --------------------------------------------------------------------------- C#

def test_csharp_runtime(tmp_path):
    dotnet = shutil.which("dotnet")
    if dotnet is None:
        pytest.skip("dotnet not installed")
    body = []
    for v in VECTORS:
        n = len(v.data)
        body.append(f"""{{
    var cfg = new ProfileConfig("Custom", HeaderConfigs.{v.header.capitalize()}, PayloadConfigs.{v.payload});
    var buf = new byte[64];
    int n = new FrameEncoder(cfg).EncodeRaw(buf, 0, {v.wire_msg_id}, new byte[] {{ {_list(v.data)} }}, {v.seq}, {v.sys_id},
                                            {v.comp_id}, {v.pkg_id}, new MessageInfo({n}, {v.magic1}, {v.magic2}, {n}));
    Console.WriteLine("E " + Convert.ToHexString(buf, 0, n).ToLowerInvariant());
}}""")
    for v, frame in zip(VECTORS, EXPECTED):
        n = len(v.data)
        body.append(f"""{{
    var cfg = new ProfileConfig("Custom", HeaderConfigs.{v.header.capitalize()}, PayloadConfigs.{v.payload});
    var r = new AccumulatingReader(cfg, 256, id => id == {v.wire_msg_id} ? new MessageInfo({n}, {v.magic1}, {v.magic2}, {n}) : null);
    foreach (byte b in new byte[] {{ {_list(frame)} }})
    {{
        var f = r.PushByte(b);
        if (f.Valid) Console.WriteLine($"D {{f.MsgId}} {{Convert.ToHexString(f.GetPayloadSpan().ToArray()).ToLowerInvariant()}}");
    }}
}}""")
    fw = (BOILERPLATE / "csharp" / "Framework").as_posix()
    proj = tmp_path / "custom"
    proj.mkdir()
    (proj / "custom.csproj").write_text(f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>disable</ImplicitUsings>
    <AllowUnsafeBlocks>true</AllowUnsafeBlocks>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="{fw}/Types/**/*.cs;{fw}/Framing/**/*.cs;{fw}/Profiles/**/*.cs;{fw}/SfSystem/**/*.cs" />
  </ItemGroup>
</Project>
""", encoding="utf-8")
    (proj / "Program.cs").write_text("using System;\nusing StructFrame;\nusing StructFrame.Framing;\n"
                                     "using StructFrame.Profiles;\n\n" + "\n".join(body) + "\n", encoding="utf-8")
    run = subprocess.run([dotnet, "run", "--project", str(proj / "custom.csproj")], capture_output=True, text=True,
                         timeout=1500)
    subprocess.run([dotnet, "build-server", "shutdown"], capture_output=True, timeout=120)
    assert run.returncode == 0, run.stdout + run.stderr
    _check(run.stdout, "C#")


# --------------------------------------------------------------------------- Rust

def test_rust_runtime(tmp_path):
    cargo = shutil.which("cargo")
    if cargo is None:
        pytest.skip("cargo not installed")
    body = []
    for v in VECTORS:
        cfg = (f"ProfileConfig::new(HEADER_{v.header.upper()}_CONFIG, "
               f"PAYLOAD_{_snake(v.payload).upper()}_CONFIG)")
        body.append(f"""    {{
        let cfg = {cfg};
        let mut buf = [0u8; 64];
        let n = encode_with_crc_ext(&cfg, &mut buf, {v.seq}, {v.sys_id}, {v.comp_id}, {v.pkg_id}, {v.msg_id},
                                    &[{_list(v.data)}], {v.magic1}, {v.magic2}, {len(v.data)});
        println!("E {{}}", hex(&buf[..n]));
    }}""")
    for v, frame in zip(VECTORS, EXPECTED):
        cfg = (f"ProfileConfig::new(HEADER_{v.header.upper()}_CONFIG, "
               f"PAYLOAD_{_snake(v.payload).upper()}_CONFIG)")
        n = len(v.data)
        body.append(f"""    {{
        let mut r = AccumulatingReader::new({cfg}, 256);
        let info = |id: u16| if id == {v.wire_msg_id} {{ Some(MessageInfo::new({n}, {v.magic1}, {v.magic2})) }} else {{ None }};
        for &b in [{_list(frame)}u8].iter() {{
            if let Some(f) = r.push_byte(b, &info) {{
                if f.valid {{ println!("D {{}} {{}}", f.msg_id, hex(&f.msg_data)); }}
            }}
        }}
    }}""")
    crate = tmp_path / "customrs"
    (crate / "src").mkdir(parents=True)
    (crate / "Cargo.toml").write_text(
        '[package]\nname = "customrs"\nversion = "0.0.0"\nedition = "2021"\n\n'
        f'[lib]\nname = "struct_frame_sdk"\npath = "{(BOILERPLATE / "rust" / "lib.rs").as_posix()}"\n\n'
        '[[bin]]\nname = "customrs"\npath = "src/main.rs"\n\n[workspace]\n', encoding="utf-8")
    (crate / "src" / "main.rs").write_text(f"""use struct_frame_sdk::frame_profiles::*;
use struct_frame_sdk::frame_headers::*;
use struct_frame_sdk::payload_types::*;
use struct_frame_sdk::MessageInfo;

fn hex(b: &[u8]) -> String {{ b.iter().map(|x| format!("{{:02x}}", x)).collect() }}

fn main() {{
{chr(10).join(body)}
}}
""", encoding="utf-8")
    run = subprocess.run([cargo, "run", "--quiet", "--manifest-path", str(crate / "Cargo.toml")],
                         capture_output=True, text=True, timeout=1500,
                         env=dict(os.environ, CARGO_TARGET_DIR=str(tmp_path / "target")))
    assert run.returncode == 0, run.stdout + run.stderr
    _check(run.stdout, "Rust")
