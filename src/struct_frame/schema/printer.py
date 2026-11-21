"""Canonical printer for the struct-frame schema language (``struct-frame fmt``).

Prints an :class:`ast.File` back to source. Every comment is kept: comments written
before a declaration stay on their own lines above it, same-line comments stay on the
declaration's line, and comments left at the end of a scope stay there. Blank lines
between declarations inside a scope are kept (collapsed to one); top-level declarations
are always separated by one blank line.

Parsing the printed text gives a tree with the same declarations, values and comment
ownership, and printing is idempotent.
"""

import math

from . import ast
from struct_frame import language_facts as facts

INDENT = "  "

_LONG_FOR_SHORT = dict(facts.PRIMITIVE_ALIASES)
_SHORT_FOR_LONG = {v: k for k, v in facts.PRIMITIVE_ALIASES.items()}
_LONG_CONTAINER = {"arr": "array", "vec": "vector", "fstring": "fixed_string", "fbytes": "fixed_bytes"}
_SHORT_CONTAINER = {v: k for k, v in _LONG_CONTAINER.items()}


def comment_text(tok):
    """Source text of a comment token as the printer writes it."""
    if tok.doc and tok.ir_text is not None:
        # Doc comments are printed from their documentation text (see lexer._doc_ir_text).
        if tok.ir_text.startswith("/*"):
            return "/**" + tok.ir_text[2:]
        return "/" + tok.ir_text
    text = tok.text.rstrip()
    # A private comment must not turn into a doc comment.
    if text.startswith("///"):
        return "//" + text[3:]
    if text.startswith("/**") and not text.startswith("/**/"):
        return "/*" + text[3:]
    return text


def quote(text):
    out = ['"']
    for ch in text:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\0":
            out.append("\\0")
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            out.append(f"\\u{ord(ch):04X}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def format_float(value):
    if math.isnan(value):
        return "nan"
    if math.isinf(value):
        return "inf" if value > 0 else "-inf"
    text = repr(float(value))
    if "e" in text or "E" in text:
        mant, exp = text.lower().split("e")
        if "." not in mant:
            mant += ".0"
        return f"{mant}e{int(exp)}"
    return text


class Printer:
    def __init__(self, types="preserve"):
        self.types = types
        self.out = []

    # -- helpers ----------------------------------------------------------------

    def emit(self, depth, text):
        self.out.append((INDENT * depth + text).rstrip())

    def blank(self):
        if self.out and self.out[-1] != "":
            self.out.append("")

    def before(self, depth, comments):
        for c in comments.before:
            self._comment_lines(depth, c)

    def _comment_lines(self, depth, tok):
        text = comment_text(tok)
        lines = text.split("\n")
        self.emit(depth, lines[0])
        # Continuation lines of a block comment are printed verbatim.
        for line in lines[1:]:
            self.out.append(line.rstrip())

    @staticmethod
    def after_text(comments):
        parts = [comment_text(c) for c in comments]
        # A line comment runs to the end of the line: put block comments first.
        parts.sort(key=lambda t: not t.startswith("/*"))
        return ("  " + " ".join(parts)) if parts else ""

    def split_after(self, comments):
        """Comments for the header line and for the closing line of a block declaration.

        A line comment ends its line, so at most one fits on each line; block comments
        can share a line with others.
        """
        head, tail = [], []
        target = head
        for c in comments.after:
            target.append(c)
            if not comment_text(c).startswith("/*") and target is head:
                target = tail
        return head, tail

    def dangling(self, depth, tokens):
        for c in tokens:
            self._comment_lines(depth, c)

    # -- values / types -----------------------------------------------------------

    def value(self, lit):
        if isinstance(lit, ast.IntLit):
            return lit.text or str(lit.value)
        if isinstance(lit, ast.FloatLit):
            return lit.text or format_float(lit.value)
        if isinstance(lit, ast.StrLit):
            return quote(lit.value)
        if isinstance(lit, ast.BoolLit):
            return "true" if lit.value else "false"
        if isinstance(lit, ast.NameRef):
            return lit.name
        if isinstance(lit, ast.Neg):
            return "-" + self.value(lit.operand)
        if isinstance(lit, ast.ArrayLit):
            return "[" + ", ".join(self.value(x) for x in lit.items) + "]"
        if isinstance(lit, ast.StructLit):
            if not lit.fields:
                return "{}"
            return "{ " + ", ".join(f"{f.name}: {self.value(f.value)}" for f in lit.fields) + " }"
        raise TypeError(lit)

    def _word(self, spelled, canonical):
        if self.types == "long":
            return _LONG_FOR_SHORT.get(spelled, _LONG_CONTAINER.get(spelled, spelled))
        if self.types == "short":
            long = _LONG_FOR_SHORT.get(spelled, _LONG_CONTAINER.get(spelled, spelled))
            return _SHORT_FOR_LONG.get(long, _SHORT_CONTAINER.get(long, long))
        return spelled or canonical

    def type(self, t):
        if t.container is None:
            return self._word(t.spelled or t.name, t.name)
        word = self._word(t.spelled or t.container, t.container)
        if t.element is not None:
            return f"{word}<{self.type(t.element)}, {self.value(t.size)}>"
        return f"{word}<{self.value(t.size)}>"

    def attrs(self, attrs):
        if not attrs:
            return ""
        parts = []
        for a in attrs:
            parts.append(a.name if a.value is None else f"{a.name} = {self.value(a.value)}")
        return " [" + ", ".join(parts) + "]"

    # -- declarations ---------------------------------------------------------------

    def file(self, f):
        for c in f.header:
            self._comment_lines(0, c)
        if f.package is not None:
            if f.header:
                self.blank()
            self.before(0, f.package.comments)
            pid = f" @{self.value(f.package.id)}" if f.package.id is not None else ""
            self.emit(0, f"package {f.package.name}{pid};{self.after_text(f.package.comments.after)}")
        if f.imports:
            self.blank()
            for imp in f.imports:
                if getattr(imp, "blank_before", False):
                    self.blank()
                self.before(0, imp.comments)
                self.emit(0, f"import {quote(imp.path)};{self.after_text(imp.comments.after)}")
        for decl in f.decls:
            self.blank()
            self.decl(0, decl)
        if f.dangling:
            self.blank()
            self.dangling(0, f.dangling)
        while self.out and self.out[-1] == "":
            self.out.pop()
        return "\n".join(self.out) + "\n"

    def decl(self, depth, d):
        if isinstance(d, ast.MessageDecl):
            self.message(depth, d)
        elif isinstance(d, ast.EnumDecl):
            self.enum(depth, d)
        elif isinstance(d, ast.ConstDecl):
            self.before(depth, d.comments)
            self.emit(depth, f"const {self.type(d.type)} {d.name} = {self.value(d.value)};"
                             f"{self.after_text(d.comments.after)}")
        elif isinstance(d, ast.ServiceDecl):
            self.service(depth, d)
        else:
            raise TypeError(d)

    def _open(self, depth, header, comments, empty=False):
        self.before(depth, comments)
        head, tail = self.split_after(comments)
        if empty:
            self.emit(depth, header + " {}" + self.after_text(head + tail))
            return None
        self.emit(depth, header + " {" + self.after_text(head))
        return tail

    def _close(self, depth, tail):
        if tail is not None:
            self.emit(depth, "}" + self.after_text(tail))

    def _members(self, depth, items, render):
        for i, item in enumerate(items):
            if i and getattr(item, "blank_before", False):
                self.blank()
            render(depth, item)

    def message(self, depth, m):
        header = f"{m.kind} {m.name}"
        if m.kind == "message" and m.id is not None:
            header += f" @{self.value(m.id)}"
        header += self.attrs(m.attrs)
        tail = self._open(depth, header, m.comments, empty=not m.members and not m.dangling)
        self._members(depth + 1, m.members, self.member)
        self.dangling(depth + 1, m.dangling)
        self._close(depth, tail)

    def member(self, depth, mem):
        if isinstance(mem, ast.FieldDecl):
            self.field(depth, mem)
        elif isinstance(mem, ast.OneofDecl):
            self.oneof(depth, mem)
        elif isinstance(mem, ast.EnumDecl):
            self.enum(depth, mem)
        elif isinstance(mem, ast.ExtensionsBlock):
            tail = self._open(depth, "extensions", mem.comments)
            self._members(depth + 1, mem.fields, self.member)
            self.dangling(depth + 1, mem.dangling)
            self._close(depth, tail)
        else:
            raise TypeError(mem)

    def field(self, depth, f):
        self.before(depth, f.comments)
        text = f"{self.type(f.type)} {f.name}{self.attrs(f.attrs)}"
        if f.default is not None:
            text += f" = {self.value(f.default)}"
        self.emit(depth, text + ";" + self.after_text(f.comments.after))

    def oneof(self, depth, o):
        tail = self._open(depth, f"oneof {o.name}{self.attrs(o.attrs)}", o.comments)
        self._members(depth + 1, o.variants, self.field)
        if o.ext_variants is not None:
            if getattr(o, "ext_blank_before", False) and o.variants:
                self.blank()
            ext_tail = self._open(depth + 1, "extensions", o.ext_comments)
            self._members(depth + 2, o.ext_variants, self.field)
            self.dangling(depth + 2, o.ext_dangling)
            self._close(depth + 1, ext_tail)
        self.dangling(depth + 1, o.dangling)
        self._close(depth, tail)

    def entry(self, depth, e):
        self.before(depth, e.comments)
        value = f" = {self.value(e.value)}" if e.value is not None else ""
        self.emit(depth, f"{e.name}{value};{self.after_text(e.comments.after)}")

    def enum(self, depth, e):
        tail = self._open(depth, f"enum {e.name}{self.attrs(e.attrs)}", e.comments)
        self._members(depth + 1, e.entries, self.entry)
        if e.ext_entries is not None:
            if getattr(e, "ext_blank_before", False) and e.entries:
                self.blank()
            ext_tail = self._open(depth + 1, "extensions", e.ext_comments)
            self._members(depth + 2, e.ext_entries, self.entry)
            self.dangling(depth + 2, e.ext_dangling)
            self._close(depth + 1, ext_tail)
        self.dangling(depth + 1, e.dangling)
        self._close(depth, tail)

    def service(self, depth, s):
        tail = self._open(depth, f"service {s.name}", s.comments)

        def rpc(d, r):
            self.before(d, r.comments)
            text = f"rpc {r.name}({self.type(r.request)})"
            if r.response is not None:
                text += f" -> {self.type(r.response)}"
            text += self.attrs(r.attrs)
            self.emit(d, text + ";" + self.after_text(r.comments.after))

        self._members(depth + 1, s.rpcs, rpc)
        self.dangling(depth + 1, s.dangling)
        self._close(depth, tail)


def print_file(tree, types="preserve"):
    """Source text for *tree*. ``types``: preserve, long (uint8...) or short (u8...)."""
    return Printer(types).file(tree)
