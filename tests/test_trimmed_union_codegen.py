#!/usr/bin/env python3
"""
Regression tests for generated code around trimmed ``oneof`` unions:

  * C++ compiles (``-Wall -Werror``) and decodes when a variant is a fixed
    string, declares a zero-valued default, or nests another oneof, and every
    such message stays default-constructible.
  * Writers zero the ``min_size`` padding that follows a short variant instead
    of leaking bytes left in the union by a previously held larger variant
    (C and JavaScript; C++ is covered by test_trimmed_union_evolution).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from test_utils import run_generator, REPO_ROOT

PROTO_DIR = REPO_ROOT / "tests" / "proto"

CPP_HARNESS = r"""
#include <vector>
#include <cstdio>
#include "trimmed_union_codegen.structframe.hpp"
using namespace structframe::trimmed_union_codegen;
int main() {
    Holder h; Outer o; Mid m;
    std::vector<Holder> hv(2);
    std::vector<Outer> ov(2);
    (void)h; (void)o; (void)m;
    uint8_t frame[18] = {1, 1};
    for (int i = 2; i < 18; ++i) frame[i] = 'A';
    Tagged t;
    size_t n = t.deserialize(frame, sizeof(frame));
    std::printf("n=%zu x=%u first=%c\n", n, (unsigned)t.x, t.payload.name[0]);
    return t.payload.name[15] == 'A' ? 0 : 1;
}
"""

C_HARNESS = r"""
#include <stdio.h>
#include <string.h>
#include "trimmed_union_v2.structframe.h"
int main(void) {
    TrimmedUnionV2TaskEnvelope e;
    TrimmedUnionV2TaskEnvelope_init(&e);
    memset(&e.task, 0xAA, sizeof(e.task));
    e.task_discriminator = TRIMMED_UNION_V2_TASK_ENVELOPE_TASK_FIELD_SCAN_TASK;
    uint8_t buf[512];
    size_t n = TrimmedUnionV2TaskEnvelope_serialize(&e, buf);
    printf("n=%zu\n", n);
    for (size_t i = n - 8; i < n; ++i) if (buf[i] != 0) { printf("dirty padding at %zu\n", i); return 1; }
    return 0;
}
"""

JS_HARNESS = r"""
const assert = require('assert');
const mod = require(process.argv[1]);
const env = new mod.TaskEnvelope();
env.taskDiscriminator = 1;
env.taskData = Buffer.alloc(env.taskData.length, 0xAA);
const out = env.serialize();
assert.strictEqual(out.length, 62);
assert.deepStrictEqual([...out.subarray(54)], new Array(8).fill(0));
"""


@pytest.fixture(scope="module")
def gen(tmp_path_factory):
    out = tmp_path_factory.mktemp("trimmed_codegen")
    for name, flags in (
            ("trimmed_union_codegen", ("--build_cpp", "--cpp_path", str(out / "cpp"))),
            ("trimmed_union_v2", ("--build_c", "--c_path", str(out / "c"),
                                  "--build_js", "--js_path", str(out / "js")))):
        result = run_generator(PROTO_DIR / f"{name}.sf", *flags, "--force")
        assert result.returncode == 0, result.stdout + result.stderr
    return out


def test_cpp_defaulted_and_string_variants_compile_and_decode(gen, tmp_path):
    if not shutil.which("g++"):
        pytest.skip("g++ not available")
    src = tmp_path / "h.cpp"
    src.write_text(CPP_HARNESS)
    exe = tmp_path / "h"
    build = subprocess.run(["g++", "-std=c++20", "-Wall", "-Werror", f"-I{gen / 'cpp'}",
                            str(src), "-o", str(exe)], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    assert run.returncode == 0 and "n=18 x=1 first=A" in run.stdout, run.stdout + run.stderr


def test_c_writer_zeroes_min_size_padding(gen, tmp_path):
    if not shutil.which("gcc"):
        pytest.skip("gcc not available")
    src = tmp_path / "h.c"
    src.write_text(C_HARNESS)
    exe = tmp_path / "hc"
    build = subprocess.run(["gcc", "-Wall", "-Werror", f"-I{gen / 'c'}", str(src), "-o", str(exe)],
                           capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr


def test_js_writer_zeroes_min_size_padding(gen):
    if not shutil.which("node"):
        pytest.skip("node not available")
    module = gen / "js" / "trimmed-union-v2.structframe.js"
    run = subprocess.run(["node", "-e", JS_HARNESS, str(module)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
