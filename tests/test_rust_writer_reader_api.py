#!/usr/bin/env python3
"""The Rust ``BufferWriter::write`` / ``write_ext`` and the stored-callback reader API.

``write`` picks checksummed or minimal encoding from the profile (``write_crc`` /
``write_minimal`` made the caller choose), ``write_ext`` carries sequence and system/component
IDs (the Rust encoder used to hard-code them to 0), and ``AccumulatingReader::with_message_info``
+ ``frames()`` drain frames without passing the callback on every call. Frames must be
byte-identical to the Python writer's.

Run with ``pytest tests/test_rust_writer_reader_api.py``.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

from test_utils import run_generator

MAIN_SF = """package tw;
option pkgid = 0;
import "twp.sf";
message Fixed { option msgid = 1; uint16 a = 1; float b = 2; }
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

RUST_MAIN = r"""
use struct_frame_sdk::prelude::*;
use struct_frame_sdk::{get_message_info, tw, twp};

fn hex(data: &[u8]) -> String {
    data.iter().map(|b| format!("{:02x}", b)).collect()
}

fn show(label: &str, name: &str, w: &BufferWriter, n: usize) {
    if n == 0 { println!("{} {} none", label, name); } else { println!("{} {} {}", label, name, hex(w.data())); }
}

fn main() {
    let profiles = [("STANDARD", PROFILE_STANDARD_CONFIG), ("SENSOR", PROFILE_SENSOR_CONFIG),
                    ("IPC", PROFILE_IPC_CONFIG), ("BULK", PROFILE_BULK_CONFIG),
                    ("NETWORK", PROFILE_NETWORK_CONFIG)];
    let fixed = tw::Fixed { a: 0x1234, b: 1.5 };
    let ext = tw::Ext { a: 9, c: 4, b: 0xDEADBEEF };
    let p = twp::P { x: 42 };
    for (label, cfg) in profiles.iter() {
        let mut w = BufferWriter::new(*cfg, 512);
        let n = w.write(&fixed);
        show(label, "Fixed", &w, n);
        w.reset();
        let n = w.write_ext(&ext, 3, 1, 2);
        show(label, "Ext", &w, n);
        w.reset();
        let n = w.write(&p);
        show(label, "P", &w, n);
    }

    let mut w = BufferWriter::new(PROFILE_NETWORK_CONFIG, 512);
    w.write(&fixed);
    w.write(&p);
    let mut reader = AccumulatingReader::with_message_info(PROFILE_NETWORK_CONFIG, 1024, get_message_info);
    reader.add_data(w.data());
    let mut seen = 0;
    for frame in reader.frames().filter(|f| f.valid) {
        if frame.msg_id == tw::Fixed::MSG_ID {
            let d = tw::Fixed::deserialize(&frame).unwrap();
            if d.a == 0x1234 { seen |= 1; }
        } else if frame.msg_id == twp::P::MSG_ID {
            let d = twp::P::deserialize(&frame).unwrap();
            if d.x == 42 { seen |= 2; }
        }
    }
    let mut pushed = 0;
    for &b in w.data() {
        if let Some(f) = reader.push(b) { if f.valid { pushed += 1; } }
    }
    println!("seen {} pushed {}", seen, pushed);
}
"""

PY_PROGRAM = r"""
from structframe import frame_profiles as fp
from structframe.tw import Fixed, Ext
from structframe.twp import P

msgs = [("Fixed", Fixed(a=0x1234, b=1.5), {}),
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


def test_rust_write_and_frames_api(tmp_path):
    cargo = shutil.which("cargo")
    if cargo is None:
        pytest.skip("cargo not installed")
    (tmp_path / "tw.sf").write_text(MAIN_SF, encoding="utf-8")
    (tmp_path / "twp.sf").write_text(PKG_SF, encoding="utf-8")
    gen = run_generator(tmp_path / "tw.sf", "--build_rust", "--rust_path", str(tmp_path / "rust"),
                        "--build_py", "--py_path", str(tmp_path / "py"))
    assert gen.returncode == 0, gen.stdout + gen.stderr

    app = tmp_path / "app"
    (app / "src").mkdir(parents=True)
    rust_dir = (tmp_path / "rust").as_posix()
    (app / "Cargo.toml").write_text(
        '[package]\nname = "app"\nversion = "0.0.0"\nedition = "2021"\n\n'
        f'[dependencies]\nstruct_frame_sdk = {{ path = "{rust_dir}" }}\n', encoding="utf-8")
    (app / "src" / "main.rs").write_text(RUST_MAIN, encoding="utf-8")
    run = subprocess.run([cargo, "run", "--quiet", "--manifest-path", str(app / "Cargo.toml")],
                         capture_output=True, text=True, timeout=1200,
                         env=dict(os.environ, CARGO_TARGET_DIR=str(tmp_path / "target")))
    assert run.returncode == 0, run.stdout + run.stderr
    lines = run.stdout.splitlines()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path / "py")
    py = subprocess.run([sys.executable, "-c", PY_PROGRAM], capture_output=True, text=True,
                        env=env, timeout=60)
    assert py.returncode == 0, py.stderr

    assert lines[:-1] == py.stdout.splitlines()
    assert lines[-1] == "seen 3 pushed 2"
    # seq/sys/comp reach the wire on the Network profile (they used to be hard-coded to 0).
    network_ext = next(line for line in lines if line.startswith("NETWORK Ext "))
    assert network_ext.split()[2][4:10] == "030102"
