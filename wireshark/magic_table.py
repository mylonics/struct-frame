#!/usr/bin/env python3
"""Print the Wireshark "Magic bytes" preference value for a struct-frame schema.

The struct-frame checksum is Fletcher-16 over the frame *plus two schema-derived
magic bytes*, so the dissector can only verify a frame when it knows the magic
bytes of that message. Paste the output of this script into
Edit > Preferences > Protocols > STRUCT_FRAME > "Magic bytes".

    python wireshark/magic_table.py path/to/messages.sf
    # 0:1=27,55;0:2=17,19

Entries are ``<package id>:<message id>=<magic1>,<magic2>``; the package id is 0
for packages that do not use one. Messages with extension fields use an
extension-aware checksum that this simple form cannot express, so the dissector
reports those frames as unverified when they carry extension bytes.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import os
import sys

REPO_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")


def magic_entries(schema_path: str) -> list[tuple[int, int, int, int]]:
    """Return ``(package id, message id, magic1, magic2)`` for every message."""
    if os.path.isdir(REPO_SRC):
        sys.path.insert(0, REPO_SRC)
    from struct_frame import generate as gen

    log = io.StringIO()
    with contextlib.redirect_stdout(log):
        ok = gen.parseFile(schema_path) and gen.validate_packages()
    if not ok:
        raise SystemExit(f"{schema_path}: schema is not valid\n{log.getvalue().strip()}")

    entries = []
    for package in gen.packages.values():
        pkg_id = package.package_id if package.package_id is not None else 0
        for message in package.messages.values():
            if message.id is None or not message.magic_bytes:
                continue
            entries.append((pkg_id, message.id, message.magic_bytes[0], message.magic_bytes[1]))
    return sorted(entries)


def format_table(entries) -> str:
    return ";".join(f"{pkg}:{msg}={m1},{m2}" for pkg, msg, m1, m2 in entries)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("schema", help="struct-frame .sf schema")
    args = parser.parse_args(argv)
    print(format_table(magic_entries(args.schema)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
