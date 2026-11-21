"""Lowering: build the generator's model (``generate.Package``/``Message``/...) from a
parsed schema file.

The model is exactly what the generators have always consumed, so lowering is the only
place that knows the surface syntax. Semantic checks that need positions (duplicate
declarations, attribute values, sizes, literal types) happen here; the remaining checks
(type resolution, sizes, defaults against resolved types, IDs) stay in the model's
``validate()`` methods.
"""

import math
import os

from struct_frame import language_facts as facts

from . import ast
from .diagnostics import did_you_mean


# The generator module whose model is being built. It is passed in by the caller: the
# generator can be imported under more than one name (``struct_frame.generate`` and, in
# some test setups, a top-level ``generate``), and each copy has its own global model.
_GEN = None


def _gen():
    if _GEN is not None:
        return _GEN
    from struct_frame import generate
    return generate


# ---------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------

class _Value:
    """An evaluated literal: ``kind`` is int, float, str, bool, name, array or struct."""

    __slots__ = ("kind", "value", "pos")

    def __init__(self, kind, value, pos):
        self.kind = kind
        self.value = value
        self.pos = pos


_KIND_WORDS = {"int": "an integer", "float": "a number", "str": "a string", "bool": "true or false",
               "name": "a name", "array": "an array", "struct": "a struct value"}


class _Ctx:
    """Lowering context for one file."""

    def __init__(self, sink, package_name, abs_filename):
        self.sink = sink
        self.package_name = package_name
        self.abs_filename = abs_filename
        self.ok = True

    def error(self, code, message, pos, length=1, hint=None):
        self.sink.error(code, message, pos, length, hint)
        self.ok = False

    def warning(self, code, message, pos, length=1, hint=None):
        self.sink.warning(code, message, pos, length, hint)

    # -- constants ------------------------------------------------------------

    def lookup_const(self, name):
        g = _gen()
        if "." in name:
            pkg_name, bare = name.split(".", 1)
            pkg = g.packages.get(pkg_name)
            if pkg is not None and bare in pkg.consts:
                return pkg.consts[bare]
            return None
        pkg = g.packages.get(self.package_name)
        if pkg is not None:
            return pkg.consts.get(name)
        return None

    def evaluate(self, lit):
        if isinstance(lit, ast.IntLit):
            return _Value("int", lit.value, lit.pos)
        if isinstance(lit, ast.FloatLit):
            return _Value("float", lit.value, lit.pos)
        if isinstance(lit, ast.StrLit):
            return _Value("str", lit.value, lit.pos)
        if isinstance(lit, ast.BoolLit):
            return _Value("bool", lit.value, lit.pos)
        if isinstance(lit, ast.Neg):
            inner = self.evaluate(lit.operand)
            if inner.kind in ("int", "float"):
                return _Value(inner.kind, -inner.value, lit.pos)
            self.error("SF0401", f"'-' needs a number, not {_KIND_WORDS[inner.kind]}", lit.pos)
            return _Value("int", 0, lit.pos)
        if isinstance(lit, ast.NameRef):
            if lit.name == "inf":
                return _Value("float", math.inf, lit.pos)
            if lit.name == "nan":
                return _Value("float", math.nan, lit.pos)
            const = self.lookup_const(lit.name)
            if const is not None:
                kind = {"string": "str", "bool": "bool", "float": "float",
                        "double": "float"}.get(const.const_type, "int")
                return _Value(kind, const.value, lit.pos)
            return _Value("name", lit.name, lit.pos)
        if isinstance(lit, ast.ArrayLit):
            return _Value("array", [self.evaluate(x) for x in lit.items], lit.pos)
        if isinstance(lit, ast.StructLit):
            return _Value("struct", [(f.name, self.evaluate(f.value), f.pos) for f in lit.fields],
                          lit.pos)
        raise TypeError(lit)

    def integer(self, lit, what, lo=None, hi=None):
        """Evaluate *lit* as an integer in [lo, hi]; report and return None otherwise."""
        val = self.evaluate(lit)
        if val.kind == "name":
            self.error("SF0402", f"unknown constant '{val.value}'", val.pos, len(val.value),
                       hint=self._const_hint(val.value))
            return None
        if val.kind != "int":
            self.error("SF0401", f"{what} must be an integer, not {_KIND_WORDS[val.kind]}", val.pos)
            return None
        if (lo is not None and val.value < lo) or (hi is not None and val.value > hi):
            self.error("SF0403", f"{what} {val.value} is out of range ({lo}..{hi})", val.pos,
                       len(str(val.value)))
            return None
        return val.value

    def _const_hint(self, name):
        g = _gen()
        pkg = g.packages.get(self.package_name)
        names = list(pkg.consts) if pkg else []
        hint = did_you_mean(name, names).strip()
        return hint.strip(" ()") if hint else None


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

_SCALAR_KINDS = {name: kind for name, (kind, _size) in facts.PRIMITIVES.items()}


def _canonical_name(name):
    return facts.PRIMITIVE_ALIASES.get(name, name)


def _apply_type(ctx, f, typ):
    """Set the type/array/size attributes of model field *f* from *typ*."""
    g = _gen()
    lo, hi = facts.SIZE_OPTION_RANGE

    def size_of(t, what):
        return ctx.integer(t.size, what, lo, hi)

    if typ.container in ("array", "vector"):
        f.is_array = True
        count = size_of(typ, "array length" if typ.container == "array" else "vector capacity")
        if typ.container == "array":
            f.size_option = count
        else:
            f.max_size = count
        elem = typ.element
        if elem.container in ("array", "vector"):
            ctx.error("SF0321", f"nested {elem.spelled}s are not supported", elem.pos, len(elem.spelled),
                      hint="wrap the inner array in a struct")
            elem_type = "uint8"
        elif elem.container in ("string", "bytes"):
            ctx.error("SF0322", f"{typ.spelled} elements cannot be bounded {elem.spelled}s",
                      elem.pos, len(elem.spelled),
                      hint=f"use fixed_{elem.container}<N>: each element is stored at full size")
            elem_type = elem.container
        elif elem.container in ("fixed_string", "fixed_bytes"):
            elem_type = "string" if elem.container == "fixed_string" else "bytes"
            f.element_size = size_of(elem, "element capacity")
        else:
            elem_type = _canonical_name(elem.name)
        f.field_type = elem_type
    elif typ.container in ("string", "bytes"):
        f.field_type = typ.container
        f.max_size = size_of(typ, f"{typ.spelled} capacity")
    elif typ.container in ("fixed_string", "fixed_bytes"):
        f.field_type = "string" if typ.container == "fixed_string" else "bytes"
        f.size_option = size_of(typ, f"{typ.spelled} size")
    else:
        f.field_type = _canonical_name(typ.name)

    if f.field_type in g.default_types:
        f.is_default_type = True
        f.size = g.default_types[f.field_type]["size"]
        f.validated = True


def _type_text(typ):
    if typ.container is None:
        return typ.name
    if typ.element is not None:
        return f"{typ.container}<{_type_text(typ.element)}, N>"
    return f"{typ.container}<N>"


# ---------------------------------------------------------------------------
# Declarations
# ---------------------------------------------------------------------------

def _set_pos(obj, pos):
    obj.line = pos.line
    obj.col = pos.col


def _docs(node_comments, obj):
    for text in node_comments.trailing_docs():
        obj.add_trailing_comment(text)


# Options of the old proto-style syntax that are no longer attributes, and what replaced them.
_LEGACY_ATTRIBUTE_HINTS = {
    "default": "write a default after the name: uint32 retry_ms = 1000;",
    "size": "sizes are part of the type: fixed_string<N>, fixed_bytes<N>, array<T, N>",
    "max_size": "sizes are part of the type: string<N>, bytes<N>, vector<T, N>",
    "element_size": "string array elements are typed: vector<fixed_string<N>, COUNT>",
    "msgid": "write the id after the name: message Name @ID { ... }",
    "pkgid": "write the id after the package name: package name @ID;",
    "is_envelope": "the attribute is called 'envelope'",
    "magic_bytes": "the attribute is called 'magic': [magic = [0xA3, 0x7F]]",
    "extensions_start": "put extension fields in an 'extensions { ... }' block at the end",
}


def _attrs(ctx, attrs, kind, decl_name):
    """Validate attribute names/values for a declaration kind; returns {name: _Value|True}."""
    allowed = facts.ATTRIBUTES.get(kind, {})
    out = {}
    for attr in attrs:
        if attr.name not in allowed:
            legacy = _LEGACY_ATTRIBUTE_HINTS.get(attr.name)
            if allowed:
                listing = ", ".join(allowed)
                ctx.error("SF0330", f"unknown attribute '{attr.name}' on {kind} {decl_name}"
                          f"{'' if legacy else did_you_mean(attr.name, allowed)}", attr.pos,
                          len(attr.name), hint=legacy or f"{kind} attributes: {listing}")
            else:
                ctx.error("SF0330", f"{kind}s take no attributes", attr.pos, len(attr.name))
            continue
        if attr.name in out:
            ctx.error("SF0331", f"attribute '{attr.name}' is given twice", attr.pos, len(attr.name))
            continue
        vtype = allowed[attr.name]
        if attr.value is None:
            if vtype != "bool":
                ctx.error("SF0332", f"attribute '{attr.name}' needs a value: [{attr.name} = ...]",
                          attr.pos, len(attr.name))
                continue
            out[attr.name] = True
            continue
        val = ctx.evaluate(attr.value)
        if vtype == "bool":
            if val.kind != "bool":
                ctx.error("SF0333", f"attribute '{attr.name}' is a flag: write [{attr.name}] or "
                          f"[{attr.name} = true]", val.pos)
                continue
            out[attr.name] = val.value
        elif vtype == "int":
            v = ctx.integer(attr.value, f"'{attr.name}'", facts.ONEOF_SIZE_MIN, facts.SIZE_OPTION_RANGE[1])
            if v is not None:
                out[attr.name] = v
        elif vtype == "discriminator":
            text = val.value if val.kind in ("name", "str") else None
            mode = text if text in facts.DISCRIMINATOR_MODES else None
            if mode is None:
                ctx.error("SF0334", f"invalid discriminator '{val.value}'"
                          f"{did_you_mean(str(val.value), facts.DISCRIMINATOR_MODES)}",
                          val.pos, len(str(val.value)),
                          hint=f"one of: {', '.join(facts.DISCRIMINATOR_MODES)}")
                continue
            out[attr.name] = mode
        elif vtype == "magic":
            lo, hi = facts.MAGIC_BYTE_RANGE
            if val.kind != "array" or len(val.value) != facts.MAGIC_BYTES_COUNT:
                ctx.error("SF0335", "magic needs exactly two bytes, e.g. [magic = [0xA3, 0x7F]]",
                          val.pos)
                continue
            got = []
            for item in val.value:
                if item.kind != "int":
                    ctx.error("SF0335", "magic bytes must be integers", item.pos)
                    break
                if item.value == 0:
                    ctx.error("SF0335", "magic bytes must be non-zero", item.pos,
                              hint="zero is reserved: it is the seed of messages the receiver "
                                   "does not know")
                    break
                if not lo <= item.value <= hi:
                    ctx.error("SF0335", f"magic byte {item.value} is out of range ({lo}..{hi})",
                              item.pos)
                    break
                got.append(item.value)
            else:
                out[attr.name] = tuple(got)
    return out


def _raw_value(ctx, val):
    """An evaluated literal as the raw value Field.validate checks against the type:
    scalars as Python values, names as ``DefaultRef``, arrays as lists and struct
    literals as dicts."""
    g = _gen()
    if val.kind == "name":
        return g.DefaultRef(val.value)
    if val.kind == "array":
        return [_raw_value(ctx, item) for item in val.value]
    if val.kind == "struct":
        out = {}
        for name, item, pos in val.value:
            if name in out:
                ctx.error("SF0407", f"'{name}' is given twice in a struct value", pos, len(name))
                continue
            out[name] = _raw_value(ctx, item)
        return out
    return val.value


def _default_value(ctx, f, decl):
    """Raw default value for model field *f*, type-checked here where the type is known
    (a scalar field); composite values are checked by Field.validate."""
    val = ctx.evaluate(decl.default)
    ftype = f.field_type
    if f.is_default_type and not f.is_array:
        kind = _SCALAR_KINDS[ftype]
        want = {"int": ("int",), "float": ("int", "float"), "bool": ("bool",),
                "string": ("str",), "bytes": ("str", "array")}[kind]
        if val.kind == "name":
            ctx.error("SF0402", f"unknown constant '{val.value}'", val.pos, len(val.value),
                      hint=ctx._const_hint(val.value))
            return None
        if val.kind not in want:
            ctx.error("SF0404", f"default of {decl.name} must be {_KIND_WORDS[want[0]]} "
                      f"(field type {_type_text(decl.type)}), not {_KIND_WORDS[val.kind]}", val.pos)
            return None
    if f.is_array and val.kind != "array":
        ctx.error("SF0404", f"default of array {decl.name} must be an array literal such as "
                  f"[1, 2, 3], not {_KIND_WORDS[val.kind]}", val.pos)
        return None
    return _raw_value(ctx, val)


def _field(ctx, decl, number, in_oneof):
    g = _gen()
    f = g.Field(ctx.package_name, decl.comments.leading_docs())
    _docs(decl.comments, f)
    f.name = decl.name
    _set_pos(f, decl.pos)
    f.number = number
    _apply_type(ctx, f, decl.type)
    attrs = _attrs(ctx, decl.attrs, "field", decl.name)
    if attrs.get("flatten"):
        f.flatten = True
    if decl.default is not None:
        f.default = _default_value(ctx, f, decl)
    f.source_file = ctx.abs_filename
    return f


def _enum(ctx, decl, message_name=None):
    g = _gen()
    e = g.Enum(ctx.package_name, decl.comments.leading_docs())
    e.name = decl.name
    _set_pos(e, decl.pos)
    e.source_file = ctx.abs_filename
    e.message = message_name
    _attrs(ctx, decl.attrs, "enum", decl.name)
    lo, hi = facts.ENUM_VALUE_RANGE
    seen = {}

    def add(entry, is_ext):
        if entry.name in e.data:
            ctx.error("SF0340", f"enum entry '{entry.name}' is declared twice in enum {decl.name}",
                      entry.pos, len(entry.name))
            return None
        value = ctx.integer(entry.value, f"value of {entry.name}", lo, hi) if entry.value else None
        if value is None:
            value = 0
            ctx.ok = False
        elif value in seen:
            ctx.error("SF0341", f"{entry.name} = {value} reuses the value of {seen[value]}",
                      entry.pos, len(entry.name), hint="enum values must be unique")
        seen[value] = entry.name
        entry_docs = g._EntryDocs(entry.comments.leading_docs())
        _set_pos(entry_docs, entry.pos)
        _docs(entry.comments, entry_docs)
        e.data[entry.name] = (value, entry_docs.comments)
        e.entry_trailing_comments[entry.name] = entry_docs.trailing_comments
        return value

    base_values = [v for v in (add(x, False) for x in decl.entries) if v is not None]
    if decl.ext_entries is not None:
        ext_values = [v for v in (add(x, True) for x in decl.ext_entries) if v is not None]
        if ext_values:
            e.extensions_start = min(ext_values)
            if base_values and max(base_values) >= e.extensions_start:
                ctx.error("SF0342", f"extension entries of enum {decl.name} must have larger values "
                          f"than every base entry (base goes up to {max(base_values)})",
                          decl.ext_pos, 10)
        else:
            ctx.warning("SF0343", "empty 'extensions' block has no effect", decl.ext_pos, 10)
    _docs(decl.comments, e)
    return e


def _oneof(ctx, decl, message):
    g = _gen()
    o = g.OneOf(ctx.package_name, decl.comments.leading_docs())
    o.name = decl.name
    _set_pos(o, decl.pos)
    o.source_file = message.source_file
    attrs = _attrs(ctx, decl.attrs, "oneof", decl.name)
    if "discriminator" in attrs:
        o.discriminator_mode = attrs["discriminator"]
    if attrs.get("variable"):
        o.variable = True
    if "max_size" in attrs:
        o.max_size_override = attrs["max_size"]
    if "min_size" in attrs:
        o.min_size_override = attrs["min_size"]
    variants = list(decl.variants)
    ext = decl.ext_variants or []
    if decl.ext_variants is not None:
        if not ext:
            ctx.warning("SF0343", "empty 'extensions' block has no effect", decl.ext_pos, 10)
        elif not variants:
            ctx.error("SF0344", f"oneof {decl.name} needs at least one variant before its "
                      f"'extensions' block", decl.ext_pos, 10)
        else:
            o.extensions_start = len(variants) + 1
    for number, var in enumerate(variants + ext, start=1):
        if var.name in o.fields:
            ctx.error("SF0345", f"variant '{var.name}' is declared twice in oneof {decl.name}",
                      var.name_pos, len(var.name))
            continue
        f = _field(ctx, var, number, in_oneof=True)
        o.fields[var.name] = f
        o.field_order.append(var.name)
    _docs(decl.comments, o)
    return o


def _message(ctx, decl):
    g = _gen()
    m = g.Message(ctx.package_name, decl.comments.leading_docs())
    m.name = decl.name
    _set_pos(m, decl.pos)
    m.source_file = ctx.abs_filename
    if decl.kind == "message" and decl.id is not None:
        m.id = ctx.integer(decl.id, f"id of message {decl.name}", 0, facts.MSGID_RANGE[1])
    attrs = _attrs(ctx, decl.attrs, decl.kind, decl.name)
    if attrs.get("variable"):
        m.variable = True
    if attrs.get("envelope"):
        m.is_envelope = True
    if "magic" in attrs:
        m.magic_bytes_override = attrs["magic"]

    names = {}

    def claim(name, pos, what):
        if name in names:
            ctx.error("SF0346", f"{what} '{name}' is declared twice in {decl.kind} {decl.name}",
                      pos, len(name))
            return False
        names[name] = what
        return True

    number = 0
    seen_oneof = None
    seen_ext = None
    for member in decl.members:
        if isinstance(member, ast.FieldDecl):
            if seen_ext is not None:
                ctx.error("SF0347", "fields cannot follow the 'extensions' block",
                          member.pos, 1, hint="move the field into the block or above it")
            if seen_oneof is not None:
                ctx.error("SF0348", f"field {member.name} is declared after oneof {seen_oneof}",
                          member.pos, 1,
                          hint="declare fields before oneofs: oneofs are always encoded after the fields")
            if not claim(member.name, member.name_pos, "field"):
                continue
            number += 1
            m.fields[member.name] = _field(ctx, member, number, in_oneof=False)
        elif isinstance(member, ast.ExtensionsBlock):
            if seen_ext is not None:
                ctx.error("SF0305", "only one 'extensions' block is allowed per scope", member.pos, 10)
                continue
            seen_ext = member
            if not member.fields:
                ctx.warning("SF0343", "empty 'extensions' block has no effect", member.pos, 10)
                continue
            if number == 0:
                ctx.error("SF0344", f"{decl.kind} {decl.name} needs at least one field before its "
                          f"'extensions' block", member.pos, 10)
            m.extensions_start = number + 1
            for fdecl in member.fields:
                if not claim(fdecl.name, fdecl.name_pos, "field"):
                    continue
                number += 1
                m.fields[fdecl.name] = _field(ctx, fdecl, number, in_oneof=False)
        elif isinstance(member, ast.OneofDecl):
            if not claim(member.name, member.pos, "oneof"):
                continue
            seen_oneof = member.name
            m.oneofs[member.name] = _oneof(ctx, member, m)
        elif isinstance(member, ast.EnumDecl):
            if member.name in m.enums:
                ctx.error("SF0346", f"enum '{member.name}' is declared twice in {decl.kind} {decl.name}",
                          member.pos, len(member.name))
                continue
            m.enums[member.name] = _enum(ctx, member, message_name=decl.name)
    _docs(decl.comments, m)
    return m


def _const(ctx, decl):
    g = _gen()
    tname = _canonical_name(decl.type.name) if decl.type.container is None else None
    if tname not in facts.PRIMITIVES or tname == "bytes":
        ctx.error("SF0350", f"constant {decl.name} must have a primitive or string type",
                  decl.type.pos, len(decl.type.spelled or decl.type.name))
        return None
    val = ctx.evaluate(decl.value)
    kind = _SCALAR_KINDS[tname]
    want = {"int": ("int",), "float": ("int", "float"), "bool": ("bool",), "string": ("str",)}[kind]
    if val.kind not in want:
        if val.kind == "name":
            ctx.error("SF0402", f"unknown constant '{val.value}'", val.pos, len(val.value))
        else:
            ctx.error("SF0404", f"constant {decl.name} of type {decl.type.spelled} needs "
                      f"{_KIND_WORDS[want[-1]]}, not {_KIND_WORDS[val.kind]}", val.pos)
        return None
    value = val.value
    if kind == "int":
        lo, hi = facts.INTEGER_RANGES[tname]
        if not lo <= value <= hi:
            ctx.error("SF0403", f"constant {decl.name} = {value} does not fit {tname} ({lo}..{hi})",
                      val.pos)
            return None
    elif kind == "float":
        value = float(value)
        if tname == "float" and math.isfinite(value) and abs(value) > facts.FLOAT_MAX:
            ctx.error("SF0403", f"constant {decl.name} = {value} does not fit float", val.pos)
            return None
    c = g.Const(ctx.package_name, decl.name, tname, value, decl.comments.leading_docs())
    _docs(decl.comments, c)
    _set_pos(c, decl.pos)
    c.source_file = ctx.abs_filename
    return c


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

def lower_file(tree, sink, filename, abs_filename, base_path, importing_package, gen_module=None):
    """Add the declarations of one parsed file to the generator's global model.

    Mirrors the bookkeeping of the original front end: package/file docs, package ids,
    import edges (``package_imports``/``pending_package_imports``) and recursive parsing
    of imported files. Returns True on success; diagnostics go to *sink*.
    """
    global _GEN
    previous = _GEN
    if gen_module is not None:
        _GEN = gen_module
    try:
        return _lower_file(tree, sink, filename, abs_filename, base_path, importing_package)
    finally:
        _GEN = previous


def _lower_file(tree, sink, filename, abs_filename, base_path, importing_package):
    g = _gen()
    if tree.package is None:
        return False
    package_name = tree.package.name
    if package_name not in g.packages:
        g.packages[package_name] = g.Package(package_name)
    pkg = g.packages[package_name]
    pkg.add_file_docs(abs_filename, tree.file_docs())
    g.file_to_package[abs_filename] = package_name
    ctx = _Ctx(sink, package_name, abs_filename)

    def record_package_import(importer, import_path):
        imported_abs_path = os.path.abspath(import_path)
        imported_package_name = g.file_to_package.get(imported_abs_path)
        if not imported_package_name or importer == imported_package_name:
            return False
        g.package_imports.setdefault(importer, [])
        if imported_package_name not in g.package_imports[importer]:
            g.package_imports[importer].append(imported_package_name)
        return True

    if importing_package and importing_package != package_name:
        record_package_import(importing_package, abs_filename)

    if tree.package.id is not None:
        pkgid = ctx.integer(tree.package.id, f"id of package {package_name}", *facts.PKGID_RANGE)
        if pkgid is None:
            return False
        if not g.validate_package_id(package_name, pkgid, filename):
            return False

    for imp in tree.imports:
        import_path_base = os.path.join(base_path, imp.path)
        import_path_current = os.path.join(os.path.dirname(abs_filename), imp.path)
        if os.path.exists(import_path_base):
            import_path = import_path_base
        elif os.path.exists(import_path_current):
            import_path = import_path_current
        else:
            ctx.error("SF0360", f"cannot find imported file '{imp.path}'", imp.pos, 6,
                      hint=f"looked in {os.path.dirname(import_path_base) or '.'} and "
                           f"{os.path.dirname(import_path_current) or '.'}")
            return False
        imported_abs_path = os.path.abspath(import_path)
        if not record_package_import(package_name, imported_abs_path):
            g.pending_package_imports.append((package_name, imported_abs_path))
        if not g.parseFile(import_path, base_path, package_name):
            print(f"Error: Failed to parse imported file {imp.path}")
            return False

    # Constants first, so sizes and defaults can refer to constants declared later on.
    for decl in tree.decls:
        if isinstance(decl, ast.ConstDecl):
            if decl.name in pkg.consts:
                ctx.error("SF0351", f"constant '{decl.name}' is declared twice in package "
                          f"{package_name}", decl.name_pos, len(decl.name))
                continue
            c = _const(ctx, decl)
            if c is not None:
                pkg.consts[decl.name] = c

    for decl in tree.decls:
        if isinstance(decl, ast.EnumDecl):
            if decl.name in pkg.enums:
                ctx.error("SF0352", f"enum '{decl.name}' is declared twice in package {package_name}",
                          decl.pos, 4)
                continue
            pkg.enums[decl.name] = _enum(ctx, decl)
        elif isinstance(decl, ast.MessageDecl):
            if decl.name in pkg.messages:
                ctx.error("SF0352", f"{decl.kind} '{decl.name}' is declared twice in package "
                          f"{package_name}", decl.pos, len(decl.kind))
                continue
            pkg.messages[decl.name] = _message(ctx, decl)
        elif isinstance(decl, ast.ServiceDecl):
            ctx.error("SF0390", "service declarations are not supported yet", decl.pos, 7)
    return ctx.ok
