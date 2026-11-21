"""Recursive-descent parser for the struct-frame schema language.

Grammar (``?`` optional, ``*`` repeated, ``|`` alternatives)::

    file       = package import* decl*
    package    = "package" IDENT ("@" value)? ";"
    import     = "import" STRING ";"
    decl       = const | enum | struct | message | service
    const      = "const" type IDENT "=" value ";"
    enum       = "enum" IDENT "{" (entry | "extensions" "{" entry* "}")* "}"
    entry      = IDENT "=" value ";"
    struct     = "struct" IDENT attrs? "{" member* "}"
    message    = "message" IDENT "@" value attrs? "{" member* "}"
    member     = field | oneof | enum | "extensions" "{" field* "}"
    field      = type IDENT attrs? ("=" value)? ";"
    oneof      = "oneof" IDENT attrs? "{" (variant | "extensions" "{" variant* "}")* "}"
    variant    = type IDENT attrs? ";"
    service    = "service" IDENT "{" rpc* "}"
    rpc        = "rpc" IDENT "(" type ")" ("->" type)? attrs? ";"
    type       = ("array" | "arr" | "vector" | "vec") "<" type "," size ">"
               | ("string" | "bytes" | "fixed_string" | "fstring"
                  | "fixed_bytes" | "fbytes") "<" size ">"
               | NAME
    size       = INT | NAME
    attrs      = "[" attr ("," attr)* ","? "]"
    attr       = IDENT ("=" value)?
    value      = INT | FLOAT | STRING | "true" | "false" | NAME | "-" value
               | "[" (value ("," value)* ","?)? "]"
               | "{" (IDENT ":" value ("," IDENT ":" value)* ","?)? "}"
    NAME       = IDENT ("." IDENT)*

A ``;`` after a closing ``}`` is accepted (the formatter removes it).
"""

from . import ast
from .diagnostics import DiagnosticSink, SchemaError
from .lexer import COMMENT, EOF, FLOAT, IDENT, INT, PUNCT, STRING, tokenize
from struct_frame import language_facts as facts

_LEGACY_HINT = "this looks like the old proto-style syntax; convert it with: struct-frame migrate FILE --in-place"


class _Sync(Exception):
    """Raised after a syntax error to unwind to the nearest recovery point."""


class Parser:
    def __init__(self, tokens, sink):
        self.toks = tokens
        self.sink = sink
        self.i = 0
        self.legacy_reported = False

    # -- token access ---------------------------------------------------------

    def _skip_to_code(self):
        j = self.i
        while self.toks[j].kind == COMMENT:
            j += 1
        return j

    def peek(self, ahead=0):
        j = self._skip_to_code()
        while ahead:
            j += 1
            while self.toks[j].kind == COMMENT:
                j += 1
            ahead -= 1
        return self.toks[min(j, len(self.toks) - 1)]

    def next(self):
        """Consume the next code token. Comments skipped here are mid-declaration."""
        j = self.i
        while self.toks[j].kind == COMMENT:
            self._mid.append(self.toks[j])
            j += 1
        tok = self.toks[j]
        if tok.kind != EOF:
            j += 1
        self.i = j
        return tok

    def boundary(self):
        """Comments between the previous code token and the next one."""
        out = []
        while self.toks[self.i].kind == COMMENT:
            out.append(self.toks[self.i])
            self.i += 1
        return out

    def at(self, text, ahead=0):
        tok = self.peek(ahead)
        return tok.kind in (PUNCT, IDENT) and tok.text == text

    def accept(self, text):
        if self.at(text):
            return self.next()
        return None

    def expect(self, text, what=None):
        tok = self.peek()
        if tok.kind in (PUNCT, IDENT) and tok.text == text:
            return self.next()
        self._unexpected(tok, f"'{text}'" if what is None else what)

    def expect_ident(self, what="a name"):
        tok = self.peek()
        if tok.kind == IDENT:
            return self.next()
        self._unexpected(tok, what)

    def _unexpected(self, tok, expected, hint=None):
        found = "end of file" if tok.kind == EOF else f"'{tok.text}'"
        self.sink.error("SF0201", f"expected {expected}, found {found}", tok.pos,
                        max(1, len(tok.text)), hint=hint)
        raise _Sync()

    def _legacy(self, tok, message):
        self.sink.error("SF0301", message, tok.pos, max(1, len(tok.text)), hint=_LEGACY_HINT)
        self.legacy_reported = True
        raise _Sync()

    def _recover(self, stop_at_close=True):
        """Skip to just after the next ';' (or to the next '}' at this depth)."""
        depth = 0
        while True:
            tok = self.peek()
            if tok.kind == EOF:
                return
            if tok.kind == PUNCT:
                if tok.text in "{[(":
                    depth += 1
                elif tok.text in ")]":
                    depth = max(0, depth - 1)
                elif tok.text == "}":
                    if depth == 0:
                        if stop_at_close:
                            return
                        self.next()
                        return
                    depth -= 1
                    if depth == 0:
                        self.next()
                        self.accept(";")
                        return
                elif tok.text == ";" and depth == 0:
                    self.next()
                    return
            self.next()

    # -- blank lines ------------------------------------------------------------

    def _prev_end_line(self):
        """Last line of the most recently consumed token (code or comment)."""
        j = self.i - 1
        if j < 0:
            return 0
        tok = self.toks[j]
        return tok.end_line if tok.kind == COMMENT else tok.pos.line

    def _feed(self, scope):
        """Hand the next boundary comments to *scope*; returns the line where the previous
        element ended (after any same-line comments), for blank-line detection."""
        prev = self._prev_end_line()
        comments = self.boundary()
        for c in comments:
            if not c.inline:
                break
            prev = c.end_line
        scope.feed(comments)
        return prev

    @staticmethod
    def _gap(node, prev_line, before, attr="blank_before"):
        first = before[0].pos.line if before else node.pos.line
        setattr(node, attr, prev_line > 0 and first - prev_line > 1)

    # -- comment distribution -------------------------------------------------

    class _Scope:
        """Hands boundary comments to the declarations of one scope."""

        def __init__(self, owner_comments):
            self.pending = []
            self.target = owner_comments   # Comments of the last declaration (or owner)

        def feed(self, comments):
            for c in comments:
                if c.inline and self.target is not None:
                    self.target.after.append(c)
                else:
                    self.pending.append(c)

        def take(self):
            out, self.pending = self.pending, []
            return out

        def declared(self, comments):
            self.target = comments

    def _begin_decl(self):
        self._mid = []

    def _end_decl(self, node_comments):
        """Mid-declaration comments go after the declaration; doc ones are reported."""
        for c in self._mid:
            if c.doc:
                self.sink.warning("SF0311", "doc comment inside a declaration documents nothing",
                                  c.pos, 3, hint="move it to the line above the declaration")
            node_comments.after.append(c)
        self._mid = []

    # -- file -----------------------------------------------------------------

    def parse_file(self, path):
        self._mid = []
        f = ast.File(path)
        f.header = self.boundary()
        tok = self.peek()
        if tok.kind == IDENT and tok.text == "syntax":
            try:
                self._legacy(tok, "'syntax' declarations are not part of the struct-frame language")
            except _Sync:
                self._recover(stop_at_close=False)
                f.header += self.boundary()
                tok = self.peek()
        if not (tok.kind == IDENT and tok.text == "package"):
            if tok.kind == EOF:
                self.sink.error("SF0302", "empty schema: expected 'package NAME;'", tok.pos)
                return f
            self.sink.error("SF0302", "a schema must start with 'package NAME;'", tok.pos,
                            max(1, len(tok.text)))
        else:
            try:
                self._begin_decl()
                f.package = self.parse_package()
                self._end_decl(f.package.comments)
            except _Sync:
                self._recover(stop_at_close=False)
        scope = self._Scope(f.package.comments if f.package else None)
        seen_decl = False
        while True:
            gap = self._feed(scope)
            tok = self.peek()
            if tok.kind == EOF:
                break
            try:
                self._begin_decl()
                before = scope.take()
                node = self.parse_top(tok, seen_decl)
                if node is None:
                    continue
                node.comments.before = before + node.comments.before
                self._end_decl(node.comments)
                if isinstance(node, ast.ImportDecl):
                    if seen_decl:
                        self.sink.error("SF0303", "imports must come before declarations",
                                        node.pos, 6)
                    f.imports.append(node)
                    self._gap(node, gap, node.comments.before)
                    for c in node.comments.before:
                        if c.doc:
                            self.sink.warning("SF0312", "doc comment before 'import' documents nothing",
                                              c.pos, 3, hint="use // for a private comment")
                else:
                    seen_decl = True
                    f.decls.append(node)
                self._gap(node, gap, node.comments.before)
                scope.declared(node.comments)
            except _Sync:
                self._recover(stop_at_close=False)
                scope.declared(None)
        f.dangling = scope.take()
        self._dangling_docs(f.dangling)
        return f

    def _dangling_docs(self, comments):
        for c in comments:
            if c.doc:
                self.sink.warning("SF0313", "doc comment documents nothing", c.pos, 3,
                                  hint="put it directly above a declaration, or use // for a private comment")

    def parse_package(self):
        kw = self.next()
        name = self.expect_ident("a package name")
        if self.at("."):
            self.sink.error("SF0304", "package names are single identifiers", self.peek().pos, 1,
                            hint="use an underscore: package robot_sensors;")
            raise _Sync()
        pkg = ast.PackageDecl(name.text, kw.pos)
        if self.accept("@"):
            pkg.id = self.parse_value()
        self._semicolon()
        return pkg

    def parse_top(self, tok, seen_decl):
        word = tok.text if tok.kind == IDENT else None
        if word == "package":
            self.sink.error("SF0302", "only one 'package' declaration is allowed per file", tok.pos, 7)
            raise _Sync()
        if word == "import":
            kw = self.next()
            path = self.peek()
            if path.kind != STRING:
                self._unexpected(path, "a quoted file name")
            self.next()
            self._semicolon()
            return ast.ImportDecl(path.value, kw.pos)
        if word == "const":
            return self.parse_const()
        if word == "enum":
            return self.parse_enum()
        if word in ("message", "struct"):
            return self.parse_message()
        if word == "service":
            return self.parse_service()
        if word == "option":
            self._legacy(tok, "'option' statements are not part of the struct-frame language "
                              "(use 'package NAME @ID;' for a package id)")
        if word in ("syntax", "edition"):
            self._legacy(tok, f"'{word}' declarations are not part of the struct-frame language")
        self._unexpected(tok, "a declaration (message, struct, enum, const, service or import)")

    # -- declarations ---------------------------------------------------------

    def parse_const(self):
        kw = self.next()
        tok = self.peek()
        if tok.kind == IDENT and tok.text in ("string", "bytes") and not self.at("<", 1):
            self.next()     # a string constant has no capacity
            typ = ast.TypeRef(tok.text, tok.pos, tok.text)
        else:
            typ = self.parse_type()
        name = self.expect_ident("a constant name")
        self.expect("=")
        value = self.parse_value()
        self._semicolon()
        return ast.ConstDecl(typ, name.text, value, kw.pos, name.pos)

    def parse_enum(self):
        kw = self.next()
        name = self.expect_ident("an enum name")
        node = ast.EnumDecl(name.text, kw.pos)
        if self.at("["):
            node.attrs = self.parse_attrs()
        self.expect("{")
        scope = self._Scope(node.comments)
        self._end_decl(node.comments)
        node.dangling = self._enum_body(node.entries, scope, allow_ext=True, node=node)
        self.expect("}")
        self._closing_semicolon()
        return node

    def _enum_body(self, entries, scope, allow_ext, node):
        while True:
            gap = self._feed(scope)
            tok = self.peek()
            if tok.kind == EOF or self.at("}"):
                break
            try:
                self._begin_decl()
                before = scope.take()
                if allow_ext and self.at("extensions") and self.at("{", 1):
                    ext_kw = self.next()
                    self.next()
                    if node.ext_entries is not None:
                        self.sink.error("SF0305", "only one 'extensions' block is allowed per scope",
                                        ext_kw.pos, 10)
                    node.ext_entries = []
                    node.ext_pos = ext_kw.pos
                    node.ext_comments.before = before
                    ext_scope = self._Scope(node.ext_comments)
                    self._end_decl(node.ext_comments)
                    node.ext_dangling = self._enum_body(node.ext_entries, ext_scope, False, node)
                    self.expect("}")
                    node.ext_blank_before = gap > 0 and (before[0].pos.line if before else ext_kw.pos.line) - gap > 1
                    scope.declared(node.ext_comments)
                    continue
                if tok.kind == IDENT and tok.text == "option":
                    self._legacy(tok, "'option' statements are not part of the struct-frame language")
                entry = self.parse_enum_entry()
                entry.comments.before = before + entry.comments.before
                self._end_decl(entry.comments)
                entries.append(entry)
                self._gap(entry, gap, entry.comments.before)
                scope.declared(entry.comments)
            except _Sync:
                self._recover()
                scope.declared(None)
        dangling = scope.take()
        self._dangling_docs(dangling)
        return dangling

    def parse_enum_entry(self):
        name = self.expect_ident("an enum entry name")
        value = None
        if self.accept("="):
            value = self.parse_value()
        else:
            self.sink.error("SF0306", f"enum entry '{name.text}' needs a value",
                            name.pos, len(name.text),
                            hint=f"write {name.text} = N; (enum values are always explicit)")
        self._semicolon()
        return ast.EnumEntry(name.text, value, name.pos)

    def parse_message(self):
        kw = self.next()
        name = self.expect_ident(f"a {kw.text} name")
        node = ast.MessageDecl(kw.text, name.text, kw.pos)
        if self.at("@"):
            at = self.next()
            value = self.parse_value()
            if kw.text == "struct":
                self.sink.error("SF0307", f"struct {name.text} cannot have an id", at.pos, 1,
                                hint=f"use 'message {name.text} @ID' for a type that is sent on its own")
            else:
                node.id = value
        elif kw.text == "message":
            tok = self.peek()
            self.sink.error("SF0307", f"message {name.text} needs an id: message {name.text} @ID {{ ... }}",
                            name.pos, len(name.text),
                            hint="use 'struct' for a type that is only embedded in other messages"
                                 + ("" if self.legacy_reported else
                                    f"; if this file uses the old syntax: {_LEGACY_HINT}"))
            self.legacy_reported = True
        if self.at("["):
            node.attrs = self.parse_attrs()
        self.expect("{")
        self._end_decl(node.comments)
        scope = self._Scope(node.comments)
        node.dangling = self._members(node.members, scope, allow_ext=True)
        self.expect("}")
        self._closing_semicolon()
        return node

    def _members(self, members, scope, allow_ext):
        while True:
            gap = self._feed(scope)
            tok = self.peek()
            if tok.kind == EOF or self.at("}"):
                break
            try:
                self._begin_decl()
                before = scope.take()
                node = self.parse_member(tok, allow_ext)
                node.comments.before = before + node.comments.before
                self._end_decl(node.comments)
                members.append(node)
                self._gap(node, gap, node.comments.before)
                scope.declared(node.comments)
            except _Sync:
                self._recover()
                scope.declared(None)
        dangling = scope.take()
        self._dangling_docs(dangling)
        return dangling

    def parse_member(self, tok, allow_ext):
        word = tok.text if tok.kind == IDENT else None
        if word == "oneof" and self.peek(1).kind == IDENT and (self.at("{", 2) or self.at("[", 2)):
            return self.parse_oneof()
        if word == "enum" and self.peek(1).kind == IDENT and (self.at("{", 2) or self.at("[", 2)):
            return self.parse_enum()
        if word == "extensions" and self.at("{", 1):
            kw = self.next()
            self.next()
            block = ast.ExtensionsBlock(kw.pos)
            if not allow_ext:
                self.sink.error("SF0305", "'extensions' blocks cannot be nested", kw.pos, 10)
            self._end_decl(block.comments)
            scope = self._Scope(block.comments)
            block.dangling = self._members(block.fields, scope, allow_ext=False)
            self.expect("}")
            for m in block.fields:
                if not isinstance(m, ast.FieldDecl):
                    self.sink.error("SF0305", "an 'extensions' block of a message holds only fields",
                                    m.pos, 5)
            return block
        if word in ("message", "struct") and self.peek(1).kind == IDENT:
            self.sink.error("SF0308", f"nested {word} declarations are not supported", tok.pos,
                            len(word), hint=f"declare the {word} at package level")
            raise _Sync()
        if word == "option":
            self._legacy(tok, "'option' statements are not part of the struct-frame language "
                              "(write the id as 'message Name @ID' and other options as [attributes])")
        if word == "repeated" and self.peek(1).kind == IDENT and self.peek(2).kind == IDENT:
            self._legacy(tok, "'repeated' is not part of the struct-frame language "
                              "(use array<T, N> or vector<T, N>)")
        if word in ("map", "reserved", "optional", "required"):
            self.sink.error("SF0309", f"'{word}' is not supported by struct-frame", tok.pos, len(word))
            raise _Sync()
        return self.parse_field(allow_default=True)

    def parse_field(self, allow_default):
        start = self.peek()
        typ = self.parse_type()
        name = self.expect_ident("a field name")
        node = ast.FieldDecl(typ, name.text, start.pos, name.pos)
        if self.at("["):
            node.attrs = self.parse_attrs()
        if self.at("="):
            eq = self.next()
            value = self.parse_value()
            if allow_default:
                node.default = value
            else:
                self.sink.error("SF0405", "oneof variants cannot have default values", eq.pos, 1)
            if self.at("["):
                attrs = self.parse_attrs()
                self.sink.error("SF0310", "attributes go before the default value",
                                attrs[0].pos if attrs else self.peek().pos, 1,
                                hint=f"write: {typ.spelled or typ.name} {name.text} [{attrs[0].name if attrs else '...'}] = ...;")
                node.attrs.extend(attrs)
        self._semicolon()
        return node

    def parse_oneof(self):
        kw = self.next()
        name = self.expect_ident("a oneof name")
        node = ast.OneofDecl(name.text, kw.pos)
        if self.at("["):
            node.attrs = self.parse_attrs()
        self.expect("{")
        self._end_decl(node.comments)
        scope = self._Scope(node.comments)
        node.dangling = self._variants(node, node.variants, scope, allow_ext=True)
        self.expect("}")
        self._closing_semicolon()
        return node

    def _variants(self, node, variants, scope, allow_ext):
        while True:
            gap = self._feed(scope)
            tok = self.peek()
            if tok.kind == EOF or self.at("}"):
                break
            try:
                self._begin_decl()
                before = scope.take()
                if self.at("extensions") and self.at("{", 1):
                    kw = self.next()
                    self.next()
                    if not allow_ext:
                        self.sink.error("SF0305", "'extensions' blocks cannot be nested", kw.pos, 10)
                    elif node.ext_variants is not None:
                        self.sink.error("SF0305", "only one 'extensions' block is allowed per scope",
                                        kw.pos, 10)
                    node.ext_variants = node.ext_variants or []
                    node.ext_pos = kw.pos
                    node.ext_comments.before = before
                    self._end_decl(node.ext_comments)
                    ext_scope = self._Scope(node.ext_comments)
                    node.ext_dangling = self._variants(node, node.ext_variants, ext_scope, False)
                    self.expect("}")
                    node.ext_blank_before = gap > 0 and (before[0].pos.line if before else kw.pos.line) - gap > 1
                    scope.declared(node.ext_comments)
                    continue
                if tok.kind == IDENT and tok.text == "option":
                    self._legacy(tok, "'option' statements are not part of the struct-frame language "
                                      "(write oneof options as [attributes])")
                var = self.parse_field(allow_default=False)
                var.comments.before = before + var.comments.before
                self._end_decl(var.comments)
                variants.append(var)
                self._gap(var, gap, var.comments.before)
                scope.declared(var.comments)
            except _Sync:
                self._recover()
                scope.declared(None)
        dangling = scope.take()
        self._dangling_docs(dangling)
        return dangling

    def parse_service(self):
        kw = self.next()
        name = self.expect_ident("a service name")
        node = ast.ServiceDecl(name.text, kw.pos)
        self.expect("{")
        self._end_decl(node.comments)
        scope = self._Scope(node.comments)
        while True:
            gap = self._feed(scope)
            tok = self.peek()
            if tok.kind == EOF or self.at("}"):
                break
            try:
                self._begin_decl()
                before = scope.take()
                rpc = self.parse_rpc()
                rpc.comments.before = before + rpc.comments.before
                self._end_decl(rpc.comments)
                node.rpcs.append(rpc)
                self._gap(rpc, gap, rpc.comments.before)
                scope.declared(rpc.comments)
            except _Sync:
                self._recover()
                scope.declared(None)
        node.dangling = scope.take()
        self._dangling_docs(node.dangling)
        self.expect("}")
        self._closing_semicolon()
        return node

    def parse_rpc(self):
        kw = self.expect("rpc", "'rpc'")
        name = self.expect_ident("an rpc name")
        self.expect("(")
        req = self.parse_type()
        self.expect(")")
        resp = None
        if self.accept("->"):
            resp = self.parse_type()
        node = ast.RpcDecl(name.text, req, resp, kw.pos)
        if self.at("["):
            node.attrs = self.parse_attrs()
        self._semicolon()
        return node

    # -- types, attributes, values --------------------------------------------

    def parse_name(self, what="a type name"):
        first = self.expect_ident(what)
        parts = [first.text]
        while self.at(".") and self.peek(1).kind == IDENT:
            self.next()
            parts.append(self.next().text)
        return ".".join(parts), first.pos

    def parse_type(self):
        tok = self.peek()
        if tok.kind != IDENT:
            self._unexpected(tok, "a type")
        info = facts.CONTAINER_TYPES.get(tok.text)
        if info is not None and self.at("<", 1):
            canonical, element_kind, _sizing = info
            self.next()
            self.next()
            node = ast.TypeRef(canonical, tok.pos, tok.text, canonical)
            if element_kind == "elements":
                node.element = self.parse_type()
                self.expect(",", "',' and the element count")
            node.size = self.parse_size()
            self.expect(">", "'>'")
            return node
        if tok.text in ("string", "bytes") and not self.at("<", 1):
            self.sink.error("SF0320", f"'{tok.text}' needs a capacity", tok.pos, len(tok.text),
                            hint=f"write {tok.text}<N> (up to N bytes) or fixed_{tok.text}<N> (exactly N)")
            self.next()
            return ast.TypeRef(tok.text, tok.pos, tok.text, tok.text, size=ast.IntLit(1, tok.pos))
        if tok.text in ("array", "arr", "vector", "vec", "fixed_string", "fstring",
                        "fixed_bytes", "fbytes") and not self.at("<", 1):
            self.sink.error("SF0320", f"'{tok.text}' needs type parameters", tok.pos, len(tok.text),
                            hint="e.g. array<uint8, 8>, vector<uint8, 100>, fixed_string<16>")
            raise _Sync()
        name, pos = self.parse_name()
        return ast.TypeRef(name, pos, name)

    def parse_size(self):
        tok = self.peek()
        if tok.kind == INT:
            self.next()
            return ast.IntLit(tok.value, tok.pos, tok.text)
        if tok.kind == IDENT:
            name, pos = self.parse_name("a size")
            return ast.NameRef(name, pos)
        if tok.kind == PUNCT and tok.text == "<" or (tok.kind == PUNCT and tok.text == "="):
            self._unexpected(tok, "a size", hint="sizes have no '<=': vector<T, N> holds up to N "
                                                 "elements, array<T, N> exactly N")
        self._unexpected(tok, "a size (an integer or a constant)")

    def parse_attrs(self):
        self.expect("[")
        attrs = []
        while not self.at("]"):
            name = self.expect_ident("an attribute name")
            value = None
            if self.accept("="):
                value = self.parse_value()
            attrs.append(ast.Attribute(name.text, value, name.pos))
            if not self.accept(","):
                break
        self.expect("]", "',' or ']'")
        return attrs

    def parse_value(self):
        tok = self.peek()
        if tok.kind == INT:
            self.next()
            return ast.IntLit(tok.value, tok.pos, tok.text)
        if tok.kind == FLOAT:
            self.next()
            return ast.FloatLit(tok.value, tok.pos, tok.text)
        if tok.kind == STRING:
            self.next()
            return ast.StrLit(tok.value, tok.pos, tok.text)
        if tok.kind == IDENT:
            if tok.text in ("true", "false"):
                self.next()
                return ast.BoolLit(tok.text == "true", tok.pos)
            name, pos = self.parse_name("a value")
            return ast.NameRef(name, pos)
        if tok.kind == PUNCT and tok.text == "-":
            self.next()
            return ast.Neg(self.parse_value(), tok.pos)
        if tok.kind == PUNCT and tok.text == "[":
            self.next()
            items = []
            while not self.at("]"):
                items.append(self.parse_value())
                if not self.accept(","):
                    break
            self.expect("]", "',' or ']'")
            return ast.ArrayLit(items, tok.pos)
        if tok.kind == PUNCT and tok.text == "{":
            self.next()
            fields = []
            while not self.at("}"):
                fname = self.expect_ident("a field name")
                self.expect(":")
                fields.append(ast.StructLitField(fname.text, self.parse_value(), fname.pos))
                if not self.accept(","):
                    break
            self.expect("}", "',' or '}'")
            return ast.StructLit(fields, tok.pos)
        self._unexpected(tok, "a value")

    # -- punctuation ----------------------------------------------------------

    def _semicolon(self):
        tok = self.peek()
        if tok.kind == PUNCT and tok.text == ";":
            self.next()
            return
        prev = self.toks[self.i - 1] if self.i else tok
        # Report at the end of the previous token: that is where the ';' is missing.
        from .diagnostics import Position
        pos = Position(prev.pos.line, prev.end_col) if prev.kind != EOF else tok.pos
        found = "end of file" if tok.kind == EOF else f"'{tok.text}'"
        self.sink.error("SF0202", f"expected ';', found {found}", pos, 1)
        raise _Sync()

    def _closing_semicolon(self):
        # `};` is tolerated; the formatter drops the ';'.
        if self.at(";"):
            self.next()


def parse_text(text, path=None, sink=None):
    """Parse schema *text*. Returns ``(ast.File, sink)``; check ``sink.errors``."""
    sink = sink or DiagnosticSink(path, text)
    tokens = tokenize(text, sink)
    parser = Parser(tokens, sink)
    tree = parser.parse_file(path)
    return tree, sink


def parse(text, path=None):
    """Parse schema *text*, raising :class:`SchemaError` if it has errors."""
    tree, sink = parse_text(text, path)
    sink.raise_if_errors()
    return tree
