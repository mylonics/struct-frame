#!/usr/bin/env python3
import argparse, importlib, inspect, json, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = Path(__file__).with_name('snapshot.json')
MODULES = ['struct_frame']

def public_names(module):
    names = getattr(module, '__all__', None)
    if names is None:
        names = [n for n in dir(module) if not n.startswith('_')]
    return sorted(set(names))

def signature(obj):
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return None

def capture():
    if str(ROOT/'src') not in sys.path:
        sys.path.insert(0, str(ROOT/'src'))
    snap = {}
    for modname in MODULES:
        mod = importlib.import_module(modname)
        entries = []
        for name in public_names(mod):
            obj = getattr(mod, name)
            entries.append({'name': name, 'kind': type(obj).__name__, 'signature': signature(obj)})
        snap[modname] = entries
    return snap

def compatible(old_sig, new_sig):
    if old_sig in (None, ''):
        return True
    if new_sig is None:
        return False
    if old_sig == new_sig:
        return True
    # Conservative compatibility: existing required parameter names must remain present.
    old = [p.strip().split('=')[0].split(':')[0].lstrip('*') for p in old_sig.strip('()').split(',') if p.strip()]
    return all(p in new_sig for p in old)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--update', action='store_true'); args = ap.parse_args()
    current = capture()
    if args.update:
        SNAPSHOT.write_text(json.dumps(current, indent=2, sort_keys=True) + '\n')
        print(f'Updated {SNAPSHOT}')
        return 0
    expected = json.loads(SNAPSHOT.read_text())
    failures = []
    for modname, entries in expected.items():
        now = {e['name']: e for e in current.get(modname, [])}
        for old in entries:
            cur = now.get(old['name'])
            if cur is None:
                failures.append(f'{modname}.{old["name"]}: removed')
            elif not compatible(old.get('signature'), cur.get('signature')):
                failures.append(f'{modname}.{old["name"]}: signature changed {old.get("signature")} -> {cur.get("signature")}')
    if failures:
        print('\n'.join(failures), file=sys.stderr)
        return 1
    print('Python public API is compatible with snapshot.')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
