#!/usr/bin/env python3
# kate: replace-tabs on; indent-width 4;


import io
import os
import re
import shutil
import hashlib
import json
import struct
import time
import contextlib
import keyword
from struct_frame import FileCGen
from struct_frame import FileTsGen, TestTsGen
from struct_frame import FileJsGen, TestJsGen
from struct_frame import FilePyGen
from struct_frame import FileGqlGen
from struct_frame import FileCppGen
from struct_frame import FileCSharpGen
from struct_frame import FileRustGen, TestRustGen
from struct_frame import TestCppGen
from struct_frame import TestPyGen
from struct_frame import TestCGen
from struct_frame import TestCSharpGen
from struct_frame import pascal_case
from struct_frame import camel_to_snake_case
from struct_frame.naming import NameOverrides, NameOverrideError, validate_generated_names
from struct_frame import language_facts as facts
from struct_frame.language_facts import INTEGER_RANGES
from proto_schema_parser.parser import Parser
from proto_schema_parser import ast
from proto_schema_parser.ast import FieldCardinality
from proto_schema_parser import parser as _psp_parser

import argparse
import sys

current_error_field = ""
current_error_message = ""

# Built-in types (from language_facts.PRIMITIVES). string/bytes have no fixed size; the
# 4 here is a placeholder that Field.validate replaces with the [size]/[max_size] size.
default_types = {
    name: {"size": size if size is not None else 4}
    for name, (_kind, size) in facts.PRIMITIVES.items()
}

# Type codes for magic number calculation
type_codes = {
    "uint8": 1,
    "int8": 2,
    "uint16": 3,
    "int16": 4,
    "uint32": 5,
    "int32": 6,
    "bool": 7,
    "float": 8,
    "double": 9,
    "int64": 10,
    "uint64": 11,
    "string": 12,
    "bytes": 14,  # Raw byte array (distinct from string for magic number purposes)
    "enum": 13,  # Fixed code for all enum types (name-independent)
}

# Little-endian struct.pack() format codes per scalar wire type, used to encode
# [default = ...] literals into the wire-format byte pattern (see
# Message.default_bytes / _field_default_bytes below). Enum fields are always
# packed as a single byte ("B"), matching Enum.size (== 1) everywhere else.
wire_struct_format = {
    "uint8": "B",
    "int8": "b",
    "uint16": "H",
    "int16": "h",
    "uint32": "I",
    "int32": "i",
    "uint64": "Q",
    "int64": "q",
    "bool": "B",
    "float": "f",
    "double": "d",
}

# INTEGER_RANGES (imported from language_facts above): inclusive (min, max) value
# ranges for integer field types, used to validate [default = N] literals.


def calculate_magic_numbers(message):
    """
    Calculate two magic number bytes for a message based on field types and positions.
    This ensures the checksum starts with non-zero values unique to each message structure.

    The magic numbers are calculated using a Fletcher-like algorithm over:
    - Field type codes (not field names)
    - Field positions
    - Field sizes

    Extension fields (Message.extensions_start, set by `option extensions_start = N;`)
    are excluded from the magic number computation: extending the message by appending
    new fields past `extensions_start` does not change the magic, so older parsers can
    still validate the base portion. Extension bytes are mixed into the runtime CRC
    *after* the magic, so the extension data is still covered by the checksum.

    Returns: tuple (byte1, byte2)
    """
    magic1 = 0
    magic2 = 0

    position = 0
    for field_name, field in message.fields.items():
        if getattr(field, 'is_extension', False):
            continue
        # Get type code
        if field.field_type in type_codes:
            type_code = type_codes[field.field_type]
        elif getattr(field, 'is_enum', False):
            # All enum types share the same type code regardless of name:
            # renaming an enum or moving it inline doesn't change the wire layout.
            type_code = type_codes["enum"]
        else:
            # For nested message types, use a hash of the type name so that
            # different message types still get different codes.
            type_code = sum(ord(c) for c in field.field_type) % 256

        # Incorporate type code, position, and size into magic numbers
        # Use Fletcher-like algorithm but ensure non-zero result
        magic1 = (magic1 + type_code + position + 1) & 0xFF
        magic2 = (magic2 + magic1) & 0xFF

        position += 1

    # Handle oneofs — extension fields inside a oneof are excluded from the
    # magic computation just like top-level extension fields, so adding oneof
    # extension variants doesn't change the magic bytes that older parsers see.
    for oneof_name, oneof in message.oneofs.items():
        for field_name, field in oneof.fields.items():
            if getattr(field, 'is_extension', False):
                continue
            if field.field_type in type_codes:
                type_code = type_codes[field.field_type]
            elif getattr(field, 'is_enum', False):
                type_code = type_codes["enum"]
            else:
                type_code = sum(ord(c) for c in field.field_type) % 256

            magic1 = (magic1 + type_code + position + 1) & 0xFF
            magic2 = (magic2 + magic1) & 0xFF

            position += 1

    # Ensure magic numbers are non-zero
    # If they are zero, use a default non-zero value
    if magic1 == 0:
        magic1 = 0x5A  # Default non-zero magic byte
    if magic2 == 0:
        magic2 = 0xA5  # Default non-zero magic byte

    return (magic1, magic2)


def _coerce_scalar_default(field_type, raw_value):
    """Validate/coerce a parsed [default = ...] literal against a scalar field_type.

    `raw_value` is whatever proto_schema_parser produced for the option value:
    a Python bool, int, float, or str (compact-option values are never
    Identifier instances -- see Field.parse). Returns (True, coerced_value) on
    success, or (False, error_message) on failure. Does not handle enum types;
    callers check `field.is_enum` separately.
    """
    if field_type == "bool":
        if not isinstance(raw_value, bool):
            return False, f"default value must be a bool literal (true/false), got {raw_value!r}"
        return True, raw_value

    if field_type in INTEGER_RANGES:
        # bool is a subclass of int in Python -- must reject it explicitly.
        if isinstance(raw_value, bool) or not isinstance(raw_value, int):
            return False, f"default value must be an integer literal for type {field_type}, got {raw_value!r}"
        lo, hi = INTEGER_RANGES[field_type]
        if raw_value < lo or raw_value > hi:
            return False, f"default value {raw_value} out of range for {field_type} ({lo}..{hi})"
        return True, raw_value

    if field_type in ("float", "double"):
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            return False, f"default value must be a numeric literal for type {field_type}, got {raw_value!r}"
        value = float(raw_value)
        if field_type == "float" and abs(value) > facts.FLOAT_MAX \
                and value != float("inf") and value != float("-inf"):
            return False, (f"default value {raw_value} out of range for float "
                           f"(max {facts.FLOAT_MAX!r})")
        return True, value

    if field_type in ("string", "bytes"):
        # proto_schema_parser's compact-option value coercion is lossy for
        # quoted literals that look like a bool/int/float (e.g. default =
        # "1000" and default = 1000 are indistinguishable after parsing --
        # both arrive as Python int(1000)). Reconstruct canonical text rather
        # than rejecting: bools become lowercase true/false, everything else
        # goes through str(). This is an accepted, documented limitation of
        # reusing the third-party parser's compact-option grammar rather than
        # writing a custom one.
        if isinstance(raw_value, bool):
            return True, ("true" if raw_value else "false")
        return True, str(raw_value)

    return False, f"default values are not supported for field type {field_type}"


def _field_default_bytes(field):
    """Return the little-endian wire-format bytes for `field` when unset.

    This is the schema default's byte pattern if one was declared, otherwise
    exactly `field.size` zero bytes -- i.e. byte-identical to today's
    (pre-default-values) zero-fill for any field without a [default=...].
    """
    if field.is_array:
        return b"\x00" * field.size

    if field.default is not None:
        if field.is_enum:
            return struct.pack("<B", field.default_numeric)

        if field.field_type in ("string", "bytes"):
            text_bytes = field.default.encode("utf-8")
            if field.size_option is not None:
                return text_bytes.ljust(field.size_option, b"\x00")[:field.size_option]
            else:
                count_fmt = "<H" if _prefix_bytes(field.max_size) == 2 else "<B"
                payload = text_bytes.ljust(field.max_size, b"\x00")
                return struct.pack(count_fmt, len(text_bytes)) + payload

        fmt = wire_struct_format[field.field_type]
        return struct.pack("<" + fmt, field.default)

    if not field.is_default_type and not field.is_enum:
        # Message-typed field with no default of its own (defaults are
        # rejected on message-typed fields -- see Field.validate) recursively
        # uses the nested message's own default_bytes so that a nested type's
        # internal schema defaults still apply through the parent field.
        nested = field.type_ref
        if nested is not None and getattr(nested, "default_bytes", b""):
            return nested.default_bytes

    return b"\x00" * field.size


def _compute_message_default_bytes(msg):
    """Concatenate the default-initialized wire bytes for every field/oneof in
    `msg`, in wire order (fields, then oneofs) -- see Message.default_bytes.
    """
    parts = []
    for field in msg.fields.values():
        parts.append(_field_default_bytes(field))

    for oneof in msg.oneofs.values():
        # Defaults are rejected on oneof member fields (see OneOf.validate), so
        # an unset oneof is always all-zero: this is identical to today's
        # "no variant selected" wire representation.
        length_prefix = 2 if oneof.variable else 0
        if oneof.auto_discriminator:
            disc_width = 2 if oneof.discriminator_type == "msgid" else 1
        else:
            disc_width = 0
        parts.append(b"\x00" * (length_prefix + disc_width + oneof.size))

    return b"".join(parts)


# Output languages as (key, display name). The key names the CLI flags
# (--build-<key>, --<key>-path) and the default output subdirectory. The order
# picks the default directory for the generation hash (get_hash_file_path).
LANGUAGES = (
    ('c', 'C'), ('cpp', 'C++'), ('py', 'Python'), ('ts', 'TypeScript'),
    ('js', 'JavaScript'), ('csharp', 'C#'), ('gql', 'GraphQL'), ('rust', 'Rust'),
)
LANG_KEYS = tuple(key for key, _ in LANGUAGES)
LANG_NAMES = dict(LANGUAGES)
# Extra spellings accepted by --lang.
_LANG_ALIASES = {
    'python': 'py', 'typescript': 'ts', 'javascript': 'js', 'c++': 'cpp', 'cxx': 'cpp',
    'cs': 'csharp', 'c#': 'csharp', 'dotnet': 'csharp', 'graphql': 'gql', 'rs': 'rust',
}


def enabled_languages(args):
    """Languages selected on the command line, in LANGUAGES order."""
    return [lang for lang in LANG_KEYS if getattr(args, 'build_' + lang)]


def output_path(args, lang):
    """Resolved output directory for one language."""
    return getattr(args, lang + '_path')


# Python output: one importable package holding the runtime and a module per schema
# package (PY_PATH/<py-package>/...). Its name must not be `struct_frame`, the
# generator's own package.
DEFAULT_PY_PACKAGE = 'structframe'
# Modules of the Python runtime inside that package; schema packages cannot reuse them.
PY_RUNTIME_MODULES = ('frame_base', 'frame_headers', 'payload_types', 'frame_profiles',
                      'struct_frame_sdk')


# Generation hash file name
HASH_FILENAME = ".structframe.hash"

# Per-output-directory record of which files each root schema generated, so a later run can
# delete the files a schema no longer produces (renamed/removed messages and packages).
MANIFEST_FILENAME = ".structframe-manifest.json"


def _manifest_key(schema_path, out_dir, scope=""):
    """Stable key for a root schema: its path relative to the output directory, '/'-separated.

    *scope* names the set of languages written to the directory in this run (e.g. ``c`` or
    ``c+cpp``). Separate per-language runs into one directory therefore never see each other's
    files as their own, and so never prune them.
    """
    try:
        rel = os.path.relpath(os.path.abspath(schema_path), os.path.abspath(out_dir))
    except ValueError:  # different drive on Windows
        rel = os.path.abspath(schema_path)
    rel = rel.replace(os.sep, "/")
    return f"{rel}#{scope}" if scope else rel


def _load_manifest(out_dir):
    try:
        with open(os.path.join(out_dir, MANIFEST_FILENAME), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def prune_stale_outputs(out_dir, schema_path, generated_files, scope=""):
    """Delete files that *schema_path* generated into *out_dir* last time but not this time.

    Only files listed for this same schema and *scope* in the directory's manifest are
    candidates, and a file any other entry still claims is kept, so several schemas (or several
    per-language runs) can share one output directory. Returns the deleted paths and updates
    the manifest.
    """
    out_abs = os.path.abspath(out_dir)
    current = sorted({os.path.relpath(os.path.abspath(f), out_abs).replace(os.sep, "/")
                      for f in generated_files
                      if os.path.abspath(f).startswith(out_abs + os.sep)})
    manifest = _load_manifest(out_dir)
    key = _manifest_key(schema_path, out_dir, scope)
    claimed_elsewhere = {f for k, files in manifest.items() if k != key for f in files}
    removed = []
    for rel in manifest.get(key, []):
        if rel in current or rel in claimed_elsewhere or rel.startswith("../") or os.path.isabs(rel):
            continue
        target = os.path.join(out_abs, *rel.split("/"))
        if os.path.isfile(target):
            os.remove(target)
            removed.append(target)
            # Drop directories the deletion left empty (C# Messages/ folders etc.).
            parent = os.path.dirname(target)
            while parent != out_abs and os.path.isdir(parent) and not os.listdir(parent):
                os.rmdir(parent)
                parent = os.path.dirname(parent)
    manifest[key] = current
    os.makedirs(out_abs, exist_ok=True)
    with open(os.path.join(out_abs, MANIFEST_FILENAME), "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")
    return removed


def get_version():
    """The struct-frame version of the code that is running.

    A source checkout (``src/struct_frame`` next to ``pyproject.toml``) reports its own
    version, so running from ``src`` with an older release installed does not report the
    installed release. Otherwise the installed package metadata is used.
    """
    try:
        import pathlib
        src_dir = pathlib.Path(__file__).resolve().parent.parent
        pyproject_path = src_dir.parent / "pyproject.toml"
        if src_dir.name == 'src' and pyproject_path.exists():
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                in_project = False
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith('['):
                        in_project = stripped == '[project]'
                    elif in_project and stripped.startswith('version'):
                        # Parse: version = "0.6.3"
                        parts = stripped.split('=', 1)
                        if len(parts) == 2:
                            return parts[1].strip().strip('"\'')
    except (OSError, UnicodeDecodeError):
        pass

    try:
        from importlib.metadata import PackageNotFoundError, version as get_pkg_version
        return get_pkg_version('struct-frame')
    except (ImportError, PackageNotFoundError):
        pass
    return "unknown"


_GENERATOR_FINGERPRINT = None
_FINGERPRINT_SKIP_DIRS = {'__pycache__', 'node_modules', 'asio', 'asio-repo', '.git', 'bin', 'obj'}
_FINGERPRINT_EXTS = {'.py', '.h', '.hpp', '.ts', '.js', '.cs', '.rs', '.toml', '.json'}


def generator_fingerprint():
    """Hash of the generator and the runtime files it copies into the output.

    The version string alone is not enough: editing a generator or a runtime
    file in a development checkout (or installing a patched copy) must
    invalidate previously generated output, otherwise a hash match skips
    generation and leaves stale code behind. Vendored ASIO is skipped because
    it is large and never changes with the generator.
    """
    global _GENERATOR_FINGERPRINT
    if _GENERATOR_FINGERPRINT is not None:
        return _GENERATOR_FINGERPRINT
    root = os.path.dirname(os.path.realpath(__file__))
    hasher = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _FINGERPRINT_SKIP_DIRS)
        for filename in sorted(filenames):
            if os.path.splitext(filename)[1] not in _FINGERPRINT_EXTS:
                continue
            path = os.path.join(dirpath, filename)
            try:
                with open(path, 'rb') as handle:
                    content = handle.read()
            except OSError:
                continue
            hasher.update(os.path.relpath(path, root).replace(os.sep, '/').encode('utf-8'))
            # Normalise line endings so a CRLF checkout hashes like an LF one.
            hasher.update(content.replace(bytes([13, 10]), bytes([10])))
    _GENERATOR_FINGERPRINT = hasher.hexdigest()
    return _GENERATOR_FINGERPRINT


def _hash_line(hasher, text):
    hasher.update(f"{text}\n".encode('utf-8'))


def _hash_enum_entries(hasher, enum, indent):
    """Hash enum entries in declaration order (values *and* order matter)."""
    for entry_name, (value, _comments) in enum.data.items():
        marker = ""
        if enum.extensions_start is not None and value >= enum.extensions_start:
            marker = ":extension"
        _hash_line(hasher, f"{indent}{entry_name}={value}{marker}")


def compute_schema_hash(packages_dict):
    """
    Hash everything that determines the *structure* of the generated code:
    packages, enums, messages, field types/numbers/options and oneof variants.

    Field and oneof-variant declaration order is part of the hash: it defines
    the wire layout and (for ``field_order`` discriminators) the discriminator
    values, so reordering must invalidate cached output.  Packages, enums and
    messages are hashed by name because generated output lists them in a
    layout-independent (sorted, dependency-aware) order.
    """
    hasher = hashlib.sha256()
    for pkg_name in sorted(packages_dict.keys()):
        pkg = packages_dict[pkg_name]
        _hash_line(hasher, f"package:{pkg_name}")

        if pkg.package_id is not None:
            _hash_line(hasher, f"  pkgid:{pkg.package_id}")

        # Enums (sorted by name; entries in declaration order)
        for enum_name in sorted(pkg.enums.keys()):
            enum = pkg.enums[enum_name]
            _hash_line(hasher, f"  enum:{enum_name}")
            if enum.source_file:
                _hash_line(hasher, f"    source:{os.path.basename(enum.source_file)}")
            if enum.extensions_start is not None:
                _hash_line(hasher, f"    extensions_start:{enum.extensions_start}")
            _hash_enum_entries(hasher, enum, "    ")

        # Messages (sorted by name)
        for msg_name in sorted(pkg.messages.keys()):
            msg = pkg.messages[msg_name]
            _hash_line(hasher, f"  message:{msg_name}")
            if msg.source_file:
                _hash_line(hasher, f"    source:{os.path.basename(msg.source_file)}")
            if msg.id is not None:
                _hash_line(hasher, f"    msgid:{msg.id}")
            if msg.variable:
                _hash_line(hasher, "    variable:true")
            if msg.is_envelope:
                _hash_line(hasher, "    is_envelope:true")
            if msg.discriminator_mode:
                _hash_line(hasher, f"    discriminator:{msg.discriminator_mode}")
            if msg.extensions_start is not None:
                _hash_line(hasher, f"    extensions_start:{msg.extensions_start}")
            if msg.magic_bytes_override is not None:
                _hash_line(hasher, f"    magic_bytes:{msg.magic_bytes_override[0]},{msg.magic_bytes_override[1]}")

            # Message-scoped enums (sorted by name; entries in declaration order)
            for enum_name in sorted(msg.enums.keys()):
                enum = msg.enums[enum_name]
                _hash_line(hasher, f"    enum:{enum_name}")
                if enum.extensions_start is not None:
                    _hash_line(hasher, f"      extensions_start:{enum.extensions_start}")
                _hash_enum_entries(hasher, enum, "      ")

            # Fields in declaration order (== wire order)
            for field_name, field in msg.fields.items():
                _hash_line(hasher, "    " + _field_signature(field_name, field))

            # Oneofs in declaration order (== wire order); variants in declaration order
            for oneof_name in msg.oneofs:
                oneof = msg.oneofs[oneof_name]
                _hash_line(hasher, f"    oneof:{oneof_name}")
                if oneof.variable:
                    _hash_line(hasher, "      variable:true")
                if oneof.discriminator_mode and oneof.discriminator_mode != "auto":
                    _hash_line(hasher, f"      discriminator:{oneof.discriminator_mode}")
                if oneof.max_size_override is not None:
                    _hash_line(hasher, f"      max_size:{oneof.max_size_override}")
                if oneof.min_size_override is not None:
                    _hash_line(hasher, f"      min_size:{oneof.min_size_override}")
                if oneof.extensions_start is not None:
                    _hash_line(hasher, f"      extensions_start:{oneof.extensions_start}")
                for oneof_field_name, oneof_field in oneof.fields.items():
                    _hash_line(hasher, "      " + _field_signature(oneof_field_name, oneof_field))

    return hasher.hexdigest()


def _field_signature(field_name, field):
    info = f"field:{field_name}:{field.field_type}"
    if field.type_package:
        info += f":pkg={field.type_package}"
    if field.number is not None:
        info += f":number={field.number}"
    if field.is_array:
        info += ":array"
    if field.size_option is not None:
        info += f":size={field.size_option}"
    if field.max_size is not None:
        info += f":max_size={field.max_size}"
    if field.element_size is not None:
        info += f":element_size={field.element_size}"
    if field.flatten:
        info += ":flatten"
    if field.default is not None:
        info += f":default={field.default}"
    return info


def compute_documentation_hash(packages_dict):
    """
    Hash every comment that can reach generated output: file-level docs and
    the leading/trailing docs of packages' enums (and entries), messages,
    fields and oneofs.

    Kept separate from :func:`compute_schema_hash` so a comment-only edit is
    recognised as such (and still invalidates the generation cache).
    """
    hasher = hashlib.sha256()

    def hash_docs(label, comments):
        if comments:
            _hash_line(hasher, label)
            for comment in comments:
                _hash_line(hasher, "  " + json.dumps(comment))

    def hash_enum(label, enum):
        hash_docs(f"{label}:{enum.name}", enum.comments)
        for entry_name, (_value, comments) in enum.data.items():
            hash_docs(f"{label}:{enum.name}:{entry_name}", comments)

    for pkg_name in sorted(packages_dict.keys()):
        pkg = packages_dict[pkg_name]
        for index, block in enumerate(pkg.file_doc_blocks()):
            hash_docs(f"file:{pkg_name}:{index}", block)
        for enum_name in sorted(pkg.enums.keys()):
            hash_enum(f"enum:{pkg_name}", pkg.enums[enum_name])
        for msg_name in sorted(pkg.messages.keys()):
            msg = pkg.messages[msg_name]
            hash_docs(f"message:{pkg_name}:{msg_name}", msg.comments)
            for enum_name in sorted(msg.enums.keys()):
                hash_enum(f"enum:{pkg_name}:{msg_name}", msg.enums[enum_name])
            for field_name, field in msg.fields.items():
                hash_docs(f"field:{pkg_name}:{msg_name}:{field_name}", field.comments)
            for oneof_name in msg.oneofs:
                oneof = msg.oneofs[oneof_name]
                hash_docs(f"oneof:{pkg_name}:{msg_name}:{oneof_name}", oneof.comments)
                for field_name, field in oneof.fields.items():
                    hash_docs(f"field:{pkg_name}:{msg_name}:{oneof_name}:{field_name}", field.comments)

    return hasher.hexdigest()


def compute_generation_hash(args, packages_dict, name_overrides=None):
    """
    Compute a hash based on CLI parameters, struct-frame version, the parsed
    schema (structure) and the documentation comments.

    Comments are part of the key: they are emitted into generated code as
    docs, so editing one must regenerate the output.

    Args:
        args: Parsed argparse arguments
        packages_dict: Dictionary of parsed packages with their messages and enums
        name_overrides: Optional NameOverrides (their content is part of the key)

    Returns:
        str: SHA256 hash hex string
    """
    hasher = hashlib.sha256()

    # 1. Add struct-frame version
    version = get_version()
    _hash_line(hasher, f"version:{version}")
    _hash_line(hasher, f"generator:{generator_fingerprint()}")

    # 2. Add relevant CLI parameters (sorted for consistency)
    cli_params = {}
    for lang in LANG_KEYS:
        enabled = getattr(args, 'build_' + lang)
        cli_params['build_' + lang] = enabled
        cli_params[lang + '_path'] = output_path(args, lang) if enabled else None
    cli_params.update({
        'generate_tests': args.generate_tests,
        'catalog_path': args.catalog_path,
        'sdk': args.sdk,
        'sdk_embedded': args.sdk_embedded,
        'equality': args.equality,
        'csharp_namespace': args.csharp_namespace,
        'py_package': args.py_package if args.build_py else None,
        'no_packed': args.no_packed,
        'name_overrides': name_overrides.fingerprint() if name_overrides else None,
    })
    _hash_line(hasher, f"cli:{json.dumps(cli_params, sort_keys=True)}")

    # 3. Schema structure and 4. documentation, hashed separately and combined
    _hash_line(hasher, f"schema:{compute_schema_hash(packages_dict)}")
    _hash_line(hasher, f"docs:{compute_documentation_hash(packages_dict)}")

    # 5. Import graph: generated #include / import lines come from it, so
    # adding or removing an import changes the output even when no message does.
    imports = {name: sorted(deps) for name, deps in sorted(package_imports.items())}
    _hash_line(hasher, f"imports:{json.dumps(imports, sort_keys=True)}")

    return hasher.hexdigest()


def expected_outputs_exist(args):
    """True when every enabled output directory exists and is non-empty.

    The hash file lives next to one output directory, so a matching hash says
    nothing about the others: deleting e.g. the Python output must trigger
    regeneration instead of being skipped as "unchanged".
    """
    for lang in enabled_languages(args):
        path = output_path(args, lang)
        if not os.path.isdir(path):
            return False
        with os.scandir(path) as entries:
            if not any(entries):
                return False
    return True


def get_hash_file_path(args):
    """
    Determine the path for the hash file.

    Args:
        args: Parsed argparse arguments

    Returns:
        str: Path to the hash file
    """
    # Use explicit hash_path if provided, else the first enabled output path
    # (in LANGUAGES order), else the current directory.
    if args.hash_path is not None:
        hash_dir = args.hash_path
    else:
        langs = enabled_languages(args)
        hash_dir = output_path(args, langs[0]) if langs else "."

    return os.path.join(hash_dir, HASH_FILENAME)


def read_previous_hash(hash_file_path):
    """
    Read the previously stored generation hash.

    Args:
        hash_file_path: Path to the hash file

    Returns:
        str or None: The stored hash, or None if file doesn't exist
    """
    try:
        if os.path.exists(hash_file_path):
            with open(hash_file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
    except OSError:
        pass
    return None


def write_generation_hash(hash_file_path, hash_value):
    """
    Write the generation hash to file.

    Args:
        hash_file_path: Path to the hash file
        hash_value: Hash string to write
    """
    dirname = os.path.dirname(hash_file_path)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)

    with open(hash_file_path, 'w', encoding='utf-8') as f:
        f.write(hash_value)


class _Documented:
    """Documentation attached to a declaration (message, enum, field, oneof).

    Comment ownership rules (see docs: "Comments and documentation"):

    * ``leading_comments``  -- own-line comments that directly precede the
      declaration (no other declaration or statement in between).
    * ``trailing_comments`` -- comments on the same line *after* the
      declaration (``uint32 x = 1;  // note``).  For a message/enum/oneof, a
      comment on the same line as the opening ``{`` also counts.
    * ``comments`` -- what generators emit as the declaration's documentation:
      the leading comments followed by the trailing comments.
    """

    def _init_docs(self, comments):
        self.line = None          # source line, set by parse()
        self.source_file = None   # schema file, set by the owning package/message
        self.leading_comments = list(comments)
        self.trailing_comments = []
        self.comments = list(comments)

    def add_trailing_comment(self, text):
        self.trailing_comments.append(text)
        self.comments.append(text)


class _EntryDocs(_Documented):
    """Docs holder for one enum entry (shares its lists with Enum.data/entry_trailing_comments)."""

    def __init__(self, comments):
        self._init_docs(comments)


class _DocCollector:
    """Tracks comment ownership while walking the elements of one scope.

    Own-line comments are held back until the next declaration arrives and
    become its leading documentation.  Comments that share a line with a
    preceding declaration (``inline``) are attached to *that* declaration as
    trailing documentation instead of leaking onto the next one.  Comments
    that precede a non-declaration statement (``option``/``import``) or that
    are left dangling at the end of a scope document nothing and are dropped.
    """

    def __init__(self, owner=None):
        self.pending = []
        self.target = owner

    def comment(self, element):
        if getattr(element, 'inline', False):
            if self.target is not None:
                self.target.add_trailing_comment(element.text)
        else:
            self.pending.append(element.text)

    def statement(self, owner=None):
        """A non-declaration statement (option/import) was seen."""
        self.pending = []
        self.target = owner

    def take(self):
        """Return and clear the pending leading comments."""
        comments, self.pending = self.pending, []
        return comments

    def declared(self, declaration):
        """A documentable declaration was seen; later inline comments belong to it."""
        self.target = declaration


class Enum(_Documented):
    def __init__(self, package, comments):
        self.name = None
        self.data = {}
        self.size = 1
        self._init_docs(comments)
        # Per-entry trailing (same-line) comments; entries' combined docs
        # (leading + trailing) live in the second item of data[name].
        self.entry_trailing_comments = {}
        self.package = package
        self.is_enum = True
        self.source_file = None
        self.message = None  # Parent message name, or None for package-level enums
        # Enum-level wire-evolution: entries with value >= extensions_start are
        # extensions and must not affect the generation hash.
        self.extensions_start = None

    def parse(self, enum):
        self.name = enum.name
        self.line = getattr(enum, '_sf_line', None)
        self.error_line = self.line
        docs = _DocCollector(owner=self)
        for e in enum.elements:
            self.error_line = getattr(e, '_sf_line', None) or self.line
            if type(e) == ast.Comment:
                docs.comment(e)
            elif type(e) == ast.Option:
                docs.statement(owner=self)
                if e.name == "extensions_start":
                    try:
                        self.extensions_start = int(e.value)
                    except (TypeError, ValueError):
                        print(
                            f"Invalid extensions_start value '{e.value}' in "
                            f"enum {self.name}: must be an integer")
                        return False
            else:
                if e.name in self.data:
                    print(f"{location(self, self.error_line)}Enum entry '{e.name}' is declared twice in enum {self.name}")
                    return False
                entry_docs = _EntryDocs(docs.take())
                self.data[e.name] = (e.number, entry_docs.comments)
                self.entry_trailing_comments[e.name] = entry_docs.trailing_comments
                docs.declared(entry_docs)

        return True

    def validate(self, current_package, packages, debug=False):
        # Enums are stored in a single unsigned byte on the wire (self.size),
        # so every entry must fit 0..255 and map to a distinct value.
        seen = {}
        for key, (number, _docs) in self.data.items():
            if isinstance(number, bool) or not isinstance(number, int):
                print(f"{location(self)}Enum {self.name}: entry {key} has non-integer value {number!r}")
                return False
            lo, hi = facts.ENUM_VALUE_RANGE
            if number < lo or number > hi:
                print(f"{location(self)}Enum {self.name}: entry {key} = {number} is out of range "
                      f"(enums are stored in 1 byte: {lo}..{hi})")
                return False
            if number in seen:
                print(f"Enum {self.name}: entries {seen[number]} and {key} both have "
                      f"value {number}; enum values must be unique")
                return False
            seen[number] = key
        return True

    def __str__(self):
        output = ""
        for c in self.comments:
            output = output + c + "\n"

        output = output + f"Enum: {self.name}\n"

        for key, value in self.data.items():
            output = output + f"Key: {key}, Value: {value}" + "\n"
        return output


_MESSAGE_OPTIONS = tuple(facts.MESSAGE_OPTIONS) + tuple(facts.MESSAGE_OPTION_ALIASES)
_ONEOF_OPTIONS = tuple(facts.ONEOF_OPTIONS)
_FIELD_OPTIONS = tuple(facts.FIELD_OPTIONS)
_SIZE_MIN, _SIZE_MAX = facts.SIZE_OPTION_RANGE


def _prefix_bytes(max_size):
    """Width of the length/count prefix of a [max_size=N] field."""
    return 2 if max_size > facts.ONE_BYTE_PREFIX_MAX else 1


def _did_you_mean(name, candidates):
    """Return a ' (did you mean 'x'?)' hint, or '' when nothing is close."""
    import difflib
    close = difflib.get_close_matches(str(name), candidates, n=1, cutoff=0.6)
    listing = ", ".join(candidates)
    if close:
        return f" (did you mean '{close[0]}'? valid options: {listing})"
    return f" (valid options: {listing})"


_field_option_base = facts.option_base_name


class Field(_Documented):
    def __init__(self, package, comments):
        self.name = None
        self.field_type = None
        self.is_default_type = False
        self.size = 0
        self.validated = False
        self._init_docs(comments)
        self.package = package  # Package where this field is defined
        # Package where the field's type is defined (for cross-package refs)
        self.type_package = None
        self.type_message = None  # Message name if type is a nested enum, else None
        self.is_enum = False
        self.flatten = False
        self.is_array = False
        self.size_option = None   # Fixed size using [size=X]
        self.max_size = None      # Variable size using [max_size=X]
        # Element size for repeated string arrays [element_size=X]
        self.element_size = None
        # Source-level field number (.sf "= N" suffix). Must be 1..N sequential
        # within its scope (parent message's non-oneof fields, or each oneof
        # independently). Does NOT affect wire layout — wire order follows
        # source declaration order, which the validator pins to == number order.
        self.number = None
        # True if this field is in the trailing extensions block
        # (number >= message.extensions_start). Set during Message.validate.
        self.is_extension = False
        # Schema default from [default = ...]. Canonical form: bool/int/float
        # for those field types, decoded str text for string/bytes, the enum
        # *member name* (str) for enums. None means no default was declared.
        self.default = None
        # Resolved numeric value of an enum default (set only when is_enum is
        # True and self.default is not None). Used by generators that store
        # enum fields as raw integers, and by _field_default_bytes.
        self.default_numeric = None
        # The resolved Enum or Message object this field's type points to
        # (set during validate()). Used to validate enum default names and to
        # recurse into a nested message type's own default_bytes.
        self.type_ref = None

    def parse(self, field):
        self.name = field.name
        self.line = getattr(field, '_sf_line', None)
        self.field_type = field.type
        self.number = getattr(field, 'number', None)

        # Check if this is a repeated field (array)
        if hasattr(field, 'cardinality') and field.cardinality == FieldCardinality.REPEATED:
            self.is_array = True

        if self.field_type in default_types:
            self.is_default_type = True
            self.size = default_types[self.field_type]["size"]
            self.validated = True

        if hasattr(field, 'options') and field.options:
            # options is typically a list of ast.Option
            for opt in field.options:
                oname = getattr(opt, 'name', None)
                ovalue = getattr(opt, 'value', None)
                if not oname:
                    continue
                lname = str(oname).strip()
                base = _field_option_base(lname)
                if base not in _FIELD_OPTIONS:
                    print(f"{location(self)}warning: unknown option '{lname}' on field {self.name}, ignored"
                          f"{_did_you_mean(base, _FIELD_OPTIONS)}",
                          file=sys.stderr)
                    continue
                if base == 'flatten':
                    if facts.is_true(ovalue):
                        self.flatten = True
                elif base in ('size', 'max_size', 'element_size'):
                    # size: fixed size for arrays or strings; max_size: variable size;
                    # element_size: individual element size for repeated string arrays.
                    try:
                        value = int(ovalue)
                    except (ValueError, TypeError):
                        print(
                            f"Invalid {base} value {ovalue} for field {self.name}, must be an integer")
                        return False
                    if value < _SIZE_MIN or value > _SIZE_MAX:
                        print(
                            f"Invalid {base} {value} for field {self.name}, must be {_SIZE_MIN}-{_SIZE_MAX}")
                        return False
                    if base == 'size':
                        self.size_option = value
                    elif base == 'max_size':
                        self.max_size = value
                    else:
                        self.element_size = value
                elif base == 'default':
                    # Raw literal (bool/int/float/str) from the parser.
                    # Type-checked/coerced against field_type in validate()
                    # once the type is resolved (enum lookups need it).
                    self.default = ovalue
        return True

    def validate(self, current_package, packages, debug=False, current_message=None):

        global current_error_field
        current_error_field = self.name
        if not self.validated:
            # Check for nested enum in the current message first (unqualified name only)
            if (current_message and '.' not in self.field_type
                    and self.field_type in current_message.enums):
                nested_enum = current_message.enums[self.field_type]
                if not nested_enum.validate(current_package, packages, debug):
                    return False
                self.is_enum = True
                self.type_message = current_message.name
                self.validated = True
                self.type_ref = nested_enum
                base_size = nested_enum.size
            else:
                # Handle fully-qualified type names like "pkg_name.TypeName"
                bare_type = self.field_type
                qualified_pkg = None
                if '.' in self.field_type:
                    parts = self.field_type.split('.', 1)
                    qualified_pkg = parts[0]
                    bare_type = parts[1]

                visible = [current_package.name] + [
                    name for name in package_imports.get(current_package.name, [])
                    if name != current_package.name]
                if qualified_pkg:
                    # Qualified name: search only in the named package, which
                    # must be this package or one it imports directly.
                    ret = None
                    source_package = None
                    if qualified_pkg in packages and qualified_pkg not in visible:
                        print(f"Field {self.name}: type '{self.field_type}' refers to package "
                              f"'{qualified_pkg}', which is not imported by package "
                              f"'{current_package.name}'")
                        return False
                    if qualified_pkg in packages:
                        ret = packages[qualified_pkg].find_field_type(bare_type)
                        if ret:
                            source_package = packages[qualified_pkg]
                else:
                    # A type in the current package always wins; otherwise the
                    # name must resolve in exactly one directly imported package.
                    ret = current_package.find_field_type(self.field_type)
                    source_package = current_package

                    if not ret:
                        found = []
                        for pkg_name in visible[1:]:
                            pkg = packages.get(pkg_name)
                            hit = pkg.find_field_type(self.field_type) if pkg else None
                            if hit:
                                found.append((pkg, hit))
                        if len(found) > 1:
                            names = ", ".join(pkg.name for pkg, _ in found)
                            print(f"Field {self.name}: type '{self.field_type}' is ambiguous in "
                                  f"package '{current_package.name}' (defined in: {names}); "
                                  f"qualify it, e.g. '{found[0][0].name}.{self.field_type}'")
                            return False
                        if found:
                            source_package, ret = found[0]
                        elif any(pkg.find_field_type(self.field_type)
                                 for pkg in packages.values()):
                            print(f"Field {self.name}: type '{self.field_type}' is defined in a "
                                  f"package that '{current_package.name}' does not import")
                            return False

                if ret:
                    # Validate the type in the context of the package that owns
                    # it, never the referencing package: names inside it must
                    # resolve against its own scope.
                    if ret.validate(source_package, packages, debug):
                        self.is_enum = ret.is_enum
                        self.validated = True
                        base_size = ret.size
                        self.type_ref = ret
                        # Track which package the type comes from
                        self.type_package = source_package.name
                        # Normalize field_type to the bare name (strip package qualifier)
                        self.field_type = bare_type
                    else:
                        print(
                            f"Failed to validate Field: {self.name} of Type: {self.field_type} in Package: {current_package.name}")
                        return False
                else:
                    print(
                        f"Failed to find Field: {self.name} of Type: {self.field_type} in Package: {current_package.name}")
                    return False
        else:
            base_size = self.size

        if self.size_option is not None and self.max_size is not None:
            print(f"Field {self.name}: 'size' (fixed) and 'max_size' (variable) are "
                  f"mutually exclusive; use one")
            return False
        if self.element_size is not None and not (
                self.is_array and self.field_type in ("string", "bytes")):
            print(f"Field {self.name}: 'element_size' only applies to repeated "
                  f"string/bytes fields")
            return False

        # Calculate size for arrays and strings
        if self.is_array:
            if self.field_type in ("string", "bytes"):
                # String arrays need both array size AND individual element size
                if self.element_size is None:
                    print(
                        f"String array field {self.name} missing required element_size option")
                    return False

                if self.size_option is not None:
                    # Fixed string array: size_option strings, each element_size bytes
                    self.size = self.size_option * self.element_size
                elif self.max_size is not None:
                    # Variable string array: count bytes (1 or 2) + max_size strings of element_size bytes each
                    count_bytes = _prefix_bytes(self.max_size)
                    self.size = count_bytes + \
                        (self.max_size * self.element_size)
                else:
                    print(
                        f"String array field {self.name} missing required size or max_size option")
                    return False
            else:
                # Non-string arrays
                if self.size_option is not None:
                    # Fixed array: always full, no count byte needed
                    self.size = base_size * self.size_option
                elif self.max_size is not None:
                    # Variable array: count bytes (1 or 2) + max space
                    count_bytes = _prefix_bytes(self.max_size)
                    self.size = count_bytes + (base_size * self.max_size)
                else:
                    print(
                        f"Array field {self.name} missing required size or max_size option")
                    return False
        elif self.field_type in ("string", "bytes"):
            if self.size_option is not None:
                # Fixed string: exactly size_option characters
                self.size = self.size_option
            elif self.max_size is not None:
                # Variable string: length bytes (1 or 2) + max characters
                length_bytes = _prefix_bytes(self.max_size)
                self.size = length_bytes + self.max_size
            else:
                print(
                    f"String field {self.name} missing required size or max_size option")
                return False
        else:
            self.size = base_size

        # Validate [default = ...], if declared. Wire size/layout above is
        # already final and unaffected by this -- defaults never change
        # self.size.
        if self.default is not None:
            if self.is_array:
                print(
                    f"Field {self.name}: [default] is not supported on repeated fields")
                return False
            elif self.is_enum:
                enum_member = getattr(self.default, "name", self.default)
                if not isinstance(enum_member, str) or self.type_ref is None or enum_member not in self.type_ref.data:
                    print(
                        f"Field {self.name}: default value '{enum_member}' is not a member of enum {self.field_type}")
                    return False
                self.default = enum_member
                self.default_numeric = self.type_ref.data[enum_member][0]
            elif self.is_default_type:
                ok, result = _coerce_scalar_default(self.field_type, self.default)
                if not ok:
                    print(f"Field {self.name}: {result}")
                    return False
                self.default = result
                if self.field_type in ("string", "bytes"):
                    limit = self.size_option if self.size_option is not None else self.max_size
                    encoded_len = len(self.default.encode("utf-8"))
                    if limit is not None and encoded_len > limit:
                        limit_name = "size" if self.size_option is not None else "max_size"
                        print(
                            f"Field {self.name}: default value ({encoded_len} bytes) exceeds "
                            f"{limit_name}={limit}")
                        return False
            else:
                # Neither a primitive nor an enum -> a message-typed field.
                print(
                    f"Field {self.name}: [default] is not supported on message-typed fields")
                return False

        # Debug output - only show when debug flag is enabled
        if debug:
            array_info = ""
            if self.is_array:
                if self.field_type in ("string", "bytes"):
                    # String arrays show both array size and individual element size
                    if self.size_option is not None:
                        array_info = f", fixed_string_array size={self.size_option}, element_size={self.element_size}"
                    elif self.max_size is not None:
                        array_info = f", bounded_string_array max_size={self.max_size}, element_size={self.element_size}"
                else:
                    # Regular arrays
                    if self.size_option is not None:
                        array_info = f", fixed_array size={self.size_option}"
                    elif self.max_size is not None:
                        array_info = f", bounded_array max_size={self.max_size}"
            elif self.field_type in ("string", "bytes"):
                # Regular strings
                if self.size_option is not None:
                    array_info = f", fixed_string size={self.size_option}"
                elif self.max_size is not None:
                    array_info = f", variable_string max_size={self.max_size}"
            print(
                f"  Field {self.name}: type={self.field_type}, is_array={self.is_array}{array_info}, calculated_size={self.size}")

        return True

    def __str__(self):
        output = ""
        for c in self.comments:
            output = output + c + "\n"
        array_info = ""
        if self.is_array:
            if self.size_option is not None:
                array_info = f", Array[size={self.size_option}]"
            elif self.max_size is not None:
                array_info = f", Array[max_size={self.max_size}]"
            else:
                array_info = ", Array[no size specified]"
        elif self.field_type in ("string", "bytes"):
            if self.size_option is not None:
                array_info = f", String[size={self.size_option}]"
            elif self.max_size is not None:
                array_info = f", String[max_size={self.max_size}]"
        output = output + \
            f"Field: {self.name}, Type:{self.field_type}, Size:{self.size}{array_info}"
        return output


class OneOf(_Documented):
    """Represents a oneof (union) construct in a message.

    Discriminator modes:
    - "auto" (default): Use msgid if all fields are messages with msgid, otherwise use field_order
    - "msgid": Force use of message IDs as discriminator (error if any field lacks msgid)
    - "field_order": Force use of field order (1-based index) as discriminator
    - "none": No discriminator generated
    """

    def __init__(self, package, comments):
        self.name = None
        # Fields within this oneof (preserves insertion order in Python 3.7+)
        self.fields = {}
        self.field_order = []  # List of field names in declaration order
        self.size = 0  # Size of the largest field (including extension fields)
        # Size of the largest *base* (non-extension) field.  Equal to self.size
        # when there are no extensions in this oneof.
        self.base_size = 0
        self.validated = False
        self._init_docs(comments)
        self.package = package
        self.discriminator_mode = "auto"  # "auto", "msgid", "field_order", "none"
        # True if using msgid, False if using field_order, None if none
        self.auto_discriminator = None
        self.discriminator_type = None  # "msgid" or "field_order" after validation
        # Wire-evolution: field number at which the trailing extension block
        # starts inside this oneof.  Fields with .number >= extensions_start
        # are extension variants; they are excluded from magic computation and
        # from base_size.  None means no extension variants (all base).
        self.extensions_start = None
        # Internal parse-time flag: set True when a '// Extension::' comment
        # is encountered; cleared after the next field's number is captured.
        self._pending_extensions = False
        # Maximum size override: forces the union wire allocation to this value.
        # Allows reserving space for future variants without changing current sizes.
        self.max_size_override = None
        # Minimum serialized payload size for variable oneofs.
        # When set, the variable-length payload is zero-padded to at least this many bytes.
        # Useful for wire-compatibility: receivers compiled against older protocol versions
        # (when oneof.size was smaller) can still deserialize messages from newer senders.
        self.min_size_override = None
        # Variable oneof: if True, wire format is [disc][uint16 len][variant bytes].
        # Only valid when the parent message is also variable.
        self.variable = False
        # Pre-computed variant info for code generation: [(disc_value, field_name, field_size), ...]
        self.variant_info = []
        # Parallel to variant_info: per-variant (base_size, default_bytes) used
        # for trimmed-union wire evolution (short reads / schema defaults).
        self.variant_extra = []

    def variant_min_wire(self, index):
        """Smallest accepted trimmed-union payload length for variant `index`."""
        return max(self.variant_extra[index][0], self.min_size_override or 0)

    def variant_max_wire(self, index):
        """Trimmed-union payload length written for variant `index`."""
        return max(self.variant_info[index][2], self.min_size_override or 0)

    def min_wire_size(self):
        """Smallest valid trimmed-union payload length across all variants."""
        if not self.variant_extra:
            return self.size
        return min(self.variant_min_wire(i) for i in range(len(self.variant_extra)))

    def parse(self, oneof_element):
        """Parse a oneof element from the AST."""
        self.name = oneof_element.name
        self.line = getattr(oneof_element, '_sf_line', None)
        self.error_line = self.line
        docs = _DocCollector(owner=self)

        for e in oneof_element.elements:
            self.error_line = getattr(e, '_sf_line', None) or self.line
            if type(e) == ast.Comment:
                docs.comment(e)
                # Detect the visual extension marker: a standalone comment that
                # begins with 'Extension::' (case-sensitive) marks the start of
                # extension variants.  The next field encountered becomes
                # extensions_start.  Prose that merely mentions the marker, or a
                # trailing comment on the previous variant, must not change the
                # wire layout.
                marker_text = e.text.strip().lstrip('/*# ').lstrip()
                if (marker_text.startswith('Extension::')
                        and not getattr(e, 'inline', False)
                        and self.extensions_start is None):
                    self._pending_extensions = True
                elif 'Extension::' in e.text and self.extensions_start is None:
                    # Older versions accepted any comment containing the marker. Say that
                    # this one is now ignored: the variants after it are base variants, and
                    # that changes magic bytes and base sizes compared with older builds.
                    print(f"{location(self, self.error_line)}warning: comment mentioning "
                          f"'Extension::' in oneof '{self.name}' is not an extension marker "
                          f"(it must be a standalone comment starting with 'Extension::', or "
                          f"use 'option extensions_start'); the variants after it are base "
                          f"variants", file=sys.stderr)
            elif type(e) == ast.Option:
                docs.statement(owner=self)
                if e.name == "extensions_start":
                    try:
                        self.extensions_start = int(e.value)
                    except (TypeError, ValueError):
                        print(
                            f"Invalid extensions_start value '{e.value}' in "
                            f"oneof {self.name}: must be an integer field number")
                        return False
                    if self.extensions_start < facts.EXTENSIONS_START_MIN:
                        print(
                            f"extensions_start in oneof {self.name} must be >= {facts.EXTENSIONS_START_MIN} "
                            f"(at least one base variant is required)")
                        return False
                elif e.name == "discriminator":
                    mode = facts.normalize_discriminator(e.value)
                    if mode is None:
                        print(f"Invalid discriminator option '{e.value}' in oneof {self.name}. "
                              f"Valid values: {', '.join(facts.DISCRIMINATOR_MODES)}")
                        return False
                    self.discriminator_mode = mode
                elif e.name == "max_size":
                    try:
                        self.max_size_override = int(e.value)
                    except (TypeError, ValueError):
                        print(f"Invalid max_size value '{e.value}' in oneof {self.name}: must be an integer")
                        return False
                    if self.max_size_override < facts.ONEOF_SIZE_MIN:
                        print(f"max_size in oneof {self.name} must be > 0")
                        return False
                elif e.name == "min_size":
                    try:
                        self.min_size_override = int(e.value)
                    except (TypeError, ValueError):
                        print(f"Invalid min_size value '{e.value}' in oneof {self.name}: must be an integer")
                        return False
                    if self.min_size_override < facts.ONEOF_SIZE_MIN:
                        print(f"min_size in oneof {self.name} must be > 0")
                        return False
                elif e.name == "variable":
                    self.variable = facts.is_true(e.value)
                else:
                    print(f"{location(self, self.error_line)}warning: unknown option '{e.name}' in oneof "
                          f"{self.name}, ignored{_did_you_mean(e.name, _ONEOF_OPTIONS)}",
                          file=sys.stderr)
            elif type(e) == ast.Field:
                if e.name in self.fields:
                    print(f"Field Redeclaration in oneof {self.name}")
                    return False
                self.fields[e.name] = Field(self.package, docs.take())
                self.field_order.append(e.name)  # Track declaration order
                docs.declared(self.fields[e.name])
                if not self.fields[e.name].parse(e):
                    return False
                # Apply the pending Extension:: marker: the first field after
                # the marker becomes extensions_start (if not already set by
                # option extensions_start).
                if self._pending_extensions and self.extensions_start is None:
                    fnum = self.fields[e.name].number
                    if fnum is not None:
                        self.extensions_start = fnum
                    self._pending_extensions = False
        return True

    def validate(self, current_package, packages, debug=False, current_message=None):
        """Validate all fields in the oneof and determine size."""
        if self.validated:
            return True

        # Field-number validation: each oneof has its own number space; fields
        # must be 1..M sequentially in declaration order.
        msg_label = (current_message.name + ".") if current_message else ""
        for idx, (fname, fval) in enumerate(self.fields.items(), start=1):
            if fval.number is None:
                print(
                    f"Field '{fname}' in OneOf {msg_label}{self.name}: "
                    f"missing field number (expected '= {idx}').")
                return False
            if fval.number != idx:
                print(
                    f"Field '{fname}' in OneOf {msg_label}{self.name}: has number "
                    f"{fval.number} but must be {idx} "
                    f"(oneof fields must be numbered 1..M in declaration order).")
                return False

        # Wire-evolution: validate and apply extensions_start if set.
        if self.extensions_start is not None:
            field_numbers = [f.number for f in self.fields.values()]
            if self.extensions_start not in field_numbers:
                print(
                    f"extensions_start = {self.extensions_start} in oneof "
                    f"{msg_label}{self.name} must equal the field number of an "
                    f"existing variant (have {field_numbers}).")
                return False
            if self.extensions_start < facts.EXTENSIONS_START_MIN:
                print(
                    f"extensions_start in oneof {msg_label}{self.name} must be "
                    f">= {facts.EXTENSIONS_START_MIN} (at least one base variant required).")
                return False
            for fval in self.fields.values():
                fval.is_extension = (fval.number >= self.extensions_start)

        if not self.fields:
            print(f"Error: oneof '{msg_label}{self.name}' has no variants "
                  f"(an empty union is invalid C and has no wire representation)")
            return False

        if (self.max_size_override is not None and self.min_size_override is not None
                and self.min_size_override > self.max_size_override):
            print(f"Error: oneof '{msg_label}{self.name}' has min_size={self.min_size_override} "
                  f"greater than max_size={self.max_size_override}")
            return False

        # Validate each field and track the largest size
        max_size = 0
        max_base_size = 0
        all_have_msg_id = True

        for key, field in self.fields.items():
            if not field.validate(current_package, packages, debug, current_message=current_message):
                print(f"Failed to validate field {key} in oneof {self.name}")
                return False
            if field.default is not None:
                print(
                    f"Field '{key}' in OneOf {self.name}: [default] is not supported on oneof fields")
                return False
            max_size = max(max_size, field.size)
            if not getattr(field, 'is_extension', False):
                max_base_size = max(max_base_size, field.size)

            # Check if this field's type has a message ID
            if not field.is_default_type and not field.is_enum:
                # The field was already resolved (in the right package) by
                # Field.validate; never re-look it up by bare name.
                field_type = field.type_ref

                if field_type and hasattr(field_type, 'id') and field_type.id is not None:
                    # This message type has an ID
                    pass
                else:
                    all_have_msg_id = False
            else:
                # Primitive types or enums don't have message IDs
                all_have_msg_id = False

        self.size = max_size
        # base_size is the size of the largest non-extension variant.  When
        # there are no extension variants (extensions_start is None), every
        # variant is a base variant so base_size == size.
        self.base_size = max_base_size if self.extensions_start is not None else max_size

        # Determine discriminator type based on mode
        if self.discriminator_mode == "none":
            self.auto_discriminator = None
            self.discriminator_type = None
        elif self.discriminator_mode == "msgid":
            if not all_have_msg_id:
                print(
                    f"Error: oneof '{self.name}' has discriminator=msgid but not all fields are messages with msgid")
                return False
            self.auto_discriminator = True
            self.discriminator_type = "msgid"
        elif self.discriminator_mode == "field_order":
            self.auto_discriminator = True  # True means discriminator is present
            self.discriminator_type = "field_order"
        else:  # "auto" - default behavior
            if all_have_msg_id and len(self.fields) > 0:
                self.auto_discriminator = True
                self.discriminator_type = "msgid"
            elif len(self.fields) > 0:
                # Fallback to field_order
                self.auto_discriminator = True
                self.discriminator_type = "field_order"
            else:
                self.auto_discriminator = None
                self.discriminator_type = None

        # Apply max_size_override if specified
        if self.max_size_override is not None:
            if self.max_size_override < self.size:
                print(f"Error: oneof '{self.name}' max_size={self.max_size_override} is smaller than "
                      f"the computed max variant size {self.size}. max_size must be >= largest variant.")
                return False
            self.size = self.max_size_override
            if self.extensions_start is None:
                self.base_size = self.max_size_override

        # Validate min_size_override if specified
        if self.min_size_override is not None:
            if not self.variable:
                # For fixed oneofs: min_size grows the union buffer if the current size is smaller,
                # mirroring max_size behaviour as a lower bound.
                if self.min_size_override > self.size:
                    self.size = self.min_size_override
                    if self.extensions_start is None:
                        self.base_size = self.min_size_override
                # If current size already >= min_size, this is a no-op — no warning needed.
            else:
                # For variable oneofs: min_size pads the wire payload but cannot exceed the buffer.
                if self.min_size_override > self.size:
                    print(f"Error: oneof '{self.name}' min_size={self.min_size_override} exceeds the "
                          f"union buffer size {self.size}. min_size must be <= oneof size (use max_size "
                          f"to increase union buffer size first).")
                    return False

        # Validate variable oneof flag
        if self.variable:
            if current_message is not None and not current_message.variable:
                print(f"Error: oneof '{self.name}' has variable=true but parent message "
                      f"'{current_message.name}' is not marked as variable. "
                      f"Add 'option variable = true;' to the message.")
                return False

        # Pre-compute discriminator values for each variant (used by code generators)
        self.variant_info = []
        self.variant_extra = []
        for field_name, field in self.fields.items():
            if self.discriminator_type is not None:
                disc_val = self.get_field_discriminator_value(field_name, current_package, packages)
            else:
                disc_val = 0
            self.variant_info.append((disc_val, field_name, field.size))
            nested = None if (field.is_default_type or field.is_enum) else field.type_ref
            if nested is not None and getattr(nested, "base_size", 0):
                base = min(nested.base_size, field.size)
                default_bytes = getattr(nested, "default_bytes", b"")
            else:
                base = field.size
                default_bytes = b""
            if len(default_bytes) != field.size or not any(default_bytes):
                default_bytes = b""
            self.variant_extra.append((base, default_bytes))

        if self.discriminator_type is not None:
            seen_disc = {}
            for disc_val, field_name, _size in self.variant_info:
                if disc_val in seen_disc:
                    print(f"Error: oneof '{msg_label}{self.name}': variants "
                          f"'{seen_disc[disc_val]}' and '{field_name}' have the same "
                          f"discriminator value {disc_val}, so a receiver cannot tell "
                          f"them apart. Use distinct message types, or "
                          f"'option discriminator = field_order;'")
                    return False
                seen_disc[disc_val] = field_name

        self.validated = True
        return True

    def get_field_discriminator_value(self, field_name, current_package, packages):
        """Get the discriminator value for a field based on discriminator_type.

        Returns:
            int: The discriminator value (msgid or 1-based field order index)
        """
        if self.discriminator_type == "msgid":
            field_type = self.fields[field_name].type_ref
            return field_type.id if field_type is not None and field_type.id is not None else 0
        elif self.discriminator_type == "field_order":
            # 1-based index
            return self.field_order.index(field_name) + 1
        return 0

    def __str__(self):
        output = f"OneOf: {self.name}, Size: {self.size}, Discriminator: {self.discriminator_type}\n"
        for key, value in self.fields.items():
            output += "  " + value.__str__() + "\n"
        return output


class Message(_Documented):
    def __init__(self, package, comments):
        self.id = None
        self.size = 0
        self.name = None
        self.fields = {}
        self.oneofs = {}  # Dictionary of oneof constructs
        self.enums = {}  # Nested enum definitions (message-scoped)
        self.validated = False
        self._init_docs(comments)
        self.package = package
        self.is_enum = False
        self.magic_bytes = None  # Magic numbers for checksum (byte1, byte2)
        self.magic_bytes_override = None  # User-specified magic bytes (option magic_bytes)
        self.variable = False  # Variable length message encoding
        self.discriminator_mode = None  # Optional message-level discriminator override
        # True if this message is an envelope/container for other messages
        self.is_envelope = False
        self.source_file = None
        # Wire-evolution: field number at which the trailing extension block
        # starts. Fields with .number >= extensions_start are extensions and
        # form a contiguous trailing block. None == no extensions (legacy).
        self.extensions_start = None
        # Computed during validate(): byte size of the non-extension portion
        # of the encoded message (== self.size when extensions_start is None).
        self.base_size = 0
        # Computed during validate(): the wire-format bytes of this message
        # with schema [default = ...] values applied to unset fields, and
        # zero bytes everywhere else (fields with no default, oneofs). Used
        # by generators as the pad/pre-fill source for decode/construction so
        # missing trailing bytes resolve to the schema default instead of
        # zero. Byte-identical to an all-zero buffer of length self.size when
        # no field in this message (or its nested message fields) has a
        # default -- i.e. a no-op for schemas that don't use this feature.
        self.default_bytes = b""

    def parse(self, msg):
        self.name = msg.name
        self.line = getattr(msg, '_sf_line', None)
        self.error_line = self.line
        docs = _DocCollector(owner=self)
        for e in msg.elements:
            self.error_line = getattr(e, '_sf_line', None) or self.line
            if type(e) == ast.Option:
                docs.statement(owner=self)
                if e.name == "msgid":
                    if self.id is not None:
                        print(f"Redefinition of msgid in message {self.name}")
                        return False
                    if isinstance(e.value, bool) or not isinstance(e.value, int):
                        print(f"Invalid msgid {e.value!r} in message {self.name}: "
                              f"must be an integer")
                        return False
                    self.id = e.value
                elif e.name == "variable":
                    if facts.is_true(e.value):
                        self.variable = True
                elif e.name == "discriminator":
                    mode = facts.normalize_discriminator(e.value)
                    if mode is None:
                        print(f"Invalid discriminator option '{e.value}' in message {self.name}. "
                              f"Valid values: {', '.join(facts.DISCRIMINATOR_MODES)}")
                        return False
                    self.discriminator_mode = mode
                elif facts.MESSAGE_OPTION_ALIASES.get(e.name, e.name) == "is_envelope":
                    if facts.is_true(e.value):
                        self.is_envelope = True
                elif e.name == "extensions_start":
                    try:
                        self.extensions_start = int(e.value)
                    except (TypeError, ValueError):
                        print(
                            f"Invalid extensions_start value '{e.value}' in "
                            f"message {self.name}: must be an integer field number")
                        return False
                    if self.extensions_start < facts.EXTENSIONS_START_MIN:
                        print(
                            f"extensions_start in message {self.name} must be >= {facts.EXTENSIONS_START_MIN} "
                            f"(at least one base field is required)")
                        return False
                elif e.name == "magic_bytes":
                    raw = str(e.value).strip()
                    parts = [p.strip() for p in raw.split(',')]
                    if len(parts) != facts.MAGIC_BYTES_COUNT:
                        print(
                            f"Invalid magic_bytes value '{raw}' in message {self.name}: "
                            f"expected two comma-separated byte values, e.g. \"0xAB, 0xCD\"")
                        return False
                    try:
                        b1 = int(parts[0], 0)
                        b2 = int(parts[1], 0)
                    except ValueError:
                        print(
                            f"Invalid magic_bytes value '{raw}' in message {self.name}: "
                            f"values must be integers (hex or decimal)")
                        return False
                    if not (0 <= b1 <= 255 and 0 <= b2 <= 255):
                        print(
                            f"Invalid magic_bytes value '{raw}' in message {self.name}: "
                            f"each byte must be in range 0-255")
                        return False
                    if min(b1, b2) < facts.MAGIC_BYTE_RANGE[0]:
                        print(
                            f"Invalid magic_bytes value '{raw}' in message {self.name}: "
                            f"magic bytes must be non-zero")
                        return False
                    self.magic_bytes_override = (b1, b2)
                else:
                    print(f"{location(self, self.error_line)}warning: unknown option '{e.name}' in message "
                          f"{self.name}, ignored{_did_you_mean(e.name, _MESSAGE_OPTIONS)}",
                          file=sys.stderr)
            elif type(e) == ast.Comment:
                docs.comment(e)
            elif type(e) == ast.OneOf:
                if e.name in self.oneofs:
                    print(f"{location(self, self.error_line)}oneof '{e.name}' is declared twice in message {self.name}")
                    return False
                self.oneofs[e.name] = OneOf(self.package, docs.take())
                self.oneofs[e.name].source_file = self.source_file
                docs.declared(self.oneofs[e.name])
                if not self.oneofs[e.name].parse(e):
                    self.error_line = self.oneofs[e.name].error_line or self.error_line
                    return False
            elif type(e) == ast.Enum:
                if e.name in self.enums:
                    print(f"{location(self, self.error_line)}enum '{e.name}' is declared twice in message {self.name}")
                    return False
                self.enums[e.name] = Enum(self.package, docs.take())
                self.enums[e.name].message = self.name
                self.enums[e.name].source_file = self.source_file
                docs.declared(self.enums[e.name])
                if not self.enums[e.name].parse(e):
                    self.error_line = self.enums[e.name].error_line or self.error_line
                    return False
            elif type(e) == ast.Field:
                if e.name in self.fields:
                    print(f"{location(self, self.error_line)}field '{e.name}' is declared twice in message {self.name}")
                    return False
                self.fields[e.name] = Field(self.package, docs.take())
                self.fields[e.name].source_file = self.source_file
                docs.declared(self.fields[e.name])
                if not self.fields[e.name].parse(e):
                    return False
        return True

    def validate(self, current_package, packages, debug=False):
        if self.validated:
            return True

        global current_error_message
        current_error_message = self.name

        # Field-number validation: non-oneof fields must be numbered 1..N
        # in declaration order. Numbers carry no wire-format meaning (wire
        # order follows declaration order); the rule pins source numbering to
        # match declaration order so the numbers are useful as a stable,
        # human-readable identifier (and so `extensions_start = N` is
        # unambiguous).
        for idx, (fname, fval) in enumerate(self.fields.items(), start=1):
            if fval.number is None:
                print(
                    f"Field '{fname}' in Message {self.name}: missing field number "
                    f"(expected '= {idx}').")
                return False
            if fval.number != idx:
                print(
                    f"Field '{fname}' in Message {self.name}: has number "
                    f"{fval.number} but must be {idx} "
                    f"(non-oneof fields must be numbered 1..N in declaration order).")
                return False

        # Wire-evolution: tag extension fields and validate extensions_start.
        # Extension semantics apply only to top-level message fields; oneof
        # fields are always treated as base.
        if self.extensions_start is not None:
            # Extension fields must form the trailing bytes of the wire payload,
            # but the wire order is all plain fields followed by all oneofs. A
            # message-level extensions_start combined with a oneof would place
            # extension bytes BEFORE the oneof, breaking the base-prefix CRC
            # split and cross-version interop. Use `option extensions_start`
            # inside the oneof instead to add extension variants.
            if self.oneofs:
                print(
                    f"Message {self.name}: message-level `option extensions_start` "
                    f"cannot be combined with oneof fields (extension fields would "
                    f"not be trailing on the wire). Declare `option extensions_start` "
                    f"inside the oneof to add extension variants instead.")
                return False
            field_numbers = [f.number for f in self.fields.values()]
            if self.extensions_start not in field_numbers:
                print(
                    f"extensions_start = {self.extensions_start} in message "
                    f"{self.name} must equal the field number of an existing "
                    f"non-oneof field (have {field_numbers}).")
                return False
            for fval in self.fields.values():
                fval.is_extension = (fval.number >= self.extensions_start)

        # Validate regular fields
        for key, value in self.fields.items():
            if not value.validate(current_package, packages, debug, current_message=self):
                print(
                    f"{location(value)}Failed To validate Field: {key}, in Message {self.name}\n")
                return False
            self.size = self.size + value.size
            if not value.is_extension:
                self.base_size = self.base_size + value.size

        # Validate oneofs - they contribute their max size to the message
        if self.discriminator_mode is not None and len(self.oneofs) == 1:
            sole_oneof = next(iter(self.oneofs.values()))
            if sole_oneof.discriminator_mode == "auto":
                sole_oneof.discriminator_mode = self.discriminator_mode

        for key, oneof in self.oneofs.items():
            if not oneof.validate(current_package, packages, debug, current_message=self):
                print(
                    f"{location(oneof)}Failed To validate OneOf: {key}, in Message {self.name}\n")
                return False
            # Add oneof size (largest field size)
            # For variable oneof, add 2 bytes for the uint16 length prefix on the wire.
            length_prefix = 2 if oneof.variable else 0
            self.size = self.size + oneof.size + length_prefix
            # Use oneof.base_size so that extension variants within a oneof are
            # not counted as part of the base wire footprint.
            self.base_size = self.base_size + oneof.base_size + length_prefix
            # Discriminator is always a base field — it is present in every
            # frame regardless of which variant is active.
            if oneof.auto_discriminator:
                if oneof.discriminator_type == "msgid":
                    self.size = self.size + 2  # uint16_t for message ID
                    self.base_size = self.base_size + 2
                else:  # field_order
                    self.size = self.size + 1  # uint8_t for field order index
                    self.base_size = self.base_size + 1

        # Flatten collision detection: if a field is marked as flatten and is a message,
        # ensure none of the child field names collide with fields in this message.
        taken = {name: name for name in self.fields.keys()}
        # oneof members become sibling fields too (GraphQL emits them on the same type).
        for oneof in getattr(self, 'oneofs', {}).values():
            for member in getattr(oneof, 'fields', {}).keys():
                taken.setdefault(member, member)
        for key, value in self.fields.items():
            if getattr(value, 'flatten', False):
                # Only meaningful for non-default, non-enum message types
                if value.is_default_type or value.is_enum:
                    # Flatten has no effect on primitives/enums; skip
                    continue
                # Use the type resolved by Field.validate: it may live in an
                # imported package, not in current_package.
                child = value.type_ref
                if not child or getattr(child, 'is_enum', False) or not hasattr(child, 'fields'):
                    # Unknown or non-message type; skip
                    continue
                for ck in child.fields.keys():
                    if ck in taken:
                        other = taken[ck]
                        what = (f"existing field '{ck}'" if other == ck
                                else f"field '{other}.{ck}' (also flattened)")
                        print(
                            f"Flatten collision in Message {self.name}: field '{key}.{ck}' collides with {what}.")
                        return False
                    taken[ck] = f"{key}"

        # Array validation
        for key, value in self.fields.items():
            if value.is_array:
                # All arrays must have size or max_size specified
                if value.size_option is None and value.max_size is None:
                    print(
                        f"Array field {key} in Message {self.name}: must specify size or max_size option")
                    return False
            elif value.field_type in ("string", "bytes"):
                # Strings must have size or max_size specified
                if value.size_option is None and value.max_size is None:
                    print(
                        f"String field {key} in Message {self.name}: must specify size or max_size option")
                    return False
            elif value.max_size is not None or value.size_option is not None or value.element_size is not None:
                print(
                    f"Field {key} in Message {self.name}: size/max_size/element_size options can only be used with repeated fields or strings")
                return False

        # Envelope message validation
        if self.is_envelope:
            # Envelope messages must have exactly one oneof field
            if len(self.oneofs) != 1:
                print(
                    f"Envelope message {self.name}: must have exactly one oneof field (found {len(self.oneofs)})")
                return False

            # Get the single oneof
            oneof_name = list(self.oneofs.keys())[0]
            oneof = self.oneofs[oneof_name]

            # All fields in the oneof must be message types (not primitives or enums)
            for field_name, field in oneof.fields.items():
                if field.is_default_type:
                    print(
                        f"Envelope message {self.name}: oneof field '{field_name}' must be a message type, not a primitive")
                    return False
                if field.is_enum:
                    print(
                        f"Envelope message {self.name}: oneof field '{field_name}' must be a message type, not an enum")
                    return False

            # If discriminator mode is "msgid" (explicit or auto-determined), all messages must have msgid
            # Note: oneof.validate() is called before message.validate(), so discriminator_type is set
            if oneof.discriminator_type == "msgid":
                for field_name, field in oneof.fields.items():
                    # Find the message type and verify it has a message ID
                    field_type = current_package.find_field_type(
                        field.field_type)
                    if not field_type:
                        for pkg_name, pkg in packages.items():
                            field_type = pkg.find_field_type(field.field_type)
                            if field_type:
                                break

                    if not field_type or not hasattr(field_type, 'id') or field_type.id is None:
                        print(
                            f"Envelope message {self.name}: oneof field '{field_name}' type '{field.field_type}' must have a message ID (option msgid) when using msgid discriminator")
                        return False

        self.validated = True

        # Calculate magic numbers for this message (skip if user hardcoded them)
        if self.magic_bytes_override is not None:
            self.magic_bytes = self.magic_bytes_override
        else:
            self.magic_bytes = calculate_magic_numbers(self)

        # Calculate minimum size for variable messages
        # min_size is the size when all variable-length fields are at their minimum.
        # Extension fields contribute nothing: an older (extension-unaware) sender
        # omits them entirely, so the smallest valid payload is base fields only.
        if self.variable:
            self.min_size = 0
            for key, value in self.fields.items():
                if value.is_extension:
                    continue
                if value.is_array and value.max_size is not None:
                    # Bounded array: only the count bytes (1 or 2, no data when empty)
                    count_bytes = _prefix_bytes(value.max_size)
                    self.min_size += count_bytes
                elif value.field_type in ("string", "bytes") and value.max_size is not None:
                    # Variable string: only the length bytes (1 or 2, no data when empty)
                    length_bytes = _prefix_bytes(value.max_size)
                    self.min_size += length_bytes
                else:
                    # Fixed-size fields use their full size
                    self.min_size += value.size
            # Oneofs: discriminator + union payload (or length-prefix + 0 bytes for variable oneof)
            for key, oneof in self.oneofs.items():
                if oneof.auto_discriminator:
                    disc_bytes = 2 if oneof.discriminator_type == "msgid" else 1
                    self.min_size += disc_bytes
                if oneof.variable:
                    self.min_size += 2  # uint16 length prefix; minimum payload is 0 bytes
                elif oneof.discriminator_type is not None:
                    # Trimmed union: smallest valid wire payload, not the largest variant
                    self.min_size += oneof.min_wire_size()
                else:
                    self.min_size += oneof.size
        else:
            self.min_size = self.size

        # Wire-format bytes for this message with schema defaults applied to
        # unset fields (see Field.default / _field_default_bytes). Computed
        # last, after all fields/oneofs are validated and sized, so any
        # nested message field's own default_bytes is already available.
        self.default_bytes = _compute_message_default_bytes(self)

        return True

    def __str__(self):
        output = ""
        for c in self.comments:
            output = output + c + "\n"
        if self.variable:
            output = output + \
                f"Message: {self.name}, Size: {self.size}, MinSize: {self.min_size}, ID: {self.id}, Variable: True\n"
        else:
            output = output + \
                f"Message: {self.name}, Size: {self.size}, ID: {self.id}\n"

        for key, value in self.fields.items():
            output = output + value.__str__() + "\n"

        for key, value in self.oneofs.items():
            output = output + value.__str__() + "\n"

        return output


class Package:
    def __init__(self, name):
        self.name = name
        self.enums = {}
        self.messages = {}
        self.package_id = None  # Package ID for extended message IDs (0-255)
        self.package_id_explicit = False
        # File-level documentation: own-line comments that precede the
        # ``package`` statement of a source file (license/overview headers).
        # Keyed by absolute source path; they document the file, not the first
        # declaration that happens to follow.
        self.file_docs = {}

    def add_file_docs(self, source_file, comments):
        if comments:
            self.file_docs.setdefault(source_file, []).extend(comments)

    def file_doc_blocks(self):
        """File-doc comment blocks in a layout-independent order.

        Sorted by file name (then path) so that the generated output does not
        depend on the order in which files were imported.
        """
        return [self.file_docs[path] for path in sorted(
            self.file_docs, key=lambda p: (os.path.basename(p), p))]

    def file_doc_lines(self):
        """Flattened :meth:`file_doc_blocks` (one list of comment strings)."""
        return [line for block in self.file_doc_blocks() for line in block]

    def addEnum(self, enum, comments, source_file=None):
        if enum.name in self.enums:
            where = f"{source_file}:{getattr(enum, '_sf_line', '')}: " if source_file else ""
            print(f"{where}enum '{enum.name}' is declared twice in package {self.name}")
            return False
        self.enums[enum.name] = Enum(self.name, comments)
        self.enums[enum.name].source_file = source_file
        return self.enums[enum.name].parse(enum)

    def addMessage(self, message, comments, source_file=None):
        if message.name in self.messages:
            where = f"{source_file}:{getattr(message, '_sf_line', '')}: " if source_file else ""
            print(f"{where}message '{message.name}' is declared twice in package {self.name}")
            return False
        self.messages[message.name] = Message(self.name, comments)
        self.messages[message.name].source_file = source_file
        return self.messages[message.name].parse(message)

    def validate_package(self, all_packages, debug=False):
        names = []
        for key, value in self.enums.items():
            if value.name in names:
                print(
                    f"Name collision with Enum and Message: {value.name} in Packaage {self.name}")
                return False
            names.append(value.name)
        for key, value in self.messages.items():
            if value.name in names:
                print(
                    f"Name collision with Enum and Message: {value.name} in Packaage {self.name}")
                return False
            names.append(value.name)

        # Validate package ID if specified
        if self.package_id is not None:
            lo, hi = facts.PKGID_RANGE
            if self.package_id < lo or self.package_id > hi:
                print(
                    f"Package ID {self.package_id} for package {self.name} out of range ({lo}-{hi})")
                return False

            # Note: We allow different packages to share the same package ID if one inherited
            # from the other through imports. The package_imports tracking handles this.
            # Only error if the same package NAME has different IDs (checked in validate_package_id).

        # Validate message IDs based on whether package has a package ID
        seen_msg_ids = {}
        for key, value in self.messages.items():
            if value.id is not None:
                if value.id in seen_msg_ids:
                    other = seen_msg_ids[value.id]
                    print(
                        f"Error: duplicate msgid {value.id} in package '{self.name}' used by messages '{other}' and '{value.name}'")
                    return False
                seen_msg_ids[value.id] = value.name

                if self.package_id is not None:
                    # With a package ID the wire id is (pkgid << 8) | msgid, so msgid is one byte
                    lo, hi = facts.MSGID_RANGE_WITH_PKGID
                    if value.id < lo or value.id > hi:
                        print(
                            f"Error: Message '{value.name}' in package '{self.name}' has msgid={value.id}")
                        print(
                            f"  When package has 'option pkgid={self.package_id}', all message IDs must be in range [{lo}, {hi}]")
                        return False
                else:
                    lo, hi = facts.MSGID_RANGE
                    if value.id < lo or value.id > hi:
                        print(
                            f"Error: Message '{value.name}' in package '{self.name}' has msgid={value.id}")
                        print(
                            f"  Without package ID, message IDs must be in range [{lo}, {hi}]")
                        return False

        for key, value in self.messages.items():
            if not value.validate(self, all_packages, debug):
                print(
                    f"{location(value)}Failed To validate Message: {key}, in Package {self.name}\n")
                return False

        return True

    def find_field_type(self, name):
        for key, value in self.enums.items():
            if value.name == name:
                return value

        for key, value in self.messages.items():
            if value.name == name:
                return value

    def sortedMessages(self):
        # Need to sort messages to ensure no out of order dependencies.
        return self.messages

    def __str__(self):
        output = "Package: " + self.name
        if self.package_id is not None:
            output += f" (ID: {self.package_id})"
        output += "\n"
        for key, value in self.enums.items():
            output = output + value.__str__() + "\n"
        for key, value in self.messages.items():
            output = output + value.__str__() + "\n"
        return output


packages = {}
processed_file = []
required_file = []
# Track which package imports which other packages: {importing_pkg: [imported_pkg1, imported_pkg2, ...]}
package_imports = {}
# Imports that could not be resolved when first seen because the target
# package had not been parsed yet: [(importing_pkg, imported_abs_path), ...]
pending_package_imports = []
# Track the owning package for each parsed file so repeated imports can still
# contribute package-level edges even when parseFile short-circuits.
file_to_package = {}

def reset_parse_state():
    """Forget every schema parsed so far, so ``main()`` can run more than once per process.

    The containers are cleared in place: other modules and the tests hold references to them.
    """
    packages.clear()
    processed_file.clear()
    required_file.clear()
    package_imports.clear()
    pending_package_imports.clear()
    file_to_package.clear()


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

DEFAULT_OUT = 'generated'
CONFIG_FILENAME = 'structframe.toml'

# Options whose values are paths. Relative paths in a config file are resolved against the
# directory of that file, so a build can run from anywhere.
_PATH_DESTS = frozenset({'filename', 'out', 'catalog_path', 'hash_path', 'name_overrides'}
                        | {lang + '_path' for lang in LANG_KEYS})


class ConfigError(Exception):
    """A structframe.toml file could not be read or contains an unknown or mistyped key."""


def _add_option(group, name, **kwargs):
    """Register ``--kebab-name`` plus the historical ``--snake_name`` spelling.

    Both set the same destination; only the kebab-case form is listed in ``--help``.
    """
    kebab = '--' + name.replace('_', '-')
    group.add_argument(kebab, dest=name, **kwargs)
    snake = '--' + name
    if snake != kebab:
        hidden = dict(kwargs, help=argparse.SUPPRESS, default=argparse.SUPPRESS)
        group.add_argument(snake, dest=name, **hidden)


def build_parser():
    """Return the argument parser for code generation (``diff`` has its own parser)."""
    parser = argparse.ArgumentParser(
        prog='struct-frame',
        usage='%(prog)s [options] [SCHEMA]\n       %(prog)s diff OLD NEW [options]',
        description=('Generate message code and framing runtimes from a struct-frame schema '
                     '(.sf, or .proto with struct-frame options).'),
        epilog=('examples:\n'
                '  struct-frame robot.sf --lang c,py --out build/gen\n'
                '  struct-frame robot.sf --build-cpp --cpp-path firmware/gen\n'
                '  struct-frame robot.sf --validate\n'
                '  struct-frame                      (reads ./structframe.toml)\n'
                '  struct-frame diff old.sf new.sf   (wire-compatibility check; see '
                '"struct-frame diff --help")\n\n'
                'Older snake_case spellings of every option (--build_c, --c_path, ...) are '
                'still accepted.'),
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('filename', nargs='?', default=None, metavar='SCHEMA',
                        help='Schema file to compile; its imports are followed. Optional when a '
                             'config file names it.')
    parser.add_argument('--version', action='version', version=f'%(prog)s {get_version()}')

    langs = parser.add_argument_group('languages')
    langs.add_argument('--lang', action='append', default=None, metavar='LANGS',
                       help=f'Comma-separated languages to generate: {", ".join(LANG_KEYS)} or '
                            'all. May be repeated.')
    for lang, name in LANGUAGES:
        _add_option(langs, 'build_' + lang, action='store_true', help=f'Generate {name}')

    out = parser.add_argument_group('output locations')
    out.add_argument('--out', default=None, metavar='DIR',
                     help=f'Root output directory: each language is written to DIR/<lang> unless '
                          f'its --<lang>-path is given (default: {DEFAULT_OUT})')
    for lang, name in LANGUAGES:
        _add_option(out, lang + '_path', default=None, metavar='DIR',
                    help=f'Output directory for {name} (default: OUT/{lang})')
    _add_option(out, 'catalog_path', default=None, metavar='DIR',
                help='Directory for the editor type catalog sf_compile.json (default: the '
                     'directory shared by the enabled outputs)')
    _add_option(out, 'hash_path', default=None, metavar='DIR',
                help='Directory for the generation hash .structframe.hash (default: the first '
                     'enabled output directory)')

    gen = parser.add_argument_group('generated code')
    _add_option(gen, 'sdk', action='store_true',
                help='Also copy the SDK (transports, message router) for C++, Python, '
                     'TypeScript and JavaScript')
    _add_option(gen, 'sdk_embedded', action='store_true',
                help='Copy the embedded C++ SDK only (serial transport, no ASIO). Other '
                     'languages receive the full SDK')
    _add_option(gen, 'equality', action='store_true',
                help='Generate equality operators/methods for messages')
    _add_option(gen, 'generate_tests', action='store_true',
                help='Generate round-trip test programs with dummy values for every message')
    _add_option(gen, 'no_packed', action='store_true',
                help='Treat every message as variable so C/C++ encode field by field instead of '
                     'relying on packed struct layout (for targets without struct packing)')
    _add_option(gen, 'csharp_namespace', default='StructFrame', metavar='NS',
                help='Root namespace for generated C# code (default: StructFrame)')
    _add_option(gen, 'py_package', default=DEFAULT_PY_PACKAGE, metavar='NAME',
                help=f'Python package that holds the generated modules and the runtime, '
                     f'created inside the Python output directory (default: {DEFAULT_PY_PACKAGE})')
    _add_option(gen, 'name_overrides', default=None, metavar='FILE',
                help=('JSON file with explicit per-language name overrides, e.g. '
                      '{"csharp": {"BleMCuHost": "BleMcuHost"}}. Keys are source names '
                      '(Message, Message.field, Message.oneof.variant, Enum.ENTRY, ...), '
                      'optionally package-qualified; "all" applies to every language. '
                      'Wire layout is unaffected.'))

    run = parser.add_argument_group('run control')
    run.add_argument('--validate', action='store_true',
                     help='Check the schema (against every language unless some are selected) '
                          'without writing files')
    run.add_argument('--force', action='store_true',
                     help='Regenerate even when the schema, options and generator are unchanged')
    run.add_argument('--config', default=None, metavar='FILE',
                     help=f'Read options from a TOML file (default: ./{CONFIG_FILENAME} when no '
                          f'SCHEMA is given). Command-line options override it.')
    run.add_argument('-q', '--quiet', action='store_true',
                     help='Print only warnings and errors')
    run.add_argument('--debug', action='store_true',
                     help='Print the parsed model and cache decisions')
    return parser


def _option_dests(parser):
    """Map every option spelling (without dashes, '-' and '_' both accepted) to its dest."""
    dests = {'schema': 'filename'}
    for action in parser._actions:
        for opt in action.option_strings:
            if opt.startswith('--'):
                key = opt[2:].replace('-', '_')
                dests[key] = action.dest
    for key in ('help', 'version', 'config'):
        dests.pop(key, None)
    return dests


def load_config(path, parser):
    """Read a structframe.toml file into ``{dest: value}`` for ``parser.set_defaults``.

    Keys are the long option names (``lang``, ``out``, ``c-path``, ``equality``, ...) plus
    ``schema``; ``-`` and ``_`` are interchangeable. Relative paths are resolved against the
    file's directory.
    """
    try:
        import tomllib
    except ModuleNotFoundError:  # Python < 3.11
        try:
            import tomli as tomllib
        except ModuleNotFoundError:
            raise ConfigError(f"{path}: reading TOML needs Python 3.11+ or the 'tomli' package "
                              "(pip install tomli)") from None
    try:
        with open(path, 'rb') as f:
            data = tomllib.load(f)
    except OSError as err:
        raise ConfigError(f"{path}: {err.strerror or err}") from None
    except tomllib.TOMLDecodeError as err:
        raise ConfigError(f"{path}: {err}") from None

    dests = _option_dests(parser)
    flags = {a.dest for a in parser._actions if isinstance(a, argparse._StoreTrueAction)}
    base = os.path.dirname(os.path.abspath(path))
    result = {}
    for key, value in data.items():
        norm = key.replace('-', '_')
        dest = dests.get(norm)
        if dest is None:
            hint = _did_you_mean(norm, [k.replace('_', '-') for k in dests])
            raise ConfigError(f"{path}: unknown key '{key}'{hint}")
        if dest == 'lang':
            if isinstance(value, str):
                value = [value]
            if not (isinstance(value, list) and all(isinstance(v, str) for v in value)):
                raise ConfigError(f"{path}: '{key}' must be a string or a list of strings")
            value = [','.join(value)]
        elif dest in flags:
            if not isinstance(value, bool):
                raise ConfigError(f"{path}: '{key}' must be true or false")
        else:
            if not isinstance(value, str):
                raise ConfigError(f"{path}: '{key}' must be a string")
            if dest in _PATH_DESTS and not os.path.isabs(value):
                value = os.path.normpath(os.path.join(base, value))
        result[dest] = value
    return result


def _default_catalog_dir(args, default_langs):
    """Where sf_compile.json goes when --catalog-path is not given.

    The directory shared by the enabled outputs (``generated/`` for the default layout,
    ``OUT`` with ``--out``). When the outputs share nothing narrower than the working
    directory, the first output directory is used instead of writing into the working
    directory.
    """
    langs = enabled_languages(args)
    if args.out is not None:
        return args.out
    if not langs or all(lang in default_langs for lang in langs):
        return DEFAULT_OUT + '/'
    dirs = [os.path.abspath(DEFAULT_OUT if lang in default_langs else output_path(args, lang))
            for lang in langs]
    try:
        common = os.path.commonpath(dirs)
    except ValueError:  # different drives
        common = None
    cwd = os.path.abspath(os.getcwd())
    if common is None or common == cwd or cwd.startswith(common.rstrip(os.sep) + os.sep):
        return output_path(args, langs[0])
    return common


def resolve_args(parser, args):
    """Apply --lang and --out, and fill in default paths. Reports usage errors via parser."""
    for value in args.lang or []:
        for item in value.split(','):
            item = item.strip().lower()
            if not item:
                continue
            if item == 'all':
                for lang in LANG_KEYS:
                    setattr(args, 'build_' + lang, True)
                continue
            lang = _LANG_ALIASES.get(item, item)
            if lang not in LANG_KEYS:
                parser.error(f"unknown language '{item}' in --lang "
                             f"(choose from {', '.join(LANG_KEYS)}, all)")
            setattr(args, 'build_' + lang, True)

    default_langs = set()
    for lang in LANG_KEYS:
        if output_path(args, lang) is None:
            if args.out is None:
                # Same spelling as before --out existed, so the generation hash is unchanged.
                path = f'{DEFAULT_OUT}/{lang}/'
                default_langs.add(lang)
            else:
                path = os.path.join(args.out, lang)
            setattr(args, lang + '_path', path)
    if args.catalog_path is None:
        args.catalog_path = _default_catalog_dir(args, default_langs)
    return args


def parse_args(parser, argv):
    """Parse argv, merging a config file (explicit --config, or ./structframe.toml when no
    schema is given) underneath the command line."""
    args = parser.parse_args(argv)
    config_path = args.config
    if config_path is None and args.filename is None and os.path.isfile(CONFIG_FILENAME):
        config_path = CONFIG_FILENAME
    if config_path is not None:
        parser.set_defaults(**load_config(config_path, parser))
        args = parser.parse_args(argv)
    return resolve_args(parser, args)


# Kept for code that imported the module-level parser.
parser = build_parser()


_SYNTAX_ERROR_RE = re.compile(r"^line \d+:\d+ ", re.M)


def _install_line_tracking():
    """Record the source line of every AST node the parser builds (as ``_sf_line``).

    proto-schema-parser's AST carries no positions. Its visitor sees the ANTLR context of
    each node, so wrapping ``visit`` lets error messages say ``file:line``. If a future
    parser version changes this internal API, errors simply lose their line numbers.
    """
    ctor = getattr(_psp_parser, "_ASTConstructor", None)
    if ctor is None or getattr(ctor, "_sf_line_tracking", False):
        return
    original = ctor.visit

    def visit(self, tree):
        node = original(self, tree)
        start = getattr(tree, "start", None)
        if start is not None and hasattr(node, "__dataclass_fields__") and not hasattr(node, "_sf_line"):
            try:
                node._sf_line = start.line
            except (AttributeError, TypeError):
                pass
        return node

    ctor.visit = visit
    ctor._sf_line_tracking = True


def location(obj, line=None):
    """``path:line: `` for a parsed element (or just ``path: ``), for error messages."""
    path = getattr(obj, "source_file", None)
    line = line if line is not None else getattr(obj, "line", None)
    if path and line:
        return f"{path}:{line}: "
    return f"{path}: " if path else ""


def _parse_schema_text(text, filename):
    """Parse schema text, treating any ANTLR syntax error as fatal.

    proto-schema-parser prints syntax errors to stderr and then carries on with
    a partial AST, which used to produce "successful" generation of a
    truncated schema. Capture that output and fail instead. Returns the parsed
    file, or None after printing the errors.
    """
    _install_line_tracking()
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured):
        result = Parser().parse(text)
    errors = captured.getvalue()
    if _SYNTAX_ERROR_RE.search(errors):
        print(f"Error: syntax error in {filename}:")
        for line in errors.strip().splitlines():
            print(f"  {line}")
        return None
    if errors.strip():
        sys.stderr.write(errors)
    return result


_parser_checked = False


def _warn_if_parser_lacks_inline_comments():
    """Comment ownership needs ``ast.Comment.inline`` (proto-schema-parser >= 2.0.0).

    Older parsers do not expose it, which would silently attach same-line
    trailing comments to the *next* declaration. Warn once instead.
    """
    global _parser_checked
    if _parser_checked:
        return
    _parser_checked = True
    fields = getattr(ast.Comment, '__dataclass_fields__', None)
    if fields is not None and 'inline' not in fields:
        print("Warning: proto-schema-parser < 2.0.0 detected; same-line trailing comments "
              "will not be attributed correctly. Upgrade with: pip install -U 'proto-schema-parser>=2.0.0'",
              file=sys.stderr)


def parseFile(filename, base_path=None, importing_package=None):
    """Parse a proto file and handle imports recursively.

    Args:
        filename: Path to the proto file to parse
        base_path: Base directory for resolving relative imports (defaults to filename's directory)
        importing_package: Name of the package that is importing this file (for tracking imports)

    Returns:
        bool: True if parsing succeeded, False otherwise
    """
    _warn_if_parser_lacks_inline_comments()

    # Convert to absolute path for circular import detection
    abs_filename = os.path.abspath(filename)

    if not processed_file and not packages and not package_imports:
        file_to_package.clear()
        pending_package_imports.clear()

    # Avoid circular imports
    if abs_filename in processed_file:
        return True

    processed_file.append(abs_filename)

    # Set base path for resolving imports
    if base_path is None:
        base_path = os.path.dirname(abs_filename)

    try:
        with open(abs_filename, "r", encoding="utf-8") as f:
            text = f.read()
        result = _parse_schema_text(text, filename)
        if result is None:
            return False
    except FileNotFoundError:
        print(f"Error: Could not find file {filename}")
        return False
    except UnicodeDecodeError as e:
        print(f"Error: {filename} is not valid UTF-8: {e}")
        return False
    except (OSError, ValueError, TypeError, SyntaxError, RuntimeError) as e:
        print(f"Error parsing file {filename}: {e}")
        return False

    foundPackage = False
    package_name = ""
    # Own-line comments seen before the ``package`` statement document the
    # file; once the package is known, comment ownership follows the usual
    # leading/trailing rules via _DocCollector.
    file_header = []
    docs = _DocCollector()
    pending_imports = []

    def record_package_import(importer, import_path):
        imported_abs_path = os.path.abspath(import_path)
        imported_package_name = file_to_package.get(imported_abs_path)
        if not imported_package_name or importer == imported_package_name:
            return False
        if importer not in package_imports:
            package_imports[importer] = []
        if imported_package_name not in package_imports[importer]:
            package_imports[importer].append(imported_package_name)
        return True

    for e in result.file_elements:
        if (type(e) == ast.Package):
            if foundPackage:
                print(
                    f"Multiple Package declaration found in file {filename} - {package_name}")
                return False
            foundPackage = True
            package_name = e.name
            if package_name not in packages:
                packages[package_name] = Package(package_name)
            packages[package_name].add_file_docs(abs_filename, file_header)
            file_header = []
            docs.statement()
            file_to_package[abs_filename] = package_name
            # Track import relationship if this file was imported
            if importing_package and importing_package != package_name:
                record_package_import(importing_package, abs_filename)
                for pending_import in pending_imports:
                    record_package_import(package_name, pending_import)
                pending_imports.clear()

        elif (type(e) == ast.Import):
            # Handle import statements
            docs.statement()
            import_file = e.name

            # Try to resolve import path relative to base_path first
            import_path_base = os.path.join(base_path, import_file)
            import_path_current = os.path.join(
                os.path.dirname(abs_filename), import_file)

            if os.path.exists(import_path_base):
                import_path = import_path_base
            elif os.path.exists(import_path_current):
                import_path = import_path_current
            else:
                print(
                    f"Error: Could not find imported file '{import_file}' from {filename}")
                print(f"  Tried: {import_path_base}")
                print(f"  Tried: {import_path_current}")
                return False

            imported_abs_path = os.path.abspath(import_path)
            if foundPackage and package_name:
                if not record_package_import(package_name, imported_abs_path):
                    pending_package_imports.append((package_name, imported_abs_path))
            else:
                pending_imports.append(imported_abs_path)

            # Recursively parse the imported file, passing current package as importer
            if not parseFile(import_path, base_path, package_name):
                print(f"Error: Failed to parse imported file {import_file}")
                return False

        elif (type(e) == ast.Option):
            # Handle file-level options (like pkgid)
            docs.statement()
            if not foundPackage:
                print(
                    f"Option {e.name} found before package declaration in {filename}")
                return False
            if e.name == "pkgid":
                if not validate_package_id(package_name, e.value, filename):
                    return False

        elif (type(e) == ast.Enum):
            if not foundPackage:
                print(f"Enum found before package declaration in {filename}")
                return False
            if not packages[package_name].addEnum(e, docs.take(), source_file=abs_filename):
                enum_obj = packages[package_name].enums.get(e.name)
                line = getattr(enum_obj, 'error_line', None) or getattr(e, '_sf_line', None)
                print(f"{abs_filename}:{line}: error in enum {e.name} (package {package_name})"
                      if line else f"Enum Error in Package: {package_name}  FileName: {filename} EnumName: {e.name}")
                return False
            docs.declared(packages[package_name].enums[e.name])

        elif (type(e) == ast.Message):
            if not foundPackage:
                print(
                    f"Message found before package declaration in {filename}")
                return False
            if not packages[package_name].addMessage(e, docs.take(), source_file=abs_filename):
                msg_obj = packages[package_name].messages.get(e.name)
                line = getattr(msg_obj, 'error_line', None) or getattr(e, '_sf_line', None)
                print(f"{abs_filename}:{line}: error in message {e.name} (package {package_name})"
                      if line else f"Message Error in Package: {package_name}  FileName: {filename} MessageName: {e.name}")
                return False
            docs.declared(packages[package_name].messages[e.name])

        elif (type(e) == ast.Comment):
            if foundPackage:
                docs.comment(e)
            elif not getattr(e, 'inline', False):
                file_header.append(e.text)

    if foundPackage and pending_imports:
        for pending_import in pending_imports:
            if not record_package_import(package_name, pending_import):
                pending_package_imports.append((package_name, pending_import))

    return True


def validate_package_id(package_name, new_id, filename):
    """Validate package ID assignment.

    Args:
        package_name: Name of the package
        new_id: Package ID being assigned
        filename: File where the assignment occurs

    Returns:
        bool: True if valid, False if conflict detected
    """
    if isinstance(new_id, bool) or not isinstance(new_id, int):
        print(f"Error: Package '{package_name}' has invalid pkgid {new_id!r} in "
              f"{filename}: must be an integer in range 0-255")
        return False

    current_id = packages[package_name].package_id

    if current_id is not None:
        # Check if this is a conflicting value
        if current_id != new_id:
            print(
                f"Error: Package '{package_name}' has conflicting package IDs:")
            print(f"  Already defined as: {current_id}")
            print(f"  Trying to redefine as: {new_id} in {filename}")
            return False
        # Same value - this is OK (multiple files in same package)
    else:
        # First assignment
        packages[package_name].package_id = new_id
        packages[package_name].package_id_explicit = True

    return True


def apply_package_id_inheritance():
    """Apply package ID inheritance rules.

    After all files are parsed, if an imported package has no package ID,
    it inherits the package ID from the importing package.

    Returns:
        bool: True if successful, False if conflicts detected
    """
    # Iterate through import relationships
    for importing_pkg, imported_pkgs in package_imports.items():
        importing_pkg_id = packages[importing_pkg].package_id

        for imported_pkg in imported_pkgs:
            imported_pkg_id = packages[imported_pkg].package_id

            # If imported package has no ID, inherit from importing package
            if imported_pkg_id is None:
                if importing_pkg_id is not None:
                    # Inheritance: imported package gets the importing package's ID
                    packages[imported_pkg].package_id = importing_pkg_id
                    packages[imported_pkg].package_id_explicit = False
                # else: Neither package has an ID - this will be caught by validatePackages if needed
            # If both packages have IDs, they are validated separately
            # Note: Same package name with different IDs is caught by validate_package_id()
            # during parsing, not here

    return True


def validate_packages(debug=False):
    """Validate all packages and enforce multi-package rules."""

    # Apply package ID inheritance first
    if not apply_package_id_inheritance():
        return False

    # Resolve deferred import edges now that all package/file mappings exist.
    for importing_pkg, imported_abs_path in pending_package_imports:
        imported_pkg = file_to_package.get(os.path.abspath(imported_abs_path))
        if imported_pkg and importing_pkg != imported_pkg:
            if importing_pkg not in package_imports:
                package_imports[importing_pkg] = []
            if imported_pkg not in package_imports[importing_pkg]:
                package_imports[importing_pkg].append(imported_pkg)

    # Reject package import cycles (A -> B -> A).
    visiting = set()
    visited = set()

    def dfs(pkg_name, stack):
        if pkg_name in visiting:
            cycle_start = stack.index(pkg_name)
            cycle = stack[cycle_start:] + [pkg_name]
            print("Error: circular package import detected: " + " -> ".join(cycle))
            return False
        if pkg_name in visited:
            return True

        visiting.add(pkg_name)
        stack.append(pkg_name)
        for dep in package_imports.get(pkg_name, []):
            if dep in packages and not dfs(dep, stack):
                return False
        stack.pop()
        visiting.remove(pkg_name)
        visited.add(pkg_name)
        return True

    for pkg_name in sorted(packages):
        if not dfs(pkg_name, []):
            return False

    # Reject duplicate explicit package IDs across compiled packages.
    seen_pkg_ids = {}
    for pkg_name in sorted(packages):
        pkg = packages[pkg_name]
        if pkg.package_id is None or not pkg.package_id_explicit:
            continue
        if pkg.package_id in seen_pkg_ids:
            other = seen_pkg_ids[pkg.package_id]
            print(
                f"Error: duplicate package ID {pkg.package_id} used by packages '{other}' and '{pkg_name}'")
            return False
        seen_pkg_ids[pkg.package_id] = pkg_name

    # Check if multiple packages exist
    if len(packages) > 1:
        # When multiple packages are being compiled, they must have package IDs
        packages_without_ids = [
            name for name, pkg in packages.items() if pkg.package_id is None]
        if packages_without_ids:
            print(f"Error: Multiple packages are being compiled, but the following packages do not have package IDs assigned:")
            for pkg_name in packages_without_ids:
                print(f"  - {pkg_name}")
            print(f"\nWhen compiling multiple packages, each package must specify 'option pkgid = N;' where N is 0-255.")
            print(f"This ensures unique message IDs across all packages using the format: (package_id << 8) | msg_id")
            return False

    # Validate each package
    for key, value in packages.items():
        if not value.validate_package(packages, debug):
            print(f"Failed To Validate Package: {key}")
            return False

    # Reject effective message-ID collisions across packages. Packages that
    # inherit a pkgid from their importer share that pkgid, so msgid 5 in the
    # importer and msgid 5 in the inheriting package would both be 0x<pkgid>05.
    effective_ids = {}
    for pkg_name in sorted(packages):
        pkg = packages[pkg_name]
        for msg_name, msg in pkg.messages.items():
            if msg.id is None:
                continue
            effective = ((pkg.package_id << 8) | msg.id) if pkg.package_id is not None else msg.id
            if effective in effective_ids:
                other = effective_ids[effective]
                print(f"Error: message ID collision: {other} and {pkg_name}.{msg_name} both "
                      f"have effective ID 0x{effective:04X} "
                      f"(package ID {pkg.package_id}, msgid {msg.id}). Packages without their "
                      f"own 'option pkgid' inherit their importer's, so give '{pkg_name}' an "
                      f"explicit pkgid or renumber the message.")
                return False
            effective_ids[effective] = f"{pkg_name}.{msg_name}"

    return True


def needs_extended_payload_types():
    """
    Determine if only Extended* payload types should be used.

    Returns True if:
    - Any package has a package ID, OR
    - Any message ID is >= 256

    When this returns True, only Extended* payload types should be generated:
    - ExtendedMsgIds, Extended, ExtendedMinimal, ExtendedMultiSystemStream, ExtendedLength

    Standard payload types (Minimal, Default, SysComp, Seq, MultiSystemStream)
    and their profiles (ProfileStandard, ProfileSensor, ProfileIPC) should not be generated.
    """
    for pkg_name, pkg in packages.items():
        # Check if package has package ID
        if pkg.package_id is not None:
            return True

        # Check if any message ID >= 256
        for msg_name, msg in pkg.messages.items():
            if msg.id is not None and msg.id >= 256:
                return True

    return False


def _message_dependencies(msg, pkg):
    """Names of same-package messages that *msg* embeds (via fields or oneof variants)."""
    deps = set()
    fields = list(msg.fields.values())
    for oneof in msg.oneofs.values():
        fields.extend(oneof.fields.values())
    for field in fields:
        ref = field.type_ref
        if isinstance(ref, Message) and pkg.messages.get(ref.name) is ref and ref is not msg:
            deps.add(ref.name)
    return deps


def dependency_ordered_messages(pkg):
    """Return the package's messages as ``[(name, Message), ...]`` in a stable order.

    Messages are listed dependencies-first (a message that embeds another
    follows it); messages that are not ordered relative to each other are
    sorted by name.  The result therefore depends only on the schema, never on
    the order declarations were written, split across files, or imported.
    """
    import heapq

    names = list(pkg.messages.keys())
    deps = {name: _message_dependencies(pkg.messages[name], pkg) for name in names}
    dependants = {name: [] for name in names}
    remaining = {}
    for name in names:
        remaining[name] = len(deps[name])
        for dep in deps[name]:
            dependants[dep].append(name)

    ready = [name for name in names if remaining[name] == 0]
    heapq.heapify(ready)
    ordered = []
    while ready:
        name = heapq.heappop(ready)
        ordered.append(name)
        for dependant in dependants[name]:
            remaining[dependant] -= 1
            if remaining[dependant] == 0:
                heapq.heappush(ready, dependant)

    # Anything left is part of a dependency cycle (rejected by validation, but
    # stay deterministic regardless).
    ordered.extend(sorted(name for name in names if name not in set(ordered)))
    return [(name, pkg.messages[name]) for name in ordered]


def normalize_output_order():
    """Put parsed declarations into a stable, dependency-aware order.

    Parse and import order must not influence generated output, otherwise
    reorganising or splitting source files churns every generated file.
    After this runs:

    * packages are in dependency-first topological order (name tie-break)
    * each package's import list follows that same order
    * enums are sorted by name
    * messages are listed dependencies-first, then by name

    Order that is part of the schema is left untouched: message fields,
    oneof variants (``field_order`` discriminators depend on them), enum
    entries and message-scoped enums keep their declaration order.
    """
    order = topological_sort_packages(packages, package_imports)
    rank = {name: index for index, name in enumerate(order)}

    reordered = [(name, packages[name]) for name in order]
    packages.clear()
    packages.update(reordered)

    for pkg_name, imported in list(package_imports.items()):
        package_imports[pkg_name] = sorted(
            imported, key=lambda name: (rank.get(name, len(rank)), name))

    for pkg in packages.values():
        pkg.enums = {name: pkg.enums[name] for name in sorted(pkg.enums)}
        pkg.messages = dict(dependency_ordered_messages(pkg))


@contextlib.contextmanager
def language_model(lang, name_overrides):
    """Temporarily swap ``packages`` for the model renamed for *lang*.

    Generators read the module-level ``packages`` dict.  When name overrides
    exist for *lang*, they run against a renamed deep copy (same wire layout,
    different declaration names); otherwise nothing changes.
    """
    if name_overrides is None or not name_overrides.has_language(lang):
        yield
        return
    original = dict(packages)
    renamed = name_overrides.apply(lang, original)
    packages.clear()
    packages.update(renamed)
    try:
        yield
    finally:
        packages.clear()
        packages.update(original)


def printPackages():
    for key, value in packages.items():
        print(value)


def topological_sort_packages(pkgs, pkg_imports):
    """Return package names in dependency-first topological order (Kahn's BFS).

    Packages with no dependencies come first so that an aggregate include file
    can list them in the order a compiler needs to see them.

    Args:
        pkgs:        dict {pkg_name: Package}
        pkg_imports: dict {pkg_name: [imported_pkg_name, ...]}

    Returns:
        list of package names in topological order
    """
    from collections import deque

    # Build in-degree count and adjacency list (dependency → dependant)
    in_degree = {name: 0 for name in pkgs}
    dependants = {name: [] for name in pkgs}

    for pkg_name, deps in pkg_imports.items():
        if pkg_name not in pkgs:
            continue
        for dep in deps:
            if dep not in pkgs:
                continue
            in_degree[pkg_name] += 1
            dependants[dep].append(pkg_name)

    # Start with packages that have no dependencies
    queue = deque(name for name, deg in in_degree.items() if deg == 0)
    # Sort for determinism when multiple packages have the same degree
    queue = deque(sorted(queue))
    result = []

    while queue:
        pkg_name = queue.popleft()
        result.append(pkg_name)
        for dep in sorted(dependants[pkg_name]):
            in_degree[dep] -= 1
            if in_degree[dep] == 0:
                queue.append(dep)

    # Append any remaining packages (handles cycles or disconnected nodes)
    for name in sorted(pkgs):
        if name not in result:
            result.append(name)

    return result


def generate_lsp_file_strings(catalog_path, build_flags=None, paths=None, name_overrides=None,
                              py_package=DEFAULT_PY_PACKAGE):
    """Generate a single JSON catalog file for language-server navigation.

    Produces one language-agnostic ``sf_compile.json`` that lists
    every message, nested message, and enum defined across all packages,
    together with the source ``.proto`` file, generated file path, and
    language-specific element name for each enabled language.

    Args:
        catalog_path: Directory where ``sf_compile.json`` will be written.
        build_flags:  dict {lang: bool}  e.g. {'c': True, 'cpp': False, ...}
        paths:        dict {lang: str}   absolute output directory for each language
        name_overrides: optional NameOverrides; element names follow them per language

    Returns:
        dict {filename: content}
    """
    if build_flags is None:
        build_flags = {}
    if paths is None:
        paths = {}

    abs_catalog = os.path.abspath(catalog_path)

    def _relpath(abs_file):
        """Return a forward-slash relative path from catalog_path to abs_file."""
        try:
            rel = os.path.relpath(abs_file, abs_catalog)
        except ValueError:
            # Different drives on Windows — fall back to absolute path
            rel = abs_file
        return rel.replace(os.sep, '/')

    def _pkg_generated_files(pkg_name):
        """Return {lang: relative_path} for package-level generated files."""
        result = {}
        if build_flags.get('c'):
            result['c'] = _relpath(os.path.join(os.path.abspath(paths['c']),
                                                f'{pkg_name}.structframe.h'))
        if build_flags.get('cpp'):
            result['cpp'] = _relpath(os.path.join(os.path.abspath(paths['cpp']),
                                                  f'{pkg_name}.structframe.hpp'))
        if build_flags.get('ts'):
            result['ts'] = _relpath(os.path.join(os.path.abspath(paths['ts']),
                                                 f'{pkg_name.replace("_", "-")}.structframe.ts'))
        if build_flags.get('js'):
            result['js'] = _relpath(os.path.join(os.path.abspath(paths['js']),
                                                 f'{pkg_name.replace("_", "-")}.structframe.js'))
        if build_flags.get('py'):
            result['py'] = _relpath(os.path.join(os.path.abspath(paths['py']),
                                                 py_package, f'{pkg_name}.py'))
        if build_flags.get('gql'):
            result['gql'] = _relpath(os.path.join(os.path.abspath(paths['gql']),
                                                  f'{pkg_name}.graphql'))
        if build_flags.get('rust'):
            result['rust'] = _relpath(os.path.join(os.path.abspath(paths['rust']),
                                                   f'{pkg_name}.structframe.rs'))
        return result

    def _ov(lang, pkg_name, *path):
        """Name of the declaration at *path* in *lang* (honours --name_overrides)."""
        if name_overrides is None:
            return path[-1]
        return name_overrides.rename(lang, pkg_name, path)

    def _lang_symbol_info(lang, pkg, symbol_name):
        """Return language-specific namespace, element, and qualified element."""
        pkg_name = pkg.name
        symbol_name = _ov(lang, pkg_name, symbol_name)
        pkg_pascal = pascal_case(pkg_name)

        if lang == 'c':
            element = f'{pkg_pascal}{symbol_name}'
            return None, element, element

        if lang == 'cpp':
            # C++ always uses structframe::<pkg_name> nested namespace
            namespace = f'structframe::{camel_to_snake_case(pkg_name)}'
            element = symbol_name
            return namespace, element, f'{namespace}::{element}'

        if lang in ('ts', 'js'):
            element = symbol_name
            return None, element, element

        if lang == 'gql':
            element = f'{pkg_pascal}{symbol_name}'
            return None, element, element

        if lang == 'py':
            namespace = f'{py_package}.{pkg_name}'
            element = symbol_name
            return namespace, element, f'{namespace}.{element}'

        if lang == 'rust':
            namespace = pkg_name
            element = symbol_name
            return namespace, element, f'{namespace}::{element}'

        if lang == 'csharp':
            namespace = f'StructFrame.{pkg_pascal}'
            element = symbol_name
            return namespace, element, f'{namespace}.{element}'

        return None, symbol_name, symbol_name

    def _generated_file_entries(pkg, symbol_name, base_generated_files):
        """Return {lang: {path, namespace, element, qualified_element}} catalog entries."""
        entries = {}
        for lang, rel_path in base_generated_files.items():
            namespace, element, qualified_element = _lang_symbol_info(
                lang, pkg, symbol_name)
            entries[lang] = {
                "path": rel_path,
                "namespace": namespace,
                "element": element,
                "qualified_element": qualified_element,
            }
        return entries

    ordered = topological_sort_packages(packages, package_imports)

    messages = []
    enums = []

    for pkg_name in ordered:
        if pkg_name not in packages:
            continue
        pkg = packages[pkg_name]
        pkg_files = _pkg_generated_files(pkg_name)
        pkg_pascal = pascal_case(pkg_name)

        for msg_name, msg in pkg.messages.items():
            gen_files = dict(pkg_files)
            # C#: one file per message — {PascalPkg}/Messages/{MsgName}.cs
            if build_flags.get('csharp'):
                gen_files['csharp'] = _relpath(
                    os.path.join(os.path.abspath(paths['csharp']),
                                 pkg_pascal, 'Messages', f'{_ov("csharp", pkg_name, msg_name)}.cs'))

            # Build oneof summary list
            oneof_entries = []
            for oneof_name, oneof in msg.oneofs.items():
                variant_list = [
                    {"disc_val": dv, "field_name": fn, "field_size": fs}
                    for dv, fn, fs in oneof.variant_info
                ] if oneof.variant_info else []
                oneof_entries.append({
                    "name": oneof_name,
                    "size": oneof.size,
                    "base_size": oneof.base_size,
                    "variable": oneof.variable,
                    "auto_discriminator": oneof.auto_discriminator,
                    "discriminator_type": oneof.discriminator_type,
                    "min_size_override": oneof.min_size_override,
                    "max_size_override": oneof.max_size_override,
                    "variants": variant_list,
                })

            # magic_bytes is a (byte1, byte2) tuple after validate(); convert to list
            magic = list(msg.magic_bytes) if msg.magic_bytes is not None else None

            messages.append({
                "name": msg_name,
                "package": pkg_name,
                "source_file": os.path.basename(msg.source_file) if msg.source_file else None,
                "msgid": msg.id,
                "max_size": msg.size,
                "base_size": msg.base_size,
                "min_size": msg.min_size,
                "is_variable": msg.variable,
                "is_envelope": msg.is_envelope,
                "extensions_start": msg.extensions_start if msg.extensions_start else None,
                "magic_bytes": magic,
                "oneofs": oneof_entries if oneof_entries else None,
                "generated_files": _generated_file_entries(
                    pkg, msg_name, gen_files
                ),
            })

            # Nested enums (message-scoped): appear in the same file as the parent message
            for nested_enum_name, nested_enum in msg.enums.items():
                nested_gen_files = {}
                for lang, rel_path in gen_files.items():
                    # Nested enums share the parent message's generated file
                    nested_gen_files[lang] = rel_path

                def _nested_enum_symbol_info(lang, pkg_, msg_name_, enum_name_):
                    pkg_name_ = pkg_.name
                    source_msg_name_ = msg_name_
                    enum_name_ = _ov(lang, pkg_name_, msg_name_, enum_name_)
                    msg_name_ = _ov(lang, pkg_name_, msg_name_)
                    pkg_pascal_ = pascal_case(pkg_name_)
                    flat_name = f'{pkg_pascal_}{msg_name_}{enum_name_}'

                    if lang == 'c':
                        return None, flat_name, flat_name

                    if lang == 'cpp':
                        # C++ always uses structframe::<pkg_name> nested namespace
                        ns = f'structframe::{camel_to_snake_case(pkg_name_)}'
                        element = f'{msg_name_}::{enum_name_}'
                        return ns, element, f'{ns}::{msg_name_}::{enum_name_}'

                    if lang == 'py':
                        ns = f'{py_package}.{pkg_name_}'
                        return ns, enum_name_, f'{ns}.{msg_name_}.{enum_name_}'

                    if lang in ('ts', 'js'):
                        element = f'{msg_name_}{enum_name_}'
                        return None, element, element

                    if lang == 'rust':
                        element = f'{msg_name_}{enum_name_}'
                        ns = pkg_name_
                        return ns, element, f'{ns}::{element}'

                    if lang == 'csharp':
                        ns = f'StructFrame.{pkg_pascal_}'
                        # Apply the same collision-avoidance logic as csharp_gen.py:
                        # if the enum name matches a field property name, add 'Enum' suffix
                        field_property_names = {
                            pascal_case(_ov('csharp', pkg_name_, source_msg_name_, f))
                            for f in msg.fields}
                        effective_name = f'{enum_name_}Enum' if enum_name_ in field_property_names else enum_name_
                        return ns, effective_name, f'{ns}.{msg_name_}.{effective_name}'

                    return None, enum_name_, enum_name_

                nested_entries = {}
                for lang, rel_path in nested_gen_files.items():
                    namespace_, element_, qualified_ = _nested_enum_symbol_info(
                        lang, pkg, msg_name, nested_enum_name)
                    nested_entries[lang] = {
                        "path": rel_path,
                        "namespace": namespace_,
                        "element": element_,
                        "qualified_element": qualified_,
                    }

                enums.append({
                    "name": nested_enum_name,
                    "package": pkg_name,
                    "parent_message": msg_name,
                    "source_file": os.path.basename(msg.source_file) if msg.source_file else None,
                    "generated_files": nested_entries,
                })

        for enum_name, enum in pkg.enums.items():
            gen_files = dict(pkg_files)
            # C#: one file per enum — {PascalPkg}/Enums/{EnumName}.cs
            if build_flags.get('csharp'):
                gen_files['csharp'] = _relpath(
                    os.path.join(os.path.abspath(paths['csharp']),
                                 pkg_pascal, 'Enums', f'{_ov("csharp", pkg_name, enum_name)}.cs'))
            enums.append({
                "name": enum_name,
                "package": pkg_name,
                "source_file": os.path.basename(enum.source_file) if enum.source_file else None,
                "generated_files": _generated_file_entries(
                    pkg, enum_name, gen_files
                ),
            })

    catalog = {
        "messages": messages,
        "enums": enums,
    }

    catalog_file = os.path.join(catalog_path, "sf_compile.json")
    return {catalog_file: json.dumps(catalog, indent=2) + "\n"}


def generateCFileStrings(path, equality=False, generate_tests=False):
    out = {}
    for key, value in packages.items():
        name = os.path.join(path, value.name + ".structframe.h")
        imported = package_imports.get(value.name, [])
        data = ''.join(FileCGen.generate(
            value, imported_packages=imported, equality=equality))
        out[name] = data

        if generate_tests:
            test_name = os.path.join(path, value.name + ".tests.h")
            out[test_name] = ''.join(TestCGen.generate(value))
            roundtrip_name = os.path.join(path, "test_roundtrip_" + value.name + ".c")
            out[roundtrip_name] = ''.join(TestCGen.generate_roundtrip_main(value))

    if 'structframe_all' not in {camel_to_snake_case(p.name) for p in packages.values()}:
        out[os.path.join(path, UMBRELLA_BASENAME + ".h")] = _umbrella_c_header()
    return out


# Umbrella header that includes every generated package header (C and C++).
UMBRELLA_BASENAME = "structframe_all"


def _umbrella_c_header():
    with_info = [p for p in packages.values() if p.messages]
    lines = ['/* Automatically generated struct frame header */\n',
             f'/* Generated by struct-frame {get_version()}. */\n\n',
             '/* Includes every package header generated together and looks message IDs up\n',
             ' * across all of them. */\n\n',
             '#pragma once\n']
    lines += [f'#include "{p.name}.structframe.h"\n' for p in packages.values()]
    lines += ['\n#ifdef __cplusplus\nextern "C" {\n#endif\n\n',
              '/* Message info (size, checksum magic bytes) for an ID from any package above.\n',
              ' * Effective IDs are unique across packages, so at most one package knows an ID.\n',
              ' * Pass this to the readers when frames of several packages share a stream. */\n',
              f'static inline bool {UMBRELLA_BASENAME}_get_message_info(uint16_t msg_id, '
              'message_info_t* info) {\n']
    if with_info:
        calls = [f'{camel_to_snake_case(p.name)}_get_message_info(msg_id, info)' for p in with_info]
        lines.append('    return ' + '\n        || '.join(calls) + ';\n')
    else:
        lines.append('    (void)msg_id;\n    (void)info;\n    return false;\n')
    lines += ['}\n\n#ifdef __cplusplus\n}\n#endif\n']
    return ''.join(lines)


def _umbrella_cpp_header():
    with_info = [p for p in packages.values() if p.messages]
    lines = ['/* Automatically generated struct frame header for C++ */\n',
             f'/* Generated by struct-frame {get_version()}. */\n\n',
             '/* Includes every package header generated together and looks message IDs up\n',
             ' * across all of them. */\n\n',
             '#pragma once\n',
             '#include <frame_base.hpp>\n']
    lines += [f'#include "{p.name}.structframe.hpp"\n' for p in packages.values()]
    lines += ['\nnamespace structframe {\n\n',
              '/* Message info (size, checksum magic bytes) for an ID from any package above.\n',
              ' * Effective IDs are unique across packages, so at most one package knows an ID.\n',
              ' * Pass it to the readers when frames of several packages share a stream:\n',
              ' *   ProfileStandardAccumulatingReader reader(structframe::get_message_info); */\n',
              'inline MessageInfo get_message_info(uint16_t msg_id) {\n']
    if with_info:
        lines.append('    MessageInfo info;\n')
        for p in with_info:
            ns = camel_to_snake_case(p.name)
            lines.append(f'    info = {ns}::get_message_info(msg_id);\n')
            lines.append('    if (info.valid) return info;\n')
        lines.append('    return info;\n')
    else:
        lines.append('    (void)msg_id;\n    return MessageInfo{};\n')
    lines += ['}\n\n}  // namespace structframe\n']
    return ''.join(lines)


def generateTsFileStrings(path, equality=False, generate_tests=False):
    import json as _json
    out = {}
    pkg_names = []
    for key, value in packages.items():
        kebab_name = value.name.replace('_', '-')
        name = os.path.join(path, kebab_name + ".structframe.ts")
        data = ''.join(FileTsGen.generate(
            value, use_class_based=True, packages=packages, equality=equality))
        out[name] = data
        pkg_names.append(kebab_name)

        # Generate test file alongside the package output if requested.
        # Mirrors the Python/C++ generator pattern: emit a runnable
        # ``test_roundtrip_<package>.ts`` containing dummy-value factories,
        # round-trip verifier, and a ``main`` entrypoint.
        if generate_tests:
            imported = package_imports.get(value.name, [])
            test_name = os.path.join(path, "test_roundtrip_" + value.name + ".ts")
            test_data = ''.join(TestTsGen.generate(value, imported_packages=imported))
            out[test_name] = test_data

    # index.ts barrel: the runtime's exports plus one namespace per generated package
    # (`export * as hello from ...`), so the output folder is a self-contained package.
    # Namespaces, because every package exports getMessageInfo / decodeMessage.
    out[os.path.join(path, 'index.ts')] = _barrel('ts', [
        f"export * as {value.name} from './{value.name.replace('_', '-')}.structframe';"
        for value in sorted(packages.values(), key=lambda p: p.name)])
    if pkg_names:

        pkg_json = {
            "exports": {
                ".": {
                    "import": "./index.ts",
                    "types": "./index.ts"
                }
            }
        }
        out[os.path.join(path, 'package.json')] = _json.dumps(
            pkg_json, indent=2) + '\n'

    return out


def generateJsFileStrings(path, equality=False, generate_tests=False):
    import json as _json
    out = {}
    pkg_names = []
    for key, value in packages.items():
        kebab_name = value.name.replace('_', '-')
        name = os.path.join(path, kebab_name + ".structframe.js")
        data = ''.join(FileJsGen.generate(
            value, use_class_based=True, packages=packages, equality=equality))
        out[name] = data
        pkg_names.append(kebab_name)

        # Generate test file alongside the package output if requested.
        # Mirrors the Python/C++ generator pattern: emit a runnable
        # ``test_roundtrip_<package>.js`` containing dummy-value factories,
        # round-trip verifier, and a ``main`` entrypoint.
        if generate_tests:
            imported = package_imports.get(value.name, [])
            test_name = os.path.join(path, "test_roundtrip_" + value.name + ".js")
            test_data = ''.join(TestJsGen.generate(value, imported_packages=imported))
            out[test_name] = test_data

    # index.js barrel: the runtime's exports plus one property per generated package.
    out[os.path.join(path, 'index.js')] = _barrel('js', [
        f"exports.{value.name} = require('./{value.name.replace('_', '-')}.structframe');"
        for value in sorted(packages.values(), key=lambda p: p.name)])

    return out


def _barrel(lang, package_lines):
    """The runtime's index.ts / index.js followed by the generated packages' exports."""
    runtime_index = os.path.join(_BOILERPLATE_ROOT, lang, 'index.' + lang)
    with open(runtime_index, 'r', encoding='utf-8') as f:
        text = f.read().rstrip('\n') + '\n'
    if package_lines:
        text += ('\n// Generated packages (struct-frame %s), one namespace per package:\n'
                 % get_version())
        text += '\n'.join(package_lines) + '\n'
    return text


def generatePyFileStrings(path, equality=False, generate_tests=False,
                          py_package=DEFAULT_PY_PACKAGE):
    out = {}

    # One package, PATH/<py_package>/, holds the runtime (copied in by main) and one module
    # per schema package. Everything inside imports relatively, so the package also works
    # nested inside the user's own package.
    generated_path = os.path.join(path, py_package)

    # __init__.py: the runtime's exports plus each schema package as a submodule.
    module_names = sorted(p.name for p in packages.values())
    out[os.path.join(generated_path, "__init__.py")] = _py_package_init(module_names)

    # Generate message files in the generated package
    for key, value in packages.items():
        name = os.path.join(generated_path, value.name + ".py")
        imported_pkg_names = package_imports.get(value.name, [])
        imported_pkg_objects = {n: packages[n]
                                for n in imported_pkg_names if n in packages}
        data = ''.join(FilePyGen.generate(value, imported_packages=imported_pkg_names,
                                          imported_package_objects=imported_pkg_objects, equality=equality))
        out[name] = data

        # Generate test file if requested
        if generate_tests:
            test_name = os.path.join(generated_path, value.name + "_tests.py")
            test_data = ''.join(TestPyGen.generate(value, imported_packages=imported_pkg_names))
            out[test_name] = test_data
            # Standalone round-trip runner: a tiny wrapper that just imports the
            # tests module and invokes its ``__main__`` entry point. Generated
            # alongside as ``test_roundtrip_<package>.py`` so the test runner
            # can launch it directly per .sf file.
            roundtrip_name = os.path.join(path, "test_roundtrip_" + value.name + ".py")
            out[roundtrip_name] = (
                '#!/usr/bin/env python3\n'
                '"""Standalone round-trip test runner for package \'%s\'.\n'
                'Generated by struct-frame %s. Exercises every message across all 5 frame profiles."""\n'
                'import os, runpy, sys\n'
                'HERE = os.path.dirname(os.path.abspath(__file__))\n'
                'sys.path.insert(0, HERE)\n'
                'runpy.run_module("%s.%s_tests", run_name="__main__")\n'
            ) % (value.name, get_version(), py_package, value.name)

    return out


def _py_package_init(module_names):
    """The runtime's __init__.py followed by imports of the generated modules."""
    runtime_init = os.path.join(_BOILERPLATE_ROOT, 'py', '__init__.py')
    with open(runtime_init, 'r', encoding='utf-8') as f:
        text = f.read().rstrip('\n') + '\n'
    if module_names:
        text += ('\n# Generated packages (struct-frame %s): `from <this package> import robot`, '
                 'then robot.Status.\n' % get_version())
        text += 'from . import %s\n' % ', '.join(module_names)
        text += '__all__ += [%s]\n' % ', '.join(repr(n) for n in module_names)
    return text


def check_python_package_names(py_package, generate_tests=False):
    """Errors for a --py-package value or schema package names the Python output cannot use."""
    errors = []
    if not py_package.isidentifier() or keyword.iskeyword(py_package):
        errors.append(f"--py-package '{py_package}' is not a valid Python identifier")
    elif py_package == 'struct_frame':
        errors.append("--py-package 'struct_frame' would shadow the struct-frame generator's own "
                      "package; choose another name")
    for pkg in packages.values():
        if pkg.name in PY_RUNTIME_MODULES:
            errors.append(f"package '{pkg.name}' has the same name as a module of the Python "
                          f"runtime ({', '.join(PY_RUNTIME_MODULES)}); rename the package")
        elif generate_tests and pkg.name.endswith('_tests') and pkg.name[:-6] in {
                p.name for p in packages.values()}:
            errors.append(f"package '{pkg.name}' collides with the generated test module of "
                          f"package '{pkg.name[:-6]}'")
    return errors


def generateCppFileStrings(path, equality=False, generate_tests=False):
    out = {}
    for key, value in packages.items():
        name = os.path.join(path, value.name + ".structframe.hpp")
        imported = package_imports.get(value.name, [])
        data = ''.join(FileCppGen.generate(
            value, imported_packages=imported, equality=equality))
        out[name] = data

        # Generate test file if requested
        if generate_tests:
            test_name = os.path.join(path, value.name + ".tests.hpp")
            test_data = ''.join(TestCppGen.generate(value))
            out[test_name] = test_data
            # Standalone round-trip main file with full ``main()``: compile this
            # single .cpp (with -I<gen_dir>) to get a binary that runs
            # round-trip tests for every message across all 5 profiles.
            roundtrip_name = os.path.join(path, "test_roundtrip_" + value.name + ".cpp")
            roundtrip_data = ''.join(TestCppGen.generate_roundtrip_main(value))
            out[roundtrip_name] = roundtrip_data
    out[os.path.join(path, UMBRELLA_BASENAME + ".hpp")] = _umbrella_cpp_header()
    return out


def generateRustFileStrings(path, equality=False, generate_tests=False):
    out = {}
    # Collect all packages being generated now
    new_package_names = []
    for key, value in packages.items():
        name = os.path.join(path, value.name + ".structframe.rs")
        data = ''.join(FileRustGen.generate(value, equality=equality))
        out[name] = data
        new_package_names.append(value.name)

        # Standalone round-trip binary per package: a single .rs file with
        # ``fn main()`` that exercises every message across all 5 profiles.
        if generate_tests:
            test_name = os.path.join(path, "test_roundtrip_" + value.name + ".rs")
            test_data = ''.join(TestRustGen.generate(value))
            out[test_name] = test_data

    out.update(rust_crate_files(path, new_package_names, generate_tests))
    return out


def rust_crate_files(path, new_package_names, generate_tests=False):
    """lib.rs and Cargo.toml for the generated crate.

    They cover every package in the directory, including ones written by earlier runs for other
    schemas, so they are rebuilt after stale outputs are pruned.
    """
    out = {}
    # Discover ALL .structframe.rs files in the output directory (from previous runs)
    all_package_names = list(new_package_names)
    if os.path.exists(path):
        for fname in sorted(os.listdir(path)):
            if fname.endswith('.structframe.rs'):
                pkg_name = fname[:-len('.structframe.rs')]
                if pkg_name not in all_package_names:
                    all_package_names.append(pkg_name)

    # Generate lib.rs and Cargo.toml for the generated crate. We also need to
    # account for test_roundtrip_*.rs files about to be written this run that
    # don't yet exist on disk: write them out first via the returned dict and
    # then synthesize the Cargo.toml binary list from the union.
    out[os.path.join(path, "lib.rs")] = FileRustGen.generate_lib_rs(
        sorted(all_package_names))
    cargo_toml = FileRustGen.generate_cargo_toml(output_path=path)
    # Append [[bin]] entries for newly-generated test files not yet on disk.
    if generate_tests:
        existing = set()
        if os.path.exists(path):
            existing = {f for f in os.listdir(path)
                        if f.startswith('test_roundtrip_') and f.endswith('.rs')}
        for pkg_name in new_package_names:
            fname = "test_roundtrip_" + pkg_name + ".rs"
            if fname not in existing:
                bin_name = fname[:-3]
                cargo_toml += f'\n[[bin]]\nname = "{bin_name}"\npath = "{fname}"\n'
    out[os.path.join(path, "Cargo.toml")] = cargo_toml
    return out


def generateCSharpFileStrings(path, equality=False, namespace='StructFrame.Generated', generate_tests=False):
    out = {}
    for key, value in packages.items():
        # Generate per-file output into a package subfolder
        pkg_folder = os.path.join(path, pascal_case(value.name))
        per_file = FileCSharpGen.generate_per_file(value, equality=equality)
        for filename, content in per_file.items():
            out[os.path.join(pkg_folder, filename)] = content

        # Always generate SDK interface (inside package folder)
        from struct_frame.csharp_sdk_interface_gen import generate_csharp_sdk_interface
        sdk_name = os.path.join(pkg_folder, "SdkInterface.cs")
        sdk_data = generate_csharp_sdk_interface(value)
        out[sdk_name] = sdk_data

        if generate_tests:
            test_name = os.path.join(pkg_folder, "test_roundtrip_" + value.name + ".cs")
            out[test_name] = ''.join(TestCSharpGen.generate(value, namespace=namespace))

    # Always generate .csproj so consumers can use <ProjectReference>
    csproj_name = os.path.join(path, "StructFrame.csproj")
    csproj_data = _generateCSharpProjectFile(namespace)
    out[csproj_name] = csproj_data

    return out


def _generateCSharpProjectFile(namespace):
    """Generate a .csproj file for the generated C# code.

    Produces an SDK-style class library project that auto-includes all .cs files.
    Consumers can reference this via <ProjectReference> instead of listing
    individual generated files.

    The Framework folder (Types, Framing, Profiles, Sdk core) and all generated
    message/SdkInterface files are always included. The Transports/ folder is
    always copied; transport implementations are excluded from compilation by
    default and enabled individually at build time:

      dotnet build -p:IncludeSerialTransport=true    # Serial (System.IO.Ports)
      dotnet build -p:IncludeNetCoreServer=true      # TCP, UDP, WebSocket (NetCoreServer)

    Both flags can be combined. The target framework defaults to net10.0 (net11.0+
    apps consume it as is). To build for other frameworks, pass
    -p:TargetFrameworks=net11.0 (plural: NuGet restore ignores a global
    TargetFramework, so -p:TargetFramework fails with NETSDK1005), or set
    TargetFramework/TargetFrameworks in a Directory.Build.props in the consuming
    repository:

      <Project>
        <PropertyGroup>
          <TargetFrameworks>net10.0;net11.0</TargetFrameworks>
        </PropertyGroup>
      </Project>
    """
    project_content = f'''<Project Sdk="Microsoft.NET.Sdk">

  <!-- Core library settings. TargetFramework is a default, not a pin: pass
       -p:TargetFrameworks=... (plural), or set TargetFramework or TargetFrameworks
       in a Directory.Build.props, to build for other frameworks. net11.0 and later
       apps consume the net10.0 build as is. The C# language version follows the
       target framework (C# 14 for net10.0) rather than the installed SDK. -->
  <PropertyGroup>
    <TargetFramework Condition="'$(TargetFramework)' == '' and '$(TargetFrameworks)' == ''">net10.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <RootNamespace>{namespace}</RootNamespace>
    <AllowUnsafeBlocks>true</AllowUnsafeBlocks>
    <!-- Ship StructFrame.xml so consumers get IntelliSense for the generated API.
         Not every generated member has a doc comment, so CS1591 is not reported. -->
    <GenerateDocumentationFile Condition="'$(GenerateDocumentationFile)' == ''">true</GenerateDocumentationFile>
    <NoWarn>$(NoWarn);CS1591</NoWarn>
    <IncludeSerialTransport Condition="'$(IncludeSerialTransport)' == ''">false</IncludeSerialTransport>
    <IncludeNetCoreServer Condition="'$(IncludeNetCoreServer)' == ''">false</IncludeNetCoreServer>
  </PropertyGroup>

  <!-- NuGet package metadata. Version and IsPackable keep the SDK defaults (1.0.0, true).
       Override these at pack time:  dotnet pack -p:Version=1.2.3 -p:PackageId=MyMessages
       Or set them in a Directory.Build.props in the consuming repository. -->
  <PropertyGroup>
    <PackageId Condition="'$(PackageId)' == ''">{namespace}</PackageId>
    <Authors Condition="'$(Authors)' == ''">{namespace}</Authors>
    <Description Condition="'$(Description)' == ''">Generated message serialization library produced by struct-frame.</Description>
    <PackageTags Condition="'$(PackageTags)' == ''">struct-frame;serialization;generated</PackageTags>
    <PackageLicenseExpression Condition="'$(PackageLicenseExpression)' == ''">MIT</PackageLicenseExpression>
    <RepositoryType Condition="'$(RepositoryType)' == ''">git</RepositoryType>
  </PropertyGroup>

  <!-- Reproducible builds, symbol packages and Source Link. Builds are deterministic
       by default. ContinuousIntegrationBuild also normalizes source paths; CI=true
       covers GitHub Actions and most CI services, TF_BUILD covers Azure Pipelines.
       Source Link needs no PackageReference: the .NET SDK has it built in (GitHub,
       Azure Repos, GitLab, Bitbucket). Adding a Microsoft.SourceLink.* 8.x package
       replaces the SDK's copy and pulls in Microsoft.Build.Tasks.Git 8.0.0, which is
       flagged by GHSA-23fw-v26w-5fgq. -->
  <PropertyGroup>
    <ContinuousIntegrationBuild Condition="'$(CI)' == 'true' or '$(TF_BUILD)' == 'true'">true</ContinuousIntegrationBuild>
    <IncludeSymbols>true</IncludeSymbols>
    <SymbolPackageFormat>snupkg</SymbolPackageFormat>
    <EmbedUntrackedSources>true</EmbedUntrackedSources>
    <PublishRepositoryUrl>true</PublishRepositoryUrl>
  </PropertyGroup>

  <!-- Define NETCORESERVER_AVAILABLE when NetCoreServer is enabled -->
  <PropertyGroup Condition="'$(IncludeNetCoreServer)' == 'true'">
    <DefineConstants>$(DefineConstants);NETCORESERVER_AVAILABLE</DefineConstants>
  </PropertyGroup>

  <!-- Never compile build intermediates or outputs. The SDK already excludes the
       default obj/ and bin/ via DefaultItemExcludes, so this is a no-op in a normal
       build. It matters when BaseIntermediateOutputPath is redirected (artifacts
       output, a Directory.Build.props override, or a nested project's obj landing
       inside this tree): a leftover AssemblyInfo.cs then gets globbed and the build
       fails with CS0579 duplicate-attribute errors that look nothing like the cause. -->
  <ItemGroup>
    <Compile Remove="**\\obj\\**" />
    <Compile Remove="**\\bin\\**" />
  </ItemGroup>

  <!-- Exclude all transports by default -->
  <ItemGroup>
    <Compile Remove="Framework\\Sdk\\Transports\\**" />
  </ItemGroup>

  <!-- Serial transport: SerialTransport.cs + System.IO.Ports package -->
  <ItemGroup Condition="'$(IncludeSerialTransport)' == 'true'">
    <Compile Include="Framework\\Sdk\\Transports\\SerialTransport.cs" />
    <PackageReference Include="System.IO.Ports" Version="10.0.0" />
  </ItemGroup>

  <!-- Network transports: TCP, UDP, WebSocket + NetCoreServer package -->
  <ItemGroup Condition="'$(IncludeNetCoreServer)' == 'true'">
    <Compile Include="Framework\\Sdk\\Transports\\TcpTransport.cs" />
    <Compile Include="Framework\\Sdk\\Transports\\UdpTransport.cs" />
    <Compile Include="Framework\\Sdk\\Transports\\WebSocketTransport.cs" />
    <PackageReference Include="NetCoreServer" Version="8.0.7" />
  </ItemGroup>

</Project>
'''
    return project_content


SCHEMA_DIFF_COMMANDS = ('diff', 'schema-diff')

# Order in which languages are generated and their runtimes copied.
_GENERATION_ORDER = ('c', 'ts', 'js', 'py', 'cpp', 'csharp', 'gql', 'rust')

_SDK_DIRS = ['struct_frame_sdk', 'Sdk']

# Runtime ("boilerplate") copied next to each language's generated code:
# lang -> names never copied (at any depth). GraphQL has no runtime. The optional SDK
# directory is copied separately, for _SDK_LANGS, by --sdk / --sdk-embedded.
_BOILERPLATE_EXCLUDES = {
    'c': _SDK_DIRS,
    # index.ts / index.js are generated (runtime barrel + the generated packages).
    'ts': _SDK_DIRS + ['index.ts'],
    # boilerplate/js/ is compiled from boilerplate/ts/ via:
    #   node_modules/.bin/tsc -p src/struct_frame/boilerplate/ts/tsconfig.cjs.json
    # Do not hand-edit boilerplate/js/; edit boilerplate/ts/ and recompile.
    'js': _SDK_DIRS + ['index.js'],
    # __init__.py is generated (runtime exports + the generated modules).
    'py': _SDK_DIRS + ['__init__.py'],
    'cpp': _SDK_DIRS,
    # C# always gets Framework/Sdk/Transports; the .csproj decides what compiles:
    #   -p:IncludeSerialTransport=true -> Serial (System.IO.Ports)
    #   -p:IncludeNetCoreServer=true   -> TCP, UDP, WebSocket (NetCoreServer)
    'csharp': [],
    # lib.rs and Cargo.toml are generated.
    'rust': _SDK_DIRS + ['lib.rs', 'Cargo.toml'],
}
_SDK_LANGS = ('ts', 'js', 'py', 'cpp')

_BOILERPLATE_ROOT = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'boilerplate')


def _generate_language(lang, path, args):
    """Return {filename: content} for one language."""
    opts = dict(equality=args.equality, generate_tests=args.generate_tests)
    if lang == 'c':
        return generateCFileStrings(path, **opts)
    if lang == 'ts':
        return generateTsFileStrings(path, **opts)
    if lang == 'js':
        return generateJsFileStrings(path, **opts)
    if lang == 'py':
        return generatePyFileStrings(path, py_package=args.py_package, **opts)
    if lang == 'cpp':
        return generateCppFileStrings(path, **opts)
    if lang == 'csharp':
        return generateCSharpFileStrings(path, namespace=args.csharp_namespace, **opts)
    if lang == 'rust':
        return generateRustFileStrings(path, **opts)
    if lang == 'gql':
        files = {}
        for value in packages.values():
            files[os.path.join(path, value.name + '.graphql')] = ''.join(FileGqlGen.generate(value))
        # One self-contained schema.graphql combining every package.
        files[os.path.join(path, 'schema.graphql')] = FileGqlGen.stitched(packages, get_version())
        return files
    raise ValueError(f"unknown language {lang!r}")


def _write_file(filename, filedata):
    dirname = os.path.dirname(filename)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)
    # Retry on transient PermissionError (e.g. Windows file lock from
    # the .NET build server or an IDE holding the .csproj open briefly).
    for attempt in range(5):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(filedata)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.5)


def copy_all_files(src_dir, dst_dir, exclude_dirs=None):
    """Copy every file and directory from src_dir to dst_dir.

    exclude_dirs: names skipped at any depth (e.g. ['struct_frame_sdk', 'Sdk']).
    """
    exclude_dirs = exclude_dirs or []
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    if not os.path.exists(src_dir):
        return
    ignore_fn = shutil.ignore_patterns(*exclude_dirs) if exclude_dirs else None
    for item in os.listdir(src_dir):
        if item in exclude_dirs:
            continue
        src_path = os.path.join(src_dir, item)
        dst_path = os.path.join(dst_dir, item)
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True, ignore=ignore_fn)
        elif os.path.isfile(src_path):
            shutil.copy2(src_path, dst_path)


def copy_sdk_files(lang, src_dir, dst_dir, embedded=False, include_asio=False):
    """Copy a language's SDK directory (struct_frame_sdk/, or Sdk/ for C#).

    For C++, ``embedded`` (or no ``include_asio``) leaves out ASIO and the network transports.
    """
    sdk_src = os.path.join(src_dir, "struct_frame_sdk")
    sdk_dst = os.path.join(dst_dir, "struct_frame_sdk")
    if not os.path.exists(sdk_src):
        sdk_src = os.path.join(src_dir, "Sdk")
        sdk_dst = os.path.join(dst_dir, "Sdk")
    if not os.path.exists(sdk_src):
        return
    if not os.path.exists(sdk_dst):
        os.makedirs(sdk_dst)

    exclude_items = []
    if lang == 'cpp' and (embedded or not include_asio):
        exclude_items = ['asio.hpp', 'asio', 'asio-repo', 'network_transports.hpp', 'sdk.hpp']

    # ASIO ships as a git submodule. Never copy the symlink or the multi-megabyte submodule
    # verbatim; copy just the headers from their real location below.
    asio_headers = os.path.join(sdk_src, 'asio-repo', 'asio', 'include', 'asio')
    copy_asio = lang == 'cpp' and 'asio' not in exclude_items and os.path.isdir(asio_headers)
    if copy_asio:
        exclude_items = list(exclude_items) + ['asio', 'asio-repo']

    for item in os.listdir(sdk_src):
        if item in exclude_items:
            continue
        src_path = os.path.join(sdk_src, item)
        dst_path = os.path.join(sdk_dst, item)
        if os.path.islink(src_path) and not os.path.exists(os.path.realpath(src_path)):
            continue  # broken symlink
        if os.path.isfile(src_path):
            shutil.copy2(src_path, dst_path)
        elif os.path.isdir(src_path):
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)

    if copy_asio:
        shutil.copytree(asio_headers, os.path.join(sdk_dst, 'asio'), dirs_exist_ok=True)


def main(argv=None):
    """Run the command line. ``argv`` defaults to ``sys.argv[1:]``; returns the exit status.

    Can be called repeatedly from Python, e.g. ``main(["robot.sf", "--lang", "py"])``.
    """
    argv = list(sys.argv[1:] if argv is None else argv)

    # ``struct-frame diff OLD NEW``: wire-compatibility check between two
    # schema revisions. A schema file that happens to be named "diff" still
    # generates code as before.
    # Leading global flags (currently only --debug) may precede the subcommand.
    lead = 0
    while lead < len(argv) and argv[lead] == '--debug':
        lead += 1
    if (lead < len(argv) and argv[lead] in SCHEMA_DIFF_COMMANDS
            and not os.path.isfile(argv[lead])):
        from struct_frame import schema_diff
        return schema_diff.main(argv[lead + 1:])

    reset_parse_state()
    cli = build_parser()
    try:
        args = parse_args(cli, argv)
    except ConfigError as err:
        print(f"struct-frame: error: {err}", file=sys.stderr)
        return 2

    if not args.filename:
        cli.error(f"no schema given: pass SCHEMA, or set 'schema' in {CONFIG_FILENAME}")
    langs = enabled_languages(args)
    if not args.validate and not langs:
        cli.error("no language selected: use --lang (e.g. --lang c,py) or --build-<lang>")

    def info(*items):
        if not args.quiet:
            print(*items)

    # Diagnostics from parsing and validation are errors when they fail: send them to
    # stderr so scripts and CI can separate them from normal output. On success the
    # buffered output (warnings, --debug detail) is replayed to stdout unchanged.
    parse_log = io.StringIO()
    with contextlib.redirect_stdout(parse_log):
        parsed_ok = parseFile(args.filename)
    if not parsed_ok:
        sys.stderr.write(parse_log.getvalue())
        print("Parsing failed", file=sys.stderr)
        return 1
    sys.stdout.write(parse_log.getvalue())

    # If --no_packed is set, mark every message as variable BEFORE validation so
    # that min_size and other variable-related metadata is computed correctly.
    # This causes serialization to be performed field-by-field instead of relying
    # on packed memory layout.
    if args.no_packed:
        for pkg in packages.values():
            for msg in pkg.messages.values():
                msg.variable = True
        if args.debug:
            print("--no_packed: all messages marked as variable")

    if args.validate:
        info("Running in validate mode - no files will be generated")

    valid = False
    validate_log = io.StringIO()
    try:
        with contextlib.redirect_stdout(validate_log):
            valid = validate_packages(args.debug)
    except RecursionError:
        sys.stderr.write(validate_log.getvalue())
        print(
            f'Recursion Error. Messages most likely have a cyclical dependancy. Check Message: {current_error_message} and Field: {current_error_field}',
            file=sys.stderr)
        return 1

    if not valid:
        sys.stderr.write(validate_log.getvalue())
        print("Validation failed", file=sys.stderr)
        return 1
    sys.stdout.write(validate_log.getvalue())

    normalize_output_order()

    if 'py' in langs or (args.validate and not langs):
        py_errors = check_python_package_names(args.py_package, args.generate_tests)
        if py_errors:
            for message in py_errors:
                print(f"Error: {message}", file=sys.stderr)
            return 1

    name_overrides = None
    try:
        if args.name_overrides:
            name_overrides = NameOverrides.load(args.name_overrides)
            name_overrides.validate(packages)
        # Nothing selected in validate mode: validate against every target so a schema
        # that passes here cannot fail later when a language is enabled.
        target_languages = langs if langs else list(LANG_KEYS)
        validate_generated_names(packages, target_languages, name_overrides)
    except NameOverrideError as err:
        # Located errors read "path:line: error: ..." (the form editors and CI annotate).
        text = str(err)
        located = re.match(r"^(.+?:\d+: )(.*)$", text, re.S)
        print(f"{located.group(1)}error: {located.group(2)}" if located else f"Error: {text}",
              file=sys.stderr)
        return 1

    if args.validate:
        info("Validation successful")
        if args.debug:
            printPackages()
        return 0

    # Compute generation hash and check if regeneration is needed
    current_hash = compute_generation_hash(args, packages, name_overrides)
    hash_file_path = get_hash_file_path(args)
    previous_hash = read_previous_hash(hash_file_path)

    if not args.force and previous_hash == current_hash and expected_outputs_exist(args):
        info("Generation skipped: no changes detected (hash matches previous generation)")
        info(f"  Hash file: {hash_file_path}")
        info("  Use --force to regenerate anyway")
        return 0

    if args.debug:
        if previous_hash is None:
            print(f"No previous hash found at {hash_file_path}")
        elif previous_hash != current_hash:
            print(f"Hash changed: {previous_hash[:16]}... -> {current_hash[:16]}...")

    files = {}
    for lang in _GENERATION_ORDER:
        if lang in langs:
            with language_model(lang, name_overrides):
                files.update(_generate_language(lang, output_path(args, lang), args))

    # Editor type catalog (single language-agnostic JSON file). Key order matters for
    # byte-identical output.
    catalog_order = ('c', 'cpp', 'ts', 'js', 'py', 'gql', 'csharp', 'rust')
    build_flags = {lang: lang in langs for lang in catalog_order}
    paths = {lang: output_path(args, lang) for lang in catalog_order}
    files.update(generate_lsp_file_strings(args.catalog_path, build_flags, paths, name_overrides,
                                           py_package=args.py_package))

    # Delete files this schema generated last time but no longer produces (renamed or removed
    # messages and packages). Other schemas' outputs in the same directory are left alone.
    shared_dirs = {}
    for lang in catalog_order:
        if lang in langs:
            shared_dirs.setdefault(os.path.abspath(paths[lang]), []).append(lang)
    for lang in catalog_order:
        if lang not in langs:
            continue
        out_dir = paths[lang]
        scope = "+".join(sorted(shared_dirs[os.path.abspath(out_dir)]))
        removed = prune_stale_outputs(out_dir, args.filename, files.keys(), scope)
        for path in removed:
            info(f"Removed stale output {path}")
        if lang == 'rust' and removed:
            with language_model('rust', name_overrides):
                files.update(rust_crate_files(
                    out_dir, [p.name for p in packages.values()], args.generate_tests))

    for filename, filedata in files.items():
        _write_file(filename, filedata)

    # Copy the runtime next to the generated code (for Python, into the generated package).
    # The SDK is handled below.
    def runtime_dir(lang):
        if lang == 'py':
            return os.path.join(output_path(args, lang), args.py_package)
        return output_path(args, lang)

    for lang in _GENERATION_ORDER:
        if lang in langs and lang in _BOILERPLATE_EXCLUDES:
            copy_all_files(os.path.join(_BOILERPLATE_ROOT, lang), runtime_dir(lang),
                           _BOILERPLATE_EXCLUDES[lang])

    if args.sdk or args.sdk_embedded:
        embedded_only = args.sdk_embedded and not args.sdk
        if args.sdk_embedded:
            ignoring = ", ".join(LANG_NAMES[lang] for lang in ('ts', 'js', 'py') if lang in langs)
            if ignoring:
                print(f"Note: --sdk_embedded only trims the C++ SDK; the full {ignoring} SDK is "
                      f"copied (those SDKs have no heavyweight dependency to leave out).",
                      file=sys.stderr)
        for lang in _GENERATION_ORDER:
            if lang in langs and lang in _SDK_LANGS:
                # ASIO is only included for C++ when the full SDK is requested.
                copy_sdk_files(lang, os.path.join(_BOILERPLATE_ROOT, lang),
                               runtime_dir(lang), embedded_only,
                               include_asio=args.sdk and not args.sdk_embedded)

    write_generation_hash(hash_file_path, current_hash)
    if args.debug:
        print(f"Generation hash written to {hash_file_path}")
        printPackages()
    info("Struct Frame successfully completed")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
