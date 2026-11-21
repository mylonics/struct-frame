"""``struct-frame migrate`` and ``struct-frame fmt``.

``migrate`` converts schemas from the old proto-style syntax to the struct-frame language;
``fmt`` reprints schemas in canonical form. Both keep every comment.
"""

import argparse
import os
import re
import sys

EXIT_OK = 0
EXIT_CHANGES = 1
EXIT_ERROR = 2


def _read(path):
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as f:
        return f.read()


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _out_path(path, out_dir):
    name = os.path.basename(path)
    if name.endswith(".proto"):
        name = name[:-len(".proto")] + ".sf"
    return os.path.join(out_dir, name) if out_dir else path


_IMPORT_RE = re.compile(r'^\s*import\s+(?:public\s+|weak\s+)?"([^"]+)"\s*;', re.M)


def _imports(text, path):
    base = os.path.dirname(os.path.abspath(path))
    for name in _IMPORT_RE.findall(text):
        candidate = os.path.join(base, name)
        if os.path.exists(candidate):
            yield candidate


def build_migrate_parser():
    ap = argparse.ArgumentParser(
        prog="struct-frame migrate",
        description="Convert schemas from the old proto-style syntax (option msgid, repeated, "
                    "field numbers, [size=...]) to the struct-frame language. Comments that "
                    "documented a declaration become /// doc comments; all others are kept as "
                    "// comments.")
    ap.add_argument("files", nargs="+", metavar="FILE", help="schema files ('-' reads stdin)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("-i", "--in-place", action="store_true", help="rewrite the files")
    mode.add_argument("-o", "--out-dir", metavar="DIR", help="write converted files to DIR")
    mode.add_argument("--check", action="store_true",
                      help="exit 1 if any file still uses the old syntax; write nothing")
    ap.add_argument("-r", "--recursive", action="store_true",
                    help="also convert the files they import")
    ap.add_argument("--types", choices=("preserve", "long", "short"), default="preserve",
                    help="spelling of primitive types: as written (default), long (uint8) "
                         "or short (u8)")
    ap.add_argument("-q", "--quiet", action="store_true", help="do not print warnings")
    return ap


def build_fmt_parser():
    ap = argparse.ArgumentParser(
        prog="struct-frame fmt",
        description="Reprint struct-frame schemas in canonical form (comments are kept).")
    ap.add_argument("files", nargs="+", metavar="FILE", help="schema files ('-' reads stdin)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("-i", "--in-place", action="store_true", help="rewrite the files")
    mode.add_argument("--check", action="store_true",
                      help="exit 1 if any file is not formatted; write nothing")
    ap.add_argument("--types", choices=("preserve", "long", "short"), default="preserve",
                    help="spelling of primitive types: as written (default), long (uint8) "
                         "or short (u8)")
    return ap


def migrate_main(argv=None, out=None, err=None):
    out = out or sys.stdout
    err = err or sys.stderr
    args = build_migrate_parser().parse_args(argv)

    from struct_frame.generate import looks_like_legacy_syntax
    from . import legacy_proto
    from .parser import parse_text

    queue = list(args.files)
    seen = set()
    status = EXIT_OK
    if len(queue) > 1 and not (args.in_place or args.out_dir or args.check):
        print("struct-frame migrate: several files need --in-place, --out-dir or --check",
              file=err)
        return EXIT_ERROR
    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)

    while queue:
        path = queue.pop(0)
        key = path if path == "-" else os.path.abspath(path)
        if key in seen:
            continue
        seen.add(key)
        try:
            text = _read(path)
        except OSError as exc:
            print(f"struct-frame migrate: {exc}", file=err)
            return EXIT_ERROR
        if args.recursive and path != "-":
            queue.extend(_imports(text, path))
        if not looks_like_legacy_syntax(text):
            if args.check:
                continue
            if not args.in_place and not args.out_dir:
                out.write(text)
            elif args.out_dir:
                _write(_out_path(path, args.out_dir), text)
            if not args.quiet:
                print(f"{path}: already in the struct-frame language", file=err)
            continue
        if args.check:
            print(f"{path}: uses the old syntax", file=out)
            status = EXIT_CHANGES
            continue
        try:
            new_text, warnings = legacy_proto.migrate_text(text, path, types=args.types)
        except legacy_proto.MigrationError as exc:
            print(f"struct-frame migrate: {exc}", file=err)
            status = EXIT_ERROR
            continue
        if not args.quiet:
            for w in warnings:
                print(w, file=err)
        _tree, sink = parse_text(new_text, path)
        if sink.errors:
            print(f"struct-frame migrate: internal error: the converted {path} does not parse:",
                  file=err)
            for d in sink.errors:
                print(d.render(), file=err)
            status = EXIT_ERROR
            continue
        if args.in_place:
            target = _out_path(path, None)
            _write(target, new_text)
            if target != path and path.endswith(".proto") and not args.quiet:
                print(f"wrote {target}", file=err)
        elif args.out_dir:
            _write(_out_path(path, args.out_dir), new_text)
        else:
            out.write(new_text)
    return status


def fmt_main(argv=None, out=None, err=None):
    out = out or sys.stdout
    err = err or sys.stderr
    args = build_fmt_parser().parse_args(argv)

    from .parser import parse_text
    from .printer import print_file

    if len(args.files) > 1 and not (args.in_place or args.check):
        print("struct-frame fmt: several files need --in-place or --check", file=err)
        return EXIT_ERROR
    status = EXIT_OK
    for path in args.files:
        try:
            text = _read(path)
        except OSError as exc:
            print(f"struct-frame fmt: {exc}", file=err)
            return EXIT_ERROR
        tree, sink = parse_text(text, path)
        if sink.errors:
            for d in sink.diagnostics:
                print(d.render(), file=err)
            status = EXIT_ERROR
            continue
        new_text = print_file(tree, types=args.types)
        if args.check:
            if new_text != text.replace("\r\n", "\n"):
                print(f"{path}: not formatted", file=out)
                status = max(status, EXIT_CHANGES)
        elif args.in_place:
            if new_text != text:
                _write(path, new_text)
        else:
            out.write(new_text)
    return status
