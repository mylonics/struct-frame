"""The struct-frame schema language: lexer, parser, diagnostics, lowering and printer.

The model a schema lowers to is checked through the real generator
(``generate.parseFile`` + ``validate_packages``); wire layout and generated output are
covered by the IR goldens (tests/test_ir_golden.py) and the migrate differential.
"""

import math
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from struct_frame import generate as gen  # noqa: E402
from struct_frame.schema import ast  # noqa: E402
from struct_frame.schema.diagnostics import DiagnosticSink  # noqa: E402
from struct_frame.schema.lexer import COMMENT, FLOAT, INT, STRING, tokenize  # noqa: E402
from struct_frame.schema.parser import parse_text  # noqa: E402
from struct_frame.schema.printer import print_file, quote  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def lex(text):
    sink = DiagnosticSink("t.sf", text)
    toks = tokenize(text, sink)
    return toks, sink


def parse(text):
    tree, sink = parse_text(text, "t.sf")
    return tree, sink


def codes(sink):
    return [d.code for d in sink.diagnostics]


def model(tmp_path, text, name="t.sf", extra=None):
    """Lower + validate *text*; returns (ok, packages, captured output)."""
    import contextlib
    import io
    for fname, ftext in (extra or {}).items():
        (tmp_path / fname).write_text(ftext, encoding="utf-8")
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    gen.reset_parse_state()
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        ok = gen.parseFile(str(path)) and gen.validate_packages()
    pkgs = dict(gen.packages)
    gen.reset_parse_state()
    return ok, pkgs, out.getvalue() + err.getvalue()


# ---------------------------------------------------------------------------
# lexer
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,value", [
    ("0", 0), ("42", 42), ("1_000", 1000), ("0x1F", 31), ("0XfF", 255), ("0b101", 5),
    ("0o17", 15), ("0x_ff", 255),
])
def test_integer_literals(text, value):
    toks, sink = lex(text)
    assert not sink.diagnostics
    assert toks[0].kind == INT and toks[0].value == value


@pytest.mark.parametrize("text,value", [
    ("1.5", 1.5), ("0.25", 0.25), ("1e3", 1000.0), ("2.5e-3", 0.0025), ("1E+2", 100.0),
])
def test_float_literals(text, value):
    toks, sink = lex(text)
    assert not sink.diagnostics
    assert toks[0].kind == FLOAT and toks[0].value == value


@pytest.mark.parametrize("text", ["012", "12abc", "0x", "0b2", "1__0", "1_"])
def test_bad_numbers(text):
    _toks, sink = lex(text)
    assert "SF0102" in codes(sink)


@pytest.mark.parametrize("text,value", [
    (r'"abc"', "abc"), (r'"a\nb"', "a\nb"), (r'"tab\t"', "tab\t"), (r'"q\"q"', 'q"q'),
    (r'"back\\slash"', "back\\slash"), (r'"\x41é"', "Aé"), (r'"nul\0"', "nul\0"),
    ('"café"', "café"),
])
def test_string_literals(text, value):
    toks, sink = lex(text)
    assert not sink.diagnostics, sink.diagnostics
    assert toks[0].kind == STRING and toks[0].value == value


@pytest.mark.parametrize("text,code", [
    (r'"bad\q"', "SF0104"), (r'"\xff"', "SF0104"), ('"open', "SF0103"), ("'single'", "SF0105"),
    ("/* open", "SF0103"), ("$", "SF0101"),
])
def test_lexical_errors(text, code):
    _toks, sink = lex(text)
    assert code in codes(sink)


def test_positions_count_lines_and_columns():
    toks, _ = lex("package p;\r\n\tmessage M @1 {}\n")
    msg = next(t for t in toks if t.text == "message")
    assert (msg.pos.line, msg.pos.col) == (2, 2)
    at = next(t for t in toks if t.text == "@")
    assert (at.pos.line, at.pos.col) == (2, 12)


def test_bom_is_ignored():
    toks, sink = lex("﻿package p;")
    assert not sink.diagnostics
    assert toks[0].text == "package" and toks[0].pos.col == 1


def test_comment_kinds():
    toks, _ = lex("/// doc\n// private\n/** block doc */\n/* block */\nx; /// inline\n")
    comments = [t for t in toks if t.kind == COMMENT]
    assert [c.doc for c in comments] == [True, False, True, False, True]
    assert comments[0].ir_text == "// doc"
    assert comments[2].ir_text == "/* block doc */"
    assert [c.inline for c in comments] == [False, False, False, False, True]


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------

FULL = """\
/// File docs.
package demo @0x10;

import "other.sf";

const uint8 NAME_LEN = 16;
const string VERSION = "1.2";

enum Mode {
  IDLE = 0;
  ACTIVE = 1;
  extensions { FAILED = 5; }
}

struct Pos { f64 lat; double lon; }

message Status @1 [variable, envelope, magic = [0xA3, 0x7F]] {
  uint32 uptime = 1000;
  fixed_string<NAME_LEN> name = "dev";
  string<64> note;
  fbytes<4> raw;
  arr<u8, 8> fixed;
  vector<int16, 100> samples;
  vec<fstring<32>, 10> tags;
  Pos pos [flatten];
  Mode mode = Mode.ACTIVE;
  float t = -inf;
  enum Local { A = 0; }
  oneof cmd [discriminator = field_order, variable, min_size = 8] {
    Pos p;
    extensions { Mode m; }
  }
}

service Config {
  rpc get(Pos) -> Status;
  rpc reboot(Pos) [idempotent];
}
"""


def test_full_grammar_parses():
    tree, sink = parse(FULL)
    assert not sink.diagnostics, [d.render() for d in sink.diagnostics]
    assert tree.package.name == "demo" and tree.package.id.value == 16
    assert [i.path for i in tree.imports] == ["other.sf"]
    kinds = [type(d).__name__ for d in tree.decls]
    assert kinds == ["ConstDecl", "ConstDecl", "EnumDecl", "MessageDecl", "MessageDecl", "ServiceDecl"]
    status = tree.decls[4]
    assert status.kind == "message" and status.id.value == 1
    assert [a.name for a in status.attrs] == ["variable", "envelope", "magic"]
    fields = {m.name: m for m in status.members if isinstance(m, ast.FieldDecl)}
    tags = fields["tags"].type
    assert (tags.container, tags.spelled, tags.element.container, tags.size.value) == \
        ("vector", "vec", "fixed_string", 10)
    assert fields["fixed"].type.element.name == "u8"
    assert isinstance(fields["t"].default, ast.Neg)
    oneof = next(m for m in status.members if isinstance(m, ast.OneofDecl))
    assert [v.name for v in oneof.variants] == ["p"]
    assert [v.name for v in oneof.ext_variants] == ["m"]
    svc = tree.decls[5]
    assert svc.rpcs[0].response.name == "Status" and svc.rpcs[1].response is None


def test_keywords_are_valid_field_names():
    tree, sink = parse("package p;\nstruct S { uint8 message; uint8 extensions; uint8 rpc; u8 oneof; }\n")
    assert not sink.diagnostics
    assert [f.name for f in tree.decls[0].members] == ["message", "extensions", "rpc", "oneof"]


def test_closing_semicolon_is_tolerated():
    tree, sink = parse("package p;\nstruct S { u8 a; };\nenum E { A = 0; };\n")
    assert not sink.errors


@pytest.mark.parametrize("src,code", [
    ("struct S { u8 a }", "SF0202"),                       # missing ;
    ("message M { u8 a; }", "SF0307"),                     # message without id
    ("struct S @1 { u8 a; }", "SF0307"),                   # struct with id
    ("struct S { string s; }", "SF0320"),                  # string without capacity
    ("struct S { vector v; }", "SF0320"),                  # container without parameters
    ("enum E { A; }", "SF0306"),                           # implicit enum value
    ("struct S { message T { u8 a; } }", "SF0308"),       # nested message
    ("struct S { map<u8, u8> m; }", "SF0309"),
    ("struct S { u8 a = 1 [flatten]; }", "SF0310"),        # attribute after default
    ("struct S { oneof o { u8 a = 1; } }", "SF0405"),      # default on a variant
    ("struct S { vector<u8, <=5> v; }", "SF0201"),         # no <= form
])
def test_syntax_errors(src, code):
    _tree, sink = parse("package p;\n" + src + "\n")
    assert code in codes(sink), [d.render() for d in sink.diagnostics]


@pytest.mark.parametrize("src", [
    'syntax = "proto3";\npackage p;\n',
    "package p;\nmessage M {\n  option msgid = 1;\n  uint8 a = 1;\n}\n",
    "package p;\nstruct S { repeated uint8 a = 1; }\n",
    "package p;\noption pkgid = 3;\n",
])
def test_legacy_syntax_points_to_migrate(src):
    _tree, sink = parse(src)
    assert any("struct-frame migrate" in (d.hint or "") for d in sink.errors), \
        [d.render() for d in sink.diagnostics]


def test_legacy_detection_ignores_comments():
    assert gen.looks_like_legacy_syntax("package p;\nmessage M {\n option msgid = 1;\n}\n")
    assert not gen.looks_like_legacy_syntax(
        "package p;\n// option msgid = 1;\n/* repeated uint8 x */\nmessage M @1 {}\n")


def test_error_recovery_reports_several_errors():
    _tree, sink = parse("package p;\nstruct A { u8 a }\nstruct B { u8 b; u8 }\nstruct C { u8 c; }\n")
    assert len(sink.errors) == 2


def test_diagnostic_rendering_has_position_caret_and_hint():
    _tree, sink = parse("package p;\nstruct S {\n  string name;\n}\n")
    text = sink.errors[0].render()
    assert text.startswith("t.sf:3:3: error[SF0320]: 'string' needs a capacity")
    assert "    3 |   string name;" in text
    assert "^^^^^^" in text
    assert "hint: write string<N>" in text


def test_missing_semicolon_points_at_end_of_previous_token():
    _tree, sink = parse("package p;\nstruct S {\n  u8 a\n  u8 b;\n}\n")
    d = next(d for d in sink.errors if d.code == "SF0202")
    assert (d.line, d.col) == (3, 7)


# ---------------------------------------------------------------------------
# comment ownership
# ---------------------------------------------------------------------------

def test_doc_comment_ownership():
    tree, sink = parse(
        "/// file doc\n"
        "package p;\n"
        "/// leading of S\n"
        "// private: not documentation\n"
        "struct S {  /// trailing of S (header line)\n"
        "  /// leading of a\n"
        "  u8 a;  /// trailing of a\n"
        "  u8 b;\n"
        "  /// dangling\n"
        "}  /// trailing of S (closing line)\n")
    s = tree.decls[0]
    assert tree.file_docs() == ["// file doc"]
    assert s.comments.leading_docs() == ["// leading of S"]
    assert s.comments.trailing_docs() == ["// trailing of S (header line)",
                                          "// trailing of S (closing line)"]
    a, b = s.members
    assert a.comments.leading_docs() == ["// leading of a"]
    assert a.comments.trailing_docs() == ["// trailing of a"]
    assert b.comments.leading_docs() == []
    assert [d.code for d in sink.warnings] == ["SF0313"]   # the dangling doc comment


def test_doc_comment_before_import_warns():
    _tree, sink = parse('package p;\n/// nothing\nimport "x.sf";\n')
    assert "SF0312" in codes(sink)


# ---------------------------------------------------------------------------
# printer
# ---------------------------------------------------------------------------

def test_printer_round_trip_is_idempotent():
    tree, sink = parse(FULL)
    assert not sink.errors
    once = print_file(tree)
    tree2, sink2 = parse(once)
    assert not sink2.errors
    assert print_file(tree2) == once


def test_printer_keeps_every_comment():
    src = ("// header\n/// file doc\npackage p;\n\n// before S\n/// doc S\nstruct S {  // head\n"
           "  u8 a;  /// a\n  // tail of scope\n}  // after S\n// end of file\n")
    tree, _ = parse(src)
    out = print_file(tree)
    for text in ("// header", "/// file doc", "// before S", "/// doc S", "// head", "/// a",
                 "// tail of scope", "// after S", "// end of file"):
        assert text in out, text
    tree2, _ = parse(out)
    assert tree2.decls[0].comments.leading_docs() == tree.decls[0].comments.leading_docs()
    assert tree2.decls[0].members[0].comments.trailing_docs() == ["// a"]


def test_printer_type_spelling():
    tree, _ = parse("package p;\nstruct S { u8 a; uint16 b; vec<f32, 4> c; fixed_string<8> d; }\n")
    long_text = print_file(tree, types="long")
    assert "uint8 a;" in long_text and "vector<float, 4> c;" in long_text
    short_text = print_file(tree, types="short")
    assert "u16 b;" in short_text and "fstring<8> d;" in short_text
    assert "vec<f32, 4> c;" in print_file(tree)


@pytest.mark.parametrize("text", ["", "a\"b", "back\\slash", "line\nbreak", "\t\0", "\x01", "café"])
def test_quote_round_trips(text):
    toks, sink = lex(quote(text))
    assert not sink.diagnostics
    assert toks[0].value == text


# ---------------------------------------------------------------------------
# lowering (through the real generator)
# ---------------------------------------------------------------------------

def test_lowering_builds_the_model(tmp_path):
    ok, pkgs, out = model(tmp_path, """\
package demo @3;
const uint8 N = 4;
enum Mode { A = 0; B = 1; extensions { C = 7; } }
struct Inner { u16 x; }
message M @0x21 [variable] {
  u8 a = 200;
  fixed_string<N> name = "ab";
  vector<Inner, N> items;
  array<fbytes<2>, 3> blobs;
  Mode mode = B;
  f64 d = -1.5;
  extensions { u32 later = 0xFFFF; }
}
""")
    assert ok, out
    pkg = pkgs["demo"]
    assert pkg.package_id == 3 and pkg.consts["N"].value == 4
    assert pkg.enums["Mode"].extensions_start == 7
    m = pkg.messages["M"]
    assert m.id == 0x21 and m.variable and m.extensions_start == 7
    f = m.fields
    assert [x.number for x in f.values()] == list(range(1, 8))
    assert f["a"].field_type == "uint8" and f["a"].default == 200
    assert (f["name"].size_option, f["name"].default) == (4, "ab")
    assert (f["items"].is_array, f["items"].max_size, f["items"].field_type) == (True, 4, "Inner")
    assert (f["blobs"].size_option, f["blobs"].element_size, f["blobs"].field_type) == (3, 2, "bytes")
    assert f["mode"].default == "B" and f["mode"].default_numeric == 1
    assert f["d"].default == -1.5
    assert f["later"].is_extension and not f["a"].is_extension
    assert pkgs["demo"].messages["Inner"].id is None


def test_short_and_long_names_build_the_same_model(tmp_path):
    ok1, p1, _ = model(tmp_path, "package p;\nmessage M @1 { u8 a; i16 b; f32 c; f64 d; vec<u64, 3> e; }\n")
    ok2, p2, _ = model(tmp_path, "package p;\nmessage M @1 { uint8 a; int16 b; float c; double d; "
                                 "vector<uint64, 3> e; }\n")
    assert ok1 and ok2
    sig = lambda p: [(f.field_type, f.size, f.max_size) for f in p["p"].messages["M"].fields.values()]
    assert sig(p1) == sig(p2)
    assert p1["p"].messages["M"].magic_bytes == p2["p"].messages["M"].magic_bytes


@pytest.mark.parametrize("body,code", [
    ("message M @1 { u8 a = 300; }", "out of range"),            # validate()
    ("message M @1 { u8 a = \"x\"; }", "SF0404"),
    ("message M @1 { fixed_string<4> s = 5; }", "SF0404"),
    ("message M @1 { bool b = 1; }", "SF0404"),
    ("message M @1 [varible] { u8 a; }", "SF0330"),
    ("message M @1 [variable, variable] { u8 a; }", "SF0331"),
    ("message M @1 [magic = [0, 1]] { u8 a; }", "SF0335"),
    ("message M @1 { oneof o [discriminator = fieldorder] { u8 a; } }", "SF0334"),
    ("message M @1 { u8 a; u8 a; }", "SF0346"),
    ("message M @1 { oneof o { u8 a; } u8 b; }", "SF0348"),
    ("message M @1 { extensions { u8 a; } }", "SF0344"),
    ("message M @1 { u8 a; extensions { u8 b; } u8 c; }", "SF0347"),
    ("message M @1 { vector<u8, 0> a; }", "SF0403"),
    ("message M @1 { vector<string<4>, 2> a; }", "SF0322"),
    ("message M @1 { vector<array<u8, 2>, 2> a; }", "SF0321"),
    ("message M @1 { fixed_string<LEN> s; }", "SF0402"),
    ("enum E { A = 0; A = 1; }", "SF0340"),
    ("enum E { A = 0; B = 0; }", "SF0341"),
    ("enum E { A = 5; extensions { B = 3; } }", "SF0342"),
    ("const uint8 X = 300;", "SF0403"),
    ("const uint8 X = 1.5;", "SF0404"),
    ("const string X = 5;", "SF0404"),
    ("const uint8 X = 1;\nconst uint8 X = 2;", "SF0351"),
    ("service S { rpc a(M) -> M; }", "SF0390"),
    ("message M @70000 { u8 a; }", "SF0403"),
])
def test_lowering_errors(tmp_path, body, code):
    ok, _pkgs, out = model(tmp_path, "package p;\n" + body + "\n")
    assert not ok
    assert code in out, out


def test_package_id_out_of_range(tmp_path):
    ok, _p, out = model(tmp_path, "package p @256;\nmessage M @1 { u8 a; }\n")
    assert not ok and "SF0403" in out


def test_constants_from_imported_package(tmp_path):
    ok, pkgs, out = model(tmp_path,
                          'package app @2;\nimport "common.sf";\n'
                          'message M @1 { fixed_string<common.NAME_LEN> name; }\n',
                          extra={"common.sf": "package common @1;\nconst u16 NAME_LEN = 12;\n"})
    assert ok, out
    assert pkgs["app"].messages["M"].fields["name"].size_option == 12


def test_special_float_defaults(tmp_path):
    ok, pkgs, out = model(tmp_path, "package p;\nmessage M @1 { f32 a = inf; f64 b = -inf; f64 c = nan; f32 d = 3; }\n")
    assert ok, out
    f = pkgs["p"].messages["M"].fields
    assert f["a"].default == math.inf and f["b"].default == -math.inf
    assert math.isnan(f["c"].default) and f["d"].default == 3.0


def test_string_escape_in_default_reaches_model(tmp_path):
    ok, pkgs, out = model(tmp_path, 'package p;\nmessage M @1 { string<8> s = "a\\tb"; }\n')
    assert ok, out
    assert pkgs["p"].messages["M"].fields["s"].default == "a\tb"


def test_docs_reach_the_model(tmp_path):
    ok, pkgs, out = model(tmp_path, "/// File.\npackage p;\n/// Leading.\nmessage M @1 {  /// Trailing.\n"
                                    "  // private\n  u8 a;  /// Field.\n}\n")
    assert ok, out
    m = pkgs["p"].messages["M"]
    assert m.comments == ["// Leading.", "// Trailing."]
    assert m.fields["a"].comments == ["// Field."]
    assert list(pkgs["p"].file_docs.values()) == [["// File."]]
