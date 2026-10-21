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


def _oneof_snapshot(oneof, package_name):
    disc = {name: value for value, name, _ in oneof.variant_info}
    variants = []
    for name, field in oneof.fields.items():
        entry = _field_snapshot(field, package_name)
        entry["disc"] = disc.get(name)
        variants.append(entry)
    return {
        "name": oneof.name,
        "variable": bool(oneof.variable),
        "discriminator": oneof.discriminator_type,
        "max_size": oneof.max_size_override,
        "min_size": oneof.min_size_override,
        "extensions_start": oneof.extensions_start,
        "base_size": oneof.base_size,
        "variants": variants,
    }


def _message_snapshot(pkg, msg, root):
    msgid = None
    if msg.id is not None:
        msgid = msg.id if pkg.package_id is None else (pkg.package_id << 8) | msg.id
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
        "fields": [_field_snapshot(f, pkg.name) for f in msg.fields.values()],
        "oneofs": [_oneof_snapshot(o, pkg.name) for o in msg.oneofs.values()],
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
        return snapshot
    return _snapshot_from_schema(path)


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

        # Enums
        for old_key, new_key in enum_pairs:
            self._diff_enum(".".join(new_key),
                            old_pkgs[old_key[0]]["enums"][old_key[1]],
                            new_pkgs[new_key[0]]["enums"][new_key[1]],
                            ".".join(old_key) if old_key != new_key else None)
        for key in enum_removed:
            self.add(BREAKING, "enum_removed", ".".join(key), "enum removed")
        for key in enum_added:
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
        for old_name, new_name in pairs:
            self._diff_oneof(path, old_oneofs[old_name], new_oneofs[new_name])

        # Nested enums
        pairs, removed, added = self.nested[(old_key, new_key)]
        for old_name, new_name in pairs:
            self._diff_enum(f"{path}.{new_name}", old["enums"][old_name], new["enums"][new_name],
                            f"{'.'.join(old_key)}.{old_name}" if old_name != new_name else None)
        for name in removed:
            self.add(BREAKING, "enum_removed", f"{'.'.join(old_key)}.{name}", "enum removed")
        for name in added:
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

        if old["base_size"] != new["base_size"] and not any(
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
        if len(old_members) == len(new_members):
            old_set = sorted(((m["name"], self._wire_signature(m, True)) for m in old_members),
                             key=lambda item: item[0])
            new_set = sorted(((m["name"], self._wire_signature(m, False)) for m in new_members),
                             key=lambda item: item[0])
            old_names = [m["name"] for m in old_members]
            new_names = [m["name"] for m in new_members]
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
        path = f"{message_path}.{new['name']}"
        if old["name"] != new["name"]:
            self.add(RENAME, "oneof_renamed", f"{message_path}.{old['name']}",
                     f"oneof renamed to {new['name']}", old["name"], new["name"])
        before = len(self.changes)
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
            self.add(COMPATIBLE, "oneof_min_size_changed", path,
                     f"min_size {old['min_size']} -> {new['min_size']}", old["min_size"], new["min_size"])

        def check_discriminator(variant_path, old_variant, new_variant):
            if old_variant["disc"] != new_variant["disc"]:
                self.add(BREAKING, "variant_discriminator_changed", variant_path,
                         f"discriminator value {old_variant['disc']} -> {new_variant['disc']}",
                         old_variant["disc"], new_variant["disc"])

        self._diff_members(path, "variant", old["variants"], new["variants"],
                           old["extensions_start"], new["extensions_start"], check_discriminator)

        if old["base_size"] != new["base_size"] and not any(
                c.category == BREAKING for c in self.changes[before:]):
            self.add(BREAKING, "oneof_size_changed", path,
                     f"base union size {old['base_size']} -> {new['base_size']} bytes",
                     old["base_size"], new["base_size"])


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
