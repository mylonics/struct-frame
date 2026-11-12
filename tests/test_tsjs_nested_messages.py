#!/usr/bin/env python3
"""TS/JS singular nested message fields are a single message, not a one-element array.

``v.pos`` used to return ``Position[]`` (and ``v.pos.lat = 1`` silently did nothing). It now
returns a view into the parent's buffer, so field writes go through, and the setter and the
constructor take a message or a plain object.

Run with ``pytest tests/test_tsjs_nested_messages.py``.
"""
from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from test_utils import REPO_ROOT, run_generator

SCHEMA = """package nest;
message Position { double lat = 1; double lon = 2; }
message Vehicle {
  option msgid = 3;
  uint32 id = 1;
  Position pos = 2;
  repeated Position history = 3 [max_size=2];
}
"""

BODY = """
const v = new nest.Vehicle({ id: 1, pos: { lat: 1.5, lon: 2.5 } });
const out: string[] = [];
out.push(String(v.pos.lat));
v.pos.lon = 9;                                   // write through the view
out.push(String(nest.Vehicle.deserialize(v.serialize()).pos.lon));
v.pos = new nest.Position({ lat: 3, lon: 4 });   // replace with a message
out.push(String(v.pos.lat));
v.pos = { lat: 5, lon: 6 };                      // or a plain object
out.push(String(v.toObject().pos.lon));
v.historyCount = 1;                              // repeated fields stay arrays
v.historyData = [{ lat: 7, lon: 8 }];
out.push(String(nest.Vehicle.deserialize(v.serialize()).historyData[0].lat));
console.log(out.join(','));
"""

EXPECTED = "1.5,9,3,6,7"


@pytest.fixture()
def schema(tmp_path):
    path = tmp_path / "nest.sf"
    path.write_text(SCHEMA, encoding="utf-8")
    return path


def test_js_singular_nested_message(schema, tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    gen = run_generator(schema, "--build_js", "--js_path", str(tmp_path / "js"))
    assert gen.returncode == 0, gen.stdout + gen.stderr
    js = "const { nest } = require('./js');\n" + BODY.replace(": string[]", "")
    (tmp_path / "t.js").write_text(js, encoding="utf-8")
    r = subprocess.run([node, "t.js"], cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == EXPECTED


def test_ts_singular_nested_message_type_checks(schema, tmp_path):
    tsc = REPO_ROOT / "node_modules" / ".bin" / ("tsc.cmd" if os.name == "nt" else "tsc")
    node = shutil.which("node")
    if not tsc.exists() or node is None:
        pytest.skip("TypeScript toolchain not installed (npm ci)")
    out = tmp_path / "ts"
    gen = run_generator(schema, "--build_ts", "--ts_path", str(out))
    assert gen.returncode == 0, gen.stdout + gen.stderr
    (out / "main.ts").write_text("import { nest } from './index';\n" + BODY, encoding="utf-8")
    build = subprocess.run(
        [str(tsc), "--target", "es2020", "--module", "commonjs", "--strict", "--skipLibCheck",
         "--types", "node", "--typeRoots", str(REPO_ROOT / "node_modules" / "@types"),
         "--outDir", str(out / "dist"), str(out / "main.ts")],
        capture_output=True, text=True, timeout=300)
    assert build.returncode == 0, build.stdout + build.stderr
    r = subprocess.run([node, str(out / "dist" / "main.js")], capture_output=True, text=True,
                       timeout=60)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == EXPECTED
