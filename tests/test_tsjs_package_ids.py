#!/usr/bin/env python3
"""TS/JS messages of a package with a package ID frame like every other runtime.

``_msgid`` used to be the local ID, so the TS/JS writers put package byte 0 on the wire
(Python, C, C++ and C# put the package ID) and the TS/JS readers then rejected their own
frames. ``_msgid`` / ``MSG_ID`` are now the package-qualified ID, as ``MSG_ID`` is in the
other languages.

Run with ``pytest tests/test_tsjs_package_ids.py``.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

from test_utils import REPO_ROOT, run_generator

SCHEMA = REPO_ROOT / "tests" / "proto" / "pkg_test_a.sf"

JS = r"""
const fp = require('./js/frame-profiles');
const a = require('./js/pkg-test-a.structframe');
const msg = new a.ActionMessage({ action: 0, targetId: 42 });
const out = { msgId: a.ActionMessage.MSG_ID, legacy: a.ActionMessage._msgid };
const w = new fp.BufferWriter(fp.ProfileBulkConfig, 256);
w.write(msg);
const data = Buffer.from(w.data());
out.frame = data.toString('hex');
const r = new fp.AccumulatingReader(fp.ProfileBulkConfig, a.getMessageInfo);
r.addData(data);
const f = r.next();
out.valid = f.valid;
out.readId = f.msgId;
out.decodedTarget = a.ActionMessage.deserialize(f).targetId;
try {
  new fp.BufferWriter(fp.ProfileStandardConfig, 256).write(msg);
  out.standard = 'written';
} catch (e) {
  out.standard = 'refused';
}
console.log(JSON.stringify(out));
"""

PY = r"""
from structframe import frame_profiles as fp
from structframe.pkg_test_a import ActionMessage
print(fp.encode_message(fp.PROFILE_BULK_CONFIG, ActionMessage(action=0, target_id=42)).hex())
"""


def test_js_package_id_frames_match_python(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed")
    gen = run_generator(SCHEMA, "--build_js", "--js_path", str(tmp_path / "js"),
                        "--build_py", "--py_path", str(tmp_path / "py"))
    assert gen.returncode == 0, gen.stdout + gen.stderr

    (tmp_path / "t.js").write_text(JS, encoding="utf-8")
    js = subprocess.run([node, "t.js"], cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert js.returncode == 0, js.stderr
    import json
    result = json.loads(js.stdout)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path / "py")
    py = subprocess.run([sys.executable, "-c", PY], capture_output=True, text=True, env=env,
                        timeout=60)
    assert py.returncode == 0, py.stderr

    assert result["msgId"] == result["legacy"] == (2 << 8) | 1
    assert result["frame"] == py.stdout.strip(), "JS and Python frame the message differently"
    assert result["valid"] and result["readId"] == 513 and result["decodedTarget"] == 42
    assert result["standard"] == "refused", "package-qualified ID truncated on Standard"


def test_ts_generated_constants(tmp_path):
    gen = run_generator(SCHEMA, "--build_ts", "--ts_path", str(tmp_path / "ts"))
    assert gen.returncode == 0, gen.stdout + gen.stderr
    text = (tmp_path / "ts" / "pkg-test-a.structframe.ts").read_text(encoding="utf-8")
    assert "static readonly MSG_ID: number = 513;" in text
    assert "static readonly _msgid: number = 513;" in text
    assert "static readonly MAX_SIZE: number = 70;" in text
    assert "case 1: return" in text  # lookup switches on the local ID
