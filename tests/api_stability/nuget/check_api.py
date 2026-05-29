#!/usr/bin/env python3
from pathlib import Path
baseline = Path(__file__).with_name('PublicAPI.Shipped.txt')
if not baseline.exists():
    print('NuGet API stability scaffold: no PublicAPI.Shipped.txt yet; skipping.')
    raise SystemExit(0)
print('NuGet API stability scaffold: compare current public API to PublicAPI.Shipped.txt here.')
