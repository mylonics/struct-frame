#!/usr/bin/env python3
"""Shared test utilities for struct-frame test suite."""

from __future__ import annotations
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
PROTO_FILE = REPO_ROOT / "tests" / "proto" / "test_messages.sf"


def _check(condition: bool, msg: str) -> None:
    """Assert *condition* is truthy; print a FAIL message and exit if not."""
    if not condition:
        print(f"FAIL: {msg}", file=sys.stderr)
        sys.exit(1)


def run_generator(proto: Path, *flags: str) -> subprocess.CompletedProcess:
    """Run the struct-frame generator with PYTHONPATH injected."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, str(SRC_DIR / "main.py"), str(proto)] + list(flags)
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def load_generated_module(pyfile: Path, name: str):
    """Import a generated Python module by file path."""
    spec = importlib.util.spec_from_file_location(name, pyfile)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
