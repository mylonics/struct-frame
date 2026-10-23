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
import keyword
import re

LANGUAGES = ('c', 'cpp', 'ts', 'js', 'py', 'gql', 'csharp', 'rust')
ALL_LANGUAGES_KEY = 'all'

_SEPARATORS = re.compile(r'[\W_]+')
_BOUNDARY = re.compile(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])')
_IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
_SCHEMA_TYPES = {
    'uint8', 'int8', 'uint16', 'int16', 'uint32', 'int32', 'bool', 'float',
    'double', 'int64', 'uint64', 'string', 'bytes',
}
_C_KEYWORDS = set('''auto break case char const continue default do double else enum extern
float for goto if inline int long register restrict return short signed sizeof static
struct switch typedef union unsigned void volatile while _Alignas _Alignof _Atomic
_Bool _Complex _Generic _Imaginary _Noreturn _Static_assert _Thread_local'''.split())
_CPP_KEYWORDS = _C_KEYWORDS | set('''alignas alignof and and_eq asm atomic_cancel atomic_commit
atomic_noexcept bitand bitor bool catch char8_t char16_t char32_t class compl concept
consteval constexpr constinit const_cast co_await co_return co_yield decltype delete
dynamic_cast explicit export false friend mutable namespace new noexcept not not_eq nullptr
operator or or_eq private protected public reflexpr reinterpret_cast requires static_assert
static_cast synchronized template this thread_local throw true try typeid typename
using virtual wchar_t xor xor_eq'''.split())
_JS_KEYWORDS = set('''await break case catch class const continue debugger default delete do
else export extends finally for function if import in instanceof let new return super
switch this throw try typeof var void while with yield enum implements interface package
private protected public static null true false'''.split())
_CSHARP_KEYWORDS = set('''abstract as base bool break byte case catch char checked class const
continue decimal default delegate do double else enum event explicit extern false finally
fixed float for foreach goto if implicit in int interface internal is lock long namespace
new null object operator out override params private protected public readonly ref return
sbyte sealed short sizeof stackalloc static string struct switch this throw true try typeof
uint ulong unchecked unsafe ushort using virtual void volatile while add alias ascending
async await by descending dynamic equals from get global group into join let nameof on orderby
partial remove select set value var when where yield'''.split())
_RUST_KEYWORDS = set('''as async await break const continue crate dyn else enum extern false fn
for if impl in let loop match mod move mut pub ref return self Self static struct super
trait true type unsafe use where while abstract become box do final macro override priv typeof
unsized virtual yield try'''.split())
_GRAPHQL_KEYWORDS = {'true', 'false', 'null'}


class ExplicitName(str):
    """A replacement name that must bypass target-language case conversion."""


def _keywords(lang):
    return {
        'c': _C_KEYWORDS,
        'cpp': _CPP_KEYWORDS,
        'ts': _JS_KEYWORDS,
        'js': _JS_KEYWORDS,
        'py': set(keyword.kwlist),
        'gql': _GRAPHQL_KEYWORDS,
        'csharp': _CSHARP_KEYWORDS,
        'rust': _RUST_KEYWORDS,
    }[lang]


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
    if isinstance(name, ExplicitName):
        return str(name)
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
    if isinstance(name, ExplicitName):
        return str(name)
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
    if isinstance(name, ExplicitName):
        return str(name)
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
        return ExplicitName(override) if override is not None else path[-1]

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
        type_paths = set()
        for pkg_name, pkg in packages.items():
            paths = _type_declaration_paths(pkg)
            type_paths.update('.'.join(path) for path in paths)
            type_paths.update('.'.join((pkg_name,) + path) for path in paths)
        for lang in LANGUAGES:
            mapping = dict(self.table.get(ALL_LANGUAGES_KEY, {}))
            mapping.update(self.table.get(lang, {}))
            for path, replacement in mapping.items():
                if replacement in _keywords(lang):
                    raise NameOverrideError(
                        f"{lang}: override '{path}' -> '{replacement}' is a reserved keyword")
                if path in type_paths and replacement in _SCHEMA_TYPES:
                    raise NameOverrideError(
                        f"{lang}: type override '{path}' -> '{replacement}' is a built-in schema type")
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


def _type_declaration_paths(pkg):
    paths = [(name,) for name in pkg.enums]
    for msg_name, msg in pkg.messages.items():
        paths.append((msg_name,))
        paths.extend((msg_name, enum_name) for enum_name in msg.enums)
    return paths


def validate_generated_names(packages, languages, overrides=None):
    """Reject final identifiers that collide within a generated language scope."""
    for lang in languages:
        language_packages = overrides.apply(lang, packages) if overrides else packages
        _validate_language_names(lang, language_packages)


def _validate_language_names(lang, packages):
    def record(scope, name, source, seen):
        previous = seen.get(name)
        if previous is not None:
            raise NameOverrideError(
                f"{lang}: generated name collision '{name}' in {scope}: {previous} and {source}")
        seen[name] = source

    def enum_entry_name(name):
        if lang == 'gql' and not isinstance(name, ExplicitName):
            value = str(name)
            return value if value.replace('_', '').isupper() else re.sub(
                r'(?<!^)(?=[A-Z])', '_', value).upper()
        if lang in ('cpp', 'ts', 'js'):
            return to_pascal_case(name)
        return to_screaming_snake_case(name)

    def member_name(name):
        if lang == 'csharp':
            return to_pascal_case(name)
        if lang in ('ts', 'js'):
            return to_camel_case(name)
        return name

    # Names a generated member can never take. C headers must stay includable
    # from C++, so C is checked against the C++ keyword set.
    if lang in ('c', 'cpp'):
        reserved = _CPP_KEYWORDS
    elif lang == 'py':
        reserved = set(keyword.kwlist) | {'self'}
    elif lang in ('ts', 'js'):
        reserved = _JS_KEYWORDS
    elif lang == 'rust':
        # The Rust generator escapes other keywords as r#name; these four
        # cannot be raw identifiers.
        reserved = {'self', 'Self', 'super', 'crate'}
    else:
        reserved = set()

    def check_reserved(emitted, what):
        if emitted in reserved:
            raise NameOverrideError(
                f"{lang}: {what} is named '{emitted}', which is a reserved word in {lang}; "
                f"rename it in the schema or map it with --name_overrides")

    def check_class_member(emitted, class_name, source):
        # C#: a member cannot share the name of its enclosing type (CS0542).
        if lang == 'csharp' and emitted == to_pascal_case(class_name):
            raise NameOverrideError(
                f"{lang}: member '{emitted}' ({source}) has the same name as its "
                f"enclosing class '{class_name}'; rename the field or the message")

    c_constants = {}
    for pkg_name, pkg in packages.items():
        types = {}
        for enum_name in pkg.enums:
            record(f"package '{pkg_name}'", enum_name, f"{pkg_name}.{enum_name}", types)
        if lang == 'c':
            # Enum values are unprefixed globals in C (ENUM_ENTRY).
            for enum_name, enum in pkg.enums.items():
                for entry in enum.data:
                    constant = f"{to_screaming_snake_case(enum_name)}_{to_screaming_snake_case(entry)}"
                    record("the C global namespace", constant,
                           f"{pkg_name}.{enum_name}.{entry}", c_constants)
        for msg_name, msg in pkg.messages.items():
            record(f"package '{pkg_name}'", msg_name, f"{pkg_name}.{msg_name}", types)
            if lang == 'c':
                # C has no nested types: Foo.Bar is flattened to the type FooBar.
                for nested in msg.enums:
                    record(f"package '{pkg_name}'", f"{msg_name}{nested}",
                           f"{pkg_name}.{msg_name}.{nested} (flattened nested enum)", types)

            members = {}
            for field_name in msg.fields:
                emitted = member_name(field_name)
                check_reserved(emitted, f"field '{pkg_name}.{msg_name}.{field_name}'")
                record(f"message '{pkg_name}.{msg_name}'", emitted,
                       f"{pkg_name}.{msg_name}.{field_name}", members)
                check_class_member(emitted, msg_name, f"{pkg_name}.{msg_name}.{field_name}")
            for oneof_name, oneof in msg.oneofs.items():
                # The oneof itself is a member (union/accessor), and the
                # generators add a "<oneof>_discriminator" member next to it.
                check_reserved(member_name(oneof_name), f"oneof '{pkg_name}.{msg_name}.{oneof_name}'")
                # In the C family the oneof union and its discriminator are
                # struct members; elsewhere (e.g. C#, where a variant may share
                # its oneof's name) they live in their own scope.
                if lang in ('c', 'cpp'):
                    record(f"message '{pkg_name}.{msg_name}'", member_name(oneof_name),
                           f"{pkg_name}.{msg_name}.{oneof_name} (oneof)", members)
                    if oneof.auto_discriminator:
                        record(f"message '{pkg_name}.{msg_name}'",
                               member_name(f"{oneof_name}_discriminator"),
                               f"{pkg_name}.{msg_name}.{oneof_name} (oneof discriminator)", members)
                if oneof.discriminator_type == "field_order":
                    # field_order oneofs get an enum with a NONE = 0 entry plus
                    # one entry per variant, in a single flat scope.
                    entries = {}
                    record(f"discriminator enum of '{pkg_name}.{msg_name}.{oneof_name}'",
                           enum_entry_name('none'), "the implicit 'none' entry", entries)
                    for variant in oneof.fields:
                        record(f"discriminator enum of '{pkg_name}.{msg_name}.{oneof_name}'",
                               enum_entry_name(variant),
                               f"{pkg_name}.{msg_name}.{oneof_name}.{variant}", entries)
                # Variants live in the message's member scope only where the
                # generator flattens them into the class (C#). Elsewhere they
                # sit inside the oneof's own union/dict/accessor namespace, so
                # sharing a name with a plain field is valid (and compiled
                # before name validation existed).
                variant_scope = members if lang == 'csharp' else {}
                for field_name in oneof.fields:
                    emitted = member_name(field_name)
                    check_reserved(emitted, f"variant '{pkg_name}.{msg_name}.{oneof_name}.{field_name}'")
                    record(f"message '{pkg_name}.{msg_name}'", emitted,
                           f"{pkg_name}.{msg_name}.{oneof_name}.{field_name}", variant_scope)
                    check_class_member(emitted, msg_name,
                                       f"{pkg_name}.{msg_name}.{oneof_name}.{field_name}")

        for enum_name, enum in pkg.enums.items():
            entries = {}
            for entry_name in enum.data:
                record(f"enum '{pkg_name}.{enum_name}'", enum_entry_name(entry_name),
                       f"{pkg_name}.{enum_name}.{entry_name}", entries)
        for msg_name, msg in pkg.messages.items():
            for enum_name, enum in msg.enums.items():
                entries = {}
                for entry_name in enum.data:
                    record(f"enum '{pkg_name}.{msg_name}.{enum_name}'", enum_entry_name(entry_name),
                           f"{pkg_name}.{msg_name}.{enum_name}.{entry_name}", entries)
