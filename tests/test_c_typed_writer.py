#!/usr/bin/env python3
"""The generated C ``<Type>_write`` helpers frame messages exactly like the Python writer.

Covers fixed, variable and extension messages and a package-ID message, on all five
standard profiles (including the minimal profiles, where variable messages travel at
MAX_SIZE, and profiles without a package-ID byte, which must refuse a package-qualified
message ID).

Run with ``pytest tests/test_c_typed_writer.py``.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from test_utils import run_generator

MAIN_SF = """package tw;
option pkgid = 0;  // IDs stay <= 255, so every profile can carry them
import "twp.sf";

message Fixed { option msgid = 1; uint16 a = 1; float b = 2; }

message Var {
  option msgid = 2;
  option variable = true;
  uint8 n = 1;
  string s = 2 [max_size=16];
  repeated uint16 v = 3 [max_size=4];
}

message Ext {
  option msgid = 3;
  uint8 a = 1;
  uint8 c = 2;
  option extensions_start = 3;
  uint32 b = 3;
}
"""

PKG_SF = """package twp;
option pkgid = 5;
message P { option msgid = 7; uint32 x = 1; }
"""

PROFILES = ("STANDARD", "SENSOR", "IPC", "BULK", "NETWORK")

C_PROGRAM = r"""
#include <stdio.h>
#include <string.h>
#include "tw.structframe.h"
#include "twp.structframe.h"

static void dump(const char* profile, const char* name, const uint8_t* data, size_t n) {
    printf("%s %s ", profile, name);
    if (n == 0) { printf("none\n"); return; }
    for (size_t i = 0; i < n; i++) printf("%02x", data[i]);
    printf("\n");
}

static void run(const char* label, const profile_config_t* cfg) {
    uint8_t buf[512];
    buffer_writer_t w;
    size_t n;

    TwFixed f; memset(&f, 0, sizeof f); f.a = 0x1234; f.b = 1.5f;
    buffer_writer_init(&w, cfg, buf, sizeof buf); n = TwFixed_write(&w, &f);
    dump(label, "Fixed", buf, n);

    TwVar v; memset(&v, 0, sizeof v); v.n = 7;
    v.s.length = 2; memcpy(v.s.data, "hi", 2);
    v.v.count = 3; v.v.data[0] = 1; v.v.data[1] = 2; v.v.data[2] = 3;
    buffer_writer_init(&w, cfg, buf, sizeof buf); n = TwVar_write(&w, &v);
    dump(label, "Var", buf, n);

    TwExt e; memset(&e, 0, sizeof e); e.a = 9; e.c = 4; e.b = 0xDEADBEEFu;
    buffer_writer_init(&w, cfg, buf, sizeof buf); n = TwExt_write_ext(&w, &e, 3, 1, 2);
    dump(label, "Ext", buf, n);

    TwpP p; memset(&p, 0, sizeof p); p.x = 42;
    buffer_writer_init(&w, cfg, buf, sizeof buf); n = TwpP_write(&w, &p);
    dump(label, "P", buf, n);

    /* A writer without room for the largest frame refuses instead of overflowing. */
    buffer_writer_init(&w, cfg, buf, 4); n = TwVar_write(&w, &v);
    printf("%s small %zu\n", label, n);
}

int main(void) {
    run("STANDARD", &PROFILE_STANDARD_CONFIG);
    run("SENSOR", &PROFILE_SENSOR_CONFIG);
    run("IPC", &PROFILE_IPC_CONFIG);
    run("BULK", &PROFILE_BULK_CONFIG);
    run("NETWORK", &PROFILE_NETWORK_CONFIG);
    return 0;
}
"""

PY_PROGRAM = r"""
from structframe import frame_profiles as fp
from structframe.tw import Fixed, Var, Ext
from structframe.twp import P

msgs = [("Fixed", Fixed(a=0x1234, b=1.5), {}),
        ("Var", Var(n=7, s=b"hi", v=[1, 2, 3]), {}),
        ("Ext", Ext(a=9, c=4, b=0xDEADBEEF), dict(seq=3, sys_id=1, comp_id=2)),
        ("P", P(x=42), {})]
for label in ("STANDARD", "SENSOR", "IPC", "BULK", "NETWORK"):
    cfg = getattr(fp, "PROFILE_%s_CONFIG" % label)
    for name, msg, extra in msgs:
        try:
            data = fp.encode_message(cfg, msg, **extra)
        except (ValueError, OverflowError):
            data = b""
        print(label, name, data.hex() if data else "none")
"""


def test_c_typed_writer_matches_python_writer(tmp_path):
    gcc = shutil.which(os.environ.get("CC", "gcc"))
    if gcc is None:
        pytest.skip("no C compiler")
    (tmp_path / "tw.sf").write_text(MAIN_SF, encoding="utf-8")
    (tmp_path / "twp.sf").write_text(PKG_SF, encoding="utf-8")
    gen = run_generator(tmp_path / "tw.sf", "--build_c", "--c_path", str(tmp_path / "c"),
                        "--build_py", "--py_path", str(tmp_path / "py"))
    assert gen.returncode == 0, gen.stdout + gen.stderr

    src = tmp_path / "main.c"
    src.write_text(C_PROGRAM, encoding="utf-8")
    exe = tmp_path / ("tw.exe" if os.name == "nt" else "tw")
    build = subprocess.run([gcc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
                            f"-I{tmp_path / 'c'}", str(src), "-o", str(exe)],
                           capture_output=True, text=True, timeout=120)
    assert build.returncode == 0, build.stdout + build.stderr
    c_run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert c_run.returncode == 0, c_run.stderr
    c_lines = c_run.stdout.splitlines()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path / "py")  # never the generator's src (same package name)
    py_run = subprocess.run([sys.executable, "-c", PY_PROGRAM], capture_output=True, text=True,
                            env=env, timeout=60)
    assert py_run.returncode == 0, py_run.stderr
    py_frames = py_run.stdout.splitlines()

    c_frames = [line for line in c_lines if " small " not in line]
    assert c_frames == py_frames

    # Every message must actually be sent on the profiles that can carry it.
    sent = {tuple(line.split()[:2]) for line in c_frames if not line.endswith(" none")}
    for profile in PROFILES:
        for name in ("Fixed", "Var", "Ext"):
            assert (profile, name) in sent, f"{name} not encoded with {profile}"
    assert ("BULK", "P") in sent and ("NETWORK", "P") in sent
    assert ("STANDARD", "P") not in sent, "package-qualified ID truncated on Standard"

    for profile in PROFILES:
        assert f"{profile} small 0" in c_lines
