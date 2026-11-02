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


# ---------------------------------------------------------------------------
# Bounded arrays of nested messages with a non-zero count (the standard suites
# only ever use count 0 for these, which is how a generator crash went unnoticed)
# ---------------------------------------------------------------------------

def test_c_nested_message_array_round_trip(tmp_path):
    gcc = shutil.which(os.environ.get("CC", "gcc"))
    if gcc is None:
        pytest.skip("no C compiler")
    out = tmp_path / "c"
    _generate(EXAMPLES / "array_test.sf", "--build_c", "--c_path", str(out))
    src = tmp_path / "nested.c"
    src.write_text(r'''
#include <stdio.h>
#include <string.h>
#include "array_test.structframe.h"
int main(void) {
  ArrayTestArrayTestMessage msg, out;
  memset(&msg, 0, sizeof(msg)); memset(&out, 0, sizeof(out));
  msg.messages.count = 3;
  msg.messages.data[0].id = 7; msg.messages.data[1].id = 9; msg.messages.data[2].id = 11;
  msg.measurements.count = 2; msg.measurements.data[0] = -5; msg.measurements.data[1] = 70000;
  uint8_t buf[4096];
  size_t n = ArrayTestArrayTestMessage_serialize(&msg, buf);
  if (n == 0) return 1;
  if (ArrayTestArrayTestMessage_deserialize(buf, n, &out) == 0) return 2;
  if (out.messages.count != 3 || out.messages.data[0].id != 7 ||
      out.messages.data[1].id != 9 || out.messages.data[2].id != 11) return 3;
  if (out.measurements.count != 2 || out.measurements.data[0] != -5 ||
      out.measurements.data[1] != 70000) return 4;
  printf("ok\n");
  return 0;
}
''', encoding="utf-8")
    exe = tmp_path / ("nested_c.exe" if os.name == "nt" else "nested_c")
    build = subprocess.run([gcc, "-std=c11", "-Wall", f"-I{out}", str(src), "-o", str(exe)],
                           capture_output=True, text=True, timeout=300)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and "ok" in run.stdout, f"exit {run.returncode}: {run.stdout}{run.stderr}"


def test_cpp_nested_message_array_round_trip(tmp_path):
    gxx = shutil.which(os.environ.get("CXX", "g++"))
    if gxx is None:
        pytest.skip("no C++ compiler")
    out = tmp_path / "cpp"
    _generate(EXAMPLES / "array_test.sf", "--build_cpp", "--cpp_path", str(out))
    src = tmp_path / "nested.cpp"
    src.write_text(r'''
#include <cstdio>
#include "array_test.structframe.hpp"
using structframe::array_test::ArrayTestMessage;
int main() {
  ArrayTestMessage msg{}, out{};
  msg.messages.count = 3;
  msg.messages.data[0].id = 7; msg.messages.data[1].id = 9; msg.messages.data[2].id = 11;
  msg.measurements.count = 2; msg.measurements.data[0] = -5; msg.measurements.data[1] = 70000;
  uint8_t buf[4096];
  size_t n = msg.serialize(buf);
  if (n == 0) return 1;
  if (out.deserialize(buf, n) != n) return 2;
  if (out.messages.count != 3 || out.messages.data[0].id != 7 ||
      out.messages.data[1].id != 9 || out.messages.data[2].id != 11) return 3;
  if (out.measurements.count != 2 || out.measurements.data[0] != -5 ||
      out.measurements.data[1] != 70000) return 4;
  std::printf("ok\n");
  return 0;
}
''', encoding="utf-8")
    exe = tmp_path / ("nested_cpp.exe" if os.name == "nt" else "nested_cpp")
    build = subprocess.run([gxx, "-std=c++20", "-Wall", f"-I{out}", str(src), "-o", str(exe)],
                           capture_output=True, text=True, timeout=300)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and "ok" in run.stdout, f"exit {run.returncode}: {run.stdout}{run.stderr}"


def test_javascript_nested_message_array_round_trip(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    out = tmp_path / "js"
    _generate(EXAMPLES / "array_test.sf", "--build_js", "--js_path", str(out))
    script = tmp_path / "nested.js"
    script.write_text(f'''
const {{ ArrayTestMessage, SubMessage }} = require({json_path(out / "array-test.structframe.js")});
const msg = new ArrayTestMessage();
msg.messagesCount = 3;
msg.messagesData = [new SubMessage({{ id: 7 }}), new SubMessage({{ id: 9 }}), new SubMessage({{ id: 11 }})];
msg.measurementsCount = 2;
msg.measurementsData = [-5, 70000];
const out = ArrayTestMessage.deserialize(msg.serialize());
const ids = out.messagesData.slice(0, out.messagesCount).map(m => m.id);
if (out.messagesCount !== 3 || ids.join() !== "7,9,11") throw new Error("nested ids " + ids);
if (out.measurementsCount !== 2 || out.measurementsData[0] !== -5 || out.measurementsData[1] !== 70000) throw new Error("measurements");
console.log("ok");
''', encoding="utf-8")
    run = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0 and "ok" in run.stdout, run.stdout + run.stderr


def json_path(path: Path) -> str:
    import json
    return json.dumps(path.as_posix())


def test_python_message_str_lists_fields(tmp_path):
    out = tmp_path / "py"
    _generate(HELLO_SF, "--build_py", "--py_path", str(out))
    script = tmp_path / "str_use.py"
    script.write_text(
        "from struct_frame.generated.hello import Pose\n"
        "text = str(Pose(pitch=1.5, yaw_rate=-2.0, sample=42))\n"
        "assert 'Pose' in text and 'ID 1' in text, text\n"
        "for needle in ('pitch', 'yaw_rate', 'sample', '42', '1.5'):\n"
        "    assert needle in text, (needle, text)\n"
        "print('ok')\n", encoding="utf-8")
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                            env=_env(str(out)), timeout=120)
    assert result.returncode == 0 and "ok" in result.stdout, result.stdout + result.stderr


def test_javascript_sdk_request_response(tmp_path):
    """JavaScript SDK request(): resolves on a matching reply, honours `match`, times out,
    and removes its temporary subscription in every case."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    out = tmp_path / "js"
    _generate(HELLO_SF, "--build_js", "--js_path", str(out), "--sdk")
    root = json_path(out)
    script = tmp_path / "req.js"
    script.write_text(f'''
const path = require("path");
const root = {root};
const {{ Pose, Heartbeat, getMessageInfo }} = require(path.join(root, "hello.structframe.js"));
const {{ BufferWriter, ProfileStandardConfig }} = require(path.join(root, "frame-profiles.js"));
const {{ StructFrameSdk }} = require(path.join(root, "struct-frame-sdk", "struct-frame-sdk.js"));

class Mock {{
  constructor() {{ this.connected = true; this.sent = []; this.onReply = null; }}
  async connect() {{}} async disconnect() {{}}
  async send(data) {{ this.sent.push(data); if (this.onReply) this.onReply(); return data.length; }}
  onData(cb) {{ this.dataCb = cb; }} onError(cb) {{ this.errCb = cb; }} onClose(cb) {{ this.closeCb = cb; }}
  isConnected() {{ return this.connected; }}
  deliver(msg) {{
    const w = new BufferWriter(ProfileStandardConfig, 256); w.write(msg); this.dataCb(w.data());
  }}
}}
const mk = () => {{
  const t = new Mock();
  const sdk = new StructFrameSdk({{ transport: t, profile: ProfileStandardConfig, getMessageInfo }});
  // Without a codec, handlers receive the raw payload bytes instead of a decoded message.
  sdk.registerCodec({{ getMsgId: () => Heartbeat._msgid, deserialize: (d) => Heartbeat.deserialize(d) }});
  return [t, sdk];
}};
const fail = (m) => {{ console.error("FAIL: " + m); process.exit(1); }};

(async () => {{
  // 1. plain success
  let [t, sdk] = mk();
  t.onReply = () => t.deliver(new Heartbeat({{ id: 5, type: 1 }}));
  let r = await sdk.request(new Pose({{ pitch: 1 }}), Heartbeat._msgid, {{ timeout: 1 }});
  if (r.id !== 5) fail("expected id 5, got " + r.id);

  // 2. match predicate skips the first reply and accepts the second
  [t, sdk] = mk();
  t.onReply = () => {{ t.deliver(new Heartbeat({{ id: 1, type: 1 }})); t.deliver(new Heartbeat({{ id: 2, type: 1 }})); }};
  r = await sdk.request(new Pose({{ pitch: 1 }}), Heartbeat._msgid, {{ match: (m) => m.id === 2, timeout: 1 }});
  if (r.id !== 2) fail("match should pick id 2, got " + r.id);

  // 3. timeout rejects
  [t, sdk] = mk();
  let rejected = false;
  try {{ await sdk.request(new Pose({{ pitch: 1 }}), Heartbeat._msgid, {{ timeout: 0.05 }}); }}
  catch (e) {{ rejected = /No response/.test(String(e.message)); }}
  if (!rejected) fail("request without a reply must reject with a timeout");

  // 4. the temporary subscription is gone: a late reply is ignored without error
  t.deliver(new Heartbeat({{ id: 9, type: 1 }}));
  console.log("ok");
}})().catch((e) => fail(String(e && e.stack || e)));
''', encoding="utf-8")
    run = subprocess.run([node, str(script)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0 and "ok" in run.stdout, run.stdout + run.stderr


def test_python_sdk_subscribe_and_request_response(tmp_path):
    """The Python SDK documented in python-sdk.md: register_codec makes handlers receive
    decoded messages, and request() returns the matching reply (or times out)."""
    out = tmp_path / "py"
    _generate(HELLO_SF, "--build_py", "--py_path", str(out), "--sdk")
    script = tmp_path / "sdk_use.py"
    script.write_text('''
from frame_profiles import BufferWriter, PROFILE_STANDARD_CONFIG
from struct_frame.generated.hello import Pose, Heartbeat, get_message_info
from struct_frame_sdk.struct_frame_sdk import StructFrameSdk, StructFrameSdkConfig
from struct_frame_sdk.transport import ITransport

class Mock(ITransport):
    def __init__(self): self.on_data = None; self.on_reply = None; self.sent = []
    def connect(self): pass
    def disconnect(self): pass
    def send(self, data):
        self.sent.append(data)
        if self.on_reply: self.on_reply()
        return len(data)
    def set_data_callback(self, cb): self.on_data = cb
    def set_error_callback(self, cb): pass
    def set_close_callback(self, cb): pass
    def is_connected(self): return True
    def deliver(self, msg):
        w = BufferWriter(PROFILE_STANDARD_CONFIG, 256); w.write(msg); self.on_data(w.data())

def make():
    t = Mock()
    sdk = StructFrameSdk(StructFrameSdkConfig(transport=t, profile=PROFILE_STANDARD_CONFIG,
                                              get_message_info=get_message_info))
    sdk.register_codec(Heartbeat)      # a generated class is a valid codec
    return t, sdk

# subscribe: handler receives a decoded message
t, sdk = make()
seen = []
sdk.subscribe(Heartbeat.MSG_ID, lambda msg, msg_id: seen.append((msg.id, msg_id)))
t.deliver(Heartbeat(id=23, type=1))
assert seen == [(23, Heartbeat.MSG_ID)], seen

# request: returns the first reply accepted by match, ignoring earlier ones
t, sdk = make()
t.on_reply = lambda: (t.deliver(Heartbeat(id=1, type=1)), t.deliver(Heartbeat(id=2, type=1)))
reply = sdk.request(Pose(pitch=1.0), Heartbeat, match=lambda r: r.id == 2, timeout=1.0)
assert reply.id == 2, reply.id

# request: timeout
t, sdk = make()
try:
    sdk.request(Pose(pitch=1.0), Heartbeat, timeout=0.05)
    raise SystemExit("expected a timeout")
except TimeoutError:
    pass
print("ok")
''', encoding="utf-8")
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                            env=_env(str(out)), timeout=120)
    assert result.returncode == 0 and "ok" in result.stdout, result.stdout + result.stderr
