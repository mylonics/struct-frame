#!/usr/bin/env python3
"""``structframe_all.h`` / ``structframe_all.hpp`` include every package and look message IDs
up across all of them, and the C++ ``Profile*AccumulatingReader`` aliases accept the generated
``get_message_info`` (the Standard alias used to be impossible to construct).

Run with ``pytest tests/test_umbrella_headers.py``.
"""
from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from test_utils import run_generator

MAIN_SF = """package um;
option pkgid = 0;  // IDs <= 255, so the Standard profile can carry them too
import "um_other.sf";
message Fixed { option msgid = 1; uint16 a = 1; float b = 2; }
"""

OTHER_SF = """package um_other;
option pkgid = 5;
message P { option msgid = 7; uint32 x = 1; }
"""

C_PROGRAM = r"""
#include <stdio.h>
#include "structframe_all.h"

int main(void) {
    uint8_t buf[256], internal[256];
    buffer_writer_t w;
    buffer_writer_init(&w, &PROFILE_BULK_CONFIG, buf, sizeof buf);
    UmFixed f = {.a = 0x1234, .b = 1.5f};
    UmOtherP p = {.x = 42};
    if (!UmFixed_write(&w, &f) || !UmOtherP_write(&w, &p)) return 1;

    accumulating_reader_t r;
    accumulating_reader_init(&r, &PROFILE_BULK_CONFIG, internal, sizeof internal,
                             structframe_all_get_message_info);
    accumulating_reader_add_data(&r, buf, buffer_writer_size(&w));
    frame_msg_info_t frame;
    int seen = 0;
    while (accumulating_reader_try_next(&r, &frame)) {
        if (!frame.valid) return 2;
        if (frame.msg_id == UM_FIXED_MSG_ID) {
            UmFixed d; UmFixed_deserialize(frame.msg_data, frame.msg_len, &d);
            if (d.a != 0x1234) return 3;
            seen |= 1;
        } else if (frame.msg_id == UM_OTHER_P_MSG_ID) {
            UmOtherP d; UmOtherP_deserialize(frame.msg_data, frame.msg_len, &d);
            if (d.x != 42) return 4;
            seen |= 2;
        }
    }
    printf("seen=%d\n", seen);
    return seen == 3 ? 0 : 5;
}
"""

CPP_PROGRAM = r"""
#include <cstdio>
#include "frame_profiles.hpp"
#include "structframe_all.hpp"

using namespace structframe;

int main() {
    uint8_t buf[256];
    ProfileBulkWriter writer(buf, sizeof(buf));
    um::Fixed f{};
    f.a = 0x1234;
    um_other::P p{};
    p.x = 42;
    if (!writer.write(f) || !writer.write(p)) return 1;

    // The alias takes the generated function; the umbrella one knows both packages.
    ProfileBulkAccumulatingReader reader(structframe::get_message_info);
    reader.add_data(buf, writer.size());
    FrameMsgInfo frame;
    int seen = 0;
    while (reader.try_next(frame)) {
        if (!frame.valid) return 2;
        if (frame.msg_id == um::Fixed::MSG_ID) {
            um::Fixed d; d.deserialize(frame);
            if (d.a != 0x1234) return 3;
            seen |= 1;
        } else if (frame.msg_id == um_other::P::MSG_ID) {
            um_other::P d; d.deserialize(frame);
            if (d.x != 42) return 4;
            seen |= 2;
        }
    }

    // The Standard alias with one package's function, byte by byte.
    uint8_t one[64];
    ProfileStandardWriter w2(one, sizeof(one));
    if (!w2.write(f)) return 6;
    ProfileStandardAccumulatingReader r2(um::get_message_info);
    int got = 0;
    for (size_t i = 0; i < w2.size(); i++) {
        if (auto info = r2.push_byte(one[i])) got++;
    }
    std::printf("seen=%d got=%d\n", seen, got);
    return (seen == 3 && got == 1) ? 0 : 5;
}
"""


@pytest.fixture()
def schema_dir(tmp_path):
    (tmp_path / "um.sf").write_text(MAIN_SF, encoding="utf-8")
    (tmp_path / "um_other.sf").write_text(OTHER_SF, encoding="utf-8")
    return tmp_path


def _build_and_run(compiler, args, cwd):
    exe = cwd / ("prog.exe" if os.name == "nt" else "prog")
    build = subprocess.run([compiler, *args, "-o", str(exe)], capture_output=True, text=True,
                           timeout=300)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, f"exit {run.returncode}: {run.stdout}{run.stderr}"
    return run.stdout


def test_c_umbrella_reads_frames_of_every_package(schema_dir):
    gcc = shutil.which(os.environ.get("CC", "gcc"))
    if gcc is None:
        pytest.skip("no C compiler")
    gen = run_generator(schema_dir / "um.sf", "--build_c", "--c_path", str(schema_dir / "c"))
    assert gen.returncode == 0, gen.stdout + gen.stderr
    assert (schema_dir / "c" / "structframe_all.h").is_file()
    src = schema_dir / "main.c"
    src.write_text(C_PROGRAM, encoding="utf-8")
    out = _build_and_run(gcc, ["-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
                               f"-I{schema_dir / 'c'}", str(src)], schema_dir)
    assert "seen=3" in out


def test_cpp_umbrella_and_reader_aliases(schema_dir):
    gxx = shutil.which(os.environ.get("CXX", "g++"))
    if gxx is None:
        pytest.skip("no C++ compiler")
    gen = run_generator(schema_dir / "um.sf", "--build_cpp", "--cpp_path", str(schema_dir / "cpp"))
    assert gen.returncode == 0, gen.stdout + gen.stderr
    src = schema_dir / "main.cpp"
    src.write_text(CPP_PROGRAM, encoding="utf-8")
    out = _build_and_run(gxx, ["-std=c++20", "-Wall", "-Wextra", "-Werror",
                               f"-I{schema_dir / 'cpp'}", str(src)], schema_dir)
    assert "seen=3 got=1" in out
