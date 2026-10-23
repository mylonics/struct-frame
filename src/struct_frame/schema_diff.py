"""Wire-compatibility check between two schema revisions (``struct-frame diff``).

Two ``.sf`` schemas (or snapshots written by ``--write-snapshot``) are reduced
to plain-data *snapshots* and compared.  Every difference is placed in exactly
one category so that a reviewer can look at each group separately:

``breaking``
    The wire format changes: message IDs, magic bytes, field types/numbers,
    enum values, extension blocks, removed declarations and order-sensitive
    oneof variants (discriminator values follow declaration order).
``compatible``
    Additive, wire-compatible changes: new messages and enums, new enum
    entries, fields/variants appended to the extension block, changed defaults.
``rename``
    Source-only renames: the wire identity (message ID, field number, enum
    value, variant position) is unchanged, only the source name differs.
``move``
    Declarations that moved to a different source file.  Harmless.

Declaration order of messages and enums, comments and documentation are
ignored: they never change the wire format.
"""

import argparse
import contextlib
import importlib
import io
import json
import os
import sys

SNAPSHOT_VERSION = 1

BREAKING = "breaking"
COMPATIBLE = "compatible"
RENAME = "rename"
MOVE = "move"

CATEGORIES = (BREAKING, COMPATIBLE, RENAME, MOVE)

_CATEGORY_TITLES = {
    BREAKING: "Wire-breaking changes",
    COMPATIBLE: "Wire-compatible changes",
    RENAME: "Source-only renames (review separately)",
    MOVE: "File moves (harmless)",
}

# --fail-on levels: the categories that produce a non-zero exit status.
_FAIL_ON = {
    "breaking": (BREAKING,),
    "rename": (BREAKING, RENAME),
    "any": (BREAKING, RENAME, COMPATIBLE),
}

EXIT_OK = 0
EXIT_CHANGES = 1
EXIT_ERROR = 2

_SCALAR_SIZES = {
    "uint8": 1, "int8": 1, "bool": 1, "uint16": 2, "int16": 2,
    "uint32": 4, "int32": 4, "float": 4, "uint64": 8, "int64": 8,
    "double": 8,
}


class SchemaLoadError(Exception):
    """A schema or snapshot could not be loaded."""


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

ENTRY_FILE = "<entry>"


def _relpath(path, root):
    """Source path relative to *root*; the entry schema itself is ``<entry>``.

    Naming the entry file symbolically means ``old.sf`` vs ``new.sf`` (or a
    renamed entry file) does not look like every declaration moved.
    """
    if not path:
        return None
    path = os.path.abspath(path)
    if path == root[1]:
        return ENTRY_FILE
    try:
        return os.path.relpath(path, root[0]).replace(os.sep, "/")
    except ValueError:  # different drive on Windows
        return path.replace(os.sep, "/")


def _type_ref(field, package_name):
    """Qualified, rename-trackable name of a field's type."""
    if field.is_default_type:
        return field.field_type
    if field.type_message:
        return f"{field.package or package_name}.{field.type_message}.{field.field_type}"
    return f"{field.type_package or field.package or package_name}.{field.field_type}"


def _field_snapshot(field, package_name):
    return {
        "name": field.name,
        "number": field.number,
        "type": _type_ref(field, package_name),
        "wire_size": field.size,
        "array": bool(field.is_array),
        "size": field.size_option,
        "max_size": field.max_size,
        "element_size": field.element_size,
        "default": field.default,
        "extension": bool(field.is_extension),
    }


def _enum_snapshot(enum, root):
    return {
        "source": _relpath(enum.source_file, root),
        "extensions_start": enum.extensions_start,
        "entries": [[name, value[0]] for name, value in enum.data.items()],
    }


def _oneof_snapshot(oneof, package_name, offset, evolvable=False):
    disc = {name: value for value, name, _ in oneof.variant_info}
    variants = []
    for index, (name, field) in enumerate(oneof.fields.items()):
        entry = _field_snapshot(field, package_name)
        entry["disc"] = disc.get(name)
        # Wire bytes of the variant's non-extension part (what an older
        # receiver understands); differs from wire_size only for nested
        # messages that grow through their own extension block.
        entry["base_wire"] = oneof.variant_extra[index][0] if index < len(oneof.variant_extra) else None
        variants.append(entry)
    return {
        "name": oneof.name,
        "variable": bool(oneof.variable),
        "discriminator": oneof.discriminator_type,
        "max_size": oneof.max_size_override,
        "min_size": oneof.min_size_override,
        "extensions_start": oneof.extensions_start,
        "base_size": oneof.base_size,
        "size": oneof.size,
        "offset": offset,
        "discriminator_size": (2 if oneof.discriminator_type == "msgid" else 1)
        if oneof.auto_discriminator else 0,
        "variants": variants,
        # Trailing trimmed oneof of a variable message: its payload runs to the
        # end of the frame, so variants may grow through extension fields.
        "evolvable": bool(evolvable),
    }


def _message_snapshot(pkg, msg, root):
    msgid = None
    if msg.id is not None:
        msgid = msg.id if pkg.package_id is None else (pkg.package_id << 8) | msg.id
    fields = [_field_snapshot(f, pkg.name) for f in msg.fields.values()]
    oneofs = []
    offset = sum(field["wire_size"] for field in fields)
    last_oneof = next(reversed(msg.oneofs.values()), None)
    for oneof in msg.oneofs.values():
        evolvable = (msg.variable and oneof is last_oneof and not oneof.variable
                     and oneof.discriminator_type is not None)
        snapshot = _oneof_snapshot(oneof, pkg.name, offset, evolvable)
        oneofs.append(snapshot)
        offset += snapshot["discriminator_size"] + (2 if snapshot["variable"] else 0) + snapshot["size"]
    return {
        "source": _relpath(msg.source_file, root),
        "id": msg.id,
        "msgid": msgid,
        "variable": bool(msg.variable),
        "discriminator_mode": msg.discriminator_mode,
        "extensions_start": msg.extensions_start,
        "magic_bytes": list(msg.magic_bytes) if msg.magic_bytes else None,
        "size": msg.size,
        "base_size": msg.base_size,
        "fields": fields,
        "oneofs": oneofs,
        "enums": {name: _enum_snapshot(e, root) for name, e in msg.enums.items()},
    }


def build_snapshot(packages, entry):
    """Reduce validated ``Package`` objects to a JSON-safe snapshot.

    Source paths are stored relative to the directory of the *entry* schema so
    snapshots taken from different checkouts compare equal.
    """
    entry = os.path.abspath(entry)
    root = (os.path.dirname(entry), entry)
    return {
        "version": SNAPSHOT_VERSION,
        "packages": {
            pkg.name: {
                "id": pkg.package_id,
                "enums": {n: _enum_snapshot(e, root) for n, e in pkg.enums.items()},
                "messages": {n: _message_snapshot(pkg, m, root) for n, m in pkg.messages.items()},
            }
            for pkg in packages.values()
        },
    }


_GENERATOR_STATE = ("packages", "processed_file", "required_file", "package_imports",
                    "pending_package_imports", "file_to_package")


@contextlib.contextmanager
def _isolated_generator_state(gen):
    """Give the parser empty module state, restoring the caller's afterwards."""
    saved = {}
    for name in _GENERATOR_STATE:
        container = getattr(gen, name)
        saved[name] = container.copy()
        container.clear()
    try:
        yield
    finally:
        for name in _GENERATOR_STATE:
            container = getattr(gen, name)
            container.clear()
            if isinstance(container, dict):
                container.update(saved[name])
            else:
                container.extend(saved[name])


def _snapshot_from_schema(path):
    gen = importlib.import_module("struct_frame.generate")
    log = io.StringIO()
    with _isolated_generator_state(gen), contextlib.redirect_stdout(log):
        try:
            ok = gen.parseFile(path) and gen.validate_packages()
        except RecursionError:
            print("Messages most likely have a cyclical dependency")
            ok = False
        if not ok:
            detail = log.getvalue().strip()
            raise SchemaLoadError(f"{path}: schema is not valid" + (f"\n{detail}" if detail else ""))
        return build_snapshot(dict(gen.packages), path)


def load_snapshot(path):
    """Load a snapshot from a ``.sf`` schema or a ``--write-snapshot`` JSON file."""
    if not os.path.isfile(path):
        raise SchemaLoadError(f"{path}: file not found")
    if path.lower().endswith(".json"):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                snapshot = json.load(handle)
        except (OSError, ValueError) as err:
            raise SchemaLoadError(f"{path}: cannot read snapshot: {err}")
        if not isinstance(snapshot, dict) or snapshot.get("version") != SNAPSHOT_VERSION \
                or not isinstance(snapshot.get("packages"), dict):
            raise SchemaLoadError(f"{path}: not a version {SNAPSHOT_VERSION} schema snapshot")
        _validate_snapshot(snapshot, path)
        return snapshot
    return _snapshot_from_schema(path)


def _validate_snapshot(snapshot, path):
    def fail(where, detail):
        raise SchemaLoadError(f"{path}: invalid schema snapshot at {where}: {detail}")

    def object_with(value, keys, where):
        if not isinstance(value, dict):
            fail(where, "expected an object")
        missing = sorted(set(keys) - set(value))
        if missing:
            fail(where, "missing " + ", ".join(missing))

    def value_type(value, expected, where, nullable=False):
        if nullable and value is None:
            return
        if expected is int:
            valid = type(value) is int
        elif expected is bool:
            valid = type(value) is bool
        else:
            valid = isinstance(value, expected)
        if not valid:
            fail(where, f"expected {expected.__name__}" + (" or null" if nullable else ""))

    def check_member(member, where):
        object_with(member, ("name", "number", "type", "array", "size", "max_size",
                             "element_size", "default", "extension"), where)
        value_type(member["name"], str, f"{where}.name")
        value_type(member["number"], int, f"{where}.number", nullable=True)
        value_type(member["type"], str, f"{where}.type")
        value_type(member["array"], bool, f"{where}.array")
        for key in ("size", "max_size", "element_size"):
            value_type(member[key], int, f"{where}.{key}", nullable=True)
        value_type(member["extension"], bool, f"{where}.extension")
        if "wire_size" in member:
            value_type(member["wire_size"], int, f"{where}.wire_size")
            if member["wire_size"] < 0:
                fail(f"{where}.wire_size", "must be non-negative")

    def check_enum(enum, where):
        object_with(enum, ("source", "extensions_start", "entries"), where)
        value_type(enum["source"], str, f"{where}.source", nullable=True)
        value_type(enum["extensions_start"], int, f"{where}.extensions_start", nullable=True)
        if not isinstance(enum["entries"], list):
            fail(f"{where}.entries", "expected an array")
        for index, entry in enumerate(enum["entries"]):
            if not isinstance(entry, list) or len(entry) != 2:
                fail(f"{where}.entries[{index}]", "expected a [name, value] pair")
            value_type(entry[0], str, f"{where}.entries[{index}][0]")
            value_type(entry[1], int, f"{where}.entries[{index}][1]")

    packages = snapshot["packages"]
    for pkg_name, pkg in packages.items():
        object_with(pkg, ("id", "enums", "messages"), f"packages.{pkg_name}")
        value_type(pkg["id"], int, f"packages.{pkg_name}.id", nullable=True)
        for kind in ("enums", "messages"):
            if not isinstance(pkg[kind], dict):
                fail(f"packages.{pkg_name}.{kind}", "expected an object")
        for enum_name, enum in pkg["enums"].items():
            check_enum(enum, f"packages.{pkg_name}.enums.{enum_name}")
        for msg_name, msg in pkg["messages"].items():
            where = f"packages.{pkg_name}.messages.{msg_name}"
            object_with(msg, ("source", "id", "msgid", "variable", "discriminator_mode",
                              "extensions_start", "magic_bytes", "size", "base_size",
                              "fields", "oneofs", "enums"), where)
            value_type(msg["source"], str, f"{where}.source", nullable=True)
            for key in ("id", "msgid", "extensions_start"):
                value_type(msg[key], int, f"{where}.{key}", nullable=True)
            value_type(msg["variable"], bool, f"{where}.variable")
            value_type(msg["discriminator_mode"], str, f"{where}.discriminator_mode", nullable=True)
            for key in ("size", "base_size"):
                value_type(msg[key], int, f"{where}.{key}")
            if msg["magic_bytes"] is not None:
                if not isinstance(msg["magic_bytes"], list) or any(
                        type(byte) is not int or not 0 <= byte <= 255 for byte in msg["magic_bytes"]):
                    fail(f"{where}.magic_bytes", "expected an array of bytes or null")
            for key in ("fields", "oneofs"):
                if not isinstance(msg[key], list):
                    fail(f"{where}.{key}", "expected an array")
            if not isinstance(msg["enums"], dict):
                fail(f"{where}.enums", "expected an object")
            for enum_name, enum in msg["enums"].items():
                check_enum(enum, f"{where}.enums.{enum_name}")
            for index, field in enumerate(msg["fields"]):
                check_member(field, f"{where}.fields[{index}]")
            for index, oneof in enumerate(msg["oneofs"]):
                oneof_path = f"{where}.oneofs[{index}]"
                object_with(oneof, ("name", "variable", "discriminator", "max_size", "min_size",
                                    "extensions_start", "base_size", "variants"), oneof_path)
                value_type(oneof["name"], str, f"{oneof_path}.name")
                value_type(oneof["variable"], bool, f"{oneof_path}.variable")
                value_type(oneof["discriminator"], str, f"{oneof_path}.discriminator", nullable=True)
                for key in ("max_size", "min_size", "extensions_start"):
                    value_type(oneof[key], int, f"{oneof_path}.{key}", nullable=True)
                value_type(oneof["base_size"], int, f"{oneof_path}.base_size")
                if oneof["base_size"] < 0:
                    fail(f"{oneof_path}.base_size", "must be non-negative")
                if not isinstance(oneof["variants"], list):
                    fail(f"{oneof_path}.variants", "expected an array")
                for variant_index, variant in enumerate(oneof["variants"]):
                    variant_path = f"{oneof_path}.variants[{variant_index}]"
                    check_member(variant, variant_path)
                    if "disc" not in variant:
                        fail(variant_path, "missing disc")
                    value_type(variant["disc"], int, f"{variant_path}.disc", nullable=True)
                for key in ("size", "offset", "discriminator_size"):
                    if key in oneof:
                        value_type(oneof[key], int, f"{oneof_path}.{key}")
                        if oneof[key] < 0:
                            fail(f"{oneof_path}.{key}", "must be non-negative")

    _normalize_snapshot_layout(snapshot)


def _normalize_snapshot_layout(snapshot):
    """Add layout values introduced after snapshot version 1 was published."""
    for pkg_name, pkg in snapshot["packages"].items():
        for msg in pkg["messages"].values():
            offset = sum(field.get("wire_size", _estimated_wire_size(field, snapshot))
                         for field in msg["fields"])
            for oneof in msg["oneofs"]:
                oneof.setdefault("size", max(
                    [variant.get("wire_size", _estimated_wire_size(variant, snapshot))
                     for variant in oneof["variants"]] + [oneof["max_size"] or 0] +
                    ([oneof["min_size"] or 0] if not oneof["variable"] else [0])))
                oneof.setdefault("discriminator_size",
                                 2 if oneof["discriminator"] == "msgid" else
                                 1 if oneof["discriminator"] == "field_order" else 0)
                oneof.setdefault("offset", offset)
                offset += oneof["discriminator_size"] + (2 if oneof["variable"] else 0) + oneof["size"]


def _estimated_wire_size(member, snapshot):
    type_name = member["type"]
    base_size = _SCALAR_SIZES.get(type_name)
    if base_size is None:
        parts = type_name.rsplit(".", 1)
        if len(parts) == 2:
            referenced = snapshot["packages"].get(parts[0], {}).get("messages", {}).get(parts[1])
            base_size = referenced["size"] if referenced else 1
        else:
            base_size = 1
    if type_name in ("string", "bytes"):
        if member["array"]:
            if member["size"] is not None:
                return member["size"] * (member["element_size"] or 1)
            if member["max_size"] is not None:
                return (2 if member["max_size"] > 255 else 1) + member["max_size"] * (member["element_size"] or 1)
        if member["size"] is not None:
            return member["size"]
        if member["max_size"] is not None:
            return member["max_size"] + (2 if member["max_size"] > 255 else 1)
    if member["array"]:
        if member["size"] is not None:
            return member["size"] * base_size
        if member["max_size"] is not None:
            return (2 if member["max_size"] > 255 else 1) + member["max_size"] * base_size
    return base_size


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

class Change:
    """One reported difference."""

    def __init__(self, category, kind, path, message, old=None, new=None):
        self.category = category
        self.kind = kind
        self.path = path
        self.message = message
        self.old = old
        self.new = new

    def to_dict(self):
        return {"category": self.category, "kind": self.kind, "path": self.path,
                "message": self.message, "old": self.old, "new": self.new}


def _describe(member):
    """Human-readable wire description of a field or variant."""
    text = member["type"]
    if member["array"]:
        text += "[]"
    options = []
    if member["size"] is not None:
        options.append(f"size={member['size']}")
    if member["max_size"] is not None:
        options.append(f"max_size={member['max_size']}")
    if member["element_size"] is not None:
        options.append(f"element_size={member['element_size']}")
    if options:
        text += "(" + ", ".join(options) + ")"
    return text


def _id_text(msgid):
    return "no message ID" if msgid is None else f"ID 0x{msgid:04X}"


class _Differ:
    def __init__(self, old, new):
        self.old = old
        self.new = new
        self.changes = []
        # old qualified type name -> new qualified type name, for every
        # message and enum that was renamed or moved to another package.
        self.type_map = {}
        self.renamed_messages = set()
        self.nested = {}
        # Enums that moved between message scope and package scope.
        self.moved_old = set()
        self.moved_new = set()

    # -- helpers ----------------------------------------------------------

    def add(self, category, kind, path, message, old=None, new=None):
        self.changes.append(Change(category, kind, path, message, old, new))

    def _wire_signature(self, member, mapped):
        type_name = member["type"]
        if mapped:
            type_name = self.type_map.get(type_name, type_name)
        return (type_name, member["array"], member["size"], member["max_size"], member["element_size"])

    def _signature_pair(self, old_member, new_member):
        return (self._wire_signature(old_member, True), self._wire_signature(new_member, False))

    # -- driver -----------------------------------------------------------

    def run(self):
        old_pkgs, new_pkgs = self.old["packages"], self.new["packages"]

        for name in sorted(set(old_pkgs) & set(new_pkgs)):
            old_id, new_id = old_pkgs[name]["id"], new_pkgs[name]["id"]
            if old_id != new_id:
                self.add(BREAKING, "package_id_changed", name,
                         f"package ID {old_id} -> {new_id}; every message ID in the package changes",
                         old_id, new_id)

        enum_pairs, enum_removed, enum_added = self._match_enums(old_pkgs, new_pkgs)
        message_pairs, message_removed, message_added = self._match_messages(old_pkgs, new_pkgs)
        self.nested = {}
        for old_key, new_key in message_pairs:
            self.nested[(old_key, new_key)] = self._match_nested_enums(old_key, new_key)

        for old_key, new_key in enum_pairs + message_pairs:
            if old_key != new_key:
                self.type_map[".".join(old_key)] = ".".join(new_key)
        self.renamed_messages = {".".join(old_key) for old_key, new_key in message_pairs if old_key != new_key}
        for (old_key, new_key), (pairs, _, _) in self.nested.items():
            for old_name, new_name in pairs:
                old_ref, new_ref = ".".join(old_key + (old_name,)), ".".join(new_key + (new_name,))
                if old_ref != new_ref:
                    self.type_map[old_ref] = new_ref

        self._pair_scope_moves(old_pkgs, new_pkgs, enum_removed, enum_added)

        # Enums
        for old_key, new_key in enum_pairs:
            self._diff_enum(".".join(new_key),
                            old_pkgs[old_key[0]]["enums"][old_key[1]],
                            new_pkgs[new_key[0]]["enums"][new_key[1]],
                            ".".join(old_key) if old_key != new_key else None)
        for key in enum_removed:
            if ".".join(key) not in self.moved_old:
                self.add(BREAKING, "enum_removed", ".".join(key), "enum removed")
        for key in enum_added:
            if ".".join(key) not in self.moved_new:
                self.add(COMPATIBLE, "enum_added", ".".join(key), "enum added")

        # Messages
        for old_key, new_key in message_pairs:
            self._diff_message(old_key, new_key,
                               old_pkgs[old_key[0]]["messages"][old_key[1]],
                               new_pkgs[new_key[0]]["messages"][new_key[1]])
        for key in message_removed:
            msg = old_pkgs[key[0]]["messages"][key[1]]
            self.add(BREAKING, "message_removed", ".".join(key),
                     f"message removed ({_id_text(msg['msgid'])})", msg["msgid"])
        for key in message_added:
            msg = new_pkgs[key[0]]["messages"][key[1]]
            self.add(COMPATIBLE, "message_added", ".".join(key),
                     f"message added ({_id_text(msg['msgid'])})", None, msg["msgid"])

        order = {category: index for index, category in enumerate(CATEGORIES)}
        self.changes.sort(key=lambda c: (order[c.category], c.path, c.kind))
        return self.changes

    # -- matching ---------------------------------------------------------

    def _pair_scope_moves(self, old_pkgs, new_pkgs, enum_removed, enum_added):
        """Pair enums that moved between message scope and package scope.

        An enum that disappears from one scope and appears in the other of the
        same package with identical entries has the same wire format (enums are
        stored as their value), so it is a source-only move, not a removal. Only
        unambiguous one-to-one matches are paired; field types follow the move
        through ``type_map``.
        """
        def signature(enum):
            return tuple(map(tuple, enum["entries"]))

        old_left, new_left = [], []
        for (old_key, new_key), (_, removed, added) in self.nested.items():
            for name in removed:
                enum = old_pkgs[old_key[0]]["messages"][old_key[1]]["enums"][name]
                old_left.append((old_key[0], ".".join(old_key + (name,)), signature(enum)))
            for name in added:
                enum = new_pkgs[new_key[0]]["messages"][new_key[1]]["enums"][name]
                new_left.append((new_key[0], ".".join(new_key + (name,)), signature(enum)))
        for key in enum_removed:
            old_left.append((key[0], ".".join(key), signature(old_pkgs[key[0]]["enums"][key[1]])))
        for key in enum_added:
            new_left.append((key[0], ".".join(key), signature(new_pkgs[key[0]]["enums"][key[1]])))

        for pkg, old_ref, sig in old_left:
            candidates = [n for n in new_left if n[0] == pkg and n[2] == sig]
            rivals = [o for o in old_left if o[0] == pkg and o[2] == sig]
            if len(candidates) != 1 or len(rivals) != 1:
                continue
            new_ref = candidates[0][1]
            self.type_map[old_ref] = new_ref
            self.moved_old.add(old_ref)
            self.moved_new.add(new_ref)
            self.add(RENAME, "enum_scope_moved", new_ref,
                     f"enum moved from {old_ref} to {new_ref} (same entries)", old_ref, new_ref)

    def _match_messages(self, old_pkgs, new_pkgs):
        old = {(p, n): m for p, pkg in old_pkgs.items() for n, m in pkg["messages"].items()}
        new = {(p, n): m for p, pkg in new_pkgs.items() for n, m in pkg["messages"].items()}
        pairs = [(key, key) for key in old if key in new]
        left_old = [key for key in old if key not in new]
        left_new = [key for key in new if key not in old]

        # Source-only renames/moves keep the (package-qualified) message ID.
        by_id = {}
        for key in left_new:
            if new[key]["msgid"] is not None:
                by_id[new[key]["msgid"]] = key
        removed = []
        for key in left_old:
            target = by_id.pop(old[key]["msgid"], None) if old[key]["msgid"] is not None else None
            if target is not None:
                pairs.append((key, target))
            else:
                removed.append(key)
        added = [key for key in left_new if key not in {t for _, t in pairs}]
        return sorted(pairs), sorted(removed), sorted(added)

    def _match_enums(self, old_pkgs, new_pkgs):
        old = {(p, n): e for p, pkg in old_pkgs.items() for n, e in pkg["enums"].items()}
        new = {(p, n): e for p, pkg in new_pkgs.items() for n, e in pkg["enums"].items()}
        pairs = [(key, key) for key in old if key in new]
        left_old = [key for key in old if key not in new]
        left_new = [key for key in new if key not in old]
        renamed, left_old, left_new = _pair_enums(old, new, left_old, left_new)
        return sorted(pairs + renamed), sorted(left_old), sorted(left_new)

    def _match_nested_enums(self, old_key, new_key):
        """Pair the message-scoped enums of a matched message pair.

        Returns ``(pairs, removed, added)`` where *pairs* holds
        ``(old_name, new_name)`` tuples (equal names are the common case).
        """
        old_enums = self.old["packages"][old_key[0]]["messages"][old_key[1]]["enums"]
        new_enums = self.new["packages"][new_key[0]]["messages"][new_key[1]]["enums"]
        pairs = [(name, name) for name in old_enums if name in new_enums]
        left_old = [name for name in old_enums if name not in new_enums]
        left_new = [name for name in new_enums if name not in old_enums]
        renamed, left_old, left_new = _pair_enums(old_enums, new_enums, left_old, left_new)
        return sorted(pairs + renamed), sorted(left_old), sorted(left_new)

    # -- enums ------------------------------------------------------------

    def _diff_enum(self, path, old, new, renamed_from=None):
        if renamed_from:
            self.add(RENAME, "enum_renamed", renamed_from, f"enum renamed to {path}", renamed_from, path)
        if old["source"] != new["source"]:
            self.add(MOVE, "file_moved", path, f"enum moved from {old['source']} to {new['source']}",
                     old["source"], new["source"])
        if old["extensions_start"] != new["extensions_start"]:
            self.add(COMPATIBLE, "extensions_start_changed", path,
                     f"extensions_start {old['extensions_start']} -> {new['extensions_start']}",
                     old["extensions_start"], new["extensions_start"])

        old_entries = dict(map(tuple, old["entries"]))
        new_entries = dict(map(tuple, new["entries"]))
        for name, value in old_entries.items():
            if name in new_entries and new_entries[name] != value:
                self.add(BREAKING, "enum_entry_value_changed", f"{path}.{name}",
                         f"value {value} -> {new_entries[name]}", value, new_entries[name])

        only_old = {n: v for n, v in old_entries.items() if n not in new_entries}
        only_new = {n: v for n, v in new_entries.items() if n not in old_entries}
        new_by_value = {v: n for n, v in only_new.items()}
        for name, value in sorted(only_old.items(), key=lambda item: item[1]):
            if value in new_by_value:
                new_name = new_by_value.pop(value)
                self.add(RENAME, "enum_entry_renamed", f"{path}.{name}",
                         f"entry {name} = {value} renamed to {new_name}", name, new_name)
            else:
                self.add(BREAKING, "enum_entry_removed", f"{path}.{name}",
                         f"entry {name} = {value} removed", name)
        for value, name in sorted(new_by_value.items()):
            self.add(COMPATIBLE, "enum_entry_added", f"{path}.{name}",
                     f"entry {name} = {value} added", None, name)

    # -- messages ---------------------------------------------------------

    def _diff_message(self, old_key, new_key, old, new):
        path = ".".join(new_key)
        before = len(self.changes)

        if old_key != new_key:
            self.add(RENAME, "message_renamed", ".".join(old_key),
                     f"message renamed to {path} ({_id_text(new['msgid'])} unchanged)",
                     ".".join(old_key), path)
        if old["source"] != new["source"]:
            self.add(MOVE, "file_moved", path,
                     f"message moved from {old['source']} to {new['source']}",
                     old["source"], new["source"])
        if old["id"] != new["id"]:
            self.add(BREAKING, "msgid_changed", path,
                     f"message ID {old['id']} -> {new['id']}", old["id"], new["id"])
        if old["variable"] != new["variable"]:
            self.add(BREAKING, "variable_changed", path,
                     f"variable encoding {old['variable']} -> {new['variable']}",
                     old["variable"], new["variable"])
        if old["discriminator_mode"] != new["discriminator_mode"]:
            self.add(BREAKING, "discriminator_changed", path,
                     f"discriminator {old['discriminator_mode']} -> {new['discriminator_mode']}",
                     old["discriminator_mode"], new["discriminator_mode"])

        self._diff_members(path, "field", old["fields"], new["fields"],
                           old["extensions_start"], new["extensions_start"])

        old_oneofs = {o["name"]: o for o in old["oneofs"]}
        new_oneofs = {o["name"]: o for o in new["oneofs"]}
        left_old = [name for name in old_oneofs if name not in new_oneofs]
        left_new = [name for name in new_oneofs if name not in old_oneofs]
        renamed = []
        if len(left_old) == len(left_new):
            renamed = list(zip(left_old, left_new))
            left_old, left_new = [], []
        for name in left_old:
            self.add(BREAKING, "oneof_removed", f"{path}.{name}", "oneof removed")
        for name in left_new:
            self.add(BREAKING, "oneof_added", f"{path}.{name}", "oneof added to the message layout")
        pairs = [(name, name) for name in old_oneofs if name in new_oneofs] + renamed
        common_old = [o["name"] for o in old["oneofs"] if o["name"] in new_oneofs]
        common_new = [o["name"] for o in new["oneofs"] if o["name"] in old_oneofs]
        if common_old != common_new:
            self.add(BREAKING, "oneofs_reordered", path,
                     f"oneof order {', '.join(common_old)} -> {', '.join(common_new)}",
                     common_old, common_new)
        tolerated = 0
        for old_name, new_name in pairs:
            tolerated += self._diff_oneof(path, old_oneofs[old_name], new_oneofs[new_name])

        # Nested enums
        pairs, removed, added = self.nested[(old_key, new_key)]
        for old_name, new_name in pairs:
            self._diff_enum(f"{path}.{new_name}", old["enums"][old_name], new["enums"][new_name],
                            f"{'.'.join(old_key)}.{old_name}" if old_name != new_name else None)
        for name in removed:
            if f"{'.'.join(old_key)}.{name}" not in self.moved_old:
                self.add(BREAKING, "enum_removed", f"{'.'.join(old_key)}.{name}", "enum removed")
        for name in added:
            if f"{path}.{name}" not in self.moved_new:
                self.add(COMPATIBLE, "enum_added", f"{path}.{name}", "enum added")

        if old["magic_bytes"] != new["magic_bytes"]:
            note = ""
            embedded = {m["type"] for m in old["fields"] if not m["extension"]}
            embedded |= {v["type"] for o in old["oneofs"] for v in o["variants"] if not v["extension"]}
            renamed_types = sorted(embedded & self.renamed_messages)
            if renamed_types:
                note = (" (magic bytes depend on embedded message type names; renamed: "
                        + ", ".join(renamed_types) + ")")
            self.add(BREAKING, "magic_bytes_changed", path,
                     f"magic bytes {old['magic_bytes']} -> {new['magic_bytes']}{note}",
                     old["magic_bytes"], new["magic_bytes"])

        if old["base_size"] + tolerated != new["base_size"] and not any(
                c.category == BREAKING for c in self.changes[before:]):
            self.add(BREAKING, "size_changed", path,
                     f"base wire size {old['base_size']} -> {new['base_size']} bytes",
                     old["base_size"], new["base_size"])

    # -- fields / variants ------------------------------------------------

    def _diff_members(self, path, kind, old_members, new_members, old_ext, new_ext, extra=None):
        """Compare fields (or oneof variants) by number.

        Wire order follows declaration order, which the schema validator pins to
        field-number order, so the number is the member's wire identity.
        """
        def number(members, index):
            member = members[index]
            return member["number"] if member["number"] is not None else index + 1

        old_by_num = {number(old_members, i): m for i, m in enumerate(old_members)}
        new_by_num = {number(new_members, i): m for i, m in enumerate(new_members)}

        # A pure reordering is one finding, not N type changes.
        old_names = [m["name"] for m in old_members]
        new_names = [m["name"] for m in new_members]
        old_common = [name for name in old_names if name in set(new_names)]
        new_common = [name for name in new_names if name in set(old_names)]
        if len(old_members) == len(new_members):
            old_set = sorted(((m["name"], self._wire_signature(m, True)) for m in old_members),
                             key=lambda item: item[0])
            new_set = sorted(((m["name"], self._wire_signature(m, False)) for m in new_members),
                             key=lambda item: item[0])
            if old_set == new_set and old_names != new_names:
                detail = ""
                if kind == "variant":
                    discs = {m["name"]: m["disc"] for m in new_members}
                    old_discs = {m["name"]: m["disc"] for m in old_members}
                    moved = [f"{m['name']} {old_discs[m['name']]} -> {discs[m['name']]}"
                             for m in old_members if old_discs[m["name"]] != discs[m["name"]]]
                    if moved:
                        detail = "; discriminator values: " + ", ".join(moved)
                self.add(BREAKING, f"{kind}s_reordered", path,
                         f"{kind} order {', '.join(old_names)} -> {', '.join(new_names)}{detail}",
                         old_names, new_names)
                return
        if old_common != new_common:
            self.add(BREAKING, f"{kind}s_reordered", path,
                     f"{kind} order {', '.join(old_common)} -> {', '.join(new_common)}",
                     old_common, new_common)

        for num in sorted(set(old_by_num) | set(new_by_num)):
            old_m, new_m = old_by_num.get(num), new_by_num.get(num)
            if old_m is not None and new_m is not None:
                member_path = f"{path}.{new_m['name']}"
                old_sig, new_sig = self._signature_pair(old_m, new_m)
                if old_sig != new_sig:
                    self.add(BREAKING, f"{kind}_type_changed", member_path,
                             f"#{num} {old_m['name']}: {_describe(old_m)} -> {_describe(new_m)}",
                             _describe(old_m), _describe(new_m))
                    continue
                if old_m["extension"] != new_m["extension"]:
                    self.add(BREAKING, f"{kind}_extension_changed", member_path,
                             f"#{num} {'moved into' if new_m['extension'] else 'moved out of'} the extension block",
                             old_m["extension"], new_m["extension"])
                if old_m["name"] != new_m["name"]:
                    self.add(RENAME, f"{kind}_renamed", f"{path}.{old_m['name']}",
                             f"#{num} renamed to {new_m['name']}", old_m["name"], new_m["name"])
                if old_m["default"] != new_m["default"]:
                    self.add(COMPATIBLE, f"{kind}_default_changed", member_path,
                             f"default {old_m['default']!r} -> {new_m['default']!r}",
                             old_m["default"], new_m["default"])
                if extra is not None:
                    extra(member_path, old_m, new_m)
            elif old_m is not None:
                self.add(BREAKING, f"{kind}_removed", f"{path}.{old_m['name']}",
                         f"#{num} {old_m['name']}: {_describe(old_m)} removed",
                         _describe(old_m), None)
            elif new_m["extension"]:
                self.add(COMPATIBLE, f"{kind}_extension_added", f"{path}.{new_m['name']}",
                         f"#{num} {new_m['name']}: {_describe(new_m)} appended to the extension block",
                         None, _describe(new_m))
            else:
                self.add(BREAKING, f"{kind}_added_to_base", f"{path}.{new_m['name']}",
                         f"#{num} {new_m['name']}: {_describe(new_m)} added to the base layout "
                         f"(append it after `extensions_start` to stay compatible)",
                         None, _describe(new_m))

        if old_ext != new_ext:
            old_base = [self._wire_signature(m, True) for m in old_members if not m["extension"]]
            new_base = [self._wire_signature(m, False) for m in new_members if not m["extension"]]
            if old_base == new_base:
                self.add(COMPATIBLE, "extensions_start_changed", path,
                         f"extensions_start {old_ext} -> {new_ext}", old_ext, new_ext)

    # -- oneofs -----------------------------------------------------------

    def _diff_oneof(self, message_path, old, new):
        """Diff one oneof; returns the base-size growth tolerated as wire-compatible."""
        path = f"{message_path}.{new['name']}"
        if old["name"] != new["name"]:
            self.add(RENAME, "oneof_renamed", f"{message_path}.{old['name']}",
                     f"oneof renamed to {new['name']}", old["name"], new["name"])
        before = len(self.changes)
        if old.get("offset") is not None and new.get("offset") is not None \
                and old["offset"] != new["offset"]:
            self.add(BREAKING, "oneof_offset_changed", path,
                     f"oneof wire offset {old['offset']} -> {new['offset']}; earlier layout growth shifts this union",
                     old["offset"], new["offset"])
        if old["variable"] != new["variable"]:
            self.add(BREAKING, "oneof_variable_changed", path,
                     f"variable {old['variable']} -> {new['variable']}", old["variable"], new["variable"])
        if old["discriminator"] != new["discriminator"]:
            self.add(BREAKING, "oneof_discriminator_changed", path,
                     f"discriminator {old['discriminator']} -> {new['discriminator']}",
                     old["discriminator"], new["discriminator"])
        if old["max_size"] != new["max_size"]:
            self.add(BREAKING, "oneof_max_size_changed", path,
                     f"max_size {old['max_size']} -> {new['max_size']}", old["max_size"], new["max_size"])
        if old["min_size"] != new["min_size"]:
            # On a variable or trailing-trimmed oneof the payload length is on
            # the wire and receivers reject payloads shorter than
            # max(variant base size, min_size). Raising min_size makes a new
            # receiver reject frames from old senders; lowering it makes a new
            # sender emit frames old receivers reject. A fixed oneof's min_size
            # only grows the union buffer, which the size/offset checks cover.
            on_wire = (old["variable"] or new["variable"]
                       or old.get("evolvable") or new.get("evolvable"))
            self.add(BREAKING if on_wire else COMPATIBLE, "oneof_min_size_changed", path,
                     f"min_size {old['min_size']} -> {new['min_size']}"
                     + (" (the minimum accepted payload length is on the wire)" if on_wire else ""),
                     old["min_size"], new["min_size"])

        def check_discriminator(variant_path, old_variant, new_variant):
            if old_variant["disc"] != new_variant["disc"]:
                self.add(BREAKING, "variant_discriminator_changed", variant_path,
                         f"discriminator value {old_variant['disc']} -> {new_variant['disc']}",
                         old_variant["disc"], new_variant["disc"])

        self._diff_members(path, "variant", old["variants"], new["variants"],
                           old["extensions_start"], new["extensions_start"], check_discriminator)

        if old["base_size"] != new["base_size"] and not any(
                c.category == BREAKING for c in self.changes[before:]):
            if self._trimmed_growth_is_compatible(old, new):
                return new["base_size"] - old["base_size"]
            self.add(BREAKING, "oneof_size_changed", path,
                     f"base union size {old['base_size']} -> {new['base_size']} bytes",
                     old["base_size"], new["base_size"])
        return 0

    @staticmethod
    def _trimmed_growth_is_compatible(old, new):
        """A trailing trimmed oneof may grow when only variants' extension parts grew.

        The payload is trimmed to the active variant and read to the end of the
        frame, so an older receiver ignores the extra tail and a newer one fills
        missing bytes with defaults. That holds only while every variant's
        non-extension wire bytes are unchanged and no explicit sizing option moved.
        """
        if not (old.get("evolvable") and new.get("evolvable")):
            return False
        if old["max_size"] != new["max_size"]:
            return False
        old_base = [v.get("base_wire") for v in old["variants"] if not v["extension"]]
        new_base = [v.get("base_wire") for v in new["variants"] if not v["extension"]]
        return None not in old_base and None not in new_base and old_base == new_base


def _pair_enums(old, new, left_old, left_new):
    """Pair renamed enums: identical entries first, then identical values.

    Only unambiguous (one-to-one) matches are paired.  Returns
    ``(pairs, still_old, still_new)``.
    """
    pairs = []
    for signature in (lambda e: tuple(map(tuple, e["entries"])),
                      lambda e: tuple(sorted(value for _, value in e["entries"]))):
        for old_key in list(left_old):
            candidates = [k for k in left_new if signature(new[k]) == signature(old[old_key])]
            rivals = [k for k in left_old if signature(old[k]) == signature(old[old_key])]
            if len(candidates) == 1 and len(rivals) == 1:
                pairs.append((old_key, candidates[0]))
                left_old.remove(old_key)
                left_new.remove(candidates[0])
    return pairs, left_old, left_new


def diff_snapshots(old, new):
    """Compare two snapshots; returns a sorted list of :class:`Change`."""
    return _Differ(old, new).run()


# ---------------------------------------------------------------------------
# Reporting / CLI
# ---------------------------------------------------------------------------

def summarize(changes):
    counts = {category: 0 for category in CATEGORIES}
    for change in changes:
        counts[change.category] += 1
    return counts


def exit_status(changes, fail_on="breaking"):
    failing = _FAIL_ON[fail_on]
    return EXIT_CHANGES if any(c.category in failing for c in changes) else EXIT_OK


def format_text(changes, old_name, new_name, fail_on="breaking"):
    counts = summarize(changes)
    lines = [f"Schema diff: {old_name} -> {new_name}"]
    for category in CATEGORIES:
        group = [c for c in changes if c.category == category]
        if not group:
            continue
        lines.append("")
        lines.append(f"{_CATEGORY_TITLES[category]} ({len(group)}):")
        for change in group:
            lines.append(f"  [{change.kind}] {change.path}: {change.message}")
    lines.append("")
    if not changes:
        lines.append("Result: no differences")
    elif counts[BREAKING]:
        lines.append(f"Result: WIRE-BREAKING ({counts[BREAKING]} breaking change(s))")
    else:
        lines.append("Result: wire-compatible")
    if exit_status(changes, fail_on) and not counts[BREAKING]:
        lines.append(f"(failing because of --fail-on {fail_on})")
    return "\n".join(lines) + "\n"


def format_json(changes, old_name, new_name, fail_on="breaking"):
    counts = summarize(changes)
    return json.dumps({
        "old": old_name,
        "new": new_name,
        "wire_compatible": counts[BREAKING] == 0,
        "summary": counts,
        "changes": [c.to_dict() for c in changes],
    }, indent=2) + "\n"


def build_parser(prog="struct-frame diff"):
    parser = argparse.ArgumentParser(
        prog=prog,
        description=("Check that a new schema revision stays wire-compatible with an old one. "
                     "Reports changes to message IDs, magic bytes, field types/numbers, enum "
                     "values, extensions and order-sensitive oneof variants. Source-only renames "
                     "and file moves are reported separately. Exit status: 0 = no failing "
                     "changes, 1 = failing changes, 2 = a schema could not be loaded."))
    parser.add_argument("old", help="Old (baseline) schema: a .sf file or a snapshot .json")
    parser.add_argument("new", help="New schema: a .sf file or a snapshot .json")
    parser.add_argument("--format", choices=("text", "json"), default="text",
                        help="Report format (default: text)")
    parser.add_argument("--fail-on", choices=tuple(_FAIL_ON), default="breaking",
                        help=("Which differences produce exit status 1: 'breaking' (default) = "
                              "wire-breaking only, 'rename' = also source-only renames, "
                              "'any' = also additive changes. File moves never fail."))
    parser.add_argument("--write-snapshot", metavar="PATH", default=None,
                        help="Write the new schema's snapshot (JSON) to PATH, usable as a future baseline")
    return parser


def main(argv=None, out=None, err=None):
    out = out or sys.stdout
    err = err or sys.stderr
    args = build_parser().parse_args(argv)
    try:
        old = load_snapshot(args.old)
        new = load_snapshot(args.new)
    except SchemaLoadError as error:
        print(f"Error: {error}", file=err)
        return EXIT_ERROR

    if args.write_snapshot:
        with open(args.write_snapshot, "w", encoding="utf-8") as handle:
            json.dump(new, handle, indent=2, sort_keys=True)
            handle.write("\n")

    changes = diff_snapshots(old, new)
    render = format_json if args.format == "json" else format_text
    out.write(render(changes, args.old, args.new, args.fail_on))
    return exit_status(changes, args.fail_on)
