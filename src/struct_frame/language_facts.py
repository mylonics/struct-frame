#!/usr/bin/env python3
"""Language facts for the struct-frame schema language: one source of truth.

The compiler (``generate.py``, ``schema_diff.py``) reads its primitive types, option
names, accepted option values and numeric limits from this module. The VS Code
extension in ``editors/vscode`` reads the same facts from a generated JSON file, so
the two can't drift apart:

    python src/struct_frame/language_facts.py --write   # regenerate the JSON
    python src/struct_frame/language_facts.py --check   # CI: fail if it is stale

This module is stdlib-only and imports nothing from the package, so the commands
above work without the compiler's dependencies installed.

When you add or change a language rule here, regenerate the JSON and add the
human-readable hover text for any new name in
``editors/vscode/server/src/docs.ts`` (the extension's tests fail until you do).
"""

import argparse
import json
import sys
from pathlib import Path

# Bump when the JSON layout changes incompatibly; the extension refuses other versions.
SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

# Built-in field types: name -> (kind, wire size in bytes). Strings and bytes are
# sized by their field options ([size=] / [max_size=]), so they have no fixed size.
PRIMITIVES = {
    "uint8": ("int", 1),
    "int8": ("int", 1),
    "uint16": ("int", 2),
    "int16": ("int", 2),
    "uint32": ("int", 4),
    "int32": ("int", 4),
    "bool": ("bool", 1),
    "float": ("float", 4),
    "double": ("float", 8),
    "int64": ("int", 8),
    "uint64": ("int", 8),
    "string": ("string", None),
    "bytes": ("bytes", None),
}

# Inclusive (min, max) value ranges of the integer types (used for [default=N]).
INTEGER_RANGES = {
    "uint8": (0, 0xFF),
    "int8": (-0x80, 0x7F),
    "uint16": (0, 0xFFFF),
    "int16": (-0x8000, 0x7FFF),
    "uint32": (0, 0xFFFFFFFF),
    "int32": (-0x80000000, 0x7FFFFFFF),
    "uint64": (0, 0xFFFFFFFFFFFFFFFF),
    "int64": (-0x8000000000000000, 0x7FFFFFFFFFFFFFFF),
}

# Largest finite float32 (for [default=] on float fields; +/-inf is also accepted).
FLOAT_MAX = 3.4028234663852886e38

# Enums are stored in one unsigned byte on the wire.
ENUM_SIZE = 1
ENUM_VALUE_RANGE = (0, 255)

# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------

# Field options may also be written qualified: [(sf.size) = 8] or [(struct_frame.size) = 8].
OPTION_QUALIFIERS = ("sf", "struct_frame")

# Option names per scope. "value" describes what the option takes:
# int / bool / discriminator / magic_bytes / literal (the field's own type).
FILE_OPTIONS = {
    "pkgid": "int",
}
MESSAGE_OPTIONS = {
    "msgid": "int",
    "variable": "bool",
    "discriminator": "discriminator",
    "is_envelope": "bool",
    "extensions_start": "int",
    "magic_bytes": "magic_bytes",
}
MESSAGE_OPTION_ALIASES = {
    "envelope": "is_envelope",
}
ONEOF_OPTIONS = {
    "discriminator": "discriminator",
    "variable": "bool",
    "max_size": "int",
    "min_size": "int",
    "extensions_start": "int",
}
ENUM_OPTIONS = {
    "extensions_start": "int",
}
FIELD_OPTIONS = {
    "size": "int",
    "max_size": "int",
    "element_size": "int",
    "flatten": "bool",
    "default": "literal",
}

# How a oneof's active variant is identified on the wire.
DISCRIMINATOR_MODES = ("auto", "msgid", "field_order", "none")
DISCRIMINATOR_ALIASES = {"false": "none", "off": "none", "disabled": "none"}

# Bool-valued options are true for these spellings (case-insensitive) and false otherwise.
TRUE_VALUES = ("true", "1", "yes", "on")
# Spellings the editor accepts silently as false; anything else gets a warning there.
FALSE_VALUES = ("false", "0", "no", "off")

# ---------------------------------------------------------------------------
# Limits (all inclusive)
# ---------------------------------------------------------------------------

MSGID_RANGE = (0, 65535)              # package without `option pkgid`
MSGID_RANGE_WITH_PKGID = (0, 255)     # package with `option pkgid` (id = pkgid << 8 | msgid)
PKGID_RANGE = (0, 255)
SIZE_OPTION_RANGE = (1, 65535)        # [size=], [max_size=], [element_size=]
ONE_BYTE_PREFIX_MAX = 255             # max_size above this uses a 2-byte length/count prefix
EXTENSIONS_START_MIN = 2              # at least one base field/variant is required
MAGIC_BYTES_COUNT = 2
MAGIC_BYTE_RANGE = (1, 255)           # each override byte must be non-zero
ONEOF_SIZE_MIN = 1                    # oneof max_size / min_size must be positive

# ---------------------------------------------------------------------------
# Helpers shared by the compiler
# ---------------------------------------------------------------------------


def option_value_text(value):
    """Lower-cased text of a parsed option value.

    proto_schema_parser hands over bools, ints, strings or Identifier objects (for
    unquoted words such as ``yes``); quotes are stripped.
    """
    if value is True:
        return "true"
    if value is False:
        return "false"
    if hasattr(value, "name"):
        value = value.name
    return str(value).strip().strip("\"'").strip().lower()


def is_true(value):
    """True when a bool-valued option value spells true (see TRUE_VALUES)."""
    return option_value_text(value) in TRUE_VALUES


def normalize_discriminator(value):
    """Canonical discriminator mode for an option value, or None if it is not valid."""
    text = option_value_text(value)
    text = DISCRIMINATOR_ALIASES.get(text, text)
    return text if text in DISCRIMINATOR_MODES else None


def option_base_name(name):
    """Strip an optional ``(sf.X)`` / ``(struct_frame.X)`` qualifier from an option name."""
    name = str(name).strip()
    for qualifier in OPTION_QUALIFIERS:
        prefix = "(" + qualifier + "."
        if name.startswith(prefix) and name.endswith(")"):
            return name[len(prefix):-1]
    return name


# ---------------------------------------------------------------------------
# JSON export for the editor extension
# ---------------------------------------------------------------------------

DEFAULT_JSON_PATH = (Path(__file__).resolve().parents[2]
                     / "editors" / "vscode" / "server" / "src" / "facts" / "language-facts.json")


def _range(pair):
    # Integers go out as strings: 64-bit bounds are not exact as JavaScript numbers.
    return {"min": str(pair[0]), "max": str(pair[1])}


def to_json():
    """The language facts as a JSON-ready dict (no version or path: the output must
    only change when the language does)."""
    return {
        "_generated": "Generated by src/struct_frame/language_facts.py. Do not edit; "
                      "run: python src/struct_frame/language_facts.py --write",
        "schema_version": SCHEMA_VERSION,
        "primitives": [
            {"name": name, "kind": kind, "size": size}
            for name, (kind, size) in PRIMITIVES.items()
        ],
        "integer_ranges": {name: _range(r) for name, r in INTEGER_RANGES.items()},
        "float_max": FLOAT_MAX,
        "enum": {"size": ENUM_SIZE, "value_range": _range(ENUM_VALUE_RANGE)},
        "option_qualifiers": list(OPTION_QUALIFIERS),
        "options": {
            "file": FILE_OPTIONS,
            "message": MESSAGE_OPTIONS,
            "oneof": ONEOF_OPTIONS,
            "enum": ENUM_OPTIONS,
            "field": FIELD_OPTIONS,
        },
        "option_aliases": {"message": MESSAGE_OPTION_ALIASES},
        "discriminator": {"modes": list(DISCRIMINATOR_MODES), "aliases": DISCRIMINATOR_ALIASES},
        "true_values": list(TRUE_VALUES),
        "false_values": list(FALSE_VALUES),
        "limits": {
            "msgid": _range(MSGID_RANGE),
            "msgid_with_pkgid": _range(MSGID_RANGE_WITH_PKGID),
            "pkgid": _range(PKGID_RANGE),
            "size_option": _range(SIZE_OPTION_RANGE),
            "one_byte_prefix_max": str(ONE_BYTE_PREFIX_MAX),
            "extensions_start_min": str(EXTENSIONS_START_MIN),
            "magic_bytes_count": str(MAGIC_BYTES_COUNT),
            "magic_byte": _range(MAGIC_BYTE_RANGE),
            "oneof_size_min": str(ONEOF_SIZE_MIN),
        },
    }


def render():
    """Deterministic JSON text (LF line endings, trailing newline)."""
    return json.dumps(to_json(), indent=2, sort_keys=True) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Export struct-frame language facts for the editor extension.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write the JSON file")
    mode.add_argument("--check", action="store_true",
                      help="exit 1 if the JSON file is missing or out of date")
    mode.add_argument("--stdout", action="store_true", help="print the JSON")
    ap.add_argument("path", nargs="?", type=Path, default=DEFAULT_JSON_PATH,
                    help=f"JSON file (default: {DEFAULT_JSON_PATH})")
    args = ap.parse_args(argv)

    text = render()
    if args.stdout:
        sys.stdout.write(text)
        return 0

    path = args.path
    if not path.parent.is_dir():
        print(f"error: {path.parent} does not exist (run this from a struct-frame checkout)",
              file=sys.stderr)
        return 2

    if args.check:
        current = path.read_text(encoding="utf-8").replace("\r\n", "\n") if path.exists() else None
        if current != text:
            print(f"error: {path} is out of date with src/struct_frame/language_facts.py.\n"
                  f"Run: python src/struct_frame/language_facts.py --write", file=sys.stderr)
            return 1
        print(f"{path.name} is up to date")
        return 0

    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
