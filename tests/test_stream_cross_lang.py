#!/usr/bin/env python3
"""
Cross-language stream-parser differential test.

Every language's streaming reader gets the same byte streams (valid frames separated by
garbage, and valid frames with bit flips / truncation / junk) in different chunk sizes. A
tiny per-language driver under ``tests/fuzz/drivers`` prints what it decoded; this test
checks, per language and profile:

* **resync**: on the garbage-separated stream every intact frame is recovered, in order
  (CRC profiles; the minimal Sensor/IPC profiles have no checksum, so they get a
  garbage-free stream);
* **no forgery**: on the corrupted stream a CRC profile only ever reports frames that were
  actually sent;
* **chunk invariance**: splitting the same bytes differently never changes the output;
* **agreement**: the output equals the Python runtime's on every stream.

Unlike the libFuzzer/atheris harnesses these use real message info (size + magic numbers),
so frames pass the checksum and reach the deeper parser paths. A driver whose toolchain is
missing is skipped unless ``SF_REQUIRE_LANGS`` lists it (the same switch run_tests.py uses).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "fuzz"))
import corpus  # noqa: E402

REPO = corpus.REPO_ROOT
DRIVERS = REPO / "tests" / "fuzz" / "drivers"
BOILER = REPO / "src" / "struct_frame" / "boilerplate"
# The largest chunk is half the readers' 1024-byte buffer: the Rust reader copies into its
# internal buffer and drops (and counts) whatever does not fit next to a pending partial
# frame, unlike the zero-copy buffer mode of the other languages. See the Rust SDK page.
CHUNKS = [1, 13, 512]
SEEDS = [1, 7, 23]
CRC_PROFILES = ["standard", "bulk", "network"]
EXE = ".exe" if sys.platform == "win32" else ""


def _required() -> set:
    return {x.strip() for x in os.environ.get("SF_REQUIRE_LANGS", "").split(",") if x.strip()}


def _unavailable(lang: str, why: str):
    if lang in _required():
        pytest.fail(f"{lang} stream driver required but unavailable: {why}")
    pytest.skip(f"{lang}: {why}")


def _run(cmd: List[str], cwd: Optional[Path] = None) -> str:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, cmd))} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
    return r.stdout


# ---- driver builders: each returns a function (profile, file, chunk) -> stdout -------------------

def _build_c(tmp: Path):
    cc = os.environ.get("CC", "gcc")
    if not shutil.which(cc):
        _unavailable("c", f"{cc} not found")
    exe = tmp / f"stream_c{EXE}"
    _run([cc, "-O1", "-std=c11", "-I", str(BOILER / "c"), str(DRIVERS / "stream_driver.c"), "-o", str(exe)])
    return lambda p, f, c: _run([str(exe), p, str(f), str(c)])


def _build_cpp(tmp: Path):
    cxx = os.environ.get("CXX", "g++")
    if not shutil.which(cxx):
        _unavailable("cpp", f"{cxx} not found")
    exe = tmp / f"stream_cpp{EXE}"
    _run([cxx, "-O1", "-std=c++20", "-I", str(BOILER / "cpp"), str(DRIVERS / "stream_driver.cpp"), "-o", str(exe)])
    return lambda p, f, c: _run([str(exe), p, str(f), str(c)])


def _build_js(tmp: Path):
    if not shutil.which("node"):
        _unavailable("js", "node not found")
    script = DRIVERS / "stream_driver.js"
    return lambda p, f, c: _run(["node", str(script), p, str(f), str(c)])


def _build_rust(tmp: Path):
    if not shutil.which("cargo"):
        _unavailable("rust", "cargo not found")
    manifest = DRIVERS / "rust" / "Cargo.toml"
    env_target = tmp / "rust_target"
    cmd = ["cargo", "build", "--quiet", "--release", "--manifest-path", str(manifest), "--target-dir", str(env_target)]
    _run(cmd)
    exe = env_target / "release" / f"stream_driver{EXE}"
    return lambda p, f, c: _run([str(exe), p, str(f), str(c)])


def _build_csharp(tmp: Path):
    if not shutil.which("dotnet"):
        _unavailable("csharp", "dotnet not found")
    proj = DRIVERS / "csharp" / "StreamDriver.csproj"
    out = tmp / "cs_out"
    _run(["dotnet", "build", "-c", "Release", "-o", str(out), "--nologo", "-v", "q", str(proj)])
    dll = out / "StreamDriver.dll"
    return lambda p, f, c: _run(["dotnet", str(dll), p, str(f), str(c)])


def _build_py(tmp: Path):
    script = DRIVERS / "stream_driver.py"
    return lambda p, f, c: _run([sys.executable, str(script), p, str(f), str(c)])


BUILDERS = {
    "py": _build_py, "c": _build_c, "cpp": _build_cpp, "js": _build_js,
    "rust": _build_rust, "csharp": _build_csharp,
}


@pytest.fixture(scope="module")
def streams(tmp_path_factory) -> Dict[str, Dict]:
    d = tmp_path_factory.mktemp("streams")
    result = {}
    for profile, seed in [(p, s) for p in corpus.PROFILES for s in SEEDS]:
        crc = profile in CRC_PROFILES
        clean, expected = corpus.clean_stream(profile, junk=crc, seed=seed)
        corrupt, originals = corpus.corrupted_stream(profile, seed=seed + 100)
        noisy = corpus.noisy_stream(profile, seed=seed + 200)
        cf, kf = d / f"{profile}_{seed}_clean.bin", d / f"{profile}_{seed}_corrupt.bin"
        nf = d / f"{profile}_{seed}_noisy.bin"
        cf.write_bytes(clean)
        kf.write_bytes(corrupt)
        nf.write_bytes(noisy)
        result[(profile, seed)] = {"clean": cf, "corrupt": kf, "noisy": nf, "expected": expected, "originals": originals,
                           "ref_clean": corpus.reference_decode(profile, clean, 1 << 20),
                           "ref_corrupt": corpus.reference_decode(profile, corrupt, 1 << 20),
                           "ref_noisy": corpus.reference_decode(profile, noisy, 1 << 20)}
    return result


@pytest.fixture(scope="module", params=sorted(BUILDERS))
def driver(request, tmp_path_factory):
    return request.param, BUILDERS[request.param](tmp_path_factory.mktemp(f"drv_{request.param}"))


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("profile", corpus.PROFILES)
def test_stream_parsing(driver, streams, profile, seed):
    lang, run = driver
    s = streams[(profile, seed)]
    outputs = {}
    for kind in ("clean", "corrupt", "noisy"):
        per_chunk = [corpus.parse_output(run(profile, s[kind], c)) for c in CHUNKS]
        for c, out in zip(CHUNKS, per_chunk):
            assert out == per_chunk[0], f"{lang}/{profile}/{kind}: chunk {c} differs from chunk {CHUNKS[0]}"
        outputs[kind] = per_chunk[0]

    if profile in CRC_PROFILES:
        assert outputs["clean"] == s["expected"], f"{lang}/{profile}: intact frames lost after garbage"
        forged = [f for f in outputs["corrupt"] if f not in s["originals"]]
        assert not forged, f"{lang}/{profile}: reported frames that were never sent: {forged[:3]}"
    else:
        assert outputs["clean"] == s["expected"], f"{lang}/{profile}: clean stream decoded wrongly"

    assert outputs["clean"] == s["ref_clean"], f"{lang}/{profile}: clean output differs from Python"
    assert outputs["corrupt"] == s["ref_corrupt"], f"{lang}/{profile}: corrupt-stream output differs from Python"
    assert outputs["noisy"] == s["ref_noisy"], f"{lang}/{profile}: noisy-stream output differs from Python"
