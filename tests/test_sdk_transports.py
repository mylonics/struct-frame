#!/usr/bin/env python3
"""
Loopback tests for the concrete SDK transports (TCP, UDP, and WebSocket where it can run without
extra packages) in the TypeScript/JavaScript, C# and C++ SDKs. The Python TCP transport has its own
suite in tests/py/test_tcp_transport.py; Rust has no transports yet.

Each language has a small program under tests/js and tests/sdk_transports that talks to a real
socket peer on 127.0.0.1 and prints PASS/FAIL lines; this wrapper builds it, runs it, and fails
with the program's output if it exits non-zero. A missing toolchain skips that language unless it is
listed in SF_REQUIRE_LANGS (the same switch run_tests.py uses).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EXE = ".exe" if sys.platform == "win32" else ""


def _required() -> set:
    return {x.strip() for x in os.environ.get("SF_REQUIRE_LANGS", "").split(",") if x.strip()}


def _unavailable(lang: str, why: str):
    if lang in _required():
        pytest.fail(f"{lang} transport test required but unavailable: {why}")
    pytest.skip(f"{lang}: {why}")


def _run(cmd, cwd=None, timeout=300):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def _assert_ok(result: subprocess.CompletedProcess, what: str):
    assert result.returncode == 0, f"{what} failed ({result.returncode}):\n{result.stdout}\n{result.stderr}"
    assert "FAIL " not in result.stdout, result.stdout
    assert "transport checks passed" in result.stdout, result.stdout


def test_js_ts_transports():
    if not shutil.which("node"):
        _unavailable("js", "node not found")
    result = _run(["node", str(REPO / "tests" / "js" / "test_transports.js")], timeout=120)
    _assert_ok(result, "tests/js/test_transports.js")


def test_csharp_transports(tmp_path):
    if not shutil.which("dotnet"):
        _unavailable("csharp", "dotnet not found")
    proj = REPO / "tests" / "sdk_transports" / "csharp" / "TransportTests.csproj"
    out = tmp_path / "out"
    build = _run(["dotnet", "build", "-c", "Release", "-o", str(out), "--nologo", "-v", "q", str(proj)])
    assert build.returncode == 0, build.stdout + build.stderr
    result = _run(["dotnet", str(out / "TransportTests.dll")], timeout=120)
    _assert_ok(result, "C# transport tests")


def test_cpp_transports(tmp_path):
    cxx = os.environ.get("CXX", "g++")
    if not shutil.which(cxx):
        _unavailable("cpp", f"{cxx} not found")
    sdk = REPO / "src" / "struct_frame" / "boilerplate" / "cpp"
    asio_include = sdk / "struct_frame_sdk" / "asio-repo" / "asio" / "include"
    if not asio_include.is_dir():
        _unavailable("cpp", "asio headers missing (git submodule not checked out)")
    exe = tmp_path / f"test_transports{EXE}"
    cmd = [cxx, "-std=c++20", "-O1", "-I", str(asio_include), "-I", str(sdk),
           str(REPO / "tests" / "sdk_transports" / "cpp" / "test_transports.cpp"), "-o", str(exe), "-pthread"]
    if sys.platform == "win32":
        cmd += ["-lws2_32", "-lmswsock"]
    build = _run(cmd)
    assert build.returncode == 0, build.stdout + build.stderr
    result = _run([str(exe)], timeout=120)
    _assert_ok(result, "C++ transport tests")


def test_cpp_serial_transport(tmp_path):
    cxx = os.environ.get("CXX", "g++")
    if not shutil.which(cxx):
        _unavailable("cpp", f"{cxx} not found")
    exe = tmp_path / f"test_serial_transport{EXE}"
    build = _run([cxx, "-std=c++20", "-O1", "-I", str(REPO / "src" / "struct_frame" / "boilerplate" / "cpp"),
                  str(REPO / "tests" / "sdk_transports" / "cpp" / "test_serial_transport.cpp"), "-o", str(exe)])
    assert build.returncode == 0, build.stdout + build.stderr
    _assert_ok(_run([str(exe)], timeout=60), "C++ serial transport tests")


def test_csharp_websocket_transport(tmp_path):
    """C# WebSocketTransport (needs the NetCoreServer NuGet package, restored on first build)."""
    if not shutil.which("dotnet"):
        _unavailable("csharp", "dotnet not found")
    proj = REPO / "tests" / "sdk_transports" / "csharp_ws" / "WsTransportTests.csproj"
    out = tmp_path / "out"
    build = _run(["dotnet", "build", "-c", "Release", "-o", str(out), "--nologo", "-v", "q", str(proj)])
    if build.returncode != 0 and "NU1101" in build.stdout + build.stderr:
        _unavailable("csharp", "NetCoreServer package could not be restored (offline?)")
    assert build.returncode == 0, build.stdout + build.stderr
    _assert_ok(_run(["dotnet", str(out / "WsTransportTests.dll")], timeout=120), "C# WebSocket transport tests")


def _pty_pair():
    """Start ``socat`` with two linked pseudo-terminals; return (process, port_a, port_b)."""
    import re
    import time
    proc = subprocess.Popen(["socat", "-d", "-d", "pty,raw,echo=0", "pty,raw,echo=0"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    ports = []
    deadline = time.time() + 10
    while len(ports) < 2 and time.time() < deadline:
        line = proc.stderr.readline()
        if not line:
            break
        m = re.search(r"PTY is (\S+)", line)
        if m:
            ports.append(m.group(1))
    if len(ports) < 2:
        proc.kill()
        raise RuntimeError("socat did not report two PTYs")
    return proc, ports[0], ports[1]


def test_csharp_serial_transport(tmp_path):
    """C# SerialTransport over a socat pseudo-terminal pair (Linux/macOS with socat only)."""
    if not shutil.which("dotnet"):
        _unavailable("csharp", "dotnet not found")
    if sys.platform == "win32" or not shutil.which("socat"):
        pytest.skip("needs socat to create a pseudo-terminal pair (Linux/macOS)")
    proj = REPO / "tests" / "sdk_transports" / "csharp_serial" / "SerialTransportTests.csproj"
    out = tmp_path / "out"
    build = _run(["dotnet", "build", "-c", "Release", "-o", str(out), "--nologo", "-v", "q", str(proj)])
    assert build.returncode == 0, build.stdout + build.stderr
    proc, port_a, port_b = _pty_pair()
    try:
        _assert_ok(_run(["dotnet", str(out / "SerialTransportTests.dll"), port_a, port_b], timeout=120),
                   "C# serial transport tests")
    finally:
        proc.kill()
