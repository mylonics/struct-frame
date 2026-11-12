#!/usr/bin/env python3
"""Generated ``decode_message`` / ``decodeMessage`` dispatchers and the TS/JS barrels.

* Python ``decode_message(frame)`` and TS/JS ``decodeMessage(frame)`` return the typed message
  for a frame's ID, or None/undefined for invalid frames and other packages' IDs.
* ``index.ts`` / ``index.js`` export the runtime plus one namespace per generated package.
  They used to be overwritten by the runtime's own barrel, which exported no generated code.

Run with ``pytest tests/test_decode_helpers.py``.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

from test_utils import REPO_ROOT, run_generator

MAIN_SF = """package two;
option pkgid = 3;
import "one.sf";
message T { option msgid = 1; uint8 v = 1; }
"""

ONE_SF = """package one;
option pkgid = 4;
message A { option msgid = 1; uint32 target = 1; }
message B { option msgid = 2; option variable = true; string s = 1 [max_size=8]; }
"""


@pytest.fixture()
def schemas(tmp_path):
    (tmp_path / "two.sf").write_text(MAIN_SF, encoding="utf-8")
    (tmp_path / "one.sf").write_text(ONE_SF, encoding="utf-8")
    return tmp_path


PY = r"""
from structframe import frame_profiles as fp
from structframe import one, two
w = fp.BufferWriter(fp.PROFILE_BULK_CONFIG, 256)
w.write(two.T(v=7)); w.write(one.A(target=42)); w.write(one.B(s=b"hi"))
lookup = lambda i: two.get_message_info(i) or one.get_message_info(i)
r = fp.AccumulatingReader(fp.PROFILE_BULK_CONFIG, get_message_info=lookup)
r.add_data(w.data())
out = []
while (f := r.try_next()) is not None:
    m = two.decode_message(f) or one.decode_message(f)
    out.append(type(m).__name__)
    assert two.decode_message(f) is None or one.decode_message(f) is None
print(",".join(out))
"""


def test_python_decode_message(schemas):
    gen = run_generator(schemas / "two.sf", "--build_py", "--py_path", str(schemas / "py"))
    assert gen.returncode == 0, gen.stdout + gen.stderr
    env = os.environ.copy()
    env["PYTHONPATH"] = str(schemas / "py")
    r = subprocess.run([sys.executable, "-c", PY], capture_output=True, text=True, env=env,
                       timeout=60)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "T,A,B"


JS = r"""
const sf = require('./js');
const w = new sf.BufferWriter(sf.ProfileBulkConfig, 256);
w.write(new sf.two.T({ v: 7 }));
w.write(new sf.one.A({ target: 42 }));
const lookup = (id) => sf.two.getMessageInfo(id) ?? sf.one.getMessageInfo(id);
const r = new sf.AccumulatingReader(sf.ProfileBulkConfig, lookup);
r.addData(Buffer.from(w.data()));
const out = [];
let f;
while ((f = r.next()) && f.valid) {
  const m = sf.two.decodeMessage(f) ?? sf.one.decodeMessage(f);
  if (m instanceof sf.two.T) out.push('T' + m.v);
  else if (m instanceof sf.one.A) out.push('A' + m.target);
}
console.log(out.join(','));
"""


def test_js_barrel_and_decode_message(schemas):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    gen = run_generator(schemas / "two.sf", "--build_js", "--js_path", str(schemas / "js"))
    assert gen.returncode == 0, gen.stdout + gen.stderr
    (schemas / "t.js").write_text(JS, encoding="utf-8")
    r = subprocess.run([node, "t.js"], cwd=schemas, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "T7,A42"


TS = r"""
import { one, two, BufferWriter, AccumulatingReader, ProfileBulkConfig } from './index';
const w = new BufferWriter(ProfileBulkConfig, 256);
w.write(new two.T({ v: 7 }));
w.write(new one.A({ target: 42 }));
const r = new AccumulatingReader(ProfileBulkConfig, (id: number) => two.getMessageInfo(id) ?? one.getMessageInfo(id));
r.addData(Buffer.from(w.data()));
const out: string[] = [];
let f;
while ((f = r.next()) && f.valid) {
  const m = two.decodeMessage(f) ?? one.decodeMessage(f);
  if (m instanceof two.T) out.push('T' + m.v);
  else if (m instanceof one.A) out.push('A' + m.target);
}
console.log(out.join(','));
"""


def test_ts_barrel_and_decode_message_compile_strict(schemas):
    tsc = REPO_ROOT / "node_modules" / ".bin" / ("tsc.cmd" if os.name == "nt" else "tsc")
    node = shutil.which("node")
    if not tsc.exists() or node is None:
        pytest.skip("TypeScript toolchain not installed (npm ci)")
    out = schemas / "ts"
    gen = run_generator(schemas / "two.sf", "--build_ts", "--ts_path", str(out))
    assert gen.returncode == 0, gen.stdout + gen.stderr
    (out / "main.ts").write_text(TS, encoding="utf-8")
    build = subprocess.run(
        [str(tsc), "--target", "es2020", "--module", "commonjs", "--esModuleInterop", "--strict",
         "--skipLibCheck", "--types", "node", "--typeRoots", str(REPO_ROOT / "node_modules" / "@types"),
         "--outDir", str(out / "dist"), str(out / "main.ts")],
        capture_output=True, text=True, timeout=300)
    assert build.returncode == 0, build.stdout + build.stderr
    r = subprocess.run([node, str(out / "dist" / "main.js")], capture_output=True, text=True,
                       timeout=60)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "T7,A42"
