"""Property-based tests of the schema language front end.

* Random well-formed schemas survive print -> parse -> print unchanged (the printer is
  canonical and the parser reads back exactly what was printed), and lower to a model
  that validates.
* Arbitrary text never crashes the lexer, parser or lowering: it either parses or gives
  diagnostics.
"""

import contextlib
import io
import os
import string
import sys
import tempfile

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from struct_frame import generate as gen  # noqa: E402
from struct_frame.schema.lower import lower_file  # noqa: E402
from struct_frame.schema.parser import parse_text  # noqa: E402
from struct_frame.schema.printer import print_file  # noqa: E402

RESERVED = {
    # struct-frame keywords and words reserved by a target language (rejected by naming).
    "package", "import", "const", "enum", "struct", "message", "oneof", "extensions",
    "service", "rpc", "true", "false", "inf", "nan", "class", "self", "def", "fn", "type",
    "default", "new", "delete", "string", "bytes", "bool", "float", "double", "int", "char",
    "long", "short", "public", "private", "static", "void", "return", "if", "else", "for",
    "while", "do", "in", "is", "as", "or", "and", "not", "None", "null", "let", "var",
    "struct", "union", "switch", "case", "break", "continue", "goto", "auto", "register",
    "signed", "unsigned", "volatile", "extern", "const", "sizeof", "typedef", "enum", "try",
    "catch", "throw", "this", "super", "with", "yield", "async", "await", "lambda", "from",
    "global", "pass", "raise", "del", "assert", "except", "finally", "elif", "match",
    "where", "impl", "trait", "mod", "use", "pub", "crate", "loop", "move", "mut", "ref",
    "dyn", "box", "object", "base", "event", "operator", "out", "params", "lock", "fixed",
    "virtual", "override", "abstract", "sealed", "readonly", "checked", "unchecked",
    "decimal", "sbyte", "ushort", "uint", "ulong", "byte", "string", "namespace", "using",
    "internal", "protected", "explicit", "implicit", "interface", "delegate", "foreach",
    "function", "instanceof", "typeof", "debugger", "export", "extends", "implements",
    "package", "arguments", "eval", "undefined", "number", "symbol", "any", "never",
    "unknown", "declare", "keyof", "infer", "constructor", "prototype",
}

lower_ident = st.from_regex(r"[a-z][a-z0-9]{1,8}", fullmatch=True).filter(lambda s: s not in RESERVED)
upper_ident = st.from_regex(r"[A-Z][a-z0-9]{1,8}", fullmatch=True).filter(lambda s: s not in RESERVED)
enum_entry = st.from_regex(r"[A-Z][A-Z0-9_]{1,8}", fullmatch=True)

PRIMS = ["uint8", "int8", "uint16", "int16", "uint32", "int32", "uint64", "int64", "bool",
         "float", "double", "u8", "i16", "u32", "f32", "f64"]


@st.composite
def field_type(draw):
    kind = draw(st.sampled_from(["prim", "prim", "string", "fstring", "array", "vector"]))
    if kind == "prim":
        return draw(st.sampled_from(PRIMS)), "prim"
    n = draw(st.integers(1, 300))
    if kind == "string":
        return f"{draw(st.sampled_from(['string', 'bytes']))}<{n}>", "str"
    if kind == "fstring":
        return f"{draw(st.sampled_from(['fixed_string', 'fstring', 'fixed_bytes']))}<{n}>", "str"
    elem = draw(st.sampled_from(PRIMS + ["fixed_string<4>"]))
    word = draw(st.sampled_from(["array", "arr"] if kind == "array" else ["vector", "vec"]))
    return f"{word}<{elem}, {n}>", "array"


def _default(draw, ftype, kind):
    if kind != "prim" or not draw(st.booleans()):
        return ""
    base = {"u8": "uint8", "i16": "int16", "u32": "uint32", "f32": "float", "f64": "double"}.get(ftype, ftype)
    if base == "bool":
        return f" = {draw(st.sampled_from(['true', 'false']))}"
    if base in ("float", "double"):
        return f" = {draw(st.sampled_from(['1.5', '-2.25', '0.0', '1e3', 'inf', '-inf']))}"
    signed = base.startswith("int")
    value = draw(st.integers(-100 if signed else 0, 100))
    text = str(value)
    if value >= 0 and draw(st.booleans()):
        text = hex(value)
    return f" = {text}"


@st.composite
def schema(draw):
    lines = ["/// Generated schema.", "package prop @1;", ""]
    enum_name = draw(upper_ident)
    entries = draw(st.lists(enum_entry, min_size=1, max_size=4, unique=True))
    lines.append(f"enum {enum_name} {{")
    for i, e in enumerate(entries):
        lines.append(f"  {e} = {i};")
    lines.append("}")
    lines.append("")
    msg_names = draw(st.lists(upper_ident.filter(lambda n: n != enum_name), min_size=1, max_size=3,
                              unique=True))
    for mid, name in enumerate(msg_names, start=1):
        attrs = " [variable]" if draw(st.booleans()) else ""
        fields = draw(st.lists(lower_ident, min_size=1, max_size=5, unique=True))
        if draw(st.booleans()):
            lines.append(f"/// Docs of {name}.")
        lines.append(f"message {name} @{mid}{attrs} {{")
        for fname in fields:
            ftype, kind = draw(field_type())
            comment = "  /// trailing" if draw(st.booleans()) else ""
            lines.append(f"  {ftype} {fname}{_default(draw, ftype, kind)};{comment}")
        if draw(st.booleans()):
            lines.append(f"  {enum_name} mode = {entries[0]};")
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(schema())
def test_random_schemas_round_trip_and_validate(text):
    tree, sink = parse_text(text, "prop.sf")
    assert not sink.errors, "\n".join(d.render() for d in sink.errors) + "\n" + text
    printed = print_file(tree)
    tree2, sink2 = parse_text(printed, "prop.sf")
    assert not sink2.errors
    assert print_file(tree2) == printed
    gen.reset_parse_state()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "prop.sf")
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            ok = lower_file(tree2, sink2, path, path, tmp, None, gen) and gen.validate_packages()
        gen.reset_parse_state()
    assert ok, out.getvalue() + "\n".join(d.render() for d in sink2.diagnostics) + "\n" + printed


# Arbitrary text built from schema-ish tokens and random characters.
TOKENS = ["package", "p", ";", "message", "M", "@", "1", "{", "}", "struct", "S", "enum", "E",
          "A", "=", "0", "u8", "x", "vector", "<", ">", ",", "string", "[", "]", "variable",
          "oneof", "o", "extensions", "const", "\"s\"", "-", "0x1F", "1.5", "///", "//", "\n",
          "/*", "*/", "import", "\"f.sf\"", "service", "rpc", "(", ")", "->", ".", ":"]


@settings(max_examples=400, deadline=None)
@given(st.lists(st.one_of(st.sampled_from(TOKENS), st.text(string.printable, max_size=3)), max_size=60))
def test_parser_never_crashes(parts):
    text = " ".join(parts)
    tree, sink = parse_text(text, "fuzz.sf")
    if sink.errors:
        for d in sink.errors:
            d.render()
        return
    gen.reset_parse_state()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "fuzz.sf")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            lower_file(tree, sink, path, path, tmp, None, gen)
            if not sink.errors:
                gen.validate_packages()
    gen.reset_parse_state()
    print_file(tree)


@settings(max_examples=300, deadline=None)
@given(st.text(max_size=200))
def test_lexer_and_parser_survive_any_text(text):
    _tree, sink = parse_text(text, "any.sf")
    for d in sink.diagnostics:
        assert d.render()
