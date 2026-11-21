"""The generated default helpers behave the same in every language.

For ``Edges`` (tests/proto/default_edges.sf) each language checks: a new message is at its
defaults; changing one field makes the message, and that field, non-default while the other
fields stay default; ``reset`` brings everything back. ``qnan`` (a ``nan`` default) must count
as default, which only works because the helpers compare encodings.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from test_utils import REPO_ROOT, load_generated_module, run_generator

SCHEMA = REPO_ROOT / "tests" / "proto" / "default_edges.sf"


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("default_helpers")
    r = run_generator(SCHEMA, "--lang", "all", "--out", str(out), "--force")
    assert r.returncode == 0, r.stdout + r.stderr
    return out


def _run(cmd, cwd, env=None):
    try:
        r = subprocess.run(cmd, capture_output=True, encoding="utf-8", cwd=cwd, env=env)
    except FileNotFoundError:
        pytest.skip(f"{cmd[0]} not available")
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def test_python_helpers(generated):
    mod = load_generated_module(generated / "py" / "structframe" / "default_edges.py", "default_edges_h")
    e = mod.Edges.defaults()
    assert e.is_default() and e.is_default("qnan") and e.is_default("vec3")
    e.imax = 5
    assert not e.is_default() and not e.is_default("imax") and e.is_default("pinf")
    e.vec3.append(7)
    assert not e.is_default("vec3")
    e.p.y = 0.0
    assert not e.is_default("p")
    e.reset()
    assert e.is_default() and e.imax == 2**63 - 1 and list(e.vec3) == [100, 200, 300]
    with pytest.raises(KeyError):
        e.is_default("nope")
    assert mod.Point.defaults().is_default()


C_DRIVER = r"""
#include <assert.h>
#include <stdio.h>
#include "default_edges.structframe.h"
int main(void) {
    DefaultEdgesEdges e;
    DefaultEdgesEdges_init(&e);
    assert(DefaultEdgesEdges_is_default(&e));
    assert(DefaultEdgesEdges_qnan_is_default(&e));
    e.imax = 5;
    assert(!DefaultEdgesEdges_is_default(&e));
    assert(!DefaultEdgesEdges_imax_is_default(&e));
    assert(DefaultEdgesEdges_pinf_is_default(&e));
    e.vec3.count = 1;
    assert(!DefaultEdgesEdges_vec3_is_default(&e));
    e.p.y = 0.0f;
    assert(!DefaultEdgesEdges_p_is_default(&e));
    DefaultEdgesEdges_reset(&e);
    assert(DefaultEdgesEdges_is_default(&e) && e.vec3.count == 3);
    puts("ok");
    return 0;
}
"""


def test_c_helpers(generated):
    if shutil.which("gcc") is None:
        pytest.skip("gcc not available")
    d = generated / "c"
    (d / "helpers.c").write_text(C_DRIVER, encoding="utf-8")
    exe = d / "helpers.exe"
    _run(["gcc", "-std=c99", "-Wall", "-Werror", "-I", str(d), str(d / "helpers.c"), "-o", str(exe), "-lm"], d)
    assert _run([str(exe)], d).strip() == "ok"


CPP_DRIVER = r"""
#include <cassert>
#include <cstdio>
#include "default_edges.structframe.hpp"
using namespace structframe::default_edges;
int main() {
    Edges e{};
    assert(e.is_default() && e.qnan_is_default());
    e.imax = 5;
    assert(!e.is_default() && !e.imax_is_default() && e.pinf_is_default());
    e.vec3.count = 1;
    assert(!e.vec3_is_default());
    e.p.y = 0.0f;
    assert(!e.p_is_default());
    e.reset();
    assert(e.is_default() && e.vec3.count == 3);
    std::puts("ok");
    return 0;
}
"""


def test_cpp_helpers(generated):
    if shutil.which("g++") is None:
        pytest.skip("g++ not available")
    d = generated / "cpp"
    (d / "helpers.cpp").write_text(CPP_DRIVER, encoding="utf-8")
    exe = d / "helpers.exe"
    _run(["g++", "-std=c++20", "-Wall", "-Werror", "-Wno-class-memaccess", "-I", str(d),
          str(d / "helpers.cpp"), "-o", str(exe)], d)
    assert _run([str(exe)], d).strip() == "ok"


JS_CHECKS = """
const assert = require('assert');
const e = m.Edges.defaults();
assert(e.isDefault() && e.isDefault('qnan') && e.isDefault('vec3'));
e.imax = 5n;
assert(!e.isDefault() && !e.isDefault('imax') && e.isDefault('pinf'));
e.vec3Count = 1;
assert(!e.isDefault('vec3'));
e.reset();
assert(e.isDefault() && e.vec3Count === 3);
assert.throws(() => e.isDefault('nope'));
assert(m.Point.defaults().isDefault());
console.log('ok');
"""


def test_javascript_helpers(generated):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    d = generated / "js"
    (d / "helpers.js").write_text("const m = require('./default-edges.structframe');\n" + JS_CHECKS,
                                  encoding="utf-8")
    assert _run([node, str(d / "helpers.js")], d).strip() == "ok"


def test_typescript_helpers(generated):
    node = shutil.which("node")
    tsc = REPO_ROOT / "node_modules" / "typescript" / "bin" / "tsc"
    if node is None or not tsc.is_file():
        pytest.skip("node or typescript not available")
    d = generated / "ts"
    (d / "helpers.ts").write_text("import * as m from './default-edges.structframe';\n" + JS_CHECKS.replace(
        "const assert = require('assert');", "import assert = require('assert');"), encoding="utf-8")
    out = d / "_helpers_out"
    _run([node, str(tsc), "--outDir", str(out), "--target", "es2020", "--module", "commonjs", "--strict",
          "--moduleResolution", "node", "--skipLibCheck", "--types", "node",
          "--typeRoots", str(REPO_ROOT / "node_modules" / "@types"), str(d / "helpers.ts")], d)
    assert _run([node, str(out / "helpers.js")], d).strip() == "ok"


RUST_DRIVER = r"""
use CRATE::default_edges::*;
fn main() {
    let mut e = Edges::default();
    assert!(e.is_default() && e.qnan_is_default());
    e.imax = 5;
    assert!(!e.is_default() && !e.imax_is_default() && e.pinf_is_default());
    e.vec3_count = 1;
    assert!(!e.vec3_is_default());
    e.p.y = 0.0;
    assert!(!e.p_is_default());
    e.reset();
    assert!(e.is_default() && e.vec3_count == 3);
    println!("ok");
}
"""


def test_rust_helpers(generated):
    if shutil.which("cargo") is None:
        pytest.skip("cargo not available")
    d = generated / "rust"
    toml = (d / "Cargo.toml").read_text(encoding="utf-8")
    crate = next(line.split("=", 1)[1].strip().strip('"') for line in toml.splitlines()
                 if line.strip().startswith("name")).replace("-", "_")
    (d / "examples").mkdir(exist_ok=True)
    (d / "examples" / "helpers.rs").write_text(RUST_DRIVER.replace("CRATE", crate), encoding="utf-8")
    out = _run(["cargo", "run", "--quiet", "--example", "helpers"], d,
               env=dict(os.environ, CARGO_TARGET_DIR=str(d / "target")))
    assert out.strip() == "ok"


CSHARP_DRIVER = r"""
using System;
using StructFrame.DefaultEdges;
static class Program {
    static void Check(bool ok, string what) { if (!ok) throw new Exception(what); }
    static int Main() {
        var e = Edges.Defaults();
        Check(e.IsDefault() && e.IsQnanDefault(), "fresh");
        e.Imax = 5;
        Check(!e.IsDefault() && !e.IsImaxDefault() && e.IsPinfDefault(), "imax");
        e.Vec3Count = 1;
        Check(!e.IsVec3Default(), "vec3");
        e.Reset();
        Check(e.IsDefault() && e.Vec3Count == 3, "reset");
        Console.WriteLine("ok");
        return 0;
    }
}
"""


def test_csharp_helpers(generated, tmp_path):
    if shutil.which("dotnet") is None:
        pytest.skip("dotnet not available")
    proj = tmp_path / "helpers"
    proj.mkdir()
    tfm = os.environ.get("SF_DOTNET_TFM", "net10.0")
    (proj / "Helpers.csproj").write_text(f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>{tfm}</TargetFramework>
  <Nullable>enable</Nullable></PropertyGroup>
  <ItemGroup><ProjectReference Include="{generated / 'csharp' / 'StructFrame.csproj'}" /></ItemGroup>
</Project>
""", encoding="utf-8")
    (proj / "Program.cs").write_text(CSHARP_DRIVER, encoding="utf-8")
    assert _run(["dotnet", "run", "--project", str(proj)], proj).strip().endswith("ok")


def test_field_named_like_a_helper_is_rejected(tmp_path):
    sf = tmp_path / "h.sf"
    sf.write_text("package h;\nmessage M @1 { uint8 reset; }\n", encoding="utf-8")
    r = run_generator(sf, "--validate")
    assert r.returncode != 0
    assert "reset" in r.stdout + r.stderr and "generated method" in r.stdout + r.stderr
