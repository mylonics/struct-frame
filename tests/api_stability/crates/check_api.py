#!/usr/bin/env python3
from pathlib import Path
baseline = Path(__file__).with_name('public-api.txt')
if not baseline.exists():
    print('crates.io API stability scaffold: no public-api.txt yet; skipping.')
    raise SystemExit(0)
print('crates.io API stability scaffold: compare cargo-public-api output to public-api.txt here.')
