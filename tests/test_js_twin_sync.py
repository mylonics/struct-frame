#!/usr/bin/env python3
"""The JavaScript runtime in boilerplate/js is compiled from the TypeScript in boilerplate/ts.

Several other tests (the stream driver, the transport tests) run the compiled JavaScript on the
grounds that it is the TypeScript runtime. That only holds while the checked-in JavaScript matches
what ``tsc -p boilerplate/ts/tsconfig.cjs.json`` produces, so this test recompiles and compares.
After changing a .ts file, regenerate with that command and commit the JavaScript.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TS_DIR = REPO / "src" / "struct_frame" / "boilerplate" / "ts"
JS_DIR = REPO / "src" / "struct_frame" / "boilerplate" / "js"


def _tsc():
    local = REPO / "tests" / "ts" / "node_modules" / ".bin" / ("tsc.cmd" if os.name == "nt" else "tsc")
    if local.exists():
        return [str(local)]
    return None


def _norm(text: str) -> str:
    return text.replace("\r\n", "\n")


def test_checked_in_js_matches_tsc_output(tmp_path):
    tsc = _tsc()
    if tsc is None:
        if "ts" in os.environ.get("SF_REQUIRE_LANGS", "").split(","):
            pytest.fail("tsc required but tests/ts/node_modules is not installed")
        pytest.skip("tsc not installed (run npm ci in tests/ts)")
    out = tmp_path / "js"
    # noEmitOnError is false in the config, so type errors about optional packages
    # (serialport) do not stop the emit; only the emitted files are compared.
    subprocess.run(tsc + ["-p", str(TS_DIR / "tsconfig.cjs.json"), "--outDir", str(out)],
                   capture_output=True, text=True, timeout=300)
    produced = sorted(p.relative_to(out) for p in out.rglob("*.js"))
    assert produced, "tsc produced no output"
    stale = []
    for rel in produced:
        checked_in = JS_DIR / rel
        if not checked_in.exists() or _norm(checked_in.read_text(encoding="utf-8")) != _norm((out / rel).read_text(encoding="utf-8")):
            stale.append(str(rel))
    assert not stale, (
        "boilerplate/js is out of date for: " + ", ".join(stale) +
        "\nRegenerate: tests/ts/node_modules/.bin/tsc -p src/struct_frame/boilerplate/ts/tsconfig.cjs.json")
