"""Read schemas written in the old proto-style syntax (``struct-frame migrate``).

The old front end used the third-party ``proto-schema-parser``. This module parses a
legacy file with it and converts the result into the new syntax tree
(:mod:`struct_frame.schema.ast`), which the printer then writes in the struct-frame
language.  The conversion keeps the meaning exactly: lowering the converted tree builds
the same model the old front end built, and comments that documented a declaration are
turned into doc comments (``///``) for the same declaration, while comments the old front
end ignored become private comments (``//``).

``proto-schema-parser`` is only needed here: ``pip install 'struct-frame[migrate]'``.
"""

import contextlib
import io
import re

from struct_frame import language_facts as facts

from . import ast
from .diagnostics import DiagnosticSink, Position
from .lexer import COMMENT, Token
# Imported eagerly (not inside functions) so this module and the printer always share
# one copy of the syntax-tree classes, even if the package is re-imported.
from .parser import parse_text
from .printer import format_float, print_file


class MigrationError(Exception):
    pass


def _psp():
    try:
        from proto_schema_parser import ast as psp_ast
        from proto_schema_parser.ast import FieldCardinality
        from proto_schema_parser.parser import Parser
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise MigrationError(
            "reading the old proto-style syntax needs proto-schema-parser: "
            "pip install 'struct-frame[migrate]'") from exc
    return psp_ast, FieldCardinality, Parser


_SYNTAX_ERROR_RE = re.compile(r"^line \d+:\d+ ", re.M)


def _install_line_tracking():
    """Record the source line of every AST node proto-schema-parser builds (``_sf_line``).

    Its AST carries no positions; its visitor sees the ANTLR context of each node, so
    wrapping ``visit`` gives every node a line number.
    """
    from proto_schema_parser import parser as psp_parser
    ctor = getattr(psp_parser, "_ASTConstructor", None)
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


def parse_legacy(text, path):
    """Parse legacy schema text with proto-schema-parser (with line numbers)."""
    psp_ast, _card, Parser = _psp()
    _install_line_tracking()
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured):
        result = Parser().parse(text)
    errors = captured.getvalue()
    if _SYNTAX_ERROR_RE.search(errors):
        raise MigrationError(f"{path}: syntax error:\n" + errors.strip())
    return result


def _line(node):
    return getattr(node, "_sf_line", None) or 0


class _Converter:
    def __init__(self, path):
        self.path = path
        self.warnings = []
        self.psp, self.Card, _ = _psp()

    def warn(self, node, message):
        line = _line(node)
        loc = f"{self.path}:{line}: " if line else f"{self.path}: "
        self.warnings.append(f"{loc}warning: {message}")

    # -- comments -------------------------------------------------------------

    def tok(self, comment, doc):
        text = comment.text.rstrip()
        return Token(COMMENT, text, Position(_line(comment), 1), doc=doc,
                     inline=bool(getattr(comment, "inline", False)),
                     end_line=_line(comment) + text.count("\n"),
                     ir_text=text if doc else None)

    @staticmethod
    def as_docs(comments):
        for c in comments:
            c.doc = True
            c.ir_text = c.text.rstrip()
        return comments

    @staticmethod
    def as_private(comments):
        for c in comments:
            c.doc = False
            c.ir_text = None
        return comments

    def note(self, line, text):
        """A private ``// migrate: ...`` comment."""
        return Token(COMMENT, f"// migrate: {text}", Position(line, 1), doc=False, end_line=line)

    class _Docs:
        """Mirror of the old front end's comment ownership (generate._DocCollector)."""

        def __init__(self, conv, owner):
            self.conv = conv
            self.pending = []    # own-line comments that may document the next declaration
            self.carry = []      # private comments waiting for the next printed element
            self.target = owner  # Comments receiving same-line comments
            self.fallback = owner

        def comment(self, e):
            if getattr(e, "inline", False):
                if self.target is not None:
                    self.target.after.append(self.conv.tok(e, doc=True))
                elif self.fallback is not None:
                    self.fallback.after.append(self.conv.tok(e, doc=False))
                else:
                    self.carry.append(self.conv.tok(e, doc=False))
            else:
                self.pending.append(self.conv.tok(e, doc=False))

        def statement(self, owner=None, fallback=None):
            self.carry += self.conv.as_private(self.pending)
            self.pending = []
            self.target = owner
            self.fallback = fallback if fallback is not None else owner

        def take(self):
            out = self.carry + self.conv.as_docs(self.pending)
            self.carry, self.pending = [], []
            return out

        def declared(self, comments):
            self.target = comments
            self.fallback = comments

        def rest(self):
            out = self.carry + self.conv.as_private(self.pending)
            self.carry, self.pending = [], []
            return out

    # -- values ----------------------------------------------------------------

    @staticmethod
    def _identifier(value):
        return getattr(value, "name", None)

    def number_lit(self, value, pos):
        if isinstance(value, bool):
            return ast.BoolLit(value, pos)
        if isinstance(value, int):
            if value < 0:
                return ast.Neg(ast.IntLit(-value, pos, str(-value)), pos)
            return ast.IntLit(value, pos, str(value))
        if isinstance(value, float):
            if value < 0:
                return ast.Neg(ast.FloatLit(-value, pos, format_float(-value)), pos)
            return ast.FloatLit(value, pos, format_float(value))
        return None

    def default_lit(self, value, ftype, pos, node):
        prim = facts.PRIMITIVES.get(ftype)
        ident = self._identifier(value)
        if prim and prim[0] in ("string", "bytes"):
            # The old front end turned whatever the parser produced into text.
            if isinstance(value, bool):
                return ast.StrLit("true" if value else "false", pos)
            if ident is not None:
                return ast.StrLit(ident, pos)
            return ast.StrLit(str(value), pos)
        if ident is not None:
            if ident in ("inf", "nan"):
                return ast.NameRef(ident, pos)
            return ast.NameRef(ident, pos)
        if isinstance(value, str):
            if prim is None:
                return ast.NameRef(value, pos)
            self.warn(node, f"default {value!r} is a string on a {ftype} field")
            return ast.StrLit(value, pos)
        lit = self.number_lit(value, pos)
        if lit is None:
            raise MigrationError(f"{self.path}:{pos.line}: cannot convert default value {value!r}")
        return lit

    @staticmethod
    def _int(value):
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        try:
            return int(str(value).strip().strip("\"'"), 0)
        except ValueError:
            return None

    # -- file ------------------------------------------------------------------

    def convert(self, result):
        psp = self.psp
        f = ast.File(self.path)
        docs = self._Docs(self, None)
        found_package = False
        last_stmt = None
        pending_imports = []

        if getattr(result, "syntax", None):
            self.warn(result, "dropped 'syntax' declaration")

        for e in result.file_elements:
            t = type(e)
            if t is psp.Comment:
                if not found_package:
                    if getattr(e, "inline", False):
                        f.header.append(self.tok(e, doc=False))
                    else:
                        f.header.append(self.tok(e, doc=True))
                else:
                    docs.comment(e)
            elif t is psp.Package:
                if found_package:
                    raise MigrationError(f"{self.path}: more than one package declaration")
                found_package = True
                f.package = ast.PackageDecl(e.name, Position(_line(e), 1))
                if "." in e.name:
                    raise MigrationError(f"{self.path}: dotted package name '{e.name}' is not "
                                         f"supported; rename it with underscores")
                last_stmt = f.package.comments
                docs.statement(owner=None, fallback=last_stmt)
                f.imports.extend(pending_imports)
                pending_imports = []
            elif t is psp.Import:
                imp = ast.ImportDecl(e.name, Position(_line(e), 1))
                docs.statement(owner=None)
                imp.comments.before = docs.rest()
                last_stmt = imp.comments
                docs.fallback = last_stmt
                if getattr(e, "public", False) or getattr(e, "weak", False):
                    self.warn(e, "'import public'/'import weak' modifiers are dropped")
                (f.imports if found_package else pending_imports).append(imp)
                imp.blank_before = False
            elif t is psp.Option:
                docs.statement(owner=None, fallback=f.package.comments if f.package else None)
                if e.name == "pkgid" and f.package is not None:
                    value = self._int(e.value)
                    if value is None:
                        raise MigrationError(f"{self.path}:{_line(e)}: invalid pkgid {e.value!r}")
                    f.package.id = ast.IntLit(value, Position(_line(e), 1), str(value))
                else:
                    self.warn(e, f"dropped file option '{e.name}'")
                    docs.carry.append(self.note(_line(e), f"dropped option {e.name}"))
            elif t is psp.Enum:
                node = self.enum(e)
                node.comments.before = docs.take() + node.comments.before
                f.decls.append(node)
                docs.declared(node.comments)
            elif t is psp.Message:
                node = self.message(e)
                node.comments.before = docs.take() + node.comments.before
                f.decls.append(node)
                docs.declared(node.comments)
            else:
                what = t.__name__.lower()
                name = getattr(e, "name", None) or getattr(e, "typeName", "")
                self.warn(e, f"dropped {what} {name} (struct-frame never supported it)")
                docs.carry.append(self.note(_line(e), f"dropped {what} {name}"))
        if pending_imports:
            f.imports.extend(pending_imports)
        f.dangling = docs.rest()
        self._gaps(f)
        return f

    # -- declarations ------------------------------------------------------------

    def enum(self, e):
        psp = self.psp
        node = ast.EnumDecl(e.name, Position(_line(e), 1))
        docs = self._Docs(self, node.comments)
        ext_start = None
        entries = []
        for el in e.elements:
            t = type(el)
            if t is psp.Comment:
                docs.comment(el)
            elif t is psp.Option:
                docs.statement(owner=node.comments)
                if el.name == "extensions_start":
                    ext_start = self._int(el.value)
                    if ext_start is None:
                        raise MigrationError(f"{self.path}:{_line(el)}: invalid extensions_start")
                else:
                    self.warn(el, f"dropped enum option '{el.name}'")
            elif t is psp.EnumValue:
                pos = Position(_line(el), 1)
                entry = ast.EnumEntry(el.name, self.number_lit(el.number, pos), pos)
                entry.comments.before = docs.take()
                if getattr(el, "options", None):
                    self.warn(el, f"dropped options of enum entry {el.name}")
                entries.append(entry)
                docs.declared(entry.comments)
            else:
                self.warn(el, f"dropped {t.__name__} in enum {e.name}")
                docs.carry.append(self.note(_line(el), f"dropped {t.__name__.lower()}"))
        node.dangling = docs.rest()
        if ext_start is None:
            node.entries = entries
        else:
            base = [x for x in entries if self._entry_value(x) < ext_start]
            ext = [x for x in entries if self._entry_value(x) >= ext_start]
            if [x.name for x in entries] != [x.name for x in base + ext]:
                self.warn(e, f"enum {e.name}: extension entries moved after the base entries")
            ext_values = [self._entry_value(x) for x in ext]
            if ext and min(ext_values) != ext_start:
                self.warn(e, f"enum {e.name}: extensions_start {ext_start} becomes "
                             f"{min(ext_values)} (the smallest extension value)")
            node.entries = base
            node.ext_entries = ext
            node.ext_pos = node.pos
        return node

    @staticmethod
    def _entry_value(entry):
        v = entry.value
        if isinstance(v, ast.Neg):
            return -v.operand.value
        return v.value

    def field(self, el, node_for_warn=None):
        psp = self.psp
        pos = Position(_line(el), 1)
        options = {}
        for opt in getattr(el, "options", None) or []:
            name = facts.option_base_name(str(opt.name).strip())
            if name not in facts.FIELD_OPTIONS:
                self.warn(el, f"dropped unknown option '{opt.name}' on field {el.name}")
                continue
            options[name] = opt.value
        repeated = getattr(el, "cardinality", None) == self.Card.REPEATED
        ftype = el.type
        sizes = {}
        for key in ("size", "max_size", "element_size"):
            if key in options:
                value = self._int(options[key])
                if value is None:
                    raise MigrationError(f"{self.path}:{pos.line}: {key} of {el.name} must be an integer")
                sizes[key] = value

        def lit(v):
            return ast.IntLit(v, pos, str(v))

        def missing(what):
            raise MigrationError(f"{self.path}:{pos.line}: field {el.name} has no {what}")

        if repeated:
            if "size" in sizes:
                container, count = "array", sizes["size"]
            elif "max_size" in sizes:
                container, count = "vector", sizes["max_size"]
            else:
                missing("size or max_size")
            if ftype in ("string", "bytes"):
                if "element_size" not in sizes:
                    missing("element_size")
                elem = ast.TypeRef(f"fixed_{ftype}", pos, f"fixed_{ftype}", f"fixed_{ftype}",
                                   size=lit(sizes["element_size"]))
            else:
                elem = ast.TypeRef(ftype, pos, ftype)
            typ = ast.TypeRef(container, pos, container, container, element=elem, size=lit(count))
        elif ftype in ("string", "bytes"):
            if "size" in sizes:
                typ = ast.TypeRef(f"fixed_{ftype}", pos, f"fixed_{ftype}", f"fixed_{ftype}",
                                  size=lit(sizes["size"]))
            elif "max_size" in sizes:
                typ = ast.TypeRef(ftype, pos, ftype, ftype, size=lit(sizes["max_size"]))
            else:
                missing("size or max_size")
        else:
            typ = ast.TypeRef(ftype, pos, ftype)
        node = ast.FieldDecl(typ, el.name, pos, pos)
        if "flatten" in options and facts.is_true(options["flatten"]):
            node.attrs.append(ast.Attribute("flatten", None, pos))
        if "default" in options:
            node.default = self.default_lit(options["default"], ftype, pos, el)
        return node

    def oneof(self, e):
        psp = self.psp
        node = ast.OneofDecl(e.name, Position(_line(e), 1))
        docs = self._Docs(self, node.comments)
        variants = []
        ext_start = None
        pending_marker = False
        attrs = {}
        for el in e.elements:
            t = type(el)
            if t is psp.Comment:
                docs.comment(el)
                marker = el.text.strip().lstrip("/*# ").lstrip()
                if (marker.startswith("Extension::") and not getattr(el, "inline", False)
                        and ext_start is None):
                    pending_marker = True
            elif t is psp.Option:
                docs.statement(owner=node.comments)
                pos = Position(_line(el), 1)
                if el.name == "extensions_start":
                    ext_start = self._int(el.value)
                elif el.name == "discriminator":
                    mode = facts.normalize_discriminator(el.value)
                    if mode is None:
                        raise MigrationError(f"{self.path}:{pos.line}: invalid discriminator {el.value!r}")
                    attrs["discriminator"] = ast.Attribute("discriminator", ast.NameRef(mode, pos), pos)
                elif el.name in ("max_size", "min_size"):
                    value = self._int(el.value)
                    if value is None:
                        raise MigrationError(f"{self.path}:{pos.line}: invalid {el.name}")
                    attrs[el.name] = ast.Attribute(el.name, ast.IntLit(value, pos, str(value)), pos)
                elif el.name == "variable":
                    if facts.is_true(el.value):
                        attrs["variable"] = ast.Attribute("variable", None, pos)
                    else:
                        attrs.pop("variable", None)
                else:
                    self.warn(el, f"dropped unknown option '{el.name}' in oneof {e.name}")
            elif t is psp.Field:
                var = self.field(el)
                var.comments.before = docs.take()
                variants.append(var)
                docs.declared(var.comments)
                if pending_marker and ext_start is None:
                    ext_start = len(variants)
                pending_marker = False
            else:
                self.warn(el, f"dropped {t.__name__} in oneof {e.name}")
                docs.carry.append(self.note(_line(el), f"dropped {t.__name__.lower()}"))
        node.dangling = docs.rest()
        order = ["discriminator", "variable", "min_size", "max_size"]
        node.attrs = [attrs[k] for k in order if k in attrs]
        if ext_start is None or ext_start > len(variants):
            node.variants = variants
        else:
            node.variants = variants[:ext_start - 1]
            node.ext_variants = variants[ext_start - 1:]
            node.ext_pos = node.pos
        return node

    def message(self, e):
        psp = self.psp
        pos = Position(_line(e), 1)
        node = ast.MessageDecl("struct", e.name, pos)
        docs = self._Docs(self, node.comments)
        fields, oneofs = [], []
        members = []          # (kind, node) in source order
        msgid = None
        attrs = {}
        ext_start = None
        msg_disc = None
        for el in e.elements:
            t = type(el)
            if t is psp.Comment:
                docs.comment(el)
            elif t is psp.Option:
                docs.statement(owner=node.comments)
                opos = Position(_line(el), 1)
                name = facts.MESSAGE_OPTION_ALIASES.get(el.name, el.name)
                if name == "msgid":
                    msgid = self._int(el.value)
                    if msgid is None:
                        raise MigrationError(f"{self.path}:{opos.line}: invalid msgid {el.value!r}")
                elif name == "variable":
                    if facts.is_true(el.value):
                        attrs["variable"] = ast.Attribute("variable", None, opos)
                elif name == "is_envelope":
                    if facts.is_true(el.value):
                        attrs["envelope"] = ast.Attribute("envelope", None, opos)
                elif name == "extensions_start":
                    ext_start = self._int(el.value)
                elif name == "discriminator":
                    msg_disc = facts.normalize_discriminator(el.value)
                elif name == "magic_bytes":
                    parts = [p.strip() for p in str(el.value).split(",")]
                    items = []
                    for p in parts:
                        try:
                            items.append(ast.IntLit(int(p, 0), opos, p))
                        except ValueError:
                            raise MigrationError(f"{self.path}:{opos.line}: invalid magic_bytes "
                                                 f"{el.value!r}") from None
                    attrs["magic"] = ast.Attribute("magic", ast.ArrayLit(items, opos), opos)
                else:
                    self.warn(el, f"dropped unknown option '{el.name}' in message {e.name}")
            elif t is psp.Field:
                f = self.field(el)
                f.comments.before = docs.take()
                fields.append(f)
                members.append(("field", f))
                docs.declared(f.comments)
                if el.number is not None and el.number != len(fields):
                    self.warn(el, f"field {el.name} is numbered {el.number} but is field "
                                  f"{len(fields)}; the number is dropped (wire order is "
                                  f"declaration order)")
            elif t is psp.OneOf:
                o = self.oneof(el)
                o.comments.before = docs.take()
                oneofs.append(o)
                members.append(("oneof", o))
                docs.declared(o.comments)
            elif t is psp.Enum:
                en = self.enum(el)
                en.comments.before = docs.take()
                members.append(("enum", en))
                docs.declared(en.comments)
            else:
                # The old front end skipped these without touching comment ownership.
                what = t.__name__
                name = getattr(el, "name", "")
                self.warn(el, f"dropped {what} {name} in message {e.name} (struct-frame never "
                              f"supported it)")
                docs.carry.append(self.note(_line(el), f"dropped {what.lower()} {name}".rstrip()))
        node.dangling = docs.rest()

        if msgid is not None:
            node.kind = "message"
            node.id = ast.IntLit(msgid, pos, str(msgid))
        node.attrs = [attrs[k] for k in ("variable", "envelope", "magic") if k in attrs]

        if msg_disc is not None:
            if len(oneofs) == 1:
                o = oneofs[0]
                current = next((a for a in o.attrs if a.name == "discriminator"), None)
                if current is None or current.value.name == "auto":
                    if current is not None:
                        o.attrs.remove(current)
                    o.attrs.insert(0, ast.Attribute("discriminator", ast.NameRef(msg_disc, pos), pos))
            else:
                self.warn(e, f"message-level discriminator of {e.name} had no effect and is dropped")

        # Fields come first (oneofs are always encoded after the fields), extension fields
        # go into a trailing `extensions` block; nested enums keep their place.
        ext_fields = []
        if ext_start is not None and 1 <= ext_start <= len(fields):
            ext_fields = fields[ext_start - 1:]
        ordered, enums_after, block = [], [], None
        for kind, m in members:
            if kind == "field" and m in ext_fields:
                if block is None:
                    block = ast.ExtensionsBlock(m.pos)
                    ordered.append(block)
                block.fields.append(m)
            elif kind == "oneof":
                continue
            else:
                ordered.append(m)
        if oneofs and members.index(next(x for x in members if x[0] == "oneof")) < max(
                (i for i, (k, _) in enumerate(members) if k == "field"), default=-1):
            self.warn(e, f"message {e.name}: fields declared after a oneof moved above it "
                         f"(oneofs are always encoded after the fields)")
        # keep oneofs at the position of the first oneof if no field follows, else at end
        node.members = ordered + oneofs + enums_after
        return node

    # -- blank lines -------------------------------------------------------------

    def _gaps(self, f):
        """Mark declarations that were preceded by a blank line in the source."""
        def first_line(node):
            if node.comments.before:
                return node.comments.before[0].pos.line
            return node.pos.line

        def last_line(node):
            end = getattr(node, "_end_line", None)
            return end or node.pos.line

        def walk(items):
            prev = None
            for item in items:
                if prev is not None and first_line(item) and last_line(prev):
                    item.blank_before = first_line(item) - self._end(prev) > 1
                prev = item
                for attr in ("members", "variants", "entries", "fields", "ext_variants", "ext_entries"):
                    sub = getattr(item, attr, None)
                    if sub:
                        walk(sub)

        walk(f.decls)

    def _end(self, node):
        """Last source line of *node* including its same-line comments (best effort)."""
        line = node.pos.line
        for c in node.comments.after:
            line = max(line, c.end_line)
        for attr in ("members", "variants", "entries", "fields", "ext_variants", "ext_entries",
                     "dangling", "ext_dangling"):
            for sub in getattr(node, attr, None) or []:
                if isinstance(sub, Token):
                    line = max(line, sub.end_line)
                else:
                    line = max(line, self._end(sub))
        return line


def convert_text(text, path):
    """Convert legacy schema *text* to a new-syntax tree. Returns ``(tree, warnings)``."""
    result = parse_legacy(text, path)
    conv = _Converter(path)
    tree = conv.convert(result)
    return tree, conv.warnings


def migrate_text(text, path, types="preserve"):
    """Legacy schema text -> struct-frame language text. Returns ``(text, warnings)``."""
    tree, warnings = convert_text(text, path)
    return print_file(tree, types=types), warnings


def check_roundtrip(new_text, path):
    """Parse migrated text with the new parser; returns its diagnostics."""
    _tree, sink = parse_text(new_text, path)
    return sink.diagnostics


__all__ = ["MigrationError", "convert_text", "migrate_text", "check_roundtrip", "DiagnosticSink"]
