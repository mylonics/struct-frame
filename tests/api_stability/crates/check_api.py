#!/usr/bin/env python3
"""Check Rust crate public API stability against a baseline snapshot.

If no baseline exists, the test is skipped. If a baseline exists, the
generated Rust source files are scanned for ``pub`` items and compared
to the baseline.  Removed items cause a failure; new items are reported
as non-breaking additions.
"""
import argparse
from pathlib import Path
import re, sys

ROOT = Path(__file__).resolve().parents[2]  # tests/
GENERATED_DIR = ROOT / 'generated' / 'rust'
BASELINE = Path(__file__).with_name('public-api.txt')

PUB_RE = re.compile(
    r'pub\s+(?:const|static|fn|struct|enum|trait|type|mod)\s+(\w+)'
)

def collect_public_items() -> list[str]:
    items = []
    if not GENERATED_DIR.exists():
        print(f'Generated directory not found: {GENERATED_DIR}', file=sys.stderr)
        sys.exit(1)
    for f in sorted(GENERATED_DIR.glob('*.rs')):
        if f.name == 'lib.rs' or f.suffix == '.rs' and '.structframe.' in f.name:
            for i, line in enumerate(f.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
                m = PUB_RE.match(line.strip())
                if m:
                    items.append(f'{f.name}:{m.group(1)}')
    return sorted(items)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--allow-missing-baseline', action='store_true',
                    help='warn and skip when baseline file is missing')
    ap.add_argument('--update', action='store_true',
                    help='refresh public-api.txt from current generated output')
    args = ap.parse_args()

    current = collect_public_items()

    if args.update:
        BASELINE.write_text('\n'.join(current) + '\n', encoding='utf-8')
        print(f'crates.io API stability: updated baseline {BASELINE} ({len(current)} items).')
        return 0

    if not BASELINE.exists():
        msg = 'crates.io API stability: missing public-api.txt baseline.'
        if args.allow_missing_baseline:
            print(msg + ' (allowed; skipping)')
            return 0
        print(msg, file=sys.stderr)
        print('Create tests/api_stability/crates/public-api.txt or run with --allow-missing-baseline.', file=sys.stderr)
        return 1
    expected = [
        l.strip() for l in BASELINE.read_text().splitlines()
        if l.strip() and not l.startswith('#')
    ]

    removed = [e for e in expected if e not in current]
    added = [c for c in current if c not in expected]

    if removed:
        print('crates.io API stability: BREAKING CHANGES detected:', file=sys.stderr)
        for r in removed:
            print(f'  REMOVED: {r}', file=sys.stderr)
        return 1

    if added:
        print('crates.io API stability: new items added (non-breaking):')
        for a in added:
            print(f'  ADDED: {a}')

    print(f'crates.io API stability: compatible ({len(current)} items checked).')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
