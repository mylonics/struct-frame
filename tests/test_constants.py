"""Schema constants (``const TYPE NAME = value;``) reach the generated code of every
language with their exact type and value.

``tests/proto/constants.sf`` declares a constant of every type, including values that need
special spelling (minimum int32/int64, maximum uint64, +/-inf, nan, escaped strings). Each
language's check program below states the expected values itself, independently of the
generator, and also uses the constants where the language needs a constant expression
(array sizes, static assertions).
"""

import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from test_utils import REPO_ROOT, load_generated_module, run_generator

SCHEMA = REPO_ROOT / "tests" / "proto" / "constants.sf"
VERSION = '1.4 "beta"\t\\ ' + chr(0xE9)   # e-acute, kept out of the source text


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("constants")
    r = run_generator(SCHEMA, "--lang", "all", "--out", str(out), "--force")
    assert r.returncode == 0, r.stdout + r.stderr
    return out


def test_schema_constants_and_their_uses(generated):
    import contextlib
    import io
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from struct_frame import generate as gen
    gen.reset_parse_state()
    with contextlib.redirect_stdout(io.StringIO()):
        assert gen.parseFile(str(SCHEMA)) and gen.validate_packages()
    pkg = gen.packages["constants"]
    gen.reset_parse_state()
    consts = pkg.consts
    assert consts["NAME_LEN"].const_type == "uint8" and consts["NAME_LEN"].value == 16
    assert consts["NAME_LEN"].comments == ["// Length of a device name."]
    assert consts["VERSION"].value == VERSION
    fields = pkg.messages["Device"].fields
    assert fields["name"].size_option == 16
    assert fields["samples"].max_size == 300
    assert fields["voltage"].default == pytest.approx(3.3)
    assert fields["offset"].default == -40


def test_python_constants(generated):
    mod = load_generated_module(generated / "py" / "structframe" / "constants.py", "constants")
    assert mod.NAME_LEN == 16 and mod.MAX_SAMPLES == 300 and mod.OFFSET == -40
    assert mod.INT32_LOW == -2**31 and mod.UINT32_HIGH == 2**32 - 1
    assert mod.INT64_LOW == -2**63 and mod.INT64_HIGH == 2**63 - 1 and mod.UINT64_HIGH == 2**64 - 1
    assert mod.NOMINAL_V == 3.3 and mod.PI == 3.141592653589793
    assert mod.POS_INF == math.inf and mod.NEG_INF == -math.inf and math.isnan(mod.NOT_A_NUMBER)
    assert mod.ENABLED is True and mod.VERSION == VERSION


def test_javascript_constants(generated):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not available")
    script = generated / "js" / "check_constants.js"
    script.write_text("""
const c = require('./constants.structframe');
const out = {};
for (const k of ['NAME_LEN', 'MAX_SAMPLES', 'OFFSET', 'INT32_LOW', 'UINT32_HIGH', 'NOMINAL_V', 'PI',
                 'ENABLED', 'VERSION']) out[k] = c[k];
for (const k of ['INT64_LOW', 'INT64_HIGH', 'UINT64_HIGH']) out[k] = { big: c[k].toString(), type: typeof c[k] };
out.POS_INF = c.POS_INF === Infinity; out.NEG_INF = c.NEG_INF === -Infinity; out.NAN = Number.isNaN(c.NOT_A_NUMBER);
console.log(JSON.stringify(out));
""", encoding="utf-8")
    r = subprocess.run([node, str(script)], capture_output=True, encoding="utf-8", cwd=script.parent)
    assert r.returncode == 0, r.stderr
    got = json.loads(r.stdout)
    assert got["NAME_LEN"] == 16 and got["MAX_SAMPLES"] == 300 and got["OFFSET"] == -40
    assert got["INT32_LOW"] == -2**31 and got["UINT32_HIGH"] == 2**32 - 1
    assert got["INT64_LOW"] == {"big": str(-2**63), "type": "bigint"}
    assert got["INT64_HIGH"] == {"big": str(2**63 - 1), "type": "bigint"}
    assert got["UINT64_HIGH"] == {"big": str(2**64 - 1), "type": "bigint"}
    assert got["NOMINAL_V"] == 3.3 and got["PI"] == 3.141592653589793
    assert got["POS_INF"] and got["NEG_INF"] and got["NAN"]
    assert got["ENABLED"] is True and got["VERSION"] == VERSION


def test_typescript_constants_type_check(generated):
    tsc = REPO_ROOT / "node_modules" / "typescript" / "bin" / "tsc"
    node = shutil.which("node")
    if node is None or not tsc.is_file():
        pytest.skip("node or typescript not available")
    ts_dir = generated / "ts"
    (ts_dir / "check_constants.ts").write_text("""
import { NAME_LEN, INT64_LOW, UINT64_HIGH, NOMINAL_V, ENABLED, VERSION, POS_INF } from './constants.structframe';
const a: 16 extends number ? number : never = NAME_LEN;
const b: bigint = INT64_LOW;
const c: bigint = UINT64_HIGH;
const d: number = NOMINAL_V + POS_INF;
const e: boolean = ENABLED;
const f: string = VERSION;
export const all = [a, b, c, d, e, f];
""", encoding="utf-8")
    r = subprocess.run([node, str(tsc), "--noEmit", "--strict", "--target", "es2020", "--module", "commonjs",
                        "--moduleResolution", "node", "--skipLibCheck", "--types", "node",
                        "--typeRoots", str(REPO_ROOT / "node_modules" / "@types"),
                        str(ts_dir / "check_constants.ts")],
                       capture_output=True, text=True, cwd=ts_dir)
    assert r.returncode == 0, r.stdout + r.stderr


C_CHECK = r"""
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "constants.structframe.h"

static char name_buf[CONSTANTS_NAME_LEN];                 /* usable as an array size */
_Static_assert(sizeof(name_buf) == 16, "NAME_LEN");
_Static_assert(CONSTANTS_MAX_SAMPLES == 300, "MAX_SAMPLES");

int main(void) {
    assert(CONSTANTS_OFFSET == -40);
    assert(CONSTANTS_INT32_LOW == INT32_MIN);
    assert(CONSTANTS_UINT32_HIGH == UINT32_MAX);
    assert(CONSTANTS_INT64_LOW == INT64_MIN);
    assert(CONSTANTS_INT64_HIGH == INT64_MAX);
    assert(CONSTANTS_UINT64_HIGH == UINT64_MAX);
    assert(CONSTANTS_NOMINAL_V == 3.3f);
    assert(CONSTANTS_PI == 3.141592653589793);
    assert(isinf(CONSTANTS_POS_INF) && CONSTANTS_POS_INF > 0);
    assert(isinf(CONSTANTS_NEG_INF) && CONSTANTS_NEG_INF < 0);
    assert(isnan(CONSTANTS_NOT_A_NUMBER));
    assert(CONSTANTS_ENABLED == true);
    assert(strcmp(CONSTANTS_VERSION, "1.4 \"beta\"\t\\ \xc3\xa9") == 0);
    (void)name_buf;
    puts("ok");
    return 0;
}
"""

CPP_CHECK = r"""
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include "constants.structframe.hpp"
using namespace structframe::constants;

static_assert(NAME_LEN == 16 && std::is_same<decltype(NAME_LEN), const uint8_t>::value, "NAME_LEN");
static_assert(MAX_SAMPLES == 300 && OFFSET == -40, "ints");
static_assert(INT32_LOW == std::numeric_limits<int32_t>::min(), "INT32_LOW");
static_assert(UINT32_HIGH == std::numeric_limits<uint32_t>::max(), "UINT32_HIGH");
static_assert(INT64_LOW == std::numeric_limits<int64_t>::min(), "INT64_LOW");
static_assert(INT64_HIGH == std::numeric_limits<int64_t>::max(), "INT64_HIGH");
static_assert(UINT64_HIGH == std::numeric_limits<uint64_t>::max(), "UINT64_HIGH");
static_assert(NOMINAL_V == 3.3f && PI == 3.141592653589793, "floats");
static_assert(ENABLED, "bool");
char name_buf[NAME_LEN];

int main() {
    if (!(std::isinf(POS_INF) && POS_INF > 0 && std::isinf(NEG_INF) && NEG_INF < 0)) return 1;
    if (!std::isnan(NOT_A_NUMBER)) return 2;
    if (std::strcmp(VERSION, "1.4 \"beta\"\t\\ \xc3\xa9") != 0) return 3;
    return sizeof(name_buf) == 16 ? 0 : 4;
}
"""


def _compile_and_run(cmd, exe, cwd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    except FileNotFoundError:
        pytest.skip(f"{cmd[0]} not available")
    assert r.returncode == 0, r.stdout + r.stderr
    r = subprocess.run([str(exe)], capture_output=True, text=True, cwd=cwd)
    assert r.returncode == 0, f"exit {r.returncode}: {r.stdout}{r.stderr}"


def test_c_constants(generated):
    if shutil.which("gcc") is None:
        pytest.skip("gcc not available")
    c_dir = generated / "c"
    (c_dir / "check_constants.c").write_text(C_CHECK, encoding="utf-8")
    exe = c_dir / "check_constants.exe"
    _compile_and_run(["gcc", "-std=c11", "-Wall", "-Werror", "-I", str(c_dir), str(c_dir / "check_constants.c"),
                      "-o", str(exe), "-lm"], exe, c_dir)


def test_cpp_constants(generated):
    if shutil.which("g++") is None:
        pytest.skip("g++ not available")
    cpp_dir = generated / "cpp"
    (cpp_dir / "check_constants.cpp").write_text(CPP_CHECK, encoding="utf-8")
    exe = cpp_dir / "check_constants.exe"
    _compile_and_run(["g++", "-std=c++20", "-Wall", "-Werror", "-I", str(cpp_dir),
                      str(cpp_dir / "check_constants.cpp"), "-o", str(exe)], exe, cpp_dir)


RUST_CHECK = r"""
use structframe::constants::*;

const NAME_BUF: [u8; NAME_LEN as usize] = [0; NAME_LEN as usize];

fn main() {
    let _: u8 = NAME_LEN;
    assert_eq!(NAME_BUF.len(), 16);
    assert_eq!(MAX_SAMPLES, 300u16);
    assert_eq!(OFFSET, -40i8);
    assert_eq!(INT32_LOW, i32::MIN);
    assert_eq!(UINT32_HIGH, u32::MAX);
    assert_eq!(INT64_LOW, i64::MIN);
    assert_eq!(INT64_HIGH, i64::MAX);
    assert_eq!(UINT64_HIGH, u64::MAX);
    assert_eq!(NOMINAL_V, 3.3f32);
    assert_eq!(PI, 3.141592653589793f64);
    assert!(POS_INF.is_infinite() && POS_INF > 0.0);
    assert!(NEG_INF.is_infinite() && NEG_INF < 0.0);
    assert!(NOT_A_NUMBER.is_nan());
    assert!(ENABLED);
    assert_eq!(VERSION, "1.4 \"beta\"\t\\ \u{e9}");
    println!("ok");
}
"""


def test_rust_constants(generated):
    if shutil.which("cargo") is None:
        pytest.skip("cargo not available")
    rust_dir = generated / "rust"
    toml = (rust_dir / "Cargo.toml").read_text(encoding="utf-8")
    name = next(line.split("=", 1)[1].strip().strip('"') for line in toml.splitlines()
                if line.strip().startswith("name"))
    (rust_dir / "examples").mkdir(exist_ok=True)
    (rust_dir / "examples" / "check_constants.rs").write_text(RUST_CHECK.replace("structframe::", f"{name}::"),
                                                              encoding="utf-8")
    r = subprocess.run(["cargo", "run", "--quiet", "--example", "check_constants"], capture_output=True,
                       text=True, cwd=rust_dir, env=dict(os.environ, CARGO_TARGET_DIR=str(rust_dir / "target")))
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip() == "ok"


CSHARP_CHECK = r"""
using System;
using StructFrame.Constants;

static class Program {
    static int Main() {
        byte nameLen = Constants.NAME_LEN;
        if (nameLen != 16 || Constants.MAX_SAMPLES != 300 || Constants.OFFSET != -40) return 1;
        if (Constants.INT32_LOW != int.MinValue || Constants.UINT32_HIGH != uint.MaxValue) return 2;
        if (Constants.INT64_LOW != long.MinValue || Constants.INT64_HIGH != long.MaxValue) return 3;
        if (Constants.UINT64_HIGH != ulong.MaxValue) return 4;
        if (Constants.NOMINAL_V != 3.3f || Constants.PI != 3.141592653589793) return 5;
        if (!float.IsPositiveInfinity(Constants.POS_INF) || !double.IsNegativeInfinity(Constants.NEG_INF)) return 6;
        if (!double.IsNaN(Constants.NOT_A_NUMBER) || !Constants.ENABLED) return 7;
        if (Constants.VERSION != "1.4 \"beta\"\t\\ é") return 8;
        Console.WriteLine("ok");
        return 0;
    }
}
"""


def test_csharp_constants(generated, tmp_path):
    if shutil.which("dotnet") is None:
        pytest.skip("dotnet not available")
    cs_dir = generated / "csharp"
    proj = tmp_path / "check"
    proj.mkdir()
    tfm = os.environ.get("SF_DOTNET_TFM", "net10.0")
    (proj / "Check.csproj").write_text(f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>{tfm}</TargetFramework>
  <Nullable>enable</Nullable><TreatWarningsAsErrors>false</TreatWarningsAsErrors></PropertyGroup>
  <ItemGroup><ProjectReference Include="{cs_dir / 'StructFrame.csproj'}" /></ItemGroup>
</Project>
""", encoding="utf-8")
    (proj / "Program.cs").write_text(CSHARP_CHECK, encoding="utf-8")
    r = subprocess.run(["dotnet", "run", "--project", str(proj)], capture_output=True, text=True)
    if r.returncode != 0 and "NETSDK1045" in r.stdout + r.stderr:
        pytest.skip(f"target framework {tfm} not installed")
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip().endswith("ok")
