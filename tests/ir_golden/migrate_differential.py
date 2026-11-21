"""Differential check of ``struct-frame migrate``: a migrated schema must build exactly
the model (and generated output) the old front end built from the original.

For every golden schema, its directory is copied to a temporary location, every legacy
``.sf`` file in it is migrated in place, and the oracle data of the migrated entry schema
is compared with the golden recorded from the original::

    python tests/ir_golden/migrate_differential.py [SCHEMA ...] [--show]
"""

import argparse
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ir_oracle  # noqa: E402
from struct_frame import generate as gen  # noqa: E402
from struct_frame.schema import legacy_proto  # noqa: E402


def migrate_dir(src_dir, dst_dir):
    shutil.copytree(src_dir, dst_dir)
    warnings = []
    for dirpath, _dirs, files in os.walk(dst_dir):
        for name in files:
            if not name.endswith(".sf"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            if not gen.looks_like_legacy_syntax(text):
                continue
            try:
                new_text, warns = legacy_proto.migrate_text(text, path)
            except legacy_proto.MigrationError as exc:
                warnings.append(f"MIGRATION FAILED {name}: {exc}")
                continue
            warnings.extend(warns)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(new_text)
    return warnings


def _diff(a, b, path="", out=None, limit=20):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}/{k}: only in migrated")
            elif k not in b:
                out.append(f"{path}/{k}: only in golden")
            else:
                _diff(a[k], b[k], f"{path}/{k}", out, limit)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            _diff(x, y, f"{path}[{i}]", out, limit)
    elif a != b:
        out.append(f"{path}: golden={json.dumps(b)[:200]} migrated={json.dumps(a)[:200]}")
    return out


def check(schema, show=False):
    golden = ir_oracle.load_golden(schema)
    src = os.path.join(ir_oracle.REPO, schema)
    with tempfile.TemporaryDirectory(prefix="sf_migrate_") as tmp:
        dst_dir = os.path.join(tmp, "schemas")
        warnings = migrate_dir(os.path.dirname(src), dst_dir)
        entry = os.path.join(dst_dir, os.path.basename(src))
        if show:
            print(open(entry, encoding="utf-8").read())
        try:
            actual = json.loads(json.dumps(ir_oracle.compute(schema, entry)))
        except RuntimeError as exc:
            return [f"generation failed: {exc}"], warnings
    problems = []
    for key in ("ir", "outputs", "outputs_no_packed"):
        problems += _diff(actual[key], golden[key], key)
    return problems, warnings


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("schemas", nargs="*")
    ap.add_argument("--show", action="store_true", help="print the migrated entry schema")
    ap.add_argument("-w", "--warnings", action="store_true", help="print migration warnings")
    args = ap.parse_args(argv)
    failed = 0
    for schema in args.schemas or ir_oracle.SCHEMAS:
        problems, warnings = check(schema, args.show)
        status = "ok     " if not problems else "DIFF   "
        print(f"{status} {schema}")
        if args.warnings:
            for w in warnings:
                print(f"    {w}")
        for p in problems:
            print(f"    {p}")
        failed += bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
