"""Default values are identical in every language.

Each language constructs every message and struct of ``tests/proto/default_edges.sf`` with
its defaults, serializes it and prints the bytes as hex. Every language must produce the
same bytes as the generated Python code, and for fixed-layout messages those bytes must be
the schema's default wire bytes computed by the generator (``Message.default_bytes``).

The fixture covers the cases that need care: non-finite and negative-zero floats, extreme
integers, escaped and non-ASCII strings, raw bytes, partial/full fixed arrays, vectors,
arrays of enums, strings and structs, and partial nested struct values.
"""

import contextlib
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from test_utils import REPO_ROOT, load_generated_module, run_generator

SCHEMA = REPO_ROOT / "tests" / "proto" / "default_edges.sf"
TYPES = ["Edges", "VarEdges", "Plain"]   # messages; Point and Box are covered as fields


def _model():
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from struct_frame import generate as gen
    gen.reset_parse_state()
    with contextlib.redirect_stdout(io.StringIO()):
        assert gen.parseFile(str(SCHEMA)) and gen.validate_packages()
    pkg = gen.packages["default_edges"]
    gen.reset_parse_state()
    return pkg


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("default_edges")
    r = run_generator(SCHEMA, "--lang", "all", "--out", str(out), "--force")
    assert r.returncode == 0, r.stdout + r.stderr
    return out


@pytest.fixture(scope="module")
def reference(generated):
    mod = load_generated_module(generated / "py" / "structframe" / "default_edges.py", "default_edges")
    return {name: getattr(mod, name)().serialize().hex() for name in TYPES}


def _parse(stdout):
    out = {}
    for line in stdout.splitlines():
        if line.strip():
            name, _, hexed = line.strip().partition(" ")
            out[name] = hexed.lower()
    return out


def _check(got, reference):
    assert set(got) == set(TYPES), got
    for name in TYPES:
        assert got[name] == reference[name], f"{name}:\n  got       {got[name]}\n  reference {reference[name]}"


def test_python_matches_the_schema_default_bytes(reference):
    pkg = _model()
    for name in TYPES:
        msg = pkg.messages[name]
        if not msg.variable:
            assert reference[name] == msg.default_bytes.hex(), name


def test_python_defaults_read_back(generated):
    mod = load_generated_module(generated / "py" / "structframe" / "default_edges.py", "default_edges")
    import math
    e = mod.Edges()
    assert e.pinf == math.inf and e.ninf == -math.inf and math.isnan(e.qnan)
    assert math.copysign(1.0, e.negzero) == -1.0
    assert (e.imin, e.imax, e.umax) == (-2**63, 2**63 - 1, 2**64 - 1)
    assert e.esc == b'a"b\\c\td\n' and e.utf == "été".encode("utf-8")
    assert e.raw == b"\x00\xff\x7f"
    assert list(e.vec3) == [100, 200, 300] and list(e.colors)[:2] == [mod.Color.BLUE, mod.Color.RED]
    assert e.p.x == 1.5 and e.p.y == 2.5 and e.box.lo.x == 3.0 and e.box.hi.x == 10.0
    assert e.box.tag.rstrip(b"\0") == b"bx" and e.pts[0].x == 7.0 and e.vpts[1].c == mod.Color.BLUE
    # Every construction gets fresh lists and structs.
    a, b = mod.Edges(), mod.Edges()
    a.vec3.append(1)
    a.p.y = 0
    assert list(b.vec3) == [100, 200, 300] and b.p.y == 2.5


def _run(cmd, cwd, env=None):
    try:
        r = subprocess.run(cmd, capture_output=True, encoding="utf-8", cwd=cwd, env=env)
    except FileNotFoundError:
        pytest.skip(f"{cmd[0]} not available")
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


C_DRIVER = r"""
#include <stdio.h>
#include "default_edges.structframe.h"
static void dump(const char* name, const uint8_t* b, size_t n) {
    printf("%s ", name);
    for (size_t i = 0; i < n; i++) printf("%02x", b[i]);
    printf("\n");
}
#define DUMP(T, NAME) do { DefaultEdges##T m; DefaultEdges##T##_init(&m); \
    static uint8_t buf[4096]; size_t n = DefaultEdges##T##_serialize(&m, buf); dump(NAME, buf, n); } while (0)
int main(void) {
    DUMP(Edges, "Edges"); DUMP(VarEdges, "VarEdges"); DUMP(Plain, "Plain");
    return 0;
}
"""


def test_c_defaults_match(generated, reference):
    if shutil.which("gcc") is None:
        pytest.skip("gcc not available")
    d = generated / "c"
    (d / "dump_defaults.c").write_text(C_DRIVER, encoding="utf-8")
    exe = d / "dump_defaults.exe"
    _run(["gcc", "-std=c99", "-Wall", "-Werror", "-I", str(d), str(d / "dump_defaults.c"), "-o", str(exe), "-lm"], d)
    _check(_parse(_run([str(exe)], d)), reference)


CPP_DRIVER = r"""
#include <cstdio>
#include "default_edges.structframe.hpp"
using namespace structframe::default_edges;
template <class T> static void dump(const char* name) {
    T m{};
    static uint8_t buf[4096];
    size_t n = m.serialize(buf);
    std::printf("%s ", name);
    for (size_t i = 0; i < n; i++) std::printf("%02x", buf[i]);
    std::printf("\n");
}
int main() {
    dump<Edges>("Edges"); dump<VarEdges>("VarEdges"); dump<Plain>("Plain");
    return 0;
}
"""


def test_cpp_defaults_match(generated, reference):
    if shutil.which("g++") is None:
        pytest.skip("g++ not available")
    d = generated / "cpp"
    (d / "dump_defaults.cpp").write_text(CPP_DRIVER, encoding="utf-8")
    exe = d / "dump_defaults.exe"
    _run(["g++", "-std=c++20", "-Wall", "-Werror", "-Wno-class-memaccess", "-I", str(d),
          str(d / "dump_defaults.cpp"), "-o", str(exe)], d)
    _check(_parse(_run([str(exe)], d)), reference)


def test_javascript_defaults_match(generated, reference):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    d = generated / "js"
    (d / "dump_defaults.js").write_text(
        "const m = require('./default-edges.structframe');\n"
        f"for (const n of {TYPES!r}) console.log(n + ' ' + Buffer.from(new m[n]().serialize()).toString('hex'));\n",
        encoding="utf-8")
    _check(_parse(_run([node, str(d / "dump_defaults.js")], d)), reference)


def test_typescript_defaults_match(generated, reference):
    node = shutil.which("node")
    tsc = REPO_ROOT / "node_modules" / "typescript" / "bin" / "tsc"
    if node is None or not tsc.is_file():
        pytest.skip("node or typescript not available")
    d = generated / "ts"
    (d / "dump_defaults.ts").write_text(
        "import * as m from './default-edges.structframe';\n"
        "const types: any = m;\n"
        f"for (const n of {TYPES!r}) console.log(n + ' ' + Buffer.from(new types[n]().serialize()).toString('hex'));\n",
        encoding="utf-8")
    out = d / "_out"
    _run([node, str(tsc), "--outDir", str(out), "--target", "es2020", "--module", "commonjs",
          "--moduleResolution", "node", "--skipLibCheck", "--esModuleInterop", "--types", "node",
          "--typeRoots", str(REPO_ROOT / "node_modules" / "@types"), str(d / "dump_defaults.ts")], d)
    _check(_parse(_run([node, str(out / "dump_defaults.js")], d)), reference)


RUST_DRIVER = r"""
use CRATE::default_edges::*;
fn dump(name: &str, bytes: &[u8]) {
    let hex: String = bytes.iter().map(|b| format!("{:02x}", b)).collect();
    println!("{} {}", name, hex);
}
fn main() {
    let mut buf = [0u8; 4096];
    let n = Edges::default().pack(&mut buf); dump("Edges", &buf[..n]);
    let n = VarEdges::default().pack(&mut buf); dump("VarEdges", &buf[..n]);
    let n = Plain::default().pack(&mut buf); dump("Plain", &buf[..n]);
}
"""


def test_rust_defaults_match(generated, reference):
    if shutil.which("cargo") is None:
        pytest.skip("cargo not available")
    d = generated / "rust"
    toml = (d / "Cargo.toml").read_text(encoding="utf-8")
    crate = next(line.split("=", 1)[1].strip().strip('"') for line in toml.splitlines()
                 if line.strip().startswith("name")).replace("-", "_")
    (d / "examples").mkdir(exist_ok=True)
    (d / "examples" / "dump_defaults.rs").write_text(RUST_DRIVER.replace("CRATE", crate), encoding="utf-8")
    out = _run(["cargo", "run", "--quiet", "--example", "dump_defaults"], d,
               env=dict(os.environ, CARGO_TARGET_DIR=str(d / "target")))
    _check(_parse(out), reference)


CSHARP_DRIVER = r"""
using System;
using StructFrame.DefaultEdges;
static class Program {
    static void Dump(string name, byte[] b) => Console.WriteLine(name + " " + Convert.ToHexString(b).ToLowerInvariant());
    static int Main() {
        Dump("Edges", new Edges().Serialize());
        Dump("VarEdges", new VarEdges().Serialize());
        Dump("Plain", new Plain().Serialize());
        return 0;
    }
}
"""


def test_csharp_defaults_match(generated, reference, tmp_path):
    if shutil.which("dotnet") is None:
        pytest.skip("dotnet not available")
    proj = tmp_path / "dump"
    proj.mkdir()
    tfm = os.environ.get("SF_DOTNET_TFM", "net10.0")
    (proj / "Dump.csproj").write_text(f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>{tfm}</TargetFramework>
  <Nullable>enable</Nullable></PropertyGroup>
  <ItemGroup><ProjectReference Include="{generated / 'csharp' / 'StructFrame.csproj'}" /></ItemGroup>
</Project>
""", encoding="utf-8")
    (proj / "Program.cs").write_text(CSHARP_DRIVER, encoding="utf-8")
    out = _run(["dotnet", "run", "--project", str(proj)], proj)
    _check(_parse(out), reference)
