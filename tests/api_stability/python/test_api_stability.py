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


def _split_signature_params(sig: str):
    """Split a signature string into top-level parameter tokens."""
    s = sig.strip()
    if not (s.startswith('(') and s.endswith(')')):
        return []
    body = s[1:-1].strip()
    if not body:
        return []

    parts = []
    buf = []
    depth = 0
    for ch in body:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == ',' and depth == 0:
            token = ''.join(buf).strip()
            if token:
                parts.append(token)
            buf = []
            continue
        buf.append(ch)
    token = ''.join(buf).strip()
    if token:
        parts.append(token)
    return parts


def _extract_param_info(sig: str):
    """Return (all_param_names, required_param_names) for a signature string."""
    all_names = []
    required = []
    for token in _split_signature_params(sig):
        if token in ('/', '*'):
            # Positional-only and keyword-only separators
            continue

        has_default = '=' in token
        left = token.split('=', 1)[0].strip() if has_default else token
        name = left.split(':', 1)[0].strip()
        name = name.lstrip('*')
        if not name:
            continue

        all_names.append(name)

        # *args / **kwargs are not "required parameters" for compatibility checks
        if token.startswith('*'):
            continue
        if not has_default:
            required.append(name)

    return set(all_names), set(required)

def compatible(old_sig, new_sig):
    if old_sig in (None, ''):
        return True
    if new_sig is None:
        return False
    if old_sig == new_sig:
        return True

    old_all, _old_required = _extract_param_info(old_sig)
    new_all, new_required = _extract_param_info(new_sig)

    # Existing parameters must remain available.
    if not old_all.issubset(new_all):
        return False

    # New required parameters are breaking changes.
    added_required = new_required - old_all
    if added_required:
        return False

    # Existing required parameters may become optional without breaking callers.
    return True

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
