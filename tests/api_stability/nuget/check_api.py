#!/usr/bin/env python3
"""Check NuGet package public API stability against a baseline snapshot.

If no baseline exists, the test is skipped. If a baseline exists, the
generated C# source files are scanned for ``public`` declarations and
compared to the baseline.  Removed items cause a failure; new items
are reported as non-breaking additions.
"""
import argparse
from pathlib import Path
import re, sys

ROOT = Path(__file__).resolve().parents[2]  # tests/
GENERATED_DIR = ROOT / 'generated' / 'csharp'
BASELINE = Path(__file__).with_name('PublicAPI.Shipped.txt')

PUB_RE = re.compile(
    r'public\s+(?:const|static|readonly|class|struct|enum|interface|delegate|void|int|uint|long|ulong|float|double|bool|string|byte|var)\s+(\w+)'
)

def collect_public_items() -> list[str]:
    items = []
    if not GENERATED_DIR.exists():
        print(f'Generated directory not found: {GENERATED_DIR}', file=sys.stderr)
        sys.exit(1)
    for f in sorted(GENERATED_DIR.rglob('*.cs')):
        rel = f.relative_to(GENERATED_DIR)
        for line in f.read_text(errors='replace').splitlines():
            m = PUB_RE.match(line.strip())
            if m:
                items.append(f'{rel}:{m.group(1)}')
    return sorted(items)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--allow-missing-baseline', action='store_true',
                    help='warn and skip when baseline file is missing')
    args = ap.parse_args()

    if not BASELINE.exists():
        msg = 'NuGet API stability: missing PublicAPI.Shipped.txt baseline.'
        if args.allow_missing_baseline:
            print(msg + ' (allowed; skipping)')
            return 0
        print(msg, file=sys.stderr)
        print('Create tests/api_stability/nuget/PublicAPI.Shipped.txt or run with --allow-missing-baseline.', file=sys.stderr)
        return 1

    current = collect_public_items()
    expected = [
        l.strip() for l in BASELINE.read_text().splitlines()
        if l.strip() and not l.startswith('#')
    ]

    removed = [e for e in expected if e not in current]
    added = [c for c in current if c not in expected]

    if removed:
        print('NuGet API stability: BREAKING CHANGES detected:', file=sys.stderr)
        for r in removed:
            print(f'  REMOVED: {r}', file=sys.stderr)
        return 1

    if added:
        print('NuGet API stability: new items added (non-breaking):')
        for a in added:
            print(f'  ADDED: {a}')

    print(f'NuGet API stability: compatible ({len(current)} items checked).')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
