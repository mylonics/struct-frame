#!/usr/bin/env python3
"""
Identifier tokenizing, case conversion and per-language name overrides.

Source identifiers come in many shapes (``PascalCase``, ``camelCase``,
``snake_case``, ``SCREAMING_SNAKE`` and acronym mixes such as ``BleMCuHost`` or
``BLEHost``).  Every language generator needs the same identifier in its own
style.  All conversions here share one tokenizer so the languages agree on
where the word boundaries are:

* separators (``_``, ``-``, anything that is not a letter or digit) end a token
* a lower-case letter or digit followed by an upper-case letter starts a new
  token (``gateCurrent`` -> ``gate`` ``Current``)
* an upper-case run followed by a capitalised word splits before the last
  capital (``BLEHost`` -> ``BLE`` ``Host``)

Conversions preserve acronyms that are visible in the source (``BleMCuHost``
stays ``BleMCuHost`` in PascalCase) instead of lower-casing everything but the
first letter.  Identifiers written in a single case (``BLE_HOST_OK``,
``gate_current``) carry no acronym information, so their tokens are
title-cased as before.

Heuristics cannot recover every intent (``BleMCuHost`` could just as well be
``Ble`` ``MCU`` ``Host``); ``NameOverrides`` lets a project spell out the
exact name a declaration should have in a given language.
"""

import copy
import json
import re

LANGUAGES = ('c', 'cpp', 'ts', 'js', 'py', 'gql', 'csharp', 'rust')
ALL_LANGUAGES_KEY = 'all'

_SEPARATORS = re.compile(r'[\W_]+')
_BOUNDARY = re.compile(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])')
_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def split_identifier(name):
    """Split *name* into word tokens (see the module docstring for the rules)."""
    tokens = []
    for chunk in _SEPARATORS.split(str(name)):
        if chunk:
            tokens.extend(token for token in _BOUNDARY.split(chunk) if token)
    return tokens


def _is_mixed_case(name):
    """True when *name* has both upper- and lower-case letters (so its casing carries meaning)."""
    letters = [c for c in str(name) if c.isalpha()]
    return any(c.isupper() for c in letters) and any(c.islower() for c in letters)


def _has_lowercase(name):
    return any(c.islower() for c in str(name))


def to_pascal_case(name):
    """Convert *name* to PascalCase, keeping acronyms that are visible in the source.

    ``gate_current`` -> ``GateCurrent``, ``BleMCuHost`` -> ``BleMCuHost``,
    ``BLEHost`` -> ``BLEHost``, ``bleHostId`` -> ``BleHostId``,
    ``BLE_HOST_OK`` -> ``BleHostOk`` (single-case names carry no acronym hint).
    """
    keep_caps = _is_mixed_case(name)
    parts = []
    for token in split_identifier(name):
        if keep_caps and token != token.lower():
            parts.append(token[0].upper() + token[1:])
        else:
            parts.append(token.title())
    return ''.join(parts)


def to_screaming_snake_case(name):
    """Convert an enum-entry style name to SCREAMING_SNAKE_CASE.

    Names without lower-case letters (``BLE_HOST_OK``, ``ADC1``) are simply
    upper-cased as before; mixed-case names are split at word boundaries
    (``GateCurrent`` -> ``GATE_CURRENT``, ``BleMCuHost`` -> ``BLE_M_CU_HOST``).
    """
    name = str(name)
    if not _has_lowercase(name):
        return name.upper()
    word = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    word = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', word)
    return word.replace('-', '_').upper()


def to_camel_case(name):
    """Convert snake_case (optionally with acronyms) to camelCase.

    The first part is kept verbatim; every following ``_`` separated part is
    capitalised.  Acronyms are kept when the identifier mixes cases
    (``ble_HOST_id`` -> ``bleHOSTId``); single-case identifiers
    (``MAX_VALUE``) are capitalised part by part as before.
    """
    parts = str(name).split('_')
    keep_caps = _is_mixed_case(name)
    out = [parts[0]]
    for part in parts[1:]:
        if keep_caps and part != part.lower():
            out.append(part[:1].upper() + part[1:])
        else:
            out.append(part.capitalize())
    return ''.join(out)


# =============================================================================
# Per-language name overrides
# =============================================================================

class NameOverrideError(ValueError):
    """Raised for malformed override files or overrides that match nothing."""


def _parse_key(key):
    return tuple(part for part in str(key).split('.'))


class NameOverrides:
    """Explicit per-language replacements for declaration names.

    The override table is a JSON object keyed by language (``c``, ``cpp``,
    ``ts``, ``js``, ``py``, ``gql``, ``csharp``, ``rust``) or ``all``::

        {
          "all":    {"BleMCuHost": "BleMcuHost"},
          "csharp": {"BleMCuHost.GateCurrent": "GateCurrentValue"}
        }

    Keys are dotted paths of *source* names, optionally prefixed by the package
    (``pkg.Message.field``):

    * ``Name``                    message or enum
    * ``Message.field``           field / oneof of a message
    * ``Message.oneof.variant``   variant of a oneof
    * ``Enum.ENTRY``              entry of an enum
    * ``Message.Nested``          message-scoped enum
    * ``Message.Nested.ENTRY``    entry of a message-scoped enum

    A language entry wins over ``all``; a package-qualified key wins over an
    unqualified one.  Overrides only change how a language *names* a
    declaration: wire layout, message IDs and magic bytes are computed from the
    source schema and are identical in every language.  Package names cannot be
    overridden.
    """

    def __init__(self, table=None):
        self.table = {}
        for lang, mapping in (table or {}).items():
            if mapping:
                self.table[lang] = dict(mapping)

    # -- loading ---------------------------------------------------------
    @classmethod
    def from_dict(cls, data, source='name overrides'):
        if not isinstance(data, dict):
            raise NameOverrideError(f"{source}: expected a JSON object keyed by language")
        table = {}
        for lang, mapping in data.items():
            key = ALL_LANGUAGES_KEY if lang == '*' else lang
            if key != ALL_LANGUAGES_KEY and key not in LANGUAGES:
                raise NameOverrideError(
                    f"{source}: unknown language '{lang}' "
                    f"(expected one of: {', '.join((ALL_LANGUAGES_KEY,) + LANGUAGES)})")
            if not isinstance(mapping, dict):
                raise NameOverrideError(f"{source}: '{lang}' must map names to replacement names")
            for name, replacement in mapping.items():
                if not isinstance(replacement, str) or not _IDENTIFIER.match(replacement):
                    raise NameOverrideError(
                        f"{source}: override '{name}' -> {replacement!r} in '{lang}' "
                        f"is not a valid identifier")
                if not name or any(not part for part in str(name).split('.')):
                    raise NameOverrideError(f"{source}: invalid override name {name!r} in '{lang}'")
            table.setdefault(key, {}).update(mapping)
        return cls(table)

    @classmethod
    def load(cls, path):
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
        except OSError as err:
            raise NameOverrideError(f"cannot read name overrides '{path}': {err}")
        except ValueError as err:
            raise NameOverrideError(f"name overrides '{path}' is not valid JSON: {err}")
        return cls.from_dict(data, source=str(path))

    def fingerprint(self):
        """Canonical JSON of the table (used as part of the generation cache key)."""
        return json.dumps(self.table, sort_keys=True)

    # -- lookup ----------------------------------------------------------
    def has_language(self, lang):
        return bool(self.table.get(lang) or self.table.get(ALL_LANGUAGES_KEY))

    def lookup(self, lang, package, path):
        """Return the override for declaration *path* (tuple of names) or None."""
        qualified = '.'.join((package,) + tuple(path))
        plain = '.'.join(path)
        for scope in (lang, ALL_LANGUAGES_KEY):
            mapping = self.table.get(scope)
            if not mapping:
                continue
            if qualified in mapping:
                return mapping[qualified]
            if plain in mapping:
                return mapping[plain]
        return None

    def rename(self, lang, package, path):
        """Name of the declaration at *path* in *lang* (the source name when not overridden)."""
        override = self.lookup(lang, package, path)
        return override if override is not None else path[-1]

    # -- applying --------------------------------------------------------
    def validate(self, packages):
        """Reject overrides that match no declaration or that create duplicate names."""
        known = set()
        for pkg_name, pkg in packages.items():
            for path in _declaration_paths(pkg):
                known.add('.'.join(path))
                known.add('.'.join((pkg_name,) + path))
        unknown = []
        for lang, mapping in sorted(self.table.items()):
            for key in mapping:
                if key not in known:
                    unknown.append(f"{lang}: {key}")
        if unknown:
            raise NameOverrideError(
                "name overrides do not match any declaration: " + ", ".join(unknown))
        for lang in LANGUAGES:
            if self.has_language(lang):
                self.apply(lang, packages)

    def apply(self, lang, packages):
        """Return a deep copy of *packages* with the overrides for *lang* applied.

        The copy is renamed consistently (declaration names, dictionary keys,
        type references, enum defaults and oneof bookkeeping); everything
        computed during validation -- sizes, message IDs, magic bytes -- is
        carried over unchanged.  *packages* itself is never modified.
        """
        if not self.has_language(lang):
            return packages
        renamed = copy.deepcopy(packages)
        entry_maps = {}
        for pkg_name, pkg in renamed.items():
            self._rename_package(lang, pkg_name, pkg, entry_maps)
        for pkg in renamed.values():
            for msg in pkg.messages.values():
                for field in _all_fields(msg):
                    ref = field.type_ref
                    if ref is None:
                        continue
                    field.field_type = ref.name
                    if field.type_message is not None:
                        field.type_message = ref.message
                    if field.is_enum and field.default is not None:
                        field.default = entry_maps.get(id(ref), {}).get(field.default, field.default)
        return renamed

    def _rename_package(self, lang, pkg_name, pkg, entry_maps):
        pkg.enums = self._rename_enums(lang, pkg_name, pkg.enums, (), entry_maps, 'enum')
        messages = {}
        for old_name, msg in pkg.messages.items():
            new_name = self.rename(lang, pkg_name, (old_name,))
            _put_unique(messages, new_name, msg, f"message in package '{pkg_name}'", lang)
            msg.name = new_name
            msg.enums = self._rename_enums(lang, pkg_name, msg.enums, (old_name,), entry_maps, 'nested enum')
            for enum in msg.enums.values():
                enum.message = new_name

            fields = {}
            for field_name, field in msg.fields.items():
                new_field = self.rename(lang, pkg_name, (old_name, field_name))
                _put_unique(fields, new_field, field, f"field of message '{old_name}'", lang)
                field.name = new_field
            msg.fields = fields

            oneofs = {}
            for oneof_name, oneof in msg.oneofs.items():
                new_oneof = self.rename(lang, pkg_name, (old_name, oneof_name))
                _put_unique(oneofs, new_oneof, oneof, f"oneof of message '{old_name}'", lang)
                oneof.name = new_oneof
                variant_names = {}
                variants = {}
                for variant_name, variant in oneof.fields.items():
                    new_variant = self.rename(lang, pkg_name, (old_name, oneof_name, variant_name))
                    _put_unique(variants, new_variant, variant, f"variant of oneof '{oneof_name}'", lang)
                    variant.name = new_variant
                    variant_names[variant_name] = new_variant
                oneof.fields = variants
                oneof.field_order = [variant_names.get(n, n) for n in oneof.field_order]
                oneof.variant_info = [
                    (disc, variant_names.get(n, n), size) for disc, n, size in oneof.variant_info]
            msg.oneofs = oneofs
        pkg.messages = messages

    def _rename_enums(self, lang, pkg_name, enums, scope, entry_maps, what):
        result = {}
        for old_name, enum in enums.items():
            path = scope + (old_name,)
            new_name = self.rename(lang, pkg_name, path)
            _put_unique(result, new_name, enum, f"{what} in package '{pkg_name}'", lang)
            enum.name = new_name
            mapping = {}
            data = {}
            trailing = {}
            for entry, value in enum.data.items():
                new_entry = self.rename(lang, pkg_name, path + (entry,))
                _put_unique(data, new_entry, value, f"entry of enum '{old_name}'", lang)
                if entry in enum.entry_trailing_comments:
                    trailing[new_entry] = enum.entry_trailing_comments[entry]
                mapping[entry] = new_entry
            enum.data = data
            enum.entry_trailing_comments = trailing
            entry_maps[id(enum)] = mapping
        return result


def _put_unique(mapping, name, value, what, lang):
    if name in mapping:
        raise NameOverrideError(f"{lang}: two declarations resolve to the name '{name}' ({what})")
    mapping[name] = value


def _all_fields(msg):
    fields = list(msg.fields.values())
    for oneof in msg.oneofs.values():
        fields.extend(oneof.fields.values())
    return fields


def _declaration_paths(pkg):
    """All override-addressable declaration paths in *pkg* (tuples of source names)."""
    paths = []
    for enum_name, enum in pkg.enums.items():
        paths.append((enum_name,))
        paths.extend((enum_name, entry) for entry in enum.data)
    for msg_name, msg in pkg.messages.items():
        paths.append((msg_name,))
        paths.extend((msg_name, field) for field in msg.fields)
        for enum_name, enum in msg.enums.items():
            paths.append((msg_name, enum_name))
            paths.extend((msg_name, enum_name, entry) for entry in enum.data)
        for oneof_name, oneof in msg.oneofs.items():
            paths.append((msg_name, oneof_name))
            paths.extend((msg_name, oneof_name, variant) for variant in oneof.fields)
    return paths
