#!/usr/bin/env python3
"""Build and run the programs in ``examples/`` so they cannot silently rot.

The examples used to reference headers, modules and APIs that no longer existed
and nothing noticed. These tests generate code from ``examples/basic/hello.sf``,
then compile/run the C, Python and TypeScript programs and check what they
print, and generate every multi-file example for every language.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from test_utils import REPO_ROOT, SRC_DIR, run_generator

EXAMPLES = REPO_ROOT / "examples"
HELLO_SF = EXAMPLES / "basic" / "hello.sf"

EXPECTED = ("pose: pitch=100.0", "sample=4883", "heartbeat: id=23 type=2")


def _env(generated_dir: str) -> dict:
    """Environment for running *generated* Python.

    The generated package is also called ``struct_frame`` (``struct_frame/generated``),
    which is the generator's own package name. Put only the generated directory on
    the path, never the generator's ``src``, or the generator shadows the output.
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = generated_dir
    return env


def _generate(sf: Path, *flags: str):
    result = run_generator(sf, *flags)
    assert result.returncode == 0, result.stdout + result.stderr


def _assert_hello_output(output: str):
    for needle in EXPECTED:
        assert needle in output, f"missing {needle!r} in example output:\n{output}"


def test_python_hello(tmp_path):
    out = tmp_path / "py"
    _generate(HELLO_SF, "--build_py", "--py_path", str(out))
    result = subprocess.run([sys.executable, str(EXAMPLES / "basic" / "hello.py")],
                            capture_output=True, text=True, env=_env(str(out)), timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    _assert_hello_output(result.stdout)


def test_c_hello(tmp_path):
    gcc = shutil.which(os.environ.get("CC", "gcc"))
    if gcc is None:
        pytest.skip("no C compiler")
    out = tmp_path / "c"
    _generate(HELLO_SF, "--build_c", "--c_path", str(out))
    exe = tmp_path / ("hello.exe" if os.name == "nt" else "hello")
    build = subprocess.run([gcc, "-std=c11", "-Wall", "-Werror", f"-I{out}",
                            str(EXAMPLES / "basic" / "hello.c"), "-o", str(exe)],
                           capture_output=True, text=True, timeout=120)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
    # The C program prints floats with %.2f, so compare the stable parts.
    assert "pose: pitch=100.0" in run.stdout and "sample=4883" in run.stdout
    assert "heartbeat: id=23 type=2" in run.stdout


def test_typescript_hello(tmp_path):
    tsc = REPO_ROOT / "node_modules" / ".bin" / ("tsc.cmd" if os.name == "nt" else "tsc")
    node = shutil.which("node")
    if not tsc.exists() or node is None:
        pytest.skip("TypeScript toolchain not installed (npm ci)")
    out = tmp_path / "ts"
    _generate(HELLO_SF, "--build_ts", "--ts_path", str(out))
    shutil.copy(EXAMPLES / "basic" / "hello.ts", out / "hello.ts")
    build = subprocess.run(
        [str(tsc), "--target", "es2020", "--module", "commonjs", "--esModuleInterop",
         "--skipLibCheck", "--types", "node",
         "--typeRoots", str(REPO_ROOT / "node_modules" / "@types"),
         "--outDir", str(out / "dist"), str(out / "hello.ts")],
        capture_output=True, text=True, timeout=300)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([node, str(out / "dist" / "hello.js")],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stdout + run.stderr
    assert "pose: pitch=100.0" in run.stdout and "sample=4883" in run.stdout
    assert "heartbeat: id=23 type=2" in run.stdout


ALL_BUILDS = [
    ("--build_c", "--c_path"), ("--build_cpp", "--cpp_path"), ("--build_ts", "--ts_path"),
    ("--build_js", "--js_path"), ("--build_py", "--py_path"), ("--build_gql", "--gql_path"),
    ("--build_csharp", "--csharp_path"), ("--build_rust", "--rust_path"),
]


@pytest.mark.parametrize("sf", [
    "multi_package/system.sf", "package_ids/fleet.sf", "generic_robot.sf", "array_test.sf",
    "basic/hello.sf",
])
def test_example_generates_for_every_language(sf, tmp_path):
    flags = []
    for build_flag, path_flag in ALL_BUILDS:
        flags += [build_flag, path_flag, str(tmp_path / build_flag.removeprefix("--build_"))]
    _generate(EXAMPLES / sf, *flags)
    assert (tmp_path / "gql" / "schema.graphql").exists()


def test_multi_package_python_imports(tmp_path):
    """The generated Python for the multi-package example must be importable:
    every cross-package type has to be imported by the module that uses it."""
    out = tmp_path / "py"
    _generate(EXAMPLES / "multi_package" / "system.sf", "--build_py", "--py_path", str(out))
    code = ("import struct_frame.generated.system, struct_frame.generated.events, "
            "struct_frame.generated.sensors, struct_frame.generated.common; print('ok')")
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                            env=_env(str(out)), timeout=120)
    assert result.returncode == 0 and "ok" in result.stdout, result.stdout + result.stderr


def test_python_nested_message_array_round_trip(tmp_path):
    """A bounded array of nested messages with a non-zero count must survive a
    round trip. (The standard suite only ever uses count 0 for these arrays, so
    this path crashed the generator unnoticed.)"""
    out = tmp_path / "py"
    _generate(EXAMPLES / "array_test.sf", "--build_py", "--py_path", str(out))
    script = tmp_path / "roundtrip.py"
    script.write_text(
        "from struct_frame.generated.array_test import ArrayTestMessage, SubMessage\n"
        "msg = ArrayTestMessage()\n"
        "msg.messages = [SubMessage(id=7, name=b'first'), SubMessage(id=9, name=b'second')]\n"
        "msg.measurements = [1, 2, 3]\n"
        "decoded = ArrayTestMessage.deserialize(msg.serialize())\n"
        "assert [m.id for m in decoded.messages] == [7, 9], decoded.messages\n"
        "assert [m.name for m in decoded.messages] == [b'first', b'second']\n"
        "assert list(decoded.measurements) == [1, 2, 3]\n"
        "print('ok')\n", encoding="utf-8")
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                            env=_env(str(out)), timeout=120)
    assert result.returncode == 0 and "ok" in result.stdout, result.stdout + result.stderr


@pytest.mark.parametrize("flag,path_flag,compiler_env,default,header,std", [
    ("--build_c", "--c_path", "CC", "gcc", "array_test.structframe.h", "-std=c11"),
    ("--build_cpp", "--cpp_path", "CXX", "g++", "array_test.structframe.hpp", "-std=c++20"),
])
def test_array_example_compiles(tmp_path, flag, path_flag, compiler_env, default, header, std):
    compiler = shutil.which(os.environ.get(compiler_env, default))
    if compiler is None:
        pytest.skip(f"no {default}")
    out = tmp_path / "out"
    _generate(EXAMPLES / "array_test.sf", flag, path_flag, str(out))
    unit = tmp_path / ("unit.c" if flag == "--build_c" else "unit.cpp")
    unit.write_text(f'#include "{header}"\nint main(void) {{ return 0; }}\n', encoding="utf-8")
    result = subprocess.run([compiler, std, f"-I{out}", "-fsyntax-only", str(unit)],
                            capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stdout + result.stderr


def test_cpp_full_sdk_has_real_asio_headers(tmp_path):
    """The full C++ SDK needs ``asio/`` next to ``asio.hpp``. It is a git symlink in
    the source tree (a text file on Windows), so the generator must copy the real
    headers, and must not drag the whole multi-megabyte submodule along."""
    out = tmp_path / "cpp"
    _generate(HELLO_SF, "--build_cpp", "--cpp_path", str(out), "--sdk")
    sdk = out / "struct_frame_sdk"
    assert (sdk / "asio").is_dir(), "asio/ is not a directory of headers"
    assert (sdk / "asio" / "io_context.hpp").is_file()
    assert not (sdk / "asio-repo").exists(), "vendored submodule copied into the output"


def test_python_enum_members_usable_as_field_values(tmp_path):
    """Enum fields hold ints, so enum members must be accepted directly (IntEnum),
    and decode must compare equal to the member."""
    out = tmp_path / "py"
    _generate(HELLO_SF, "--build_py", "--py_path", str(out))
    script = tmp_path / "enum_use.py"
    script.write_text(
        "from struct_frame.generated.hello import Heartbeat, VehicleType\n"
        "hb = Heartbeat(id=1, type=VehicleType.QUADCOPTER)\n"
        "decoded = Heartbeat.deserialize(hb.serialize())\n"
        "assert decoded.type == VehicleType.QUADCOPTER == 2\n"
        "assert VehicleType(decoded.type).name == 'QUADCOPTER'\n"
        "print('ok')\n", encoding="utf-8")
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                            env=_env(str(out)), timeout=120)
    assert result.returncode == 0 and "ok" in result.stdout, result.stdout + result.stderr
